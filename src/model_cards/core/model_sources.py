"""Source bundle for one model target, in the composer's replayable tool_output layout.

collect_model_bundle(target, out_dir) writes <out_dir>/<slug>/tool_output/{hf,docling,
github,eee,paper_resolver}/... exactly the way the Benchmark Card pipeline writes a run
dir, so the composer's --source-bundle replay reads a model bundle with no new format:
  hf/<slug>.json            model_info at the pinned revision + README + config.json
  paper_resolver/paper-verification.json   the paper binding and its tier
  docling/<slug>.json       the paper text (docling), when a paper was bound
  github/<slug>.json        the developer's README, when a repo is named
  html/<slug>.json          README-linked developer pages (blog, system card, report page)
  extras/<slug>.json        safetensors bytes, README frontmatter, BibTeX blocks
  eee/<slug>.json           Every Eval Ever records by exact model_id join, with tier
  source_bundle/            the hashed README/config snapshot (records.SourceBundle)
  _paper_cache/<arxiv>.json docling text, shared by every target that binds that paper

Paper policy: a derivative repo usually carries the BASE model's
arXiv tag, and Hub tags are sometimes plain wrong (Qwen3-8B tags the YaRN paper,
gemma-3 tags HellaSwag, Llama-3.1 tags a carbon-footprint paper). The binding tier
says whether the tagged paper introduces THIS model (every distinctive name token in
the title or abstract), references its family (a family token of the model or of its
declared base), or is an unrelated tag (no family token at all: dropped, never read).
The frame and the tech_report field read that tier, the composer never guesses.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .eee_join import find_eee_records
from .frontmatter import parse_frontmatter
from .source import HfModelSourceAdapter, ModelSourceError, split_target

logger = logging.getLogger(__name__)

_ARXIV_TAG_RE = re.compile(r"^arxiv:(\d{4}\.\d{4,5})(?:v\d+)?$", re.IGNORECASE)
_ARXIV_URL_RE = re.compile(r"https?://arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?")
# BibTeX carries the id where no URL does: eprint = {2501.00656}, arXiv:2501.00656,
# journal={arXiv preprint arXiv:2501.00656}, archivePrefix/primaryClass blocks.
_ARXIV_BIB_RE = re.compile(r"(?:eprint\s*=\s*[{\"']|arxiv[:\s]+)(\d{4}\.\d{4,5})(?:v\d+)?",
                           re.IGNORECASE)
_BIBTEX_BLOCK_RE = re.compile(r"@[a-zA-Z]+\s*\{.*?\n\}", re.DOTALL)
_URL_RE = re.compile(r"https?://[^\s<>\)\]\"'`]+")
# A README links dozens of pages. Only a page that announces or documents THIS model is
# a source: the developer's blog post, a system or safety card, a technical-report page.
_HTML_PATH_HINTS = ("blog", "system-card", "systemcard", "system_card", "safety-card",
                    "tech-report", "technical-report", "techreport", "announcing",
                    "introducing", "release", "news", "research", "model-card", "post")
_HTML_SKIP_NETLOCS = ("huggingface.co", "github.com", "arxiv.org", "raw.githubusercontent.com",
                      "colab.research.google.com", "x.com", "twitter.com", "discord.gg",
                      "discord.com", "youtube.com", "youtu.be", "pypi.org", "wandb.ai",
                      "opensource.org", "creativecommons.org", "apache.org", "llama.com",
                      "linkedin.com", "reddit.com", "medium.com")
MAX_HTML_PAGES = 3
_NAME_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_GENERIC_NAME_TOKENS = {"base", "instruct", "chat", "hf", "it", "model", "preview", "sft", "dpo",
                        "rl", "v1", "v2", "v3", "mini", "small", "large", "medium"}


def slug_for(target: str) -> str:
    """The bundle slug for model_id@revision, in the composer's own sanitized form so
    the replay reader (which keys files on sanitize_benchmark_name(query)) finds them
    when the composer is run with this slug as its query."""
    from auto_benchmarkcard.output import sanitize_benchmark_name
    model_id, revision = split_target(target)
    return sanitize_benchmark_name(f"{model_id}-{revision[:12]}")


def _write(out: Path, tool: str, filename: str, payload: Any) -> Path:
    d = out / "tool_output" / tool
    d.mkdir(parents=True, exist_ok=True)
    p = d / filename
    p.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return p


def distinctive_name_tokens(model_id: str) -> set:
    """Tokens of the repo name that can identify the model in a paper title: the
    alphabetic family tokens (olmo, qwen, gemma), not sizes, stages, or versions."""
    name = model_id.rsplit("/", 1)[-1].lower()
    out = set()
    for tok in _NAME_SPLIT_RE.split(name):
        if len(tok) >= 3 and not tok.isdigit() and tok not in _GENERIC_NAME_TOKENS \
                and not re.fullmatch(r"\d+[bm]", tok):
            out.add(tok)
    return out


_DIGIT_RE = re.compile(r"\d")
_VERSION_TOKEN_RE = re.compile(r"\d+(?:\.\d+)*")
_SIZE_TOKEN_RE_SRC = re.compile(r"\d+(?:\.\d+)?[bm]")


def name_discriminators(model_id: str) -> set:
    """The family-plus-version forms that name THIS checkpoint, not its whole family.

    "gemma 3" for gemma-3-4b-pt, "llama 3.1" and "llama 3" for Llama-3.1-8B (the herd
    paper introduces it under the shorter form). Empty when the repo name has no version
    next to its family token, in which case the family token has to carry the weight.
    """

    name = model_id.rsplit("/", 1)[-1].lower()
    parts = [p for p in _NAME_SPLIT_RE.split(name) if p]
    families = distinctive_name_tokens(model_id)
    out: set = set()
    for index, part in enumerate(parts[:-1]):
        if part not in families:
            continue
        nxt = parts[index + 1]
        forms = set()
        if _VERSION_TOKEN_RE.fullmatch(nxt) or _SIZE_TOKEN_RE_SRC.fullmatch(nxt):
            forms.add(nxt)
            if "." in nxt:
                forms.add(nxt.split(".", 1)[0])
        for form in forms:
            out |= {f"{part} {form}", f"{part}-{form}", f"{part}{form}"}
    return out


def _token_present(tok: str, text: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(tok) + r"(?![a-z0-9])", text))


PAPER_FETCH_RETRIES = 3
PAPER_FETCH_BACKOFF_S = 4.0


def paper_binding_tier(model_id: str, title: str, abstract: str,
                       base_model_ids: Optional[list] = None) -> str:
    """introduces_target: the repo name is in the abstract, or every distinctive name
    token is in the title or abstract ("Qwen3 Technical Report" for Qwen3-8B-Base).
    family_reference: some family token of the model or of a declared base model is
    there ("The Llama 3 Herd of Models" for Llama-3.1-Tulu-3-8B). unrelated_tag:
    no family token anywhere (YaRN on Qwen3-8B, HellaSwag on gemma-3): dropped."""
    tokens = distinctive_name_tokens(model_id)
    text = ((title or "") + " " + (abstract or "")).lower()
    low_abs = (abstract or "").lower()
    repo_name = model_id.rsplit("/", 1)[-1].lower()
    if repo_name and repo_name in low_abs.replace(" ", "-"):
        return "introduces_target"
    if tokens and all(_token_present(tok, text) for tok in tokens):
        # A bare family token is not identification. The IndicGenBench abstract reads
        # "we evaluate ... mt5, gemma, bloom and llama", and that single word "gemma"
        # made a benchmark paper the technical report of google/gemma-3-4b-pt and
        # meta-llama/Llama-3.1-8B (seen 2026-09-05). When the family token carries no
        # version of its own, the paper has to name the version too.
        if any(_DIGIT_RE.search(tok) for tok in tokens):
            return "introduces_target"
        discriminators = name_discriminators(model_id)
        if not discriminators or any(form in text for form in discriminators):
            return "introduces_target"
    family_tokens = set(tokens)
    for base in base_model_ids or []:
        if isinstance(base, str) and "/" in base:
            family_tokens |= distinctive_name_tokens(base)
    if any(_token_present(tok, text) for tok in family_tokens):
        return "family_reference"
    return "unrelated_tag"


# The paper search, ported from the benchmark resolver (tools/eee/paper_resolver:
# _search_openalex, _search_semantic_scholar and their normalizers). It runs only when
# the repo's own arXiv ids and its base model's produced no paper that introduces this
# checkpoint, because 63 of the 103 flagship targets of 2026-09-06 have a real report
# that no tag points to. Nothing it returns reaches a card without the same title gate
# the tags pass, plus the two rules below, which a tag does not need:
#   the family token must stand alone in the TITLE ("Yi: Open Foundation Models" yes,
#   "LLaMA-Adapter" no, because there the family name is part of another artifact's name);
#   a generation stated in the title must be this checkpoint's ("Llama 2: Open Foundation
#   and Fine-Tuned Chat Models" is not the Llama 3.2 report).
PAPER_SEARCH_QUERIES = 3
PAPER_SEARCH_CANDIDATES = 6
_TITLE_TOKEN_RE_CACHE: Dict[str, Any] = {}


def paper_search_enabled() -> bool:
    """Off unless MODELCARDS_PAPER_SEARCH is set, so a collect never reaches OpenAlex or
    Semantic Scholar by accident."""
    return os.environ.get("MODELCARDS_PAPER_SEARCH", "").strip() not in ("", "0", "false", "no")


def search_queries_for_model(model_id: str, base_model_ids: Optional[list] = None) -> list:
    """The queries the search runs, most specific first: the family and its generation,
    the way a report titles itself."""
    from .model_frame import family_name

    queries: list = []
    fam = family_name(model_id)
    if fam:
        queries.append(f"{fam} technical report")
        queries.append(f"{fam} language model")
    for base in base_model_ids or []:
        if not isinstance(base, str) or "/" not in base:
            continue
        bfam = family_name(base)
        if bfam and bfam.lower() != (fam or "").lower():
            queries.append(f"{bfam} technical report")
    seen, unique = set(), []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique.append(q)
    return unique[:PAPER_SEARCH_QUERIES]


# What may stand in front of a family token in a title. Anything else is part of another
# model's name: "Code Llama" is not the Llama report, and "Lawyer LLaMA" is not either.
# Determiners and announcement verbs only. A preposition in front of the family name is
# the signature of a paper ABOUT the model rather than its report: "Model Inversion
# Attacks on Llama 3: Extracting PII from Large Language Models" was tiered
# introduces_target for meta-llama/Meta-Llama-3-8B in the live check of 2026-09-07,
# because its abstract names the checkpoint.
_TITLE_LEAD_WORDS = frozenset({"the", "a", "an", "introducing", "presenting", "announcing"})
# token, then optionally the generation it carries ("-3.1", " 3", ".5", "-V3"), then the
# name has to END: the next character may not continue it. "DeepSeek-V3 Technical Report"
# ends; "Llama-3.1-FoundationAI-SecurityLLM-Reasoning-8B Technical Report" does not, and
# it was tiered introduces_target for meta-llama/Llama-3.2-3B in the live check of
# 2026-09-07. A size is not a generation ("Mistral 7B").
_TITLE_VERSION = r"(?:[.\-\s]?v?(\d+(?:\.\d+)*)(?![bm\d]))?"


def _title_name_match(title_low: str, token: str, name_tokens: Optional[set] = None):
    """The match of a family token standing on its own in a title, or None.

    A hyphenated continuation after the generation names a different member of the family
    ("Qwen2.5-1M Technical Report" is not Qwen2.5-32B-Instruct's) unless the checkpoint's
    own name carries that same word ("Qwen2.5-Math Technical Report" is Qwen2.5-Math-7B's).
    """
    for m in re.finditer(re.escape(token) + _TITLE_VERSION, title_low):
        before = title_low[:m.start()]
        if re.search(r"[a-z0-9-]$", before):
            continue
        lead = re.findall(r"[a-z]+", before)
        if lead and lead[-1] not in _TITLE_LEAD_WORDS:
            continue
        rest = title_low[m.end():]
        if re.match(r"[a-z0-9]", rest):
            continue
        continuation = re.match(r"-([a-z0-9]+)", rest)
        if continuation and continuation.group(1) not in (name_tokens or set()):
            continue
        return m
    return None


def family_generation(model_id: str, token: str) -> Optional[str]:
    """The generation the repo name puts next to its family token: "3.1" of
    Meta-Llama-3.1-8B, "2.5" of qwen2.5-0.5b-sft-mdpo, "3" of DeepSeek-V3, None for
    Mistral-7B-v0.3 and gemma-7b, whose names carry a size and a point release but no
    generation. family_version answers for the name as a whole and stops at the first
    name token, which is "meta" on a meta-llama repo."""
    toks = [t.strip(".") for t in re.split(r"[^a-z0-9.]+", model_id.rsplit("/", 1)[-1].lower())
            if t.strip(".")]
    glued = re.search(r"(\d+)$", token)
    for index, tok in enumerate(toks):
        if not tok.startswith(token):
            continue
        rest = tok[len(token):]
        if rest:
            if not re.fullmatch(r"\.?\d+(?:\.\d+)*", rest):
                continue
            return ".".join(p for p in (glued.group(1) if glued else "", rest.lstrip("."))
                            if p) or None
        if index + 1 < len(toks):
            nxt = toks[index + 1]
            m = re.fullmatch(r"v?(\d+(?:\.\d+)*)", nxt)
            if m and not _SIZE_RE.match(nxt):
                return m.group(1)
        return glued.group(1) if glued else None
    return None


def _version_parts(version: Optional[str]) -> list:
    return [p for p in (version or "").split(".") if p]


def _title_generation(title_low: str, token: str) -> Optional[str]:
    """The generation a title states right after a family token: "3" in "The Llama 3 Herd
    of Models". A size ("Mistral 7B") is not a generation."""
    m = _title_name_match(title_low, token)
    return m.group(1) if m else None


def head_family_token(model_id: str) -> Optional[str]:
    """The token that can name the family in a title: "qwen2" of qwen2.5-0.5b-sft-mdpo,
    "llama" of Llama_3.2_3b_Kermes_v2.1 and of Meta-Llama-3.1-8B. A tail token names the
    method or the merge ("mDPO: Conditional Preference Optimization" is not the technical
    report of a Qwen fine-tune), and a leading vendor token is not the family either:
    with "meta" as the family of Meta-Llama-3.1-8B, a survey titled "Evolution of meta's
    llama models" was bound to it in the live check of 2026-09-07.

    The family token is the one the repo name puts its generation next to; failing that,
    the first distinctive token.
    """
    distinctive = distinctive_name_tokens(model_id)
    parts = [t for t in _NAME_SPLIT_RE.split(model_id.rsplit("/", 1)[-1].lower()) if t]
    for index, tok in enumerate(parts[:-1]):
        nxt = parts[index + 1]
        if tok in distinctive and (_VERSION_TOKEN_RE.fullmatch(nxt)
                                   or _SIZE_TOKEN_RE_SRC.fullmatch(nxt)):
            return tok
    for tok in parts:
        if tok in distinctive:
            return tok
    return None


def search_title_gate(model_id: str, title: str, base_model_ids: Optional[list] = None) -> bool:
    """Whether a searched paper's title may be bound to this checkpoint at all."""
    title_low = (title or "").lower()
    if not title_low:
        return False
    families = set()
    for owner in [model_id, *[b for b in (base_model_ids or []) if isinstance(b, str) and "/" in b]]:
        token = head_family_token(owner)
        if token:
            families.add((owner, token))
    for owner, token in families:
        # the family token has to name the title's own subject: standing on its own,
        # not inside another model's name ("LLaMA-Adapter", "Qwen-VL", "Code Llama",
        # "Llama-3.1-FoundationAI-SecurityLLM-8B"), and not behind another name word.
        own_tokens = {t for t in _NAME_SPLIT_RE.split(owner.rsplit("/", 1)[-1].lower()) if t}
        match = _title_name_match(title_low, token, own_tokens)
        if match is None:
            continue
        # the generation may be glued to the token ("qwen2") and continue after it
        # (".5"), and both halves are one version
        glued = re.search(r"(\d+)$", token)
        stated = _version_parts(".".join(filter(None, [glued.group(1) if glued else "",
                                                       match.group(1) or ""])))
        mine = _version_parts(family_generation(owner, token))
        # the generation the title states must be this checkpoint's, or an earlier part
        # of it: "The Llama 3 Herd of Models" for Llama-3.2, never "Llama 2" and never
        # the later "Qwen2.5" report for a Qwen2 checkpoint. A title that states one for
        # a checkpoint whose name states none is a different generation of it.
        if stated and (not mine or mine[:len(stated)] != stated):
            continue
        # and the mirror: a checkpoint whose name carries a generation needs the title to
        # say which one. "LLaMA: Open and Efficient Foundation Language Models" is not
        # meta-llama/Llama-3.1-8B's report, and the v1 Gemma paper is not gemma-3's.
        if mine and not stated:
            continue
        return True
    return False


def search_paper_candidates(model_id: str, base_model_ids: Optional[list] = None,
                            search_fns=None) -> list:
    """arXiv candidates from OpenAlex and Semantic Scholar, title-gated before any fetch.

    Returns [{"arxiv_id", "origin", "title", "query"}], best first, at most
    PAPER_SEARCH_CANDIDATES. search_fns is [(origin, search, normalize)]; tests inject it.
    """
    if search_fns is None:
        from auto_benchmarkcard.tools.eee.paper_resolver import (
            _normalize_openalex_paper, _normalize_s2_paper, _search_openalex,
            _search_semantic_scholar,
        )
        search_fns = [("openalex_search", _search_openalex, _normalize_openalex_paper),
                      ("s2_search", _search_semantic_scholar, _normalize_s2_paper)]
    out: list = []
    seen: set = set()
    # sources outer, queries inner: Semantic Scholar without a key sleeps a second per
    # request and answers 429 under load, and a collect that walks both sources for every
    # query ran past its 900 s timeout on the first two targets of the 2026-09-07
    # re-collect. The second source is only asked when the first found nothing.
    for origin, search, normalize in search_fns:
        for query in search_queries_for_model(model_id, base_model_ids):
            try:
                results = search(query) or []
            except Exception as exc:  # a search must never lose a bundle
                logger.warning("paper search %s failed for %r: %s", origin, query, exc)
                continue
            for raw in results:
                try:
                    paper = normalize(raw) or {}
                except Exception:
                    continue
                arxiv_id = str(paper.get("arxiv_id") or "").strip()
                m = re.match(r"^(\d{4}\.\d{4,5})(?:v\d+)?$", arxiv_id)
                if not m or m.group(1) in seen:
                    continue
                if not search_title_gate(model_id, paper.get("title") or "", base_model_ids):
                    continue
                seen.add(m.group(1))
                out.append({"arxiv_id": m.group(1), "origin": origin,
                            "title": paper.get("title") or "", "query": query})
                if len(out) >= PAPER_SEARCH_CANDIDATES:
                    return out
        if out:
            break
    return out


_VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+)?)$")
_SIZE_RE = re.compile(r"^\d+(?:\.\d+)?[bm]$")


def family_version(name: str) -> Optional[str]:
    """The generation marker next to the family token: "3" for Qwen3-8B, "3.1" for
    Llama-3.1-8B, "3" for DeepSeek-V3-Base, "2" for OLMo-2-1124-7B, None for
    mistral-inference or llama-models."""
    toks = [t.strip(".") for t in re.split(r"[^a-z0-9.]+", (name or "").lower()) if t.strip(".")]
    for i, tok in enumerate(toks):
        if tok.isdigit() or _SIZE_RE.match(tok) or tok in _GENERIC_NAME_TOKENS or len(tok) < 3:
            continue
        m = re.match(r"^([a-z]+)(\d+(?:\.\d+)?)$", tok)
        if m:
            return m.group(2)
        if i + 1 < len(toks):
            nxt = toks[i + 1]
            m2 = _VERSION_RE.match(nxt)
            if m2 and not _SIZE_RE.match(nxt) and not (nxt.isdigit() and len(nxt) >= 4):
                return m2.group(1)
        return None
    return None


_GITHUB_ALL_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.IGNORECASE)


def github_repo_is_own(model_id: str, repo_url: str) -> bool:
    """The repo is THIS model's code: its name carries a family token of the model
    (QwenLM/Qwen3, meta-llama/llama-models, allenai/OLMo-core), and when both the
    model and the repo name carry a generation marker they agree (deepseek-ai/
    DeepSeek-V2 is not DeepSeek-V3's repo). huggingface/transformers, an own-org
    dataset repo (google-research-datasets/natural-questions) and a sibling
    generation's repo are all rejected."""
    m = _GITHUB_ALL_RE.search(repo_url or "")
    if not m:
        return False
    repo = m.group(2).lower().removesuffix(".git")
    tokens = distinctive_name_tokens(model_id)
    family = {re.sub(r"\d+$", "", tok) for tok in tokens} | tokens
    if not any(tok in repo for tok in family if len(tok) >= 3):
        return False
    target_version = family_version(model_id.rsplit("/", 1)[-1])
    repo_version = family_version(repo)
    if target_version and repo_version and target_version.split(".")[0] != repo_version.split(".")[0]:
        return False
    return True


def own_github_candidates(model_id: str, *texts: Any) -> list:
    """Every github.com/owner/repo mentioned in the texts (structured links first,
    README prose after), deduplicated in order, filtered by github_repo_is_own and
    ranked by how many of the model's name tokens the repo name carries."""
    seen = []
    for src in texts:
        if not isinstance(src, str) or "github.com" not in src.lower():
            continue
        for m in _GITHUB_ALL_RE.finditer(src):
            owner, repo = m.group(1), m.group(2).rstrip(".,;:)]\"'").removesuffix(".git")
            url = f"https://github.com/{owner}/{repo}"
            if url.lower() not in [u.lower() for u in seen] and github_repo_is_own(model_id, url):
                seen.append(url)
    name_tokens = [t for t in _NAME_SPLIT_RE.split(model_id.rsplit("/", 1)[-1].lower()) if t]

    def score(url):
        repo = url.rsplit("/", 1)[-1].lower()
        # most name tokens first; on a tie the shorter repo name (Qwen3 over Qwen3-Coder)
        return (-sum(1 for t in name_tokens if t in repo), len(repo))

    return sorted(seen, key=score)


def readme_bibtex_blocks(readme: str) -> list:
    """The BibTeX entries in a README, in order. A model card's citation block is often
    the only place its paper is named at all."""
    return [m.group(0) for m in _BIBTEX_BLOCK_RE.finditer(readme or "")]


def arxiv_candidates(hf_meta: Dict[str, Any]) -> list:
    """Every arXiv id the repo offers, in decreasing order of authority:
    the repo's own arxiv: tag, then ids inside the README's BibTeX blocks, then the
    remaining arXiv links in README prose. Each carries where it came from, because a
    tag can be plain wrong (Qwen3-8B tags YaRN) while the BibTeX right below it is
    correct. Deduplicated on the id, first source wins."""
    out: list = []
    seen: set = set()

    def add(arxiv_id: str, origin: str) -> None:
        if arxiv_id and arxiv_id not in seen:
            seen.add(arxiv_id)
            out.append({"arxiv_id": arxiv_id, "from": origin})

    for tag in hf_meta.get("tags") or []:
        m = _ARXIV_TAG_RE.match(str(tag))
        if m:
            add(m.group(1), "hf_arxiv_tag")
    readme = hf_meta.get("readme_markdown") or ""
    for block in readme_bibtex_blocks(readme):
        for m in _ARXIV_URL_RE.finditer(block):
            add(m.group(1), "readme_bibtex")
        for m in _ARXIV_BIB_RE.finditer(block):
            add(m.group(1), "readme_bibtex")
    for m in _ARXIV_URL_RE.finditer(readme):
        add(m.group(1), "readme_link")
    return out


def _netloc(url: str) -> str:
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def own_domain_tokens(model_id: str, hf_meta: Dict[str, Any]) -> set:
    """Host name fragments that mark a page as the developer's own: the Hub org and
    the model's family tokens (allenai -> allenai.org, Qwen -> qwenlm.github.io)."""
    tokens = {t for t in distinctive_name_tokens(model_id) if len(t) >= 4}
    author = str(hf_meta.get("author") or "").lower()
    org = model_id.split("/", 1)[0].lower()
    for name in (author, org):
        cleaned = re.sub(r"[^a-z0-9]", "", name)
        if len(cleaned) >= 4:
            tokens.add(cleaned)
    return tokens


def readme_html_candidates(model_id: str, hf_meta: Dict[str, Any], limit: int = MAX_HTML_PAGES) -> list:
    """README-linked pages worth reading as sources: a blog post, a system or safety
    card, a technical-report page. A link qualifies when its host or path carries a
    family or organization token AND its path looks like a document rather than a
    product page. Hubs, code hosts, social links and license texts never qualify."""
    readme = hf_meta.get("readme_markdown") or ""
    own = own_domain_tokens(model_id, hf_meta)
    out: list = []
    seen: set = set()
    for m in _URL_RE.finditer(readme):
        url = m.group(0).rstrip(".,;:!?)\"'")
        if url.lower() in seen:
            continue
        host = _netloc(url)
        if not host or any(host == d or host.endswith("." + d) for d in _HTML_SKIP_NETLOCS):
            continue
        if url.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip", ".json")):
            continue
        path = url.split("://", 1)[-1].split("/", 1)[-1].lower() if "/" in url.split("://", 1)[-1] else ""
        hay = (host + "/" + path).replace("_", "-")
        if not any(tok in hay for tok in own):
            continue
        if not any(hint in hay for hint in _HTML_PATH_HINTS):
            continue
        seen.add(url.lower())
        out.append(url)
        if len(out) >= limit:
            break
    return out


_SHARD_RE = re.compile(r"model-\d+-of-\d+\.safetensors")


def safetensors_bytes(model_id: str, revision: str) -> Optional[int]:
    """Total bytes of the revision's *.safetensors files, for specifications.model_size.
    The Hub only returns file sizes when they are asked for, so this is one extra call.
    Returns None when the sizes are not available (a gated or GGUF-only repo)."""
    try:
        from huggingface_hub import HfApi

        info = HfApi().model_info(model_id, revision=revision, files_metadata=True)
    except Exception as exc:
        logger.info("no file metadata for %s@%s: %s", model_id, revision[:12], str(exc)[:120])
        return None
    shards: dict[str, int] = {}
    single: dict[str, int] = {}
    other: dict[str, int] = {}
    for sib in getattr(info, "siblings", None) or []:
        name = getattr(sib, "rfilename", "") or ""
        size = getattr(sib, "size", None)
        if not name.endswith(".safetensors") or not isinstance(size, int):
            continue
        base = name.rsplit("/", 1)[-1]
        if _SHARD_RE.fullmatch(base):
            shards[name] = size
        elif base == "model.safetensors":
            single[name] = size
        else:
            other[name] = size
    # A repo often ships the SAME weights twice: mistralai/Mistral-7B-v0.3 carries
    # consolidated.safetensors next to model-0000n-of-00003.safetensors, and summing both
    # published 27.0 GiB for a 7B model in BF16, exactly double (seen 2026-09-05). One
    # packaging is the model; pick it, never add two complete copies together.
    group = shards or single or other
    return sum(group.values()) or None


def arxiv_id_from_hf(hf_meta: Dict[str, Any]) -> Optional[str]:
    """The arXiv id from the repo's tags, else the first arXiv URL in the README."""
    for tag in hf_meta.get("tags") or []:
        m = _ARXIV_TAG_RE.match(str(tag))
        if m:
            return m.group(1)
    m = _ARXIV_URL_RE.search(hf_meta.get("readme_markdown") or "")
    return m.group(1) if m else None


def collect_model_bundle(target: str, out_dir: str | Path, *, hf_metadata=None,
                         paper_meta=None, docling=None, github=None, html=None,
                         eee_datastore: Optional[str] = None,
                         allow_network: bool = True,
                         paper_search: Optional[bool] = None, search_fns=None) -> Dict[str, Any]:
    """Write the bundle for target under out_dir/<slug>/ and return a manifest dict.

    The five fetchers default to the composer's own tools (hf_model_metadata, the
    resolver's arXiv metadata lookup, extract_paper_with_docling, fetch_github_readme,
    extract_html_content); tests inject fakes. Nothing here composes a card.

    The manifest names every channel and, for every channel that produced nothing, why:
    manifest["absent_channels"] lists them, and each entry carries its own reason.
    """
    model_id, revision = split_target(target)
    slug = slug_for(target)
    out = Path(out_dir) / slug
    manifest: Dict[str, Any] = {"target": target, "slug": slug, "channels": {}}

    if hf_metadata is None:
        from auto_benchmarkcard.tools.hf.hf_tool import hf_model_metadata
        hf_metadata = lambda mid, rev: hf_model_metadata.func(mid, revision=rev)  # noqa: E731
    hf_meta = hf_metadata(model_id, revision)
    _write(out, "hf", f"{slug}.json", hf_meta)
    manifest["channels"]["hf"] = {"resolved_revision": hf_meta.get("resolved_revision"),
                                  "base_model_tags": hf_meta.get("base_model_tags"),
                                  "has_model_index": bool(hf_meta.get("model_index"))}

    # frozen README/config snapshot with hashes, for the ledger
    try:
        adapter = HfModelSourceAdapter(allow_network=allow_network)
        bundle = adapter.collect(target, model_info={k: hf_meta.get(k) for k in (
            "tags", "downloads", "likes", "license", "pipeline_tag", "library_name",
            "base_model_tags", "model_index", "safetensors", "resolved_revision", "gated")})
        (out / "source_bundle").mkdir(parents=True, exist_ok=True)
        (out / "source_bundle" / "source-bundle.json").write_text(
            bundle.model_dump_json(indent=2), encoding="utf-8")
        manifest["channels"]["source_bundle"] = {"resolved_revision": bundle.target.resolved_revision,
                                                 "files": [f.name for f in bundle.files]}
    except ModelSourceError as exc:
        manifest["channels"]["source_bundle"] = {"error": str(exc)[:200]}

    # extras the structured channel needs and model_info does not carry: the bytes on
    # disk (specifications.model_size) and the README frontmatter (card_data comes back
    # empty for model repos, so the model-index lives only in the frontmatter).
    extras: Dict[str, Any] = {"model_id": model_id, "revision": revision}
    st_bytes = safetensors_bytes(model_id, revision) if allow_network else None
    extras["safetensors_bytes"] = st_bytes
    front = parse_frontmatter(hf_meta.get("readme_markdown") or "")
    extras["readme_frontmatter"] = front
    if not hf_meta.get("model_index") and front.get("model-index"):
        extras["model_index_from_frontmatter"] = front["model-index"]
    extras["bibtex_blocks"] = readme_bibtex_blocks(hf_meta.get("readme_markdown") or "")
    _write(out, "extras", f"{slug}.json", extras)
    manifest["channels"]["extras"] = {
        "safetensors_bytes": st_bytes,
        "safetensors_bytes_reason": None if st_bytes else "no file sizes at this revision",
        "frontmatter_keys": sorted(front) if front else [],
        "model_index": "model_info" if hf_meta.get("model_index") else
                       ("readme_frontmatter" if front.get("model-index") else None),
        "bibtex_blocks": len(extras["bibtex_blocks"]),
    }

    # paper: every arXiv id the repo offers (own tag, README BibTeX, README links), each
    # behind the title gate, best tier wins; then the declared base model's tag. An
    # unrelated tag is dropped unread. Every candidate that was tried is recorded.
    sidecar: Dict[str, Any] = {"model_id": model_id, "resolved_url": None, "resolved_from": None,
                               "binding": {"tier": "none", "verdict": "no_paper"}}
    stale_docling = out / "tool_output" / "docling" / f"{slug}.json"
    if stale_docling.is_file():
        stale_docling.unlink()
    if paper_meta is None:
        from auto_benchmarkcard.tools.eee.paper_resolver import _fetch_paper_meta_for_verify
        paper_meta = _fetch_paper_meta_for_verify
    bases = [str(t).split(":")[-1] for t in hf_meta.get("base_model_tags") or []]
    bases = list(dict.fromkeys(b for b in bases if "/" in b))

    def _evaluate(arxiv_id: str, origin: str, via_base: Optional[str] = None) -> Dict[str, Any]:
        url = f"https://arxiv.org/abs/{arxiv_id}"
        meta = paper_meta(url) or {}
        # arXiv rate-limits a concurrent collect; a failed fetch has no title, and an
        # empty title tiered as unrelated_tag silently dropped the paper channel from
        # 126 of 247 bundles (2026-09-06). Retry with a pause, and when it still fails
        # say so instead of pretending the paper was read.
        attempt = 0
        while meta.get("fetch_error") and attempt < PAPER_FETCH_RETRIES:
            attempt += 1
            time.sleep(PAPER_FETCH_BACKOFF_S * (2 ** (attempt - 1)))
            meta = paper_meta(url) or {}
        if meta.get("fetch_error"):
            return {"arxiv_id": arxiv_id, "from": origin, "tier": "fetch_failed",
                    "paper_url": url, "paper_title": "", "fetch_error": True,
                    **({"via_base_model": via_base} if via_base else {})}
        tier = paper_binding_tier(model_id, meta.get("title", ""), meta.get("abstract", ""), bases)
        row: Dict[str, Any] = {"arxiv_id": arxiv_id, "from": origin, "tier": tier,
                               "paper_url": url, "paper_title": meta.get("title", ""),
                               "fetch_error": False}
        if via_base:
            row["via_base_model"] = via_base
        return row

    tried: list = []
    for cand in arxiv_candidates(hf_meta):
        tried.append(_evaluate(cand["arxiv_id"], cand["from"]))
        if tried[-1]["tier"] == "introduces_target":
            break
    seen_ids = {r["arxiv_id"] for r in tried if "arxiv_id" in r}
    if not any(r["tier"] == "introduces_target" for r in tried):
        for base_id in bases:
            try:
                base_meta = hf_metadata(base_id, "main") or {}
            except Exception as exc:
                tried.append({"base": base_id, "error": str(exc)[:120], "tier": "lookup_failed"})
                continue
            for cand in arxiv_candidates(base_meta):
                if cand["arxiv_id"] in seen_ids:
                    continue
                seen_ids.add(cand["arxiv_id"])
                tried.append(_evaluate(cand["arxiv_id"], f"base_model:{cand['from']}", base_id))
                if tried[-1]["tier"] == "introduces_target":
                    break
            if any(r.get("tier") == "introduces_target" for r in tried):
                break

    # third source: the literature search, on the same title gate plus the two rules a
    # search hit has to pass that a tag does not (search_title_gate). It runs only when
    # nothing the repo itself points at introduces this checkpoint.
    if paper_search is None:
        paper_search = paper_search_enabled()
    if paper_search and not any(r.get("tier") == "introduces_target" for r in tried):
        for cand in search_paper_candidates(model_id, bases, search_fns=search_fns):
            if cand["arxiv_id"] in seen_ids:
                continue
            seen_ids.add(cand["arxiv_id"])
            row = _evaluate(cand["arxiv_id"], cand["origin"])
            row["search_query"] = cand["query"]
            row["search_title"] = cand["title"]
            if row["tier"] in ("introduces_target", "family_reference") \
                    and not search_title_gate(model_id, row.get("paper_title") or "", bases):
                # the search result's own title passed the gate; the paper arXiv actually
                # holds is a different one, so it is not this checkpoint's
                row["search_gate"] = "arxiv_title_rejected"
                row["tier"] = "unrelated_tag"
            tried.append(row)
            if row["tier"] == "introduces_target":
                break

    usable = [r for r in tried if r.get("tier") in ("introduces_target", "family_reference")]
    usable.sort(key=lambda r: 0 if r["tier"] == "introduces_target" else 1)
    arxiv_id = None
    if usable:
        best = usable[0]
        arxiv_id = best["arxiv_id"]
        origin = best["from"] + (f":{best['via_base_model']}" if best.get("via_base_model") else "")
        binding = {"tier": best["tier"], "verdict": "kept", "paper_url": best["paper_url"],
                   "fetch_error": best["fetch_error"]}
        if best.get("via_base_model"):
            binding["via_base_model"] = best["via_base_model"]
        sidecar.update({"resolved_url": best["paper_url"], "resolved_from": origin,
                        "paper_title": best["paper_title"], "binding": binding})
    elif tried and all(r.get("tier") == "fetch_failed" for r in tried if "arxiv_id" in r):
        first = tried[0]
        sidecar["binding"] = {"tier": "fetch_failed", "verdict": "unresolved",
                              "paper_url": first.get("paper_url"),
                              "reason": "paper metadata could not be fetched; re-collect to resolve",
                              "fetch_error": True}
        sidecar["resolved_from"] = first.get("from")
        sidecar["paper_title"] = ""
    elif tried:
        first = next((r for r in tried if r.get("tier") != "fetch_failed"), tried[0])
        sidecar["binding"] = {"tier": first.get("tier", "unrelated_tag"), "verdict": "dropped",
                              "paper_url": first.get("paper_url"),
                              "reason": "no family token in title or abstract",
                              "fetch_error": bool(first.get("fetch_error"))}
        sidecar["resolved_from"] = first.get("from")
        sidecar["paper_title"] = first.get("paper_title", "")
    else:
        sidecar["binding"] = {"tier": "none", "verdict": "no_paper",
                              "reason": "no arXiv id in tags, README BibTeX, README links or base tags"}
    sidecar["candidates"] = tried

    if arxiv_id:
        url = f"https://arxiv.org/abs/{arxiv_id}"
        cache = Path(out_dir) / "_paper_cache" / f"{arxiv_id}.json"
        doc = None
        if cache.is_file():
            try:
                doc = json.loads(cache.read_text(encoding="utf-8"))
                manifest["channels"]["docling_cache"] = "hit"
            except ValueError:
                doc = None
        if doc is None:
            if docling is None:
                from auto_benchmarkcard.tools.docling.docling_tool import extract_paper_with_docling
                docling = lambda u: extract_paper_with_docling.func(paper_url=u)  # noqa: E731
            try:
                doc = docling(url)
            except Exception as exc:
                doc = {"success": False, "error": str(exc)[:200]}
            manifest["channels"]["docling_cache"] = "miss"
            if doc and doc.get("success"):
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        if doc and doc.get("success"):
            _write(out, "docling", f"{slug}.json", doc)
            manifest["channels"]["docling"] = {"chars": len(doc.get("filtered_text") or "")}
        else:
            manifest["channels"]["docling"] = {"error": (doc or {}).get("error", "no text")}
    else:
        manifest["channels"]["docling"] = {"error": "no paper bound",
                                           "reason": sidecar["binding"].get("reason")}
    _write(out, "paper_resolver", "paper-verification.json", sidecar)
    manifest["channels"]["paper"] = sidecar["binding"]

    # GitHub README from the card's structured links or README prose. A model README
    # links many repos (transformers, vllm, llama.cpp); only the developer's own repo
    # or one that bears the model family name is this model's code repository.
    card_data = hf_meta.get("card_data") if isinstance(hf_meta.get("card_data"), dict) else {}
    if github is None:
        from auto_benchmarkcard.tools.github.github_tool import fetch_github_readme

        def github(*texts):
            last = {"success": False, "url": ""}
            for repo in own_github_candidates(model_id, *texts):
                last = fetch_github_readme(repo)
                if last.get("success"):
                    return last
            return last
    gh = github(card_data.get("repository"), card_data.get("homepage"), hf_meta.get("readme_markdown"))
    gh_url = (gh or {}).get("url") or ""
    if gh and gh.get("success") and github_repo_is_own(model_id, gh_url):
        _write(out, "github", f"{slug}.json", gh)
        manifest["channels"]["github"] = {"success": True, "url": gh_url}
    else:
        manifest["channels"]["github"] = {"success": False, "url": gh_url,
                                          "reason": ("repo not the developer's own"
                                                     if gh and gh.get("success") else "no repo")}

    # README-linked HTML: the developer's blog post, system card or tech-report page.
    # Selection is conservative (own host or path token AND a document-shaped path), so a
    # gated repo whose README links only the license page contributes nothing.
    html_urls = readme_html_candidates(model_id, hf_meta)
    pages: list = []
    html_errors: list = []
    if html_urls:
        if html is None:
            from auto_benchmarkcard.tools.html.html_tool import extract_html_content
            html = lambda u: extract_html_content.func(u)  # noqa: E731
        for url in html_urls:
            try:
                page = html(url)
            except Exception as exc:
                page = {"success": False, "url": url, "error": str(exc)[:200]}
            if page and page.get("success") and len((page.get("text") or "").strip()) >= 200:
                pages.append({"url": url, "title": page.get("title", ""), "text": page["text"]})
            else:
                html_errors.append({"url": url,
                                    "error": (page or {}).get("error", "no usable text")[:160]})
    if pages:
        _write(out, "html", f"{slug}.json", {"pages": pages})
        manifest["channels"]["html"] = {"pages": [{"url": p["url"], "chars": len(p["text"])}
                                                  for p in pages]}
    else:
        manifest["channels"]["html"] = {
            "pages": [],
            "reason": ("no README link is a developer document page" if not html_urls
                       else "every candidate page failed to yield text"),
            "candidates": html_urls, "errors": html_errors}

    # EEE by exact id
    eee = find_eee_records(model_id, eee_datastore)
    _write(out, "eee", f"{slug}.json", eee)
    manifest["channels"]["eee"] = {"tier": eee["tier"], "benchmarks": sorted(eee["benchmarks"])}
    if eee["tier"] != "exact":
        manifest["channels"]["eee"]["reason"] = "no Every Eval Ever record for this exact model id"

    manifest["absent_channels"] = sorted(
        name for name, ch in manifest["channels"].items()
        if isinstance(ch, dict) and (ch.get("error") or ch.get("reason")
                                     or ch.get("success") is False
                                     or ch.get("verdict") in ("dropped", "no_paper")))
    (out / "bundle-manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                              encoding="utf-8")
    return manifest
