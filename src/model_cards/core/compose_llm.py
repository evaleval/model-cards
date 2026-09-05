"""LLM composition of a schema-v5 model card from a model source bundle, one
BindingRecord per filled value.

The Benchmark Card composer's own stages run with the v5 CardSchema:
  model frame (typed referents) -> Stage A verbatim-quote extraction per source
  (README, paper, GitHub), verified against the bundle's own bytes -> the composer's
  assignment gates + the model relation gates -> EAV audit -> Stage B grouped
  composition with the structured channel established (config.json, hub model_info,
  base_model tags, EEE join) -> BindingRecords with typed relations and exact spans ->
  the card is the projection of the ACCEPTED bindings -> quality fields from the ledger.

Withheld bindings (base-model facts on a derivative, comparison rows, unresolved
referents, score rows without a table anchor) stay in the ledger for the inspector; the
card never shows them. Nothing here touches the benchmark path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from auto_benchmarkcard.tools.composer import composer_tool as C
from auto_benchmarkcard.tools.composer import docstructure
from auto_benchmarkcard.tools.composer import eav as eav_mod
from auto_benchmarkcard.tools.composer import evidence
from auto_benchmarkcard.tools.composer import frame as frame_mod
from auto_benchmarkcard.tools.composer import validator as V

from .bridge import ComposerBridge, load_composer_bridge
from .calls import (
    EAV_MAX_TOKENS, EAV_VERDICT_SCHEMA, STAGE_A_MAX_TOKENS, SchemaBoundHandler,
    capped_generate,
)
from .support import unsupported_leaves
from .spans import (
    CompositionError, _stable_json, _digest_text, _structured_evidence,
    _target_manifest_evidence, _text_evidence,
)
from .composer_schema import HIGH_STAKES_FIELDS, model_card_schema
from .derivations import derive_architecture_type
from .model_frame import build_model_frame, family_name, relation_for
from .model_gates import FAMILY_ALLOWED_FIELDS, apply_model_gates, resolve_model_referents
from .model_sources import slug_for
from .plain_markdown import RULE as PLAIN_RULE, markdown_plain
from .records import (
    AssignmentOrigin, BenchmarkScope, BindingRecord, CardArtifact, ClaimEntity,
    DerivationTrace, EvidenceSpan, RelationToTarget, SourceBundle, SourceFile,
    VerifierAction,
)
from .schema import (
    NOT_APPLICABLE, NOT_SPECIFIED, CARD_FIELD_PATHS, SCHEMA_VERSION, blank_card,
    get_field_value, set_field_value,
)
from .source import load_source_bundle, split_target

logger = logging.getLogger(__name__)

README_CAP = 15000
GITHUB_CAP = 15000
HTML_CAP = 15000
PAPER_BUDGET = 25000
PAPER_HEAD = 4000
_PAPER_REGION_ORDER = {"intro": 0, "data": 1, "method": 2, "results": 3, "other": 4,
                       "ablation": 5, "related_work": 6, "ethics": 7, "appendix": 8}

DOC_README, DOC_PAPER, DOC_GITHUB, DOC_HTML = "hf_readme", "docling", "github_readme", "html"
_RELATION_ENUM = {
    "exact_target": RelationToTarget.EXACT_TARGET,
    "base": RelationToTarget.BASE,
    "derivative": RelationToTarget.DERIVATIVE,
    "sibling_or_comparison": RelationToTarget.SIBLING_OR_COMPARISON,
    "family": RelationToTarget.FAMILY,
    "unknown": RelationToTarget.UNKNOWN,
}
# The worst relation among the quotes a value cites decides the binding's relation. A
# family statement ranks between the target and another model: it is in scope for the
# fields whose policy allows it, and out of scope for every other field.
_RELATION_RANK = {"exact_target": 0, "family": 1, "base": 2, "derivative": 2,
                  "sibling_or_comparison": 3, "unknown": 4}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_bundle(bundle_root: str | Path, target: str) -> Dict[str, Any]:
    """The bundle files for target as written by model_sources.collect_model_bundle."""
    slug = slug_for(target)
    root = Path(bundle_root) / slug / "tool_output"
    if not root.is_dir():
        raise CompositionError(f"no bundle for {target} under {bundle_root}")

    def read(tool, name):
        p = root / tool / name
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    out = {
        "slug": slug,
        "hf": read("hf", f"{slug}.json") or {},
        "paper_sidecar": read("paper_resolver", "paper-verification.json") or {},
        "docling": read("docling", f"{slug}.json"),
        "github": read("github", f"{slug}.json"),
        "html": read("html", f"{slug}.json") or {"pages": []},
        "extras": read("extras", f"{slug}.json") or {},
        "eee": read("eee", f"{slug}.json") or {"tier": "none", "benchmarks": {}},
    }
    sb = Path(bundle_root) / slug / "source_bundle" / "source-bundle.json"
    if not sb.is_file():
        raise CompositionError(f"bundle for {target} has no source_bundle/source-bundle.json")
    out["source_bundle"] = load_source_bundle(sb)
    return out


def _extend_bundle(bundle: SourceBundle, extra: List[Tuple[str, str, str, str]]) -> SourceBundle:
    """A SourceBundle with additional hashed text files (name, uri, media_type, content)."""
    files = list(bundle.files)
    for name, uri, media_type, content in extra:
        if any(f.name == name for f in files) or not content:
            continue
        raw = content.encode("utf-8")
        files.append(SourceFile(name=name, source_uri=uri, sha256=hashlib.sha256(raw).hexdigest(),
                                size_bytes=len(raw), media_type=media_type, content=content))
    data = bundle.model_dump(mode="python")
    data["files"] = files
    meta = dict(data.get("metadata") or {})
    meta["available_files"] = [f.name for f in files]
    data["metadata"] = meta
    return SourceBundle(**data)


def _paper_context(doc_index, text: str, budget: int = PAPER_BUDGET) -> str:
    """The paper text the model reads: everything if it fits, else the head plus the
    heads of sections ranked by region (intro, data, method, results first)."""
    if len(text) <= budget:
        return text
    norm = getattr(doc_index, "normalized_text", "") or ""
    sections = list(getattr(doc_index, "sections", None) or [])
    if not norm or not sections:
        return text[:budget]
    parts = [norm[:PAPER_HEAD]]
    spans = [(0, PAPER_HEAD)]
    used = PAPER_HEAD
    for sec in sorted(sections, key=lambda s: (_PAPER_REGION_ORDER.get(s.region, 4), s.char_start)):
        remaining = budget - used
        if remaining < 300:
            break
        take = min(sec.char_end - sec.char_start, 2500, remaining)
        start, end = sec.char_start, sec.char_start + take
        if take <= 0 or any(start < b and a < end for a, b in spans):
            continue
        parts.append(norm[start:end])
        spans.append((start, end))
        used += take
    return "\n[...]\n".join(parts)


GAP_EXCERPT_BUDGET = 12000
GAP_SECTION_CAP = 2500
_GAP_INSTRUCTION = (
    "\n\nThe allowed fields above are the ones still missing evidence. Any part of "
    "the source text may support any of these missing fields, or none of them; tag "
    "each quote with the field it actually supports, or emit nothing for it."
)


def _query_tokens(query: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", (query or "").lower()) if len(t) >= 3}


def _gap_context(doc_index, text: str, targets: Dict[str, str], budget: int = GAP_EXCERPT_BUDGET) -> str:
    """Excerpts for the open gap fields: the paper's sections ranked by how many gap-query
    tokens they contain (ties by document order), each capped, within the budget and
    labelled honestly. A short text (or no index) is used as it is, within the budget."""
    norm = getattr(doc_index, "normalized_text", "") or ""
    sections = list(getattr(doc_index, "sections", None) or [])
    if not norm or not sections or len(text) <= budget:
        return text[:budget]
    tokens = set()
    for query in targets.values():
        tokens |= _query_tokens(query)
    scored = []
    for order, sec in enumerate(sections):
        body = norm[sec.char_start:sec.char_end].lower()
        hits = sum(1 for t in tokens if t in body)
        if hits:
            scored.append((-hits, order, sec))
    scored.sort()
    parts, used = [], 0
    for _, _, sec in scored:
        if used >= budget:
            break
        take = min(sec.char_end - sec.char_start, GAP_SECTION_CAP, budget - used)
        if take < 200:
            continue
        parts.append(f"[excerpt {len(parts) + 1}: {sec.title}]\n{norm[sec.char_start:sec.char_start + take]}")
        used += take
    return "\n\n".join(parts) if parts else text[:budget]


REJECTED_SAMPLES_CAP = 12


def _record_rejected(telem: Dict[str, Any], doc: str, emitted, verified: List[dict]) -> None:
    """Keep the first few quotes the verifier rejected (field, doc, quote head) so a
    read of the card can see WHAT failed to verify, not only how many."""
    kept = {evidence.normalize_ws(r.get("quote", "")) for r in verified}
    samples = telem.setdefault("rejected_samples", [])
    for it in emitted:
        d = it.model_dump() if hasattr(it, "model_dump") else dict(it)
        q = evidence.normalize_ws(str(d.get("quote", "") or ""))
        if q and q not in kept and len(samples) < REJECTED_SAMPLES_CAP:
            samples.append({"doc": doc, "field": d.get("field", ""), "quote": q[:160]})


def _counts_as_coverage(item: Dict[str, Any], frame: Dict[str, Any]) -> bool:
    """Whether a verified item closes its field for the gap pass.

    Only an item the gates can accept counts: exact_target anywhere, and a family
    statement on a field whose policy allows one. Everything else is a withheld binding,
    which leaves the field unfilled."""
    relation = relation_for(item.get("referent", ""), frame)
    if relation == "exact_target":
        return True
    if relation == "family":
        meta = frame.get("meta") or {}
        return (item.get("field") in FAMILY_ALLOWED_FIELDS
                and bool(meta.get("is_base_checkpoint"))
                and meta.get("paper_tier") == "introduces_target")
    return False


def _stage_a(llm, schema, frame, doc_index, model_id: str, revision: str, sources: Dict[str, str]):
    """Run one extraction call per available source, then one gap call per productive
    source for the schema's gap fields still without verified evidence (the composer's
    recall lever; a second sweep never runs). Returns (items_by_doc, telemetry)."""
    family = family_name(model_id)
    hf = sources.get("hf_meta") or {}
    anchor = (f'MODEL IDENTITY: "{model_id}" at revision {revision[:12]}; family "{family}"; '
              f"declared base models: {', '.join(hf.get('base_model_tags') or []) or 'none'}. "
              "Only extract facts stated for this checkpoint; facts about its base model, other "
              "sizes or variants, or comparison models must carry that entity's referent id.")
    defaults = (frame.get("meta") or {}).get("default_referent") or {}
    plan = [
        ("hf", DOC_README, "model card README", sources.get("readme", ""), README_CAP, None),
        ("paper", DOC_PAPER, "research paper", sources.get("paper", ""), None, doc_index),
        ("github", DOC_GITHUB, "GitHub README", sources.get("github", ""), GITHUB_CAP, None),
        ("html", DOC_HTML, "developer pages linked from the model card", sources.get("html", ""),
         HTML_CAP, None),
    ]
    items: Dict[str, List[dict]] = {}
    telem = evidence.new_card_telemetry()
    for key, doc, label, text, cap, index in plan:
        if not text or len(text) < 50:
            continue
        if key == "paper":
            shown = _paper_context(index, text)
            verify_source = text
        else:
            shown = text[:cap]
            verify_source = shown
        fields = evidence.fields_for_source(key, schema)
        prompt = evidence.build_extraction_prompt(label, fields, model_id.rsplit("/", 1)[-1],
                                                  identity_anchor=anchor, source_text=shown,
                                                  frame=frame, schema=schema)
        try:
            raw = capped_generate(llm, prompt,
                                  response_format=evidence.CuratorExtraction.model_json_schema(),
                                  max_tokens=STAGE_A_MAX_TOKENS, telemetry=telem,
                                  label=f"stage_a:{doc}")
        except Exception as exc:
            logger.warning("%s extraction failed: %s", label, exc)
            evidence.merge_telemetry(telem, evidence.empty_call_telemetry(doc))
            continue
        parsed = evidence.parse_curator_extraction(raw)
        recs, t = evidence.verify_items(parsed.evidence, verify_source, doc, shown_text=shown,
                                        doc_index=index, frame=frame, schema=schema,
                                        default_referent=defaults.get(doc))
        evidence.merge_telemetry(telem, t)
        _record_rejected(telem, doc, parsed.evidence, recs)
        items[doc] = recs
        # gap pass: only fields this source may carry that no source has verified yet.
        # Coverage counts only items that could actually reach the card: a quote resolved
        # to the base model or to a comparison model leaves the field just as empty as no
        # quote at all, and counting it closed the gap pass on fields nothing had filled.
        covered = {it["field"] for its in items.values() for it in its
                   if _counts_as_coverage(it, frame)}
        targets = {path: q for path, q in evidence.gap_fields(schema).items()
                   if path in fields and path not in covered}
        if not recs or not targets:
            continue
        context = _gap_context(index, text, targets) if key == "paper" else shown
        gap_prompt = evidence.build_extraction_prompt(f"{label} excerpts", list(targets),
                                                      model_id.rsplit("/", 1)[-1],
                                                      identity_anchor=anchor, source_text=context,
                                                      frame=frame, schema=schema) + _GAP_INSTRUCTION
        try:
            raw = capped_generate(llm, gap_prompt,
                                  response_format=evidence.CuratorExtraction.model_json_schema(),
                                  max_tokens=STAGE_A_MAX_TOKENS, telemetry=telem,
                                  label=f"stage_a_gap:{doc}")
        except Exception as exc:
            logger.warning("%s gap extraction failed: %s", label, exc)
            continue
        parsed = evidence.parse_curator_extraction(raw)
        gap_recs, t = evidence.verify_items(parsed.evidence, verify_source, doc, shown_text=context,
                                            doc_index=index, frame=frame, schema=schema,
                                            default_referent=defaults.get(doc))
        evidence.merge_telemetry(telem, t)
        _record_rejected(telem, doc, parsed.evidence, gap_recs)
        telem.setdefault("gap_calls", 0)
        telem["gap_calls"] += 1
        telem.setdefault("gap_verified", 0)
        telem["gap_verified"] += len(gap_recs)
        items[doc] = recs + gap_recs
    return items, telem


# A link field holds a URL. Left unchecked, the writer filled links.code_repository with
# "The instructed model can be downloaded here." on Mistral-7B-Instruct-v0.2: a true
# sentence from the README, in a field that is supposed to be clickable.
LINK_FIELDS = frozenset({"links.model_card", "links.system_card", "links.tech_report",
                         "links.code_repository"})
_URL_VALUE_RE = re.compile(r"^https?://[^\s<>\"']+$")


def is_url(value: Any) -> bool:
    return isinstance(value, str) and bool(_URL_VALUE_RE.match(value.strip()))


_PIPELINE_MODALITIES = {
    "text-generation": ("input: text", "output: text"),
    "text2text-generation": ("input: text", "output: text"),
    "image-text-to-text": ("input: image, text", "output: text"),
    "automatic-speech-recognition": ("input: audio", "output: text"),
    "image-to-text": ("input: image", "output: text"),
    "text-to-image": ("input: text", "output: image"),
}


def _table_score_specs(bundle: SourceBundle, bridge: ComposerBridge, frame: Dict[str, Any],
                       files_by_doc: Dict[str, SourceFile]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """benchmark_scores rows from README and paper tables whose row label is the target."""
    from .table_scores import reconcile_rows, target_score_rows
    target = next(n for n in frame["nodes"] if n["id"] == frame.get("target_id", "target"))
    aliases = [target["name"], *target.get("aliases", [])]
    collected: List[Dict[str, Any]] = []
    seen = set()
    for doc in (DOC_README, DOC_PAPER, DOC_HTML):
        src = files_by_doc.get(doc)
        if src is None or not src.content:
            continue
        for r in target_score_rows(src.content, aliases, doc):
            key = (r["benchmark"], r["score"], r["setting"], doc)
            if key in seen:
                continue
            seen.add(key)
            r["_src"] = src
            collected.append(r)
    accepted, conflicted = reconcile_rows(collected)

    rows: List[Dict[str, Any]] = []
    specs: List[Dict[str, Any]] = []

    def span_for(r):
        try:
            return _text_evidence(bundle, r["_src"], r["row_text"], bridge,
                                  row_anchor=r["row_text"],
                                  table_header_override=r["header"] or None)
        except CompositionError:
            return None

    for r in accepted:
        span = span_for(r)
        if span is None:
            continue
        value = {"benchmark": r["benchmark"], "metric": r["metric"], "score": r["score"],
                 "setting": r["setting"]}
        rows.append(value)
        specs.append({"path": "evaluation.benchmark_scores", "value": value, "indexed": True,
                      "evidence": span, "reason": "structured_table_row_names_target",
                      "sources": r.get("source_docs") or [r["source_doc"]],
                      "scope": BenchmarkScope(benchmark_id=r["benchmark"], setting=r["setting"])})
    for r in conflicted:
        span = span_for(r)
        if span is None:
            continue
        value = {"benchmark": r["benchmark"], "metric": r["metric"], "score": r["score"],
                 "setting": r["setting"]}
        specs.append({"path": "evaluation.benchmark_scores", "value": value, "indexed": True,
                      "evidence": span, "action": VerifierAction.WITHHOLD,
                      "reason": r["withhold_reason"], "sources": [r["source_doc"]],
                      "conflict": {"benchmark": r["benchmark"], "setting": r.get("setting"),
                                   "values": r["conflict"], "source_doc": r["source_doc"]},
                      "scope": BenchmarkScope(benchmark_id=r["benchmark"], setting=r["setting"])})
    return rows, specs


FAMILY_MAX_TOKENS = 4
FAMILY_MIN_WORD_LEN = 3


def family_is_developer_stated(family: str, corroborating_text: str) -> bool:
    """Whether a family name derived from the repo name is one the sources actually use.

    It has to be short enough to be a name, carry at least one real word, and have every
    real word of it present in the model's own documentation. A hyperparameter string is
    none of those things.
    """
    tokens = [t for t in re.split(r"[\s_-]+", family.strip()) if t]
    if not tokens or len(tokens) > FAMILY_MAX_TOKENS:
        return False
    words = [t for t in tokens if len(t) >= FAMILY_MIN_WORD_LEN and any(c.isalpha() for c in t)]
    if not words:
        return False
    low = corroborating_text.lower()
    return all(word.lower() in low for word in words)


def _det_facts(bundle: SourceBundle, hf: Dict[str, Any], paper_sidecar: Dict[str, Any],
               eee: Dict[str, Any], github: Optional[Dict[str, Any]], info_file: SourceFile,
               extras: Dict[str, Any], extras_file: Optional[SourceFile],
               paper_text: str = "", github_text: str = ""
               ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Structured-channel values plus the binding specs that carry them.

    The Every Eval Ever join is recorded in the run manifest, not on the card: the
    public contract has no field for it."""
    model_id = bundle.target.model_id
    rev = bundle.target.resolved_revision
    readme_file = next((f for f in bundle.files if f.name == "README.md"), None)
    config_file = next((f for f in bundle.files if f.name == "config.json"), None)
    config = {}
    if config_file is not None and config_file.content:
        try:
            config = json.loads(config_file.content)
        except ValueError:
            config = {}
    facts: Dict[str, Any] = {}
    specs: List[Dict[str, Any]] = []
    info_text = info_file.content or ""

    def info_span(needle: str) -> Optional[str]:
        return needle if needle in info_text else None

    facts["identity.model_id"] = model_id
    specs.append({"path": "identity.model_id", "value": model_id,
                  "evidence": _target_manifest_evidence(bundle, "/target/model_id", model_id)})
    facts["identity.version"] = rev
    specs.append({"path": "identity.version", "value": rev,
                  "evidence": _target_manifest_evidence(bundle, "/target/resolved_revision", rev)})

    # the Hub emits base_model:<repo> and base_model:<kind>:<repo> for the same base
    # (kind in finetune/adapter/merge/quantized); one row per base, the kind kept
    bases: Dict[str, Dict[str, str]] = {}
    for tag in hf.get("base_model_tags") or []:
        kind, base = "base", tag
        head, sep, rest = tag.partition(":")
        if sep and head in ("finetune", "adapter", "merge", "quantized"):
            kind, base = head, rest
        if "/" not in base:
            continue
        current = bases.get(base)
        if current is None or (current["kind"] == "base" and kind != "base"):
            bases[base] = {"tag": tag, "kind": kind}
    for base, info in bases.items():
        needle = info_span(json.dumps(f"base_model:{info['tag']}"))
        if needle:
            row = {"model_id": base, "relation": "base_model", "kind": info["kind"]}
            facts.setdefault("lineage.base_models", []).append(row)
            specs.append({"path": "lineage.base_models", "value": row, "indexed": True,
                          "text": (info_file, needle),
                          "relation": RelationToTarget.BASE, "entity": ClaimEntity(model_id=base)})
    fam = family_name(model_id)
    repo_name = model_id.rsplit("/", 1)[-1]
    # the display name is the README's own title when it names the repo (the same
    # rule the frame uses for the title alias); a structured fact, not a quote the
    # extractor may or may not emit on a given run
    # identity.name is deterministic: the README's own title when it names this repo,
    # otherwise the repo name. Leaving it to the writer produced "Model Card for
    # Mistral-7B-v0.3", "google/gemma-3-4b-it" and a comma-separated alias list, none of
    # which is a display name.
    named_from_readme = False
    if readme_file is not None and readme_file.content:
        body = frame_mod._readme_frontmatter_stripped(readme_file.content)[:2000]
        for match in re.finditer(r"^(#{1,2}\s+\S.*?)\s*$", body, re.MULTILINE):
            heading_line = match.group(1).strip()
            heading = re.sub(r"^#{1,2}\s+", "", heading_line)
            # "# Model Card for OLMo 2 7B" titles the document, not the model
            trimmed = re.sub(r"^model\s*card\s*(for|of|:)?\s*", "", heading,
                             flags=re.IGNORECASE).strip()
            key = re.sub(r"[^a-z0-9]", "", repo_name.lower())
            hkey = re.sub(r"[^a-z0-9]", "", trimmed.lower())
            if hkey and (key in hkey or hkey in key) and len(trimmed) <= 80 \
                    and heading_line in (readme_file.content or ""):
                facts["identity.name"] = trimmed
                specs.append({"path": "identity.name", "value": trimmed,
                              "text": (readme_file, heading_line)})
                named_from_readme = True
                break
    if not named_from_readme:
        facts["identity.name"] = repo_name
        specs.append({"path": "identity.name", "value": repo_name,
                      "evidence": _target_manifest_evidence(bundle, "/target/repository_name",
                                                            repo_name)})
    # A family is a name the developer uses, not a leftover of the repo name. Deriving it
    # unconditionally gave jaspionjader/f-6-8b the family "f 6" and
    # JayHyeon/Qwen_0.5-IRPO_3e-6-2ep_1alp_0lam the family "Qwen 0.5 IRPO 3e 6 2ep 1alp
    # 0lam": noise presented as a fact, on 98.8% of the 2026-09-05 batch. The derived name
    # is kept only when the sources actually use it, which is the same rule the frame
    # applies to any name a model proposes.
    corroborating = " ".join(t for t in (readme_file.content if readme_file else "",
                                         paper_text, github_text) if t).lower()
    if fam and fam != repo_name and family_is_developer_stated(fam, corroborating):
        facts["lineage.model_family"] = fam
        specs.append({"path": "lineage.model_family", "value": fam,
                      "evidence": _target_manifest_evidence(bundle, "/target/repository_name", repo_name),
                      "derivation": DerivationTrace(rule="family_from_repo_name_v1",
                                                    inputs={"repository_name": repo_name}, output=fam)})
    author = hf.get("author")
    needle = info_span(f'"author": {json.dumps(author)}') if isinstance(author, str) and author else None
    if needle:
        facts["identity.developed_by"] = f"{author} (Hub organization)"
        specs.append({"path": "identity.developed_by", "value": f"{author} (Hub organization)",
                      "text": (info_file, needle)})
    pipeline = hf.get("pipeline_tag")
    needle = info_span(f'"pipeline_tag": {json.dumps(pipeline)}') if isinstance(pipeline, str) else None
    if needle and pipeline in _PIPELINE_MODALITIES:
        facts["specifications.input_output"] = list(_PIPELINE_MODALITIES[pipeline])
        specs.append({"path": "specifications.input_output", "value": list(_PIPELINE_MODALITIES[pipeline]),
                      "text": (info_file, needle)})

    arch, inputs = derive_architecture_type(config)
    if arch and config_file is not None:
        pointer = "/config/architectures" if config.get("architectures") else "/config/model_type"
        fragment = config.get("architectures") if config.get("architectures") else config.get("model_type")
        facts["specifications.architecture_type"] = arch
        specs.append({"path": "specifications.architecture_type", "value": arch,
                      "evidence": _structured_evidence(bundle, config_file, pointer, fragment),
                      "derivation": DerivationTrace(rule="architecture_type_v1", inputs=inputs, output=arch)})
    ctx = config.get("max_position_embeddings")
    if isinstance(ctx, int) and config_file is not None:
        val = f"{ctx:,} tokens (config.json max_position_embeddings)"
        facts["specifications.context_length"] = val
        specs.append({"path": "specifications.context_length", "value": val,
                      "evidence": _structured_evidence(bundle, config_file, "/config/max_position_embeddings", ctx)})
    st = hf.get("safetensors") if isinstance(hf.get("safetensors"), dict) else {}
    total = st.get("total")
    if isinstance(total, int) and info_span(f'"total": {total}'):
        val = f"{total:,} parameters (safetensors metadata)"
        facts["specifications.num_parameters"] = val
        specs.append({"path": "specifications.num_parameters", "value": val, "text": (info_file, f'"total": {total}')})
    params = st.get("parameters") if isinstance(st.get("parameters"), dict) else {}
    if params:
        dtype = max(params, key=lambda k: params[k])
        needle = info_span(json.dumps(dtype))
        if needle:
            val = f"{dtype} (safetensors weight dtype)"
            facts["specifications.precision"] = val
            specs.append({"path": "specifications.precision", "value": val, "text": (info_file, needle)})
    created = hf.get("created_at") or hf.get("createdAt")
    needle = info_span(json.dumps(created)) if isinstance(created, str) and created else None
    if needle:
        val = f"{created[:10]} (Hugging Face repository creation date)"
        facts["identity.release_date"] = val
        specs.append({"path": "identity.release_date", "value": val, "text": (info_file, needle)})

    gated = hf.get("gated")
    needle = info_span(f'"gated": {json.dumps(gated)}') if gated is not None else None
    if needle:
        val = "gated" if gated else "open-weight"
        facts["access_and_adoption.access_type"] = val
        specs.append({"path": "access_and_adoption.access_type", "value": val, "text": (info_file, needle)})
    snapshot_date = bundle.retrieved_at.date().isoformat()
    downloads = hf.get("downloads")
    needle = info_span(f'"downloads": {downloads}') if isinstance(downloads, int) else None
    if needle:
        val = f"{downloads:,} downloads (Hub 30-day window, as of {snapshot_date})"
        facts["access_and_adoption.downloads"] = val
        specs.append({"path": "access_and_adoption.downloads", "value": val, "text": (info_file, needle)})
    likes = hf.get("likes")
    needle = info_span(f'"likes": {likes}') if isinstance(likes, int) else None
    if needle:
        val = f"{likes:,} likes on the Hub (as of {snapshot_date})"
        facts["access_and_adoption.likes"] = val
        specs.append({"path": "access_and_adoption.likes", "value": val, "text": (info_file, needle)})
    # The licence of the WEIGHTS, from the Hub tag or the card's own frontmatter, never
    # from prose: a README badge gave DeepSeek-V3 the licence "Model_License-Model_Agreement",
    # and a GitHub README states the licence of the code, which is a different thing.
    for tag in hf.get("tags") or []:
        if isinstance(tag, str) and tag.startswith("license:"):
            needle = info_span(json.dumps(tag))
            if needle:
                facts["identity.license"] = tag.split(":", 1)[1]
                specs.append({"path": "identity.license", "value": tag.split(":", 1)[1],
                              "text": (info_file, needle)})
            break
    if "identity.license" not in facts and extras_file is not None:
        declared = (extras.get("readme_frontmatter") or {}).get("license")
        if isinstance(declared, str) and declared.strip():
            facts["identity.license"] = declared.strip()
            specs.append({"path": "identity.license", "value": declared.strip(),
                          "evidence": _structured_evidence(bundle, extras_file,
                                                           "/readme_frontmatter/license",
                                                           declared)})
    # model_size: the bytes of THIS revision's weight files, with the dtype they carry.
    # The Hub returns file sizes only when they are asked for, so collect records them.
    st_bytes = extras.get("safetensors_bytes")
    if isinstance(st_bytes, int) and st_bytes > 0 and extras_file is not None:
        gib = st_bytes / (1024 ** 3)
        dtype = max(params, key=lambda k: params[k]) if params else None
        val = (f"{gib:,.1f} GiB of safetensors weights ({st_bytes:,} bytes)"
               + (f" in {dtype}" if dtype else ""))
        facts["specifications.model_size"] = val
        # the structured pointer into the frozen extras file is the evidence; a
        # derivation trace would have to be re-derivable by the artifact validator, which
        # knows only the two config-backed rules
        specs.append({"path": "specifications.model_size", "value": val,
                      "evidence": _structured_evidence(bundle, extras_file, "/safetensors_bytes",
                                                       st_bytes)})

    # citation: the developer's own BibTeX block, verbatim from the README
    blocks = extras.get("bibtex_blocks") or []
    if blocks and readme_file is not None:
        block = next((b for b in blocks if b in (readme_file.content or "")), None)
        if block:
            facts["links.citation"] = block.strip()
            specs.append({"path": "links.citation", "value": block.strip(),
                          "text": (readme_file, block)})

    card_url = f"https://huggingface.co/{model_id}"
    facts["links.model_card"] = card_url
    specs.append({"path": "links.model_card", "value": card_url,
                  "evidence": _target_manifest_evidence(bundle, "/target/model_id", model_id)})
    binding = paper_sidecar.get("binding") or {}
    url = paper_sidecar.get("resolved_url")
    if url and binding.get("tier") == "introduces_target":
        arxiv_tag = next((t for t in hf.get("tags") or [] if isinstance(t, str) and t.startswith("arxiv:")), None)
        needle = info_span(json.dumps(arxiv_tag)) if arxiv_tag else None
        if needle:
            facts["links.tech_report"] = url
            specs.append({"path": "links.tech_report", "value": url, "text": (info_file, needle)})
    if github and github.get("success") and github.get("url") and readme_file is not None \
            and github["url"] in (readme_file.content or ""):
        facts["links.code_repository"] = github["url"]
        specs.append({"path": "links.code_repository", "value": github["url"],
                      "text": (readme_file, github["url"])})
    return facts, specs


def eee_links(eee: Dict[str, Any], model_id: str) -> List[str]:
    """Every Eval Ever record links for an exact join. These go in the run manifest;
    the public contract has no field for them."""
    if eee.get("tier") != "exact":
        return []
    return [f"https://huggingface.co/datasets/evaleval/EEE_datastore/tree/main/data/"
            f"{bench}/{model_id}" for bench in sorted(eee.get("benchmarks") or {})]


def _span_for_item(bundle: SourceBundle, bridge: ComposerBridge, files_by_doc: Dict[str, SourceFile],
                   item: dict, doc_index) -> EvidenceSpan:
    src = files_by_doc[item["doc"]]
    quote = item["quote"]
    start = int(item["char_start"])
    # The structural anchor comes from the source's own table index; header cells are
    # cleaned because markdown tables often carry an empty corner cell and EvidenceSpan
    # refuses empty header items. A quote inside a table with a real header gets the
    # row anchor the benchmark_scores rule requires, README tables included.
    anchor = bridge.structural_anchor(src.content or "", start)
    header = tuple(c.strip() for c in (anchor.get("table_header") or []) if c and c.strip())
    row_anchor = quote if (header and anchor.get("table_id")) else None
    return _text_evidence(bundle, src, quote, bridge, row_anchor=row_anchor,
                          verified_span=(start, start + len(quote)),
                          table_header_override=header)


def _run_final_claim_pass(card: Dict[str, Any], bindings, bundle: SourceBundle,
                          model_id: str) -> Dict[str, Any]:
    """Run the final-claim pass if it is enabled and can run; never raise."""
    from .factcheck import final_claim_pass
    from .route import factcheck_enabled, factcheck_route_defaults

    if not factcheck_enabled():
        return {"status": "disabled",
                "reason": "MODELCARDS_FACTCHECK is not set; the pinned route returns no "
                          "token logprobs, which FactReasoner needs",
                "atoms": [], "contradicted_fields": [], "claims_built": 0}
    factcheck_route_defaults()
    sources = {f.source_uri: (f.content or "") for f in bundle.files}
    try:
        return final_claim_pass(card, bindings, sources, model_id)
    except Exception as exc:  # a validation step must not be able to lose a card
        logger.warning("final-claim pass raised: %s", exc)
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"[:200],
                "atoms": [], "contradicted_fields": [], "claims_built": 0}


def compose_model_card_llm(target: str, bundle_root: str | Path, llm, *,
                           bridge: Optional[ComposerBridge] = None,
                           allow_unpinned: bool = False) -> CardArtifact:
    """Compose the v5 card for target from its bundle with the LLM composer."""
    bridge = bridge or load_composer_bridge(allow_unpinned=allow_unpinned)
    b = load_bundle(bundle_root, target)
    base_bundle: SourceBundle = b["source_bundle"]
    model_id, rev = base_bundle.target.model_id, base_bundle.target.resolved_revision
    hf = b["hf"]
    schema = model_card_schema()

    paper_text = C._normalize_docling_text((b["docling"] or {}).get("filtered_text", "")) \
        if b["docling"] and b["docling"].get("success") else ""
    paper_url = b["paper_sidecar"].get("resolved_url") or ""
    github = b["github"] if b["github"] and b["github"].get("success") else None
    info_subset = {k: hf.get(k) for k in ("id", "author", "created_at", "tags", "downloads",
                                          "likes", "gated", "pipeline_tag", "library_name",
                                          "safetensors", "base_model_tags", "resolved_revision")}
    info_text = json.dumps(info_subset, indent=1, sort_keys=True)
    eee_text = json.dumps(b["eee"], indent=1, sort_keys=True)
    # the README the extractor reads and the verifier checks is the recorded plain
    # view (links to their text, markup removed); the raw README.md stays in the
    # bundle for the structured channel and the table rows anchor in the plain view
    readme_raw = next((f for f in base_bundle.files if f.name == "README.md"), None)
    readme_plain = markdown_plain((readme_raw.content if readme_raw else "") or "")
    extras = b["extras"] or {}
    extras_text = json.dumps({k: extras.get(k) for k in ("safetensors_bytes", "readme_frontmatter",
                                                         "model_index_from_frontmatter")},
                             indent=1, sort_keys=True)
    html_pages = [p for p in (b["html"] or {}).get("pages") or [] if (p.get("text") or "").strip()]
    html_text = "\n\n".join(f"# {p.get('title') or p['url']}\n{p['text']}" for p in html_pages)
    bundle = _extend_bundle(base_bundle, [
        ("README.plain.md",
         f"{readme_raw.source_uri}#plain" if readme_raw
         else f"https://huggingface.co/{model_id}#no-readme", "text/markdown", readme_plain),
        ("paper.md", paper_url or f"https://huggingface.co/{model_id}#paper", "text/markdown", paper_text),
        ("github_README.md", (github or {}).get("url") or "", "text/markdown", (github or {}).get("text") or ""),
        ("pages.md", html_pages[0]["url"] if html_pages else "", "text/markdown", html_text),
        ("model_info.json", f"https://huggingface.co/api/models/{model_id}?revision={rev}", "application/json", info_text),
        ("extras.json", f"https://huggingface.co/api/models/{model_id}?revision={rev}&files_metadata=1", "application/json", extras_text),
        ("eee.json", "https://huggingface.co/datasets/evaleval/EEE_datastore", "application/json", eee_text),
    ])
    files = {f.name: f for f in bundle.files}
    files_by_doc = {}
    plain = files.get("README.plain.md") or files.get("README.md")
    if plain is not None:
        files_by_doc[DOC_README] = plain
    if "paper.md" in files:
        files_by_doc[DOC_PAPER] = files["paper.md"]
    if "github_README.md" in files:
        files_by_doc[DOC_GITHUB] = files["github_README.md"]
    if "pages.md" in files:
        files_by_doc[DOC_HTML] = files["pages.md"]

    doc_index = docstructure.build_index(paper_text) if paper_text else None
    frame = build_model_frame(model_id, rev, hf, doc_index=doc_index, paper_text=paper_text,
                              github_text=(github or {}).get("text") or "", eee=b["eee"],
                              paper_tier=(b["paper_sidecar"].get("binding") or {}).get("tier", "none"),
                              llm_handler=llm)

    items_by_doc, quote_telem = _stage_a(llm, schema, frame, doc_index, model_id, rev, {
        "hf_meta": hf,
        "readme": (files_by_doc[DOC_README].content or "") if DOC_README in files_by_doc else "",
        "paper": paper_text,
        "github": (github or {}).get("text") or "", "html": html_text})
    gate_telem: Dict[str, Any] = {}
    items, _ = evidence.finalize_evidence(items_by_doc.get(DOC_PAPER, []), [], [],
                                          items_by_doc.get(DOC_README, []),
                                          items_by_doc.get(DOC_GITHUB, []) +
                                          items_by_doc.get(DOC_HTML, []),
                                          frame=frame, gate_telemetry=gate_telem, schema=schema)
    referent_telem: Dict[str, Any] = {}
    items = resolve_model_referents(items, frame, referent_telem)
    model_gate_telem: Dict[str, Any] = {}
    items, withheld_items = apply_model_gates(items, frame, model_gate_telem)
    digest = evidence.build_digest(items)
    eav_call_telem: Dict[str, Any] = {}
    digest, eav_telem = eav_mod.run_eav(
        digest, frame,
        SchemaBoundHandler(llm, EAV_VERDICT_SCHEMA, EAV_MAX_TOKENS, eav_call_telem, "eav"),
        high_stakes=HIGH_STAKES_FIELDS, card_noun="model card",
        sibling_phrase="the base model, a sibling checkpoint or variant, a comparison model, a benchmark")
    if eav_call_telem.get("truncated_calls"):
        eav_telem["truncated_calls"] = eav_call_telem["truncated_calls"]
    items_by_id = {it["evidence_id"]: it for its in digest.values() for it in its}

    det_facts, det_specs = _det_facts(bundle, hf, b["paper_sidecar"], b["eee"], github,
                                      files["model_info.json"], extras, files.get("extras.json"),
                                      paper_text=paper_text,
                                      github_text=(github or {}).get("text") or "")
    score_rows, score_specs = _table_score_specs(bundle, bridge, frame, files_by_doc)
    score_conflicts = [spec["conflict"] for spec in score_specs if "conflict" in spec]
    if score_rows:
        det_facts["evaluation.benchmark_scores"] = score_rows
    det_specs.extend(score_specs)
    digest_ids = {it["evidence_id"]: it["field"] for its in digest.values() for it in its}
    sections: Dict[str, dict] = {}
    provenance: Dict[str, dict] = {}
    group_telemetry: Dict[str, Any] = {}
    flagged: Dict[str, str] = {}
    for group_name, group_sections in schema.groups:
        prompt = C._build_group_prompt(group_name, group_sections, schema.section_models, digest,
                                       det_facts, "", schema=schema)

        def _generate(p, max_tokens=None, _schema=C._build_group_model(group_name, group_sections,
                                                                          schema.section_models).model_json_schema()):
            return llm.generate_with_meta(p, response_format=_schema, max_completion_tokens=max_tokens)

        outcome = V.run_group_with_repair(group_name, group_sections, schema.section_models, prompt,
                                          _generate, digest_ids, det_filled_paths=set(det_facts),
                                          schema=schema)
        for sec in group_sections:
            clean, prov = C.extract_provenance(outcome.sections[sec])
            sections[sec] = clean
            provenance[sec] = prov or {}
        flagged.update(outcome.flagged)
        group_telemetry[group_name] = outcome.telemetry

    target_entity = ClaimEntity(model_id=model_id, revision=rev, label=model_id.rsplit("/", 1)[-1])
    bindings: List[BindingRecord] = []
    list_index: Dict[str, int] = {}

    seen_bindings: set = set()

    def record(path, value, spans, relation, entity, action, reason, origin, scope=None, derivation=None):
        binding = BindingRecord(
            field_path=path, proposed_value=value, target=bundle.target, claim_entity=entity,
            relation_to_target=relation, benchmark_scope=scope, assignment_origin=origin,
            evidence=tuple(spans), derivation_trace=derivation, verifier_action=action,
            verifier_reason=reason)
        # binding_id is content-derived, so two records with identical content ARE one
        # binding. The same quote reaches the withheld list once per extraction call that
        # proposed it, and the ledger holds one entry for it.
        if binding.binding_id in seen_bindings:
            return
        seen_bindings.add(binding.binding_id)
        bindings.append(binding)

    def withhold_field(path: str, reason: str) -> bool:
        """Turn a field's accepted bindings into withheld ones and blank its value.

        A post-composition check refuses a value the writer already produced, so the
        ledger must not end up holding an accept and a withhold for the same field: the
        card is the projection of the accepted bindings, and two dispositions for one
        field make that projection unrepresentable.
        """
        section, fname = path.split(".", 1)
        replaced = False
        for index, existing in enumerate(bindings):
            if existing.field_path.split("[", 1)[0] != path:
                continue
            if existing.verifier_action is not VerifierAction.ACCEPT:
                continue
            data = existing.model_dump(mode="python")
            data.update({"binding_id": "", "verifier_action": VerifierAction.WITHHOLD,
                         "verifier_reason": reason})
            bindings[index] = BindingRecord(**data)
            seen_bindings.add(bindings[index].binding_id)
            replaced = True
        if replaced:
            card[section][fname] = NOT_SPECIFIED
        return replaced

    for spec in det_specs:
        path = spec["path"]
        if spec.get("indexed"):
            i = list_index.get(path, 0)
            list_index[path] = i + 1
            path = f"{path}[{i}]"
        if "text" in spec:
            src, needle = spec["text"]
            spans = [_text_evidence(bundle, src, needle, bridge)]
        else:
            spans = [spec["evidence"]]
        record(path, spec["value"], spans, spec.get("relation", RelationToTarget.EXACT_TARGET),
               spec.get("entity", target_entity), spec.get("action", VerifierAction.ACCEPT),
               spec.get("reason", "structured_explicit_source"),
               AssignmentOrigin.STRUCTURED_EXPLICIT, scope=spec.get("scope"),
               derivation=spec.get("derivation"))

    node_names = {n["id"]: n for n in frame["nodes"]}
    leaf_telemetry: List[Dict[str, Any]] = []
    # what the structured channel already fixed for this card, plus the target's own
    # names: a value saying "the 7B model" is not fabricating on a 7B checkpoint
    target_node = node_names.get(frame.get("target_id", "target"), {})
    established_support = [_stable_json(v) for v in det_facts.values()] + \
        [target_node.get("name", ""), *target_node.get("aliases", []), model_id]

    # Every record the gates refused becomes a withheld binding carrying the quote it was
    # proposed for, so the ledger says what the card decided not to say and why. Without
    # this the refusals existed only as counters in the telemetry.
    for it in withheld_items:
        rel_key = it.get("relation", "unknown")
        ref_node = node_names.get(it.get("referent", ""), {})
        bid = ref_node.get("name") if ref_node.get("type") == "base" else None
        if rel_key == "exact_target":
            # a refusal can leave the relation intact: the row-anchor and comparison
            # gates withhold a record that really is about the target, and an
            # exact_target binding must name the target commit
            entity = target_entity
        elif bid and "/" in bid:
            entity = ClaimEntity(model_id=bid)
        else:
            entity = ClaimEntity(label=ref_node.get("name") or rel_key)
        try:
            span = _span_for_item(bundle, bridge, files_by_doc, it, doc_index)
        except (CompositionError, KeyError):
            continue
        record(it.get("field", ""), it.get("quote", ""), [span],
               _RELATION_ENUM.get(rel_key, RelationToTarget.UNKNOWN), entity,
               VerifierAction.WITHHOLD, it.get("withhold_reason", "gate_refused"),
               AssignmentOrigin.UNRESOLVED)

    for sec in schema.composed_sections:
        for fname, value in (sections.get(sec) or {}).items():
            path = f"{sec}.{fname}"
            if path in det_facts or value in (None, NOT_SPECIFIED, [NOT_SPECIFIED], NOT_APPLICABLE, [], {}):
                if value == NOT_APPLICABLE:
                    record(path, value, [_target_manifest_evidence(bundle, "/target/model_id", model_id)],
                           RelationToTarget.EXACT_TARGET, target_entity, VerifierAction.ACCEPT,
                           "not_applicable_for_model_class", AssignmentOrigin.STRUCTURED_EXPLICIT)
                continue
            entry = (provenance.get(sec) or {}).get(fname) or {}
            cited = [items_by_id[i] for i in (entry.get("evidence_ids") or []) if i in items_by_id]
            if not cited:
                continue
            if path in schema.established_fields:
                # An established field is one the structured channel owns. When the
                # channel produced nothing for it, the honest value is Not specified, not
                # the writer's reading of the prose: lineage.derivatives needs the Hub
                # model tree, and a gated repo has no config.json to read a context length
                # from. The proposal stays in the ledger so the recall is visible.
                spans = [_span_for_item(bundle, bridge, files_by_doc, it, doc_index)
                         for it in cited]
                record(path, value, spans, RelationToTarget.EXACT_TARGET, target_entity,
                       VerifierAction.WITHHOLD, "established_field_without_structured_source",
                       AssignmentOrigin.LLM_INFERRED)
                continue
            spans = [_span_for_item(bundle, bridge, files_by_doc, it, doc_index) for it in cited]
            missing = unsupported_leaves(value, [it.get("quote", "") for it in cited],
                                         established=established_support)
            worst = max(cited, key=lambda it: _RELATION_RANK.get(it.get("relation", "unknown"), 4))
            rel_key = worst.get("relation", "unknown")
            relation = _RELATION_ENUM[rel_key]
            ref_node = node_names.get(worst.get("referent", ""), {})
            if rel_key == "exact_target":
                entity, action, reason, origin = target_entity, VerifierAction.ACCEPT, "llm_bound_exact_target", AssignmentOrigin.LLM_INFERRED
            elif rel_key == "family":
                # the gates already refused a family statement on any field whose policy
                # forbids one, so what reaches here is in scope; the relation stays family
                # so the reader sees the claim is about the family, not the checkpoint
                entity = ClaimEntity(label=ref_node.get("name") or "model family")
                action, reason, origin = (VerifierAction.ACCEPT,
                                          "family_statement_allowed_for_this_field",
                                          AssignmentOrigin.LLM_INFERRED)
            elif rel_key in ("base", "derivative"):
                bid = ref_node.get("name") if ref_node.get("type") == "base" else None
                entity = ClaimEntity(model_id=bid) if bid and "/" in bid else ClaimEntity(label=ref_node.get("name") or rel_key)
                action, reason, origin = VerifierAction.WITHHOLD, "base_model_fact_not_this_checkpoint", AssignmentOrigin.LLM_INFERRED
            elif rel_key == "sibling_or_comparison":
                entity = ClaimEntity(label=ref_node.get("name") or "comparison model")
                action, reason, origin = VerifierAction.WITHHOLD, "sibling_or_comparison_not_target", AssignmentOrigin.LLM_INFERRED
            else:
                entity = ClaimEntity(label=ref_node.get("name") or "unresolved referent")
                relation, action, reason, origin = RelationToTarget.UNKNOWN, VerifierAction.WITHHOLD, "referent_unresolved", AssignmentOrigin.UNRESOLVED
            if path in LINK_FIELDS and not is_url(value):
                record(path, value, spans, relation, entity, VerifierAction.WITHHOLD,
                       "link_field_is_not_a_url", AssignmentOrigin.LLM_INFERRED)
                continue
            if missing:
                # Stage B may rephrase, but it may not introduce a number or an entity
                # name that no cited quote contains. That is the splice signature: the
                # quote says 73.5 and the value says 99.0, or the quote is about the 13B
                # and the value is about the 7B.
                # the reason is a code; the offending leaves are recorded in the run
                # metadata, because a binding's derivation trace must equal its value
                leaf_telemetry.append({"field": path, "unsupported": missing[:12],
                                       "cited_evidence_ids": [it["evidence_id"] for it in cited]})
                entity = entity if rel_key != "exact_target" else target_entity
                record(path, value, spans, relation, entity, VerifierAction.WITHHOLD,
                       "leaf_value_not_in_cited_evidence", AssignmentOrigin.LLM_INFERRED)
                continue
            if path == "evaluation.benchmark_scores" and isinstance(value, list):
                anchored = any(s.row_anchor is not None for s in spans)
                for i, row in enumerate(value):
                    if not isinstance(row, dict):
                        continue
                    scope = BenchmarkScope(benchmark_id=str(row.get("benchmark") or "unresolved_benchmark"),
                                           setting=row.get("setting") or None)
                    row_action = action if anchored else VerifierAction.WITHHOLD
                    row_reason = reason if anchored else "score_row_without_table_anchor"
                    record(f"{path}[{i}]", row, spans, relation, entity, row_action, row_reason, origin, scope=scope)
                continue
            record(path, value, spans, relation, entity, action, reason, origin)

    card = blank_card()
    indexed: Dict[str, Dict[int, Any]] = {}
    for bnd in bindings:
        if bnd.verifier_action is VerifierAction.WITHHOLD:
            continue
        m = re.match(r"^(.*?)\[(\d+)\]$", bnd.field_path)
        if m:
            indexed.setdefault(m.group(1), {})[int(m.group(2))] = bnd.proposed_value
        else:
            set_field_value(card, bnd.field_path, bnd.proposed_value)
    for path, rows in indexed.items():
        set_field_value(card, path, [rows[i] for i in sorted(rows)])

    # Prose that copies its source is not a synthesis, whatever else is true of it. The
    # writer is told to paraphrase and sometimes does not: on the 2026-09-05 roster seven
    # of twelve cards carried a twelve-word run lifted verbatim out of a README, a paper
    # or a developer blog page. The field is withheld with the run recorded; the card is
    # not lost, which is what refusing the whole export did.
    from .public import source_excerpts

    copied = source_excerpts(card, [f.content or "" for f in bundle.files])
    for path in sorted(copied):
        withhold_field(path, "prose_reproduces_source_excerpt")

    # The final-claim pass: non-blocking, and its absence is recorded rather than
    # implied. A contradiction withholds the field it belongs to.
    factcheck = _run_final_claim_pass(card, bindings, bundle, model_id)
    for path in factcheck.get("contradicted_fields") or []:
        withhold_field(path, "final_claim_pass_contradiction")

    non_quality = [p for p in CARD_FIELD_PATHS if not p.startswith("provenance_and_quality.")]
    missing = [p for p in non_quality if get_field_value(card, p) in (NOT_SPECIFIED, [NOT_SPECIFIED])]
    inapplicable = [p for p in non_quality if get_field_value(card, p) == NOT_APPLICABLE]
    applicable = [p for p in non_quality if p not in inapplicable]
    filled = [p for p in applicable if p not in missing]
    withheld_paths = sorted({bd.field_path.split("[", 1)[0] for bd in bindings
                             if bd.verifier_action == VerifierAction.WITHHOLD})
    coverage = round(len(filled) / len(applicable), 6) if applicable else 0.0
    source_manifest = {f.name: f.sha256 for f in sorted(bundle.files, key=lambda f: f.name)}
    quality = {
        "provenance_and_quality.provenance": {
            "ledger": "artifact.bindings",
            "policy": "one BindingRecord per filled value; withheld bindings stay in the ledger",
            "composer": "auto_benchmarkcard composer with the v5 CardSchema",
            "quote_verify": {k: quote_telem[k] for k in ("emitted", "verified", "rejected")},
            "gates": {"composer": gate_telem.get("summary", {}),
                      "model": model_gate_telem.get("summary", {}),
                      "referent_repair": referent_telem.get("counts", {}),
                      "family_facts_allowed": model_gate_telem.get("family_facts_allowed"),
                      "leaf_unsupported": len(leaf_telemetry)},
            "eav": {k: (len(v) if isinstance(v, list) else v) for k, v in eav_telem.items()},
            "final_claim_pass": {k: factcheck.get(k) for k in ("status", "reason",
                                                               "claims_built",
                                                               "contradicted_fields")},
        },
        "provenance_and_quality.flagged_fields": withheld_paths + sorted(flagged),
        "provenance_and_quality.missing_fields": missing,
        "provenance_and_quality.coverage_score": coverage,
        "provenance_and_quality.card_info": {
            "schema_version": SCHEMA_VERSION, "target": f"{model_id}@{rev}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "composer_commit": bridge.commit,
            "llm": getattr(llm, "model_name", "unknown"),
            "source_manifest": source_manifest, "inapplicable_fields": inapplicable,
            "frame": frame.get("telemetry", {}).get("builder_counts", {}),
        },
    }
    derivation_inputs = {"accepted_paths": sorted(filled), "applicable_paths": sorted(applicable),
                         "withheld_binding_ids": sorted(bd.binding_id for bd in bindings
                                                        if bd.verifier_action == VerifierAction.WITHHOLD),
                         "source_manifest": source_manifest}
    for path, value in quality.items():
        set_field_value(card, path, value)
        exact = _stable_json({"path": path, "inputs": derivation_inputs, "output": value})
        span = EvidenceSpan(source_uri=f"file:///derivations/{model_id}@{rev}", source_revision=bridge.commit,
                            source_sha256=_digest_text(exact),
                            structured_pointer=f"/derivations/{path.replace('.', '/')}",
                            structured_fragment={"path": path, "inputs": derivation_inputs, "output": value})
        record(path, value, [span], RelationToTarget.EXACT_TARGET, target_entity, VerifierAction.ACCEPT,
               "system_computed_from_explicit_binding_ledger", AssignmentOrigin.STRUCTURED_EXPLICIT,
               derivation=DerivationTrace(rule="schema_v5_quality_fields_v1", inputs=derivation_inputs, output=value))

    return CardArtifact(
        schema_version=SCHEMA_VERSION, target=bundle.target, card=card, bindings=tuple(bindings),
        metadata={"condition": "llm_composer_v5", "composer_bridge_commit": bridge.commit,
                  "source_snapshot": rev, "source_hashes": source_manifest,
                  "derived_views": {"README.plain.md": {"from": "README.md", "rule": PLAIN_RULE},
                                    **({"paper.md": {"from": paper_url, "rule": "docling_filtered_text"}} if paper_text else {})},
                  "llm": getattr(llm, "model_name", "unknown"),
                  "frame": frame.get("telemetry", {}), "quote_verify": quote_telem,
                  "gates": {"composer": gate_telem.get("summary", {}),
                            "model": model_gate_telem.get("summary", {}),
                            "referent_repair": referent_telem.get("counts", {}),
                            "family_facts_allowed": model_gate_telem.get("family_facts_allowed")},
                  "leaf_support": leaf_telemetry, "score_conflicts": score_conflicts,
                  "source_excerpts": copied,
                  "final_claim_pass": factcheck,
                  "eee_links": eee_links(b["eee"], model_id),
                  "eav": {k: (len(v) if isinstance(v, list) else v) for k, v in eav_telem.items()},
                  "stage_b": group_telemetry},
        review_events=(), source_bundle=bundle)
