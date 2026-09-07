"""Referent repair and deterministic assignment gates for model-card evidence.

Two passes run on the finalized Stage A records, before EAV and before Stage B.

resolve_model_referents repairs what a benchmark-shaped resolver cannot see. The
pinned composer treats a span that refers to its subject by description ("this
benchmark", "we present") as still about the target, but its vocabulary is benchmark
nouns. On a model card the same sentence is written with model nouns, and without the
guard "Our model outperforms Llama 3.1 8B" has exactly one non-target name in it, so the
resolver's own quote_override rebinds the sentence to Llama. Two rules:

  deictic guard      a sentence whose subject is a model deictic ("this model", "we
                     release", "the checkpoint") belongs to the document's default
                     referent, never to a model merely named later in it;
  comparison rule    a sentence or row that names the target AND another model is a
                     comparison. It is the target's own fact only when the target is the
                     subject, meaning it is named first; otherwise the record is marked
                     as a comparison and the numeric and score gates withhold it;
  sole other model   a quote that names exactly one model, and that model is not the
                     target, is about that model whatever the extraction call declared.
                     This is the pinned composer's own quote_override rule, re-applied
                     over model nodes after the merge so the gates do not depend on which
                     extraction call produced the record.

apply_model_gates then annotates every record with its relation to the target
(model_frame.relation_for) and decides what the field can take:

  score fields (benchmark_scores, human_evals, safety_evals) keep exact_target only, and
    a benchmark_scores quote must also name the target (the row-anchor rule);
  numeric fields withhold on base, derivative, sibling_or_comparison and unknown: the
    structured channel owns those for the target, and a base model's number is not this
    checkpoint's number without an explicit statement;
  family relation is decided first and only by the field policy: allowed on the fields
    FAMILY_ALLOWED_FIELDS names, and only for a base checkpoint whose paper introduces
    it. A base checkpoint's training context IS the family's, and the paper states it in
    family words, so training_data_size is on that list even though it is a number. The
    binding keeps relation family, so a family-scope statement is never displayed as a
    checkpoint-scope fact;
  lineage.base_models and lineage.derivatives are structured-channel fields, so prose
    evidence for them is withheld.

Nothing is dropped to telemetry. Every record the gates refuse comes back in the
withheld list with a reason, and the composer writes it into the ledger as a withheld
binding, so a reader can see what the card decided not to say and why.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from auto_benchmarkcard.tools.composer import frame as frame_mod

from .model_frame import relation_for

SCORE_FIELDS = frozenset({"evaluation.benchmark_scores", "evaluation.human_evals",
                          "evaluation.safety_evals"})
NUMERIC_FIELDS = frozenset({"specifications.num_parameters", "specifications.context_length",
                            "specifications.model_size", "training_context.training_data_size",
                            "training_context.data_cutoff", "access_and_adoption.downloads",
                            "access_and_adoption.likes"})
# Relations a numeric field never takes. family is absent on purpose: it is governed by
# the field policy above, which is stricter about which fields it covers at all.
NUMERIC_REFUSED_RELATIONS = frozenset({"base", "derivative", "sibling_or_comparison", "unknown"})
STRUCTURED_ONLY_FIELDS = frozenset({"lineage.base_models", "lineage.derivatives"})

# Fields whose value may honestly be a family-level statement, and only for a base
# checkpoint whose paper introduces that family: a base checkpoint's training context IS
# the family's training context, and the paper says so in family words. A derivative
# never inherits any of it, and no numeric or score field is on this list.
# Family statements every member of a family may carry, at relation family, whatever its
# stage: what the family is, who built it, what it does, what it is called. These are
# identity, not inheritance. Gating them on "base checkpoint whose paper introduces it"
# left identity.summary empty on 45 of the 74 cards of 2026-09-06, because the README's
# one-line description is a family sentence on nearly every derivative and instruct card
# ("Qwen2 is a language model series ..."). Training data, sizes, cutoffs, adaptations,
# results and the release-level links stay behind that gate: those ARE inheritance.
FAMILY_IDENTITY_FIELDS = frozenset({
    "identity.summary", "identity.model_type", "identity.developed_by",
    "lineage.model_family",
})

FAMILY_ALLOWED_FIELDS = frozenset({
    "identity.summary", "identity.model_type", "identity.developed_by",
    "lineage.model_family",
    "training_context.training_data", "training_context.training_data_size",
    "training_context.data_cutoff", "training_context.adaptations",
    "evaluation.results_summary",
    # the release-level links: a family's report, code repository, system card and
    # citation are the base checkpoint's own. identity.license is deliberately NOT here:
    # the family's GitHub README states the CODE licence, and the weights carry their own
    "links.tech_report", "links.code_repository", "links.system_card", "links.citation",
})

_MODEL_DEICTIC_RE = re.compile(
    r"\b(our|this|the present|the proposed|the resulting|the final)\s+"
    r"(model|models|checkpoint|checkpoints|release|system)\b"
    r"|\bwe (introduce|present|propose|release|train|pretrain|post-train|fine-?tune|build)\b"
    r"|\bours\b", re.IGNORECASE)

_MODEL_NODE_TYPES = frozenset({"base", "family", "sibling", "comparison"})

# A quote that names the target plus this many other models is enumerating the family.
ROSTER_MIN_OTHER_MODELS = 2

# A sentence about "the instruction-tuned models" on a base card, or "the pretrained
# models" on an instruct card, is about the other stage. "The Llama 3.2 instruction-tuned
# text only models ... They outperform many of the available open source and closed chat
# models" was published as the base checkpoint's results_summary on four cards
# (2026-09-06). The frame has no node to move it to, because the sentence names a stage,
# not a model, so it is flagged here and refused by the gates.
_STAGE_ADJ = {
    "post": r"(?:instruction[- ]tuned|instruct|chat|aligned|post-?trained|fine-?tuned|reasoning)",
    "base": r"(?:pre-?trained|base|foundation)",
}
_STAGE_NOUN = r"(?:text[- ]only\s+)?(?:models?|versions?|variants?|checkpoints?)"
_OTHER_STAGE_RE = {
    "base": re.compile(rf"\b{_STAGE_ADJ['post']}\s+{_STAGE_NOUN}\b", re.IGNORECASE),
    "post": re.compile(rf"\b{_STAGE_ADJ['base']}\s+{_STAGE_NOUN}\b", re.IGNORECASE),
}

# A sentence that names BOTH stages describes the release, not the other member of the
# pair, and refusing it costs the card its own description. "available in English, with
# open weights for both pre-trained variants and instruction-tuned variants" was refused
# on google/gemma-2-9b and took identity.model_type and training_context.adaptations with
# it (2026-09-07). Failure class: both_stages_sentence_refused_as_other_stage.
_COORD = r"(?:\s*[,/&+]\s*|\s+(?:and|or|as well as)\s+)"
_BOTH_STAGES_RE = re.compile(
    rf"\b{_STAGE_ADJ['base']}(?:\s+{_STAGE_NOUN})?{_COORD}{_STAGE_ADJ['post']}\b"
    rf"|\b{_STAGE_ADJ['post']}(?:\s+{_STAGE_NOUN})?{_COORD}{_STAGE_ADJ['base']}\b",
    re.IGNORECASE)

# The sole-other-model rule must not follow a credit line to the technology a family was
# built from. "Gemma is a family of lightweight, state-of-the-art open models from Google,
# built from the same research and technology used to create the Gemini models" names
# Gemini once and nothing else, and rebinding it to Gemini emptied identity.summary on
# every Gemma card (2026-09-07). Failure class: technology_source_steals_the_referent.
_TECHNOLOGY_SOURCE_RE = re.compile(
    r"\b(?:built|created|developed|derived|made|trained)\s+(?:from|with|using|on|upon)\s+"
    r"(?:the\s+)?(?:same\s+)?"
    r"(?:research|technology|techniques?|methods?|recipe|architecture|codebase|infrastructure)\b"
    r"|\bthe\s+same\s+(?:research|technology|techniques?|methods?|recipe|architecture|codebase)\b"
    r"|\b(?:based\s+on|inspired\s+by)\s+the\s+(?:same\s+)?"
    r"(?:research|technology|approach|recipe|architecture|codebase)\b",
    re.IGNORECASE)


def names_both_stages(text: str) -> bool:
    """Whether a sentence names the pre-trained and the post-trained member together."""
    return bool(_BOTH_STAGES_RE.search(text or ""))


_POST_SUFFIXES = ("-instruct", "-it", "-chat", "-sft", "-dpo", "-rl", "-rlvr", "-thinking")
_BASE_SUFFIXES = ("-base", "-pt")


def _stage_of(frame: Dict[str, Any]) -> Optional[str]:
    """Which member of a base/post-trained pair the target is, or None.

    From the repo name when it says so, else from the frame: a sibling node named
    "<target>-Instruct" makes the target the base member, "<target>-Base" the
    post-trained one. Llama-3.2-1B carries no stage token, and its README names
    Llama-3.2-1B-Instruct on every other line."""
    nodes = frame.get("nodes", [])
    target = next((n for n in nodes if n.get("id") == frame.get("target_id", "target")), None)
    if not target:
        return None
    from .table_scores import target_stage

    name = target.get("name", "")
    stage = target_stage(name)
    if stage:
        return stage
    low = name.lower()
    for node in nodes:
        if node.get("type") not in ("sibling", "base", "comparison"):
            continue
        for alias in [node.get("name", ""), *(node.get("aliases") or [])]:
            a = (alias or "").lower().replace(" ", "-")
            if a.startswith(low + "-"):
                rest = a[len(low):]
                if rest in _POST_SUFFIXES:
                    return "base"
                if rest in _BASE_SUFFIXES:
                    return "post"
    return None


def _model_nodes(frame: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {n["id"]: n for n in frame.get("nodes", []) if n.get("type") in _MODEL_NODE_TYPES}


def _first_index(frame: Dict[str, Any], node_id: str, text: str) -> int:
    """Where a node is first named in the text, or a large number when it is not."""
    node = next((n for n in frame.get("nodes", []) if n.get("id") == node_id), None)
    if node is None:
        return 10 ** 6
    low = text.lower()
    best = 10 ** 6
    for name in [node.get("name", ""), *(node.get("aliases") or [])]:
        name = (name or "").strip().lower()
        if not name:
            continue
        at = low.find(name)
        if at >= 0:
            best = min(best, at)
    return best


def resolve_model_referents(records: List[Dict[str, Any]], frame: Optional[Dict[str, Any]],
                            telemetry: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Apply the deictic guard and the comparison rule. Returns new records."""
    if not frame:
        return list(records or [])
    telem = telemetry if telemetry is not None else {}
    counts = telem.setdefault("counts", {})
    target_id = frame.get("target_id", "target")
    defaults = (frame.get("meta") or {}).get("default_referent") or {}
    model_nodes = _model_nodes(frame)

    def bump(key: str) -> None:
        counts[key] = counts.get(key, 0) + 1

    out: List[Dict[str, Any]] = []
    for rec in records or []:
        rec = dict(rec)
        quote = rec.get("quote", "") or ""
        hits = frame_mod.match_mention(frame, quote)
        named_others = [h for h in hits if h != target_id and h in model_nodes]
        target_named = target_id in hits
        default = defaults.get(rec.get("doc", ""), target_id)
        if _MODEL_DEICTIC_RE.search(quote):
            rec["deictic"] = True
            if not target_named:
                deictic_at = _MODEL_DEICTIC_RE.search(quote).start()
                others_at = min((_first_index(frame, h, quote) for h in named_others),
                                default=10 ** 6)
                # the deictic is the subject when nothing else is named, or when it comes
                # first; a model named after it is the object of the comparison
                if not named_others or deictic_at < others_at:
                    if rec.get("referent") != default:
                        bump("deictic_to_default")
                        rec["referent"] = default
                        rec["referent_resolution"] = "model_deictic_default"
        stage = _stage_of(frame)
        if stage and not target_named and _OTHER_STAGE_RE[stage].search(quote):
            if names_both_stages(quote):
                # the sentence covers this checkpoint's stage as well, so it is a
                # statement about the release and not about the other member
                bump("both_stages_sentence_kept")
            else:
                rec["other_stage"] = True
                bump("other_stage_sentence")
        if target_named and len(named_others) >= ROSTER_MIN_OTHER_MODELS:
            # A roster: the quote names the target and two or more of its siblings, so it
            # enumerates the family, whatever order they come in. Position cannot decide
            # this the way it decides a two-model comparison, because the target is often
            # the first item of the list ("models of 5 sizes, including Qwen2-0.5B,
            # Qwen2-1.5B, ..."), which made target_at < others_at and stamped a family
            # roster on one checkpoint as its own identity.model_type.
            family = next((h for h in named_others
                           if model_nodes[h].get("type") == "family"), None)
            rec["comparison"] = True
            if family is not None:
                rec["referent"] = family
                rec["referent_resolution"] = "roster_sentence_names_the_family"
                bump("roster_sentence_to_family")
            else:
                rec["referent_resolution"] = "roster_sentence_without_a_family_node"
                bump("roster_sentence_no_family_node")
        elif target_named and named_others:
            target_at = _first_index(frame, target_id, quote)
            others_at = min(_first_index(frame, h, quote) for h in named_others)
            rec["comparison"] = target_at > others_at
            bump("comparison_sentence" if rec["comparison"] else "target_is_subject")
        elif len(named_others) == 1 and not rec.get("deictic"):
            # exactly one model is named and it is not the target: the quote is about
            # that model, whatever the extraction call declared it to be, unless it is
            # named as the technology this one was built from, which is a credit line
            # and not the subject of the sentence
            source_clause = _TECHNOLOGY_SOURCE_RE.search(quote)
            if source_clause and _first_index(frame, named_others[0], quote) > source_clause.start():
                rec["technology_source"] = True
                rec["referent_resolution"] = "technology_source_named_not_the_subject"
                bump("technology_source_kept_the_subject")
            elif rec.get("referent") != named_others[0]:
                bump("sole_other_model")
                rec["referent"] = named_others[0]
                rec["referent_resolution"] = "sole_other_model_named"
        out.append(rec)
    telem.setdefault("model_nodes", len(model_nodes))
    return out


def apply_model_gates(records: List[Dict[str, Any]], frame: Optional[Dict[str, Any]],
                      telemetry: Optional[Dict[str, Any]] = None
                      ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Annotate every record with its relation and split it into (kept, withheld).

    A withheld record carries `withhold_reason` and its relation, so the composer can
    write it into the ledger instead of losing it to a counter.
    """
    if not frame:
        return list(records or []), []
    telem = telemetry if telemetry is not None else {}
    actions = telem.setdefault("actions", [])
    summary = telem.setdefault("summary", {})
    meta = frame.get("meta") or {}
    family_ok = bool(meta.get("is_base_checkpoint")) and meta.get("paper_tier") == "introduces_target"
    telem["family_facts_allowed"] = family_ok

    def log(gate, action, rec, relation):
        actions.append({"gate": gate, "field": rec.get("field"), "referent": rec.get("referent", ""),
                        "relation": relation, "action": action})
        bucket = summary.setdefault(gate, {})
        bucket[action] = bucket.get(action, 0) + 1

    kept: List[Dict[str, Any]] = []
    withheld: List[Dict[str, Any]] = []

    def refuse(rec, gate, reason, relation):
        log(gate, "withhold", rec, relation)
        withheld.append({**rec, "withhold_reason": reason, "withhold_gate": gate})

    for rec in records or []:
        field = rec.get("field", "")
        relation = relation_for(rec.get("referent", ""), frame)
        rec = {**rec, "relation": relation}
        if field in STRUCTURED_ONLY_FIELDS:
            refuse(rec, "structured_only", "lineage_is_structured_channel_only", relation)
            continue
        if rec.get("other_stage"):
            # whatever node the sentence was moved to, it describes the other stage of
            # this pair, which no field policy admits as this checkpoint's fact
            refuse(rec, "other_stage", "sentence_about_the_other_stage", relation)
            continue
        if (rec.get("referent_resolution") == "roster_sentence_without_a_family_node"
                and relation == "exact_target"):
            # a roster with no family node to move to is still not a fact about one of
            # the checkpoints it lists
            refuse(rec, "roster_sentence", "roster_sentence_enumerates_the_family", relation)
            continue
        if relation == "family":
            # decided by the field policy alone, before the score and numeric gates
            if field not in FAMILY_ALLOWED_FIELDS:
                refuse(rec, "family_field_policy", "family_statement_not_allowed_for_this_field",
                       relation)
                continue
            if not family_ok and field not in FAMILY_IDENTITY_FIELDS:
                refuse(rec, "family_not_a_base_checkpoint",
                       "family_statement_not_this_checkpoint", relation)
                continue
        if field in SCORE_FIELDS:
            if relation != "exact_target":
                refuse(rec, "score_relation", f"score_of_{relation}_not_this_checkpoint", relation)
                continue
            if rec.get("comparison"):
                refuse(rec, "score_comparison_sentence",
                       "comparison_sentence_names_another_model_first", relation)
                continue
            if field == "evaluation.benchmark_scores" and not _names_target(frame, rec.get("quote", "")):
                refuse(rec, "score_row_anchor", "score_row_does_not_name_the_target", relation)
                continue
        if field in NUMERIC_FIELDS:
            if relation in NUMERIC_REFUSED_RELATIONS:
                refuse(rec, "numeric_relation", f"numeric_value_of_{relation}_not_this_checkpoint",
                       relation)
                continue
            if rec.get("comparison"):
                refuse(rec, "numeric_comparison_sentence",
                       "comparison_sentence_names_another_model_first", relation)
                continue
        if relation == "family":
            log("family_allowed", "annotate", rec, relation)
        elif relation != "exact_target":
            log("relation", "annotate", rec, relation)
        kept.append(rec)
    summary["withheld_total"] = len(withheld)
    return kept, withheld


def _names_target(frame: Dict[str, Any], text: str) -> bool:
    return frame.get("target_id", "target") in frame_mod.match_mention(frame, text)
