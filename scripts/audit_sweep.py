"""Independent deterministic sweep over a run's frozen card artifacts.

Imports nothing from model_cards.core or auto_benchmarkcard on purpose: every predicate
is reimplemented from its documented contract, so a bug shared with the generator cannot
make the generator look correct. Reports counts and the first few examples of each
problem class; exits non-zero when any problem class is non-empty.

    python scripts/audit_sweep.py runs/batch250f bundles250-v2 [schema/model-card.schema.json]
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RUN = Path(sys.argv[1])
BUNDLES = Path(sys.argv[2])
SCHEMA = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else None

_TYPO = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"', "‟": '"',
         "´": "'", "ʼ": "'", "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-"}
_TYPO_RE = re.compile("|".join(re.escape(c) for c in _TYPO))
_WS_RE = re.compile(r"\s+")


def norm(text: str) -> str:
    return _WS_RE.sub(" ", _TYPO_RE.sub(lambda m: _TYPO[m.group(0)], text)).strip()


def resolve(doc, pointer):
    cur = doc
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            if not token.isdigit() or int(token) >= len(cur):
                raise KeyError(pointer)
            cur = cur[int(token)]
        elif isinstance(cur, dict):
            if token not in cur:
                raise KeyError(pointer)
            cur = cur[token]
        else:
            raise KeyError(pointer)
    return cur


def frontmatter(readme: str):
    m = re.match(r"^---\n(.*?)\n---", readme, re.S)
    if not m:
        return {}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


SCORE_FIELDS = {"evaluation.benchmark_scores", "evaluation.human_evals", "evaluation.safety_evals"}
NUMERIC_FIELDS = {"specifications.num_parameters", "specifications.context_length",
                  "specifications.model_size", "training_context.training_data_size",
                  "access_and_adoption.downloads", "access_and_adoption.likes"}
REFUSED = {"base", "derivative", "sibling_or_comparison", "unknown"}
FAMILY_ALLOWED = {"identity.summary", "identity.model_type", "identity.developed_by",
                  "lineage.model_family", "training_context.training_data",
                  "training_context.training_data_size", "training_context.data_cutoff",
                  "training_context.adaptations", "evaluation.results_summary",
                  "links.tech_report", "links.code_repository", "links.system_card", "links.citation"}
LEAK_PATTERNS = ((r"/Users/", "local_path"), (r"hf_[A-Za-z0-9]{20,}", "hf_token"),
                 (r"sk-[A-Za-z0-9_-]{20,}", "api_key"), (r'"bindings"', "ledger"),
                 (r'"exact_text"', "evidence_text"))

counts = Counter()
problems = defaultdict(list)


def note(kind, card, detail):
    counts[kind] += 1
    if len(problems[kind]) < 5:
        problems[kind].append((card, detail))


cards = [p for p in sorted(RUN.glob("*.json"))
         if not p.name.endswith(".public.json") and p.name not in {"run-manifest.json", "readout.json"}]
try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None

for path in cards:
    doc = json.loads(path.read_text())
    slug = path.stem
    counts["cards"] += 1
    target = doc["target"]["model_id"]
    embedded = {f["source_uri"]: f for f in doc["source_bundle"]["files"]}
    for uri, entry in embedded.items():
        content = entry.get("content")
        if content is None:
            note("embedded_file_without_content", slug, uri); continue
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != entry.get("sha256"):
            note("embedded_sha_mismatch", slug, uri)
    frozen = BUNDLES / slug / "source_bundle" / "source-bundle.json"
    if frozen.exists():
        for entry in json.loads(frozen.read_text())["files"]:
            counts["frozen_files_compared"] += 1
            live = embedded.get(entry["source_uri"])
            if live is None:
                note("frozen_file_absent_from_card", slug, entry["source_uri"])
            elif live.get("content") != entry.get("content"):
                note("frozen_content_differs_from_card", slug, entry["source_uri"])
    normalized = {uri: norm(f["content"]) for uri, f in embedded.items() if f.get("content") is not None}
    family_ok = bool((doc["metadata"].get("gates") or {}).get("family_facts_allowed"))
    accepted = 0
    for b in doc["bindings"]:
        field = b.get("field_path", ""); base_field = field.split("[", 1)[0]
        relation = b.get("relation_to_target")
        if b.get("verifier_action") != "accept":
            counts["withheld_bindings"] += 1
            if not b.get("verifier_reason"):
                note("withheld_without_reason", slug, b.get("binding_id"))
            continue
        accepted += 1
        for ev in b.get("evidence") or []:
            text, uri, pointer = ev.get("exact_text"), ev.get("source_uri"), ev.get("structured_pointer")
            entry = embedded.get(uri)
            if text is not None:
                counts["quotes_checked"] += 1
                body = normalized.get(uri)
                if body is None:
                    note("quote_uri_not_in_bundle", slug, f"{field} {uri}"); continue
                s, e = ev.get("start_offset"), ev.get("end_offset")
                if s is None or e is None:
                    note("quote_without_offsets", slug, field)
                elif body[s:e] == text:
                    counts["quotes_verbatim_at_offset"] += 1
                elif text in body:
                    note("quote_offsets_point_elsewhere", slug, f"{field} {text[:50]!r}")
                else:
                    note("quote_not_in_source", slug, f"{field} {text[:50]!r}")
            elif pointer:
                counts["structured_pointers"] += 1
                if entry is None:
                    if uri.startswith(("hf://", "file:///derivations/")):
                        counts["derived_pointers"] += 1
                    else:
                        note("pointer_uri_not_in_bundle", slug, f"{field} {uri}")
                    continue
                name = entry["name"]
                try:
                    document = {"card_data": frontmatter(entry["content"])} if name == "README.md" \
                        else json.loads(entry["content"])
                    found = resolve(document, pointer)
                except (KeyError, ValueError):
                    note("pointer_does_not_resolve", slug, f"{name} {pointer}"); continue
                if found != ev.get("structured_fragment"):
                    note("pointer_fragment_differs", slug, f"{name} {pointer}")
                else:
                    counts["pointers_resolved"] += 1
            else:
                note("evidence_without_quote_or_pointer", slug, field)
        if base_field in SCORE_FIELDS | NUMERIC_FIELDS and relation in REFUSED:
            note("refused_relation_on_numeric_field", slug, f"{field} {relation}")
        if relation == "family":
            if base_field not in FAMILY_ALLOWED:
                note("family_value_outside_policy", slug, field)
            elif not family_ok and base_field not in {"identity.summary", "identity.model_type",
                                                      "identity.developed_by", "lineage.model_family"}:
                note("family_value_without_base_checkpoint", slug, field)
            else:
                counts["family_values_within_policy"] += 1
        if base_field == "evaluation.benchmark_scores":
            counts["score_rows"] += 1
            if relation != "exact_target":
                note("score_row_not_exact_target", slug, relation)
            if not any((ev.get("row_anchor") or ev.get("structured_pointer")) for ev in b.get("evidence") or []):
                note("score_without_row_anchor", slug, str(b.get("proposed_value"))[:60])
        if base_field == "risks.possible_risks":
            counts["risk_rows"] += 1
            if not any(ev.get("structured_pointer", "").startswith("/risks/") for ev in b.get("evidence") or []):
                note("risk_without_taxonomy_pointer", slug, field)
        if relation == "exact_target":
            cid = (b.get("claim_entity") or {}).get("model_id") or ""
            if cid and cid.lower() != target.lower():
                note("exact_target_names_another_model", slug, f"{field} {cid}")
    counts["accepted_bindings"] += accepted
    public = path.parent / (path.stem + ".public.json")
    if public.exists():
        payload = json.loads(public.read_text()); counts["public_cards"] += 1
        if SCHEMA is not None and jsonschema is not None:
            try:
                jsonschema.validate(payload, SCHEMA); counts["public_schema_valid"] += 1
            except jsonschema.ValidationError as exc:
                note("public_schema_invalid", slug, str(exc.message)[:100])
        if "provenance_and_quality" in payload:
            note("private_section_in_public_export", slug, "")
        blob = json.dumps(payload)
        for pattern, name in LEAK_PATTERNS:
            if re.search(pattern, blob):
                note(f"public_export_leaks_{name}", slug, "")
    else:
        note("card_without_public_export", slug, "")

print("== totals ==")
for key in sorted(counts):
    print(f"  {key}: {counts[key]}")
print("\n== problems ==")
if not problems:
    print("  none")
for kind in sorted(problems, key=lambda k: -counts[k]):
    print(f"  {kind}: {counts[kind]}")
    for card, detail in problems[kind]:
        print(f"      {card} | {detail}")
sys.exit(1 if problems else 0)
