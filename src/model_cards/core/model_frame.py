"""Referent frame for a model target, in the composer's frame shape.

Nodes (same dict shape the benchmark frame uses, so evidence._resolve_referent,
match_mention, EAV and the Stage-B digest work unchanged):
  target       this model at its pinned revision (aliases: repo name spellings, README title)
  base         base model(s) from the repo's base_model tags (structured, explicit edge)
  family       the developer-stated family (derived from the repo name; aliases from prose)
  sibling      other checkpoints, sizes or variants of the family (LLM-proposed, literal-guarded)
  comparison   models the sources compare against (LLM-proposed, literal-guarded)
  benchmark    benchmarks from the model-index and the EEE join (structured), plus prose
  metric       metrics from the model-index

Every evidence item then gets a RELATION to the target from its resolved referent
(relation_for): exact_target, base, derivative, sibling_or_comparison, family, unknown.
relation_for reports what the referent IS; whether a given field may carry it is the
gates' per-field policy. Nothing here guesses.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from auto_benchmarkcard.tools.composer import frame as frame_mod

logger = logging.getLogger(__name__)

_SIZE_TOKEN_RE = re.compile(r"^\d+(?:\.\d+)?[bm]$", re.IGNORECASE)
_DATE_TOKEN_RE = re.compile(r"^(?:\d{4}|\d{6}|\d{8}|\d{2}\d{2})$")
_STAGE_TOKENS = {"instruct", "chat", "it", "sft", "dpo", "rl", "rlhf", "rlvr", "base", "hf",
                 "preview", "think", "thinking", "reasoning", "gguf", "awq", "gptq", "fp8",
                 "int4", "int8", "bnb", "4bit", "8bit", "instruct-v2", "v0.1", "v0.2"}
_DERIVATIVE_TOKENS = {"instruct", "chat", "it", "sft", "dpo", "rl", "rlhf", "rlvr", "think",
                      "thinking", "reasoning", "tulu", "distill", "merge", "gguf", "awq",
                      "gptq", "fp8", "int4", "int8"}
MAX_LLM_NODES = 16
# The frame pass is an extraction call, so it runs with a server-enforced JSON schema and a
# small token cap. Without them a reasoning model answers with an unbounded think trace:
# the 2026-09-04 unstructured call ran past 10 minutes on one README and never returned.
FRAME_MAX_TOKENS = 2048
_NAME_LIST = {"type": "array", "maxItems": MAX_LLM_NODES,
              "items": {"type": "string", "maxLength": 80}}
FRAME_SCHEMA = {
    "type": "object",
    "properties": {"siblings": dict(_NAME_LIST), "comparisons": dict(_NAME_LIST),
                   "family_aliases": dict(_NAME_LIST)},
    "required": ["siblings", "comparisons", "family_aliases"],
    "additionalProperties": False,
}


def _frame_call(llm_handler, prompt: str) -> str:
    """One structured, token-capped frame call. Handlers without the per-call cap
    (test doubles) fall back to plain generate with the same schema."""
    if hasattr(llm_handler, "generate_with_meta"):
        text, _stop = llm_handler.generate_with_meta(
            prompt, response_format=FRAME_SCHEMA, max_completion_tokens=FRAME_MAX_TOKENS)
        return text
    return llm_handler.generate(prompt, response_format=FRAME_SCHEMA)

RELATIONS = ("exact_target", "base", "derivative", "sibling_or_comparison",
             "family", "unknown")


def _norm_key(name: str) -> str:
    """Lowercase alphanumerics only, so OLMo-2-1124-7B-Instruct, OLMo 2 1124 7B Instruct
    and olmo21124 7binstruct compare equal."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unnamed"


def _name_tokens(repo_name: str) -> List[str]:
    # dots stay inside a token so "3.1" and "v0.1" survive as one version token
    return [t for t in re.split(r"[-_/ ]+", repo_name) if t]


def family_name(model_id: str) -> str:
    """The family a repo name belongs to: the name minus size, date, stage and
    quantization tokens, with hyphens as spaces (OLMo-2-1124-7B -> "OLMo 2",
    Llama-3.1-8B-Instruct -> "Llama 3.1", Qwen3-8B-Base -> "Qwen3")."""
    kept = []
    for tok in _name_tokens(model_id.rsplit("/", 1)[-1]):
        low = tok.lower()
        if _SIZE_TOKEN_RE.match(low) or _DATE_TOKEN_RE.match(low) or low in _STAGE_TOKENS:
            continue
        if re.fullmatch(r"\d+x\d+[bm]", low):  # 8x7B
            continue
        kept.append(tok)
    return " ".join(kept) if kept else model_id.rsplit("/", 1)[-1]


def is_derivative_name(model_id: str) -> bool:
    """Whether the repo name itself declares a post-trained or converted variant."""
    return any(t.lower() in _DERIVATIVE_TOKENS for t in _name_tokens(model_id.rsplit("/", 1)[-1]))


def _target_node(model_id: str, revision: str, hf_meta: Dict[str, Any]) -> Dict[str, Any]:
    repo_name = model_id.rsplit("/", 1)[-1]
    aliases = [model_id, repo_name.replace("-", " ")]
    # The prose form a paper uses for this checkpoint: the family name plus the size
    # token ("OLMo 2 7B"), and for a post-trained variant the stage token as well
    # ("OLMo 2 7B Instruct"); a base checkpoint never claims the variant's mentions and
    # a variant never claims the bare base mention.
    fam = family_name(model_id)
    tokens = _name_tokens(repo_name)
    sizes = [t for t in tokens if _SIZE_TOKEN_RE.match(t) or re.fullmatch(r"\d+x\d+[bm]", t, re.IGNORECASE)]
    stages = [t for t in tokens if t.lower() in _DERIVATIVE_TOKENS]
    for size in sizes:
        suffix = " ".join([size] + stages)
        hyphen_fam = fam.replace(" ", "-")
        # the same checkpoint is written "OLMo 2 7B", "OLMo-2-7B" and "OLMo-2 7B" in the
        # same paper; missing the mixed form sent the model's own mentions to the family
        aliases.append(f"{fam} {suffix}")
        aliases.append(f"{fam}-{suffix.replace(' ', '-')}")
        aliases.append(f"{hyphen_fam}-{suffix.replace(' ', '-')}")
        aliases.append(f"{hyphen_fam} {suffix}")
    # a release-date token next to the size token is written in either order by the
    # developer's own README (OLMo-2-1124-7B-Instruct vs OLMo-2-7B-1124-Instruct)
    parts = repo_name.split("-")
    for i in range(len(parts) - 1):
        a, b = parts[i], parts[i + 1]
        if (re.fullmatch(r"\d{4}", a) and _SIZE_TOKEN_RE.match(b)) or (_SIZE_TOKEN_RE.match(a) and re.fullmatch(r"\d{4}", b)):
            swapped = parts[:i] + [b, a] + parts[i + 2:]
            aliases.append("-".join(swapped))
            aliases.append(" ".join(swapped))
    readme = hf_meta.get("readme_markdown") or ""
    m = re.search(r"^#{1,2}\s+(\S.*?)\s*$", frame_mod._readme_frontmatter_stripped(readme)[:2000],
                  re.MULTILINE)
    if m:
        heading = m.group(1).strip()
        key = re.sub(r"[^a-z0-9]", "", repo_name.lower())
        hkey = re.sub(r"[^a-z0-9]", "", heading.lower())
        if hkey and (key in hkey or hkey in key) and len(heading) <= 80:
            aliases.append(heading)
    return {"id": "target", "type": "target", "name": repo_name, "aliases": aliases,
            "revision": revision,
            "description": f"The target checkpoint {model_id}@{revision[:12]} this card documents."}


def _base_nodes(hf_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes = []
    for tag in hf_meta.get("base_model_tags") or []:
        if not isinstance(tag, str) or not tag.strip():
            continue
        base = tag.strip()
        if base.startswith(("finetune:", "adapter:", "merge:", "quantized:")):
            base = base.split(":", 1)[1]
        nodes.append({"id": "base:" + _slug(base), "type": "base", "name": base,
                      "aliases": [base.rsplit("/", 1)[-1], base.rsplit("/", 1)[-1].replace("-", " ")],
                      "description": "Base model declared by the repo's base_model tag (explicit edge)."})
    return nodes


def _benchmark_and_metric_nodes(hf_meta: Dict[str, Any], eee: Optional[Dict[str, Any]]):
    bench: Dict[str, Dict[str, Any]] = {}
    metrics: Dict[str, Dict[str, Any]] = {}

    def add_bench(name, desc):
        if isinstance(name, str) and name.strip():
            key = _slug(name)
            bench.setdefault(key, {"id": "benchmark:" + key, "type": "benchmark", "name": name.strip(),
                                   "aliases": [], "description": desc})

    for entry in hf_meta.get("model_index") or []:
        for res in (entry or {}).get("results") or []:
            ds = (res or {}).get("dataset") or {}
            add_bench(ds.get("name") or ds.get("type"), "Benchmark listed in the card's model-index.")
            for met in res.get("metrics") or []:
                mname = met.get("name") or met.get("type")
                if isinstance(mname, str) and mname.strip():
                    key = _slug(mname)
                    metrics.setdefault(key, {"id": "metric:" + key, "type": "metric", "name": mname.strip(),
                                             "aliases": [], "role": "unknown",
                                             "description": "Metric listed in the card's model-index."})
    for name in ((eee or {}).get("benchmarks") or {}):
        add_bench(name, "Benchmark with an Every Eval Ever record for this exact model id.")
    return list(bench.values()), list(metrics.values())


def _parse_names(raw) -> Dict[str, List[str]]:
    """{"siblings": [...], "comparisons": [...], "family_aliases": [...]} from the LLM reply."""
    out = {"siblings": [], "comparisons": [], "family_aliases": []}
    if not isinstance(raw, str):
        return out
    block = frame_mod._extract_json_list(raw)
    obj = None
    start = raw.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(raw[start:i + 1])
                    except ValueError:
                        obj = None
                    break
    if isinstance(obj, dict):
        for key in out:
            vals = obj.get(key)
            if isinstance(vals, list):
                out[key] = [v.strip() for v in vals if isinstance(v, str) and 2 <= len(v.strip()) <= 80]
    elif block:
        try:
            vals = json.loads(block)
            out["siblings"] = [v.strip() for v in vals if isinstance(v, str)]
        except ValueError:
            pass
    return out


def _llm_prompt(target_name: str, family: str, excerpts: List[Tuple[str, str]]) -> str:
    parts = [
        f'You are indexing documentation about the model checkpoint "{target_name}" '
        f'(family: "{family}").',
        "From the material below, list:\n"
        '- "siblings": other checkpoints, sizes, or variants of the SAME family that are named '
        f'(e.g. other parameter sizes, base vs instruct variants), NOT "{target_name}" itself;\n'
        '- "comparisons": OTHER models (different families) the material compares against or '
        "reports results for;\n"
        '- "family_aliases": other spellings of the family name that occur literally.',
        'Answer with ONLY a JSON object: {"siblings": [...], "comparisons": [...], '
        '"family_aliases": [...]}. Use names exactly as they appear in the text.',
    ]
    for label, text in excerpts:
        if text:
            parts.append(f"{label}:\n{text}")
    return "\n\n".join(parts)


def build_model_frame(model_id: str, revision: str, hf_meta: Dict[str, Any], *,
                      doc_index=None, paper_text: str = "", github_text: str = "",
                      eee: Optional[Dict[str, Any]] = None, paper_tier: str = "none",
                      llm_handler=None) -> Dict[str, Any]:
    """The model's referent frame: {"target_id", "nodes", "telemetry", "meta"}.

    meta records the derivation inputs the relation rule needs (family id, whether the
    target is a base checkpoint, the paper binding tier) and the per-source default
    referent the extraction calls pass to verify_items.
    """
    nodes: List[Dict[str, Any]] = []
    index: Dict[str, Dict[str, Any]] = {}
    counts: Dict[str, int] = {}
    merged = 0

    target = _target_node(model_id, revision, hf_meta)
    frame_mod._add_node(nodes, index, target)
    counts["target"] = 1

    fam = family_name(model_id)
    family_node = {"id": "family:" + _slug(fam), "type": "family", "name": fam,
                   "aliases": [fam.replace(" ", "-"), fam.replace(" ", "")],
                   "description": "The model family this checkpoint belongs to (derived from the repo name)."}
    counts["family"] = 1 if frame_mod._add_node(nodes, index, family_node) else 0

    for label, batch in (("base", _base_nodes(hf_meta)),):
        added = 0
        for node in batch:
            if frame_mod._add_node(nodes, index, node):
                added += 1
            else:
                merged += 1
        counts[label] = added
    bench_nodes, metric_nodes = _benchmark_and_metric_nodes(hf_meta, eee)
    for label, batch in (("benchmarks", bench_nodes), ("metrics", metric_nodes)):
        added = 0
        for node in batch:
            if frame_mod._add_node(nodes, index, node):
                added += 1
            else:
                merged += 1
        counts[label] = added

    telemetry: Dict[str, Any] = {"llm_pass": "skipped"}
    counts["siblings_llm"] = counts["comparisons_llm"] = counts["family_aliases_llm"] = 0
    readme = hf_meta.get("readme_markdown") or ""
    presence = [t for t in (readme, paper_text, github_text) if t]
    if llm_handler is not None and presence:
        try:
            excerpts: List[Tuple[str, str]] = [("Model card README", readme[:frame_mod.HEAD_CHARS])]
            if paper_text:
                paper_excerpts, presence_text = frame_mod._ranked_paper_excerpts(doc_index, paper_text)
                excerpts.append(("Paper text (excerpts)", "\n[...]\n".join(paper_excerpts)))
                presence.append(presence_text)
            if github_text:
                excerpts.append(("GitHub README", github_text[:frame_mod.HEAD_CHARS]))
            names = _parse_names(_frame_call(llm_handler, _llm_prompt(target["name"], fam, excerpts)))
            # the target's own names never become another node or a family alias: a
            # family alias equal to the target's name made every exact mention of the
            # target resolve to the family, which reads as base on a derivative
            own = {_norm_key(a) for a in [target["name"], *target.get("aliases", [])]}
            for key, ntype, desc in (("siblings", "sibling", "Sibling checkpoint, size or variant named in the sources (LLM pass, literal-verified)."),
                                     ("comparisons", "comparison", "Model compared against in the sources (LLM pass, literal-verified).")):
                kept = 0
                for name in names[key]:
                    if kept >= MAX_LLM_NODES:
                        break
                    if _norm_key(name) in own:
                        counts["own_name_dropped"] = counts.get("own_name_dropped", 0) + 1
                        continue
                    if not any(frame_mod._token_present(t, name) for t in presence):
                        continue
                    node = {"id": f"{ntype}:" + _slug(name), "type": ntype, "name": name,
                            "aliases": [], "description": desc}
                    if frame_mod._add_node(nodes, index, node):
                        kept += 1
                    else:
                        merged += 1
                counts[key + "_llm"] = kept
            for alias in names["family_aliases"]:
                if _norm_key(alias) in own:
                    counts["own_name_dropped"] = counts.get("own_name_dropped", 0) + 1
                    continue
                if any(frame_mod._token_present(t, alias) for t in presence):
                    if frame_mod._add_node(nodes, index, {"id": family_node["id"], "type": "family",
                                                          "name": fam, "aliases": [alias],
                                                          "description": family_node["description"]}):
                        pass
                    counts["family_aliases_llm"] += 1
            telemetry["llm_pass"] = "ok"
        except Exception as exc:
            logger.warning("model frame LLM pass failed: %s", exc)
            telemetry["llm_pass"] = "failed"
            telemetry["llm_pass_error"] = str(exc)[:200]

    telemetry["builder_counts"] = counts
    telemetry["merged_duplicates"] = merged
    telemetry["total_nodes"] = len(nodes)
    is_base = not is_derivative_name(model_id) and not (hf_meta.get("base_model_tags") or [])
    meta = {
        "model_id": model_id, "revision": revision, "family_id": family_node["id"],
        "is_base_checkpoint": is_base, "paper_tier": paper_tier,
        "default_referent": {
            "hf_readme": "target",
            "docling": family_node["id"] if paper_tier in ("introduces_target", "family_reference") else "target",
            "abstract": family_node["id"],
            "github_readme": family_node["id"],
            "html": "target",
        },
    }
    return {"target_id": "target", "nodes": nodes, "telemetry": telemetry, "meta": meta}


def relation_for(referent: str, frame: Dict[str, Any]) -> str:
    """The evidence item's relation to the target from its resolved referent node."""
    nodes = frame_mod.node_lookup(frame)
    node = nodes.get(referent or "")
    meta = frame.get("meta") or {}
    if node is None or referent == frame.get("target_id", "target"):
        return "exact_target" if node is not None else "unknown"
    ntype = node.get("type")
    if ntype == "base":
        return "base"
    if ntype in ("sibling", "comparison"):
        return "sibling_or_comparison"
    if ntype == "family":
        # A family statement stays a family statement. Whether this card may use it is a
        # per-field policy decision (model_gates.FAMILY_ALLOWED_FIELDS), not a relabelling:
        # calling it exact_target hid a family-scope claim behind a checkpoint-scope
        # binding, and calling it base or unknown threw away the recall.
        return "family"
    if ntype in ("benchmark", "metric"):
        # a score row's referent is the MODEL it names; a quote resolved to a benchmark
        # node names no model, so nothing ties it to the target
        return "unknown"
    return "unknown"
