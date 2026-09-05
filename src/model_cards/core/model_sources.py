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

Paper policy (build-brief notes): a derivative repo usually carries the BASE model's
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


def _token_present(tok: str, text: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(tok) + r"(?![a-z0-9])", text))


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
        return "introduces_target"
    family_tokens = set(tokens)
    for base in base_model_ids or []:
        if isinstance(base, str) and "/" in base:
            family_tokens |= distinctive_name_tokens(base)
    if any(_token_present(tok, text) for tok in family_tokens):
        return "family_reference"
    return "unrelated_tag"


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
    total = 0
    for sib in getattr(info, "siblings", None) or []:
        name = getattr(sib, "rfilename", "") or ""
        size = getattr(sib, "size", None)
        if name.endswith(".safetensors") and isinstance(size, int):
            total += size
    return total or None


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
                         allow_network: bool = True) -> Dict[str, Any]:
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
        tier = paper_binding_tier(model_id, meta.get("title", ""), meta.get("abstract", ""), bases)
        row: Dict[str, Any] = {"arxiv_id": arxiv_id, "from": origin, "tier": tier,
                               "paper_url": url, "paper_title": meta.get("title", ""),
                               "fetch_error": bool(meta.get("fetch_error"))}
        if via_base:
            row["via_base_model"] = via_base
        return row

    tried: list = []
    for cand in arxiv_candidates(hf_meta):
        tried.append(_evaluate(cand["arxiv_id"], cand["from"]))
        if tried[-1]["tier"] == "introduces_target":
            break
    if not any(r["tier"] == "introduces_target" for r in tried):
        seen_ids = {r["arxiv_id"] for r in tried}
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
    elif tried:
        first = tried[0]
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
