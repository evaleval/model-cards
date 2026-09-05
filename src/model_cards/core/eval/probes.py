"""Splice probes: does the card carry a value that belongs to another checkpoint?

A probe takes a card value and asks whether the same string appears in the sources
attached to a DIFFERENT entity. If it does, the value may have been spliced: lifted from
a sentence about the base model, a sibling, or a comparison model.

The selection predicate is deliberately independent of the resolver. The composer decides
a referent with the frame, match_mention and the relation gates; a probe that used any of
those would only confirm that the resolver agrees with itself, and would be blind to
exactly the cases where the resolver is wrong. So probes are selected by a plain
surface rule instead: a value's distinctive tokens are searched in the source text, and
the nearest model name on the same line decides which entity that line is about, using
the repo's own base_model tags and the literal names present in the text. No frame, no
alias expansion, no relation.

A probe is a candidate, never a verdict. Its output is a question for a human or a
screen: "the card says X for field F, and the only place X appears in the sources is a
line about Y." Detection rate and false-positive rate are measured against labels the
probes did not produce.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

from ..schema import NOT_APPLICABLE, NOT_SPECIFIED, PUBLIC_FIELD_PATHS, get_field_value

# The fields where a spliced value does real damage: numbers, data and results.
PROBED_FIELDS = (
    "specifications.num_parameters", "specifications.context_length",
    "specifications.precision", "training_context.training_data",
    "training_context.training_data_size", "training_context.data_cutoff",
    "training_context.adaptations", "evaluation.benchmark_scores",
    "evaluation.human_evals", "evaluation.safety_evals", "evaluation.results_summary",
)
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_MODEL_NAME_RE = re.compile(r"\b[A-Za-z][\w.]*(?:[-_][A-Za-z0-9][\w.]*)+\b")
# An identifier-shaped word: it carries a digit or an internal capital. "parameters",
# "safetensors" and "metadata" do not, and matching on those made a probe fire on any
# line that happened to use the word.
_IDENT_RE = re.compile(r"\b[A-Za-z][\w.-]*\b")
_MIN_NUMBER_LEN = 2


def _distinctive_tokens(value: Any) -> List[str]:
    """The tokens rare enough to locate this value in a source: its numbers, and words
    shaped like names. A common word is not evidence that two lines say the same thing."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    numbers = [m.group(0) for m in _NUMBER_RE.finditer(text)
               if len(m.group(0).replace(",", "").replace(".", "")) >= _MIN_NUMBER_LEN]
    names = [w for w in (m.group(0) for m in _IDENT_RE.finditer(text))
             if len(w) >= 3 and (any(c.isdigit() for c in w)
                                 or re.search(r"(?<=.)[A-Z]", w))]
    return list(dict.fromkeys(numbers + names))[:8]


def _entity_names(model_id: str, base_model_tags: Iterable[str]) -> Dict[str, str]:
    """{literal name: role} from the repo's own structured tags and its own id.

    Only names the Hub itself declares, so the predicate cannot inherit the composer's
    idea of who the siblings are.
    """
    names: Dict[str, str] = {model_id.rsplit("/", 1)[-1]: "target", model_id: "target"}
    for tag in base_model_tags or []:
        base = str(tag).split(":")[-1]
        if "/" in base:
            names.setdefault(base.rsplit("/", 1)[-1], "base")
            names.setdefault(base, "base")
    return names


def _other_model_on_line(line: str, target_name: str) -> Optional[str]:
    """A model-shaped name on the line that is not the target's."""
    for match in _MODEL_NAME_RE.finditer(line):
        name = match.group(0)
        if name.lower() != target_name.lower() and any(c.isdigit() for c in name):
            return name
    return None


def _line_owner(line: str, names: Dict[str, str], target_name: str) -> Optional[str]:
    """Which entity a source line is about, by the model names literally on it.

    Declared names first (the repo's own id and its base_model tags), then any other
    model-shaped name. The second case is the one that matters: a comparison model is
    not declared anywhere in the repo's metadata, and it is where a spliced number comes
    from most often.
    """
    present = [(line.find(name), name) for name in names if name in line]
    if present:
        present.sort()
        first = present[0][1]
        if names[first] == "target":
            return "target"
        return "base" if names[first] == "base" else "other"
    return "other" if _other_model_on_line(line, target_name) else None


def _strength(matched: List[str]) -> str:
    """How much a match is worth looking at. A bare four-digit year coincides with every
    citation on the page; a decimal or a long number does not."""
    if not matched:
        return "weak"
    distinctive = [token for token in matched
                   if ("." in token or "," in token
                       or len(token.replace(",", "")) >= 5
                       or any(c.isalpha() for c in token))]
    if len(matched) >= 2 and distinctive:
        return "strong"
    return "moderate" if distinctive else "weak"


def probes_for(card: Dict[str, Any], model_id: str, base_model_tags: Iterable[str],
               sources: Dict[str, str],
               structured_fields: Iterable[str] = ()) -> List[Dict[str, Any]]:
    """Probe candidates for one card. Each names the value, the line and the entity.

    structured_fields are the fields whose value this card took from config.json, the
    safetensors metadata or the Hub manifest. A structured value cannot have been spliced
    out of a sentence, so probing it only produces false positives.
    """
    target_name = model_id.rsplit("/", 1)[-1]
    names = _entity_names(model_id, base_model_tags)
    skip = set(structured_fields)
    out: List[Dict[str, Any]] = []
    for path in PROBED_FIELDS:
        if path not in PUBLIC_FIELD_PATHS or path in skip:
            continue
        value = get_field_value(card, path)
        if value in (NOT_SPECIFIED, [NOT_SPECIFIED], NOT_APPLICABLE, None, [], {}):
            continue
        tokens = _distinctive_tokens(value)
        if not tokens:
            continue
        hits, target_hits = [], 0
        for name, text in sources.items():
            for line in (text or "").splitlines():
                if not any(token in line for token in tokens):
                    continue
                owner = _line_owner(line, names, target_name)
                if owner == "target":
                    target_hits += 1
                elif owner in ("base", "other"):
                    hits.append({"source": name, "owner": owner,
                                 "other_model": _other_model_on_line(line, target_name),
                                 "line": line.strip()[:220]})
        if hits and not target_hits:
            matched = sorted({token for token in tokens
                              for hit in hits if token in hit["line"]})
            out.append({"field": path,
                        "value": value if isinstance(value, str)
                        else json.dumps(value, ensure_ascii=False)[:220],
                        "tokens": tokens[:5], "matched_tokens": matched,
                        "strength": _strength(matched),
                        "lines_about_other_entities": hits[:3],
                        "lines_about_target": target_hits,
                        "predicate": "surface_token_match_nearest_declared_name"})
    return out


def rates(probes: List[Dict[str, Any]], labels: Dict[str, bool]) -> Dict[str, Any]:
    """Detection and false-positive rate against labels the probes did not produce.

    labels maps "<target>|<field>" to whether that value really is spliced, from a human
    or from the screen. A probe with no label is counted as unlabelled, never as correct.
    """
    flagged = {f"{p['target']}|{p['field']}" for p in probes if "target" in p}
    true_positive = sum(1 for key, spliced in labels.items() if spliced and key in flagged)
    false_positive = sum(1 for key in flagged if labels.get(key) is False)
    missed = sum(1 for key, spliced in labels.items() if spliced and key not in flagged)
    positives = true_positive + missed
    return {
        "probes": len(probes), "labelled": len(labels),
        "unlabelled_probes": sum(1 for key in flagged if key not in labels),
        "true_positive": true_positive, "false_positive": false_positive,
        "missed": missed,
        "detection_rate": round(true_positive / positives, 4) if positives else None,
        "false_positive_rate": (round(false_positive / len(flagged), 4) if flagged
                                else None),
    }
