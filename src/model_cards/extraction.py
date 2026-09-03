"""Strict evidence-candidate extraction boundary.

Provider-facing source windows are ephemeral and bounded.  Persisted extraction
receipts contain only immutable proposals, candidate identifiers, and digests;
they never contain source bodies, prompts, or raw provider responses.  Python
recomputes quote coordinates and document context from the frozen source, and
structured values are replayed through the closed pointer registry.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from .bindings import binding_id_for, resolve_json_pointer, structured_binding
from .claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    make_context_statement_value,
    make_mitigation_value,
    make_publisher_risk_value,
)
from .document_structure import build_document_index
from .models import (
    Binding,
    BindingOrigin,
    Disposition,
    Evidence,
    EvidenceKind,
    JsonValue,
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from .model_family import (
    CONFIG_MODEL_FAMILY_REGISTRY_SHA256,
    ModelFamilyDerivationError,
    select_config_model_family_derivation,
)
from .pointer_registry import DEFAULT_POINTER_FIELD_REGISTRY, PointerFieldRegistry
from .policy import decide_binding
from .quote import match_quote, normalize_ws
from .schema import (
    CONTENT_FIELD_PATHS,
    LIST_FIELDS,
    canonical_field_path,
    validate_field_path,
    validate_field_value,
)
from .source_documents import SourceDocumentCatalog


EXTRACTION_VERSION = "model-card-evidence-extraction/v14"
EXTRACTION_SCHEMA_NAME = "model_card_quote_evidence_extraction_v2"
USE_RISK_EXTRACTION_SCHEMA_NAME = "model_card_use_risk_quote_extraction_v1"
DETERMINISTIC_PUBLISHER_CONTEXT_VERSION = (
    "deterministic-publisher-context/v9"
)
INFERENCE_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_WINDOW_CHARS = 12_000
DEFAULT_WINDOW_OVERLAP = 500
DEFAULT_MAX_WINDOWS = 16
# Keep one strict-schema response empirically below the provider's 8,192-token
# completion ceiling. Extraction is deliberately selective, and downstream
# field-level omission records keep absent coverage explicit.
MAX_PROVIDER_PROPOSALS = 8
MAX_USE_RISK_PROVIDER_PROPOSALS = 8
# A source can contribute one general provider response and, when it contains
# deterministic use/risk signals, one bounded dedicated response. This is a
# persisted-batch bound, not a per-call output allowance.
MAX_EXTRACTION_BATCH_PROPOSALS = (
    MAX_PROVIDER_PROPOSALS + MAX_USE_RISK_PROVIDER_PROPOSALS
)
MAX_PROVIDER_FIELD_PATH_CHARS = 160
MAX_PROVIDER_VALUE_JSON_CHARS = 1_600
MAX_PROVIDER_QUOTE_CHARS = 800
MAX_PROVIDER_ENTITY_CHARS = 256
MAX_PROVIDER_SCOPE_JSON_CHARS = 1_000
MAX_PROVIDER_RISK_NAME_CHARS = 256
MAX_PROVIDER_RISK_DESCRIPTION_CHARS = 640
MAX_PROVIDER_RISK_RATIONALE_CHARS = 512
MAX_DETERMINISTIC_PUBLISHER_CONTEXTS_PER_FIELD = 16

PUBLISHER_RISK_FIELD = "use_and_risk.identified_risks"
PUBLISHER_RISK_PROPOSAL_FIELDS = (
    "name",
    "description",
    "applicability_rationale",
)

_SCALAR_PROVIDER_FIELDS = tuple(sorted(set(CONTENT_FIELD_PATHS) - set(LIST_FIELDS)))
_LIST_PROVIDER_FIELDS = tuple(sorted(LIST_FIELDS))
_PROVIDER_FIELD_PATH_PATTERN = (
    "^(?:"
    + "|".join(re.escape(item) for item in _SCALAR_PROVIDER_FIELDS)
    + "|(?:"
    + "|".join(re.escape(item) for item in _LIST_PROVIDER_FIELDS)
    + ")\\[(?:0|[1-9][0-9]*)\\])$"
)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_PROPOSAL_ID_RE = re.compile(r"^proposal-[0-9a-f]{24}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9._:-]{1,127}$")
_PROVIDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{1,127}$")

_CONTEXT_FIELDS = frozenset(
    {
        "use_and_risk.intended_uses",
        "use_and_risk.out_of_scope_uses",
        "use_and_risk.limitations",
        "use_and_risk.known_biases",
    }
)
_USE_RISK_FIELDS = frozenset(
    set(_CONTEXT_FIELDS) | {PUBLISHER_RISK_FIELD, "use_and_risk.mitigations"}
)
_USE_RISK_FIELD_PATH_PATTERN = (
    "^(?:"
    + "|".join(re.escape(item) for item in sorted(_USE_RISK_FIELDS))
    + ")\\[(?:0|[1-9][0-9]*)\\]$"
)
_USE_RISK_SIGNAL_RE = re.compile(
    r"\b(?:intended\s+(?:uses?|usage)|use\s+cases?|out[-\s]+of[-\s]+scope|"
    r"limitations?|known\s+bias(?:es)?|safety|risks?|misuse|"
    r"mitigations?|restrictions?)\b",
    re.IGNORECASE,
)

_PUBLISHER_CONTEXT_FIELDS = (
    "use_and_risk.intended_uses",
    "use_and_risk.out_of_scope_uses",
    "use_and_risk.limitations",
    "use_and_risk.known_biases",
    "use_and_risk.mitigations",
)
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")
_MARKDOWN_LIST_RE = re.compile(
    r"^\s*(?:[-+*]|[0-9]{1,3}[.)])\s+(?:\[[ xX]\]\s+)?(\S.*)$"
)
_SENTENCE_BOUNDARY_RE = re.compile(
    r"(?<=[.!?])\s+(?=(?:[\"'({\[])?[A-Z0-9])"
)
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
_MODEL_ID_IN_PROSE_RE = re.compile(
    r"(?<![/:])\b[A-Za-z0-9][A-Za-z0-9._-]{0,63}/"
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\b"
)
_RELATED_MODEL_RE = re.compile(
    r"\b(?:base\s+(?:model|checkpoint)|parent\s+(?:model|checkpoint)|"
    r"sibling(?:\s+(?:model|checkpoint))?|comparison\s+(?:model|checkpoint)|"
    r"related\s+(?:model|checkpoint)|previous\s+(?:model|version|checkpoint)|"
    r"earlier\s+(?:model|version|checkpoint)|other\s+(?:model|checkpoint)s?|"
    r"derived\s+from|fine[-\s]+tuned\s+from|compared\s+(?:with|to))\b",
    re.IGNORECASE,
)
_FAMILY_SCOPE_HEADING_RE = re.compile(
    r"\b(?:model\s+famil(?:y|ies)|famil(?:y|ies)\s+of\s+models?|"
    r"all\s+(?:the\s+)?models?)\b",
    re.IGNORECASE,
)
_FAMILY_SCOPE_PROSE_RE = re.compile(
    r"\b(?:(?:these|those|both|our)\s+models|"
    r"all(?:\s+of)?\s+(?:the\s+)?models|"
    r"model\s+famil(?:y|ies)|famil(?:y|ies)\s+of\s+models?)\b",
    re.IGNORECASE,
)
_SCOPE_HEADING_GENERIC_TOKENS = frozenset(
    {"model", "models", "card", "checkpoint", "checkpoints", "for", "the"}
)
_MITIGATION_ACTION_RE = re.compile(
    r"(?:\b(?:users?|developers?|deployers?|operators?|publishers?)\s+"
    r"(?:should|must|need\s+to|are\s+recommended\s+to)\b|"
    r"\b(?:we|the\s+publisher)\s+recommend(?:s|ed)?\b|"
    r"\b(?:should|must)\s+be\s+(?:reviewed|validated|verified|filtered|"
    r"monitored|tested|restricted)\b|"
    r"^(?:use|apply|implement|perform|conduct|monitor|review|validate|verify|"
    r"filter|restrict|avoid|require)\b)",
    re.IGNORECASE,
)
_MITIGATION_HARM_RE = re.compile(
    r"\b(?:harms?|risks?|unsafe|safety|limitations?|bias(?:es|ed)?|inaccurate|"
    r"incorrect|hallucinat(?:e|es|ed|ion|ions)|misinformation|toxic(?:ity)?|"
    r"offensive|privacy|personal\s+data|sensitive\s+data|medical|legal|financial|"
    r"malicious|abuse|misuse|discriminat(?:e|es|ed|ion)|stereotyp(?:e|es|ed|ing)|"
    r"factual\s+(?:errors?|inaccurac(?:y|ies))|unreliable)\b",
    re.IGNORECASE,
)
_MODEL_OR_OUTPUT_RE = re.compile(
    r"\b(?:model|checkpoint|system|outputs?|responses?|generations?|predictions?)\b",
    re.IGNORECASE,
)
_FORBIDDEN_CONTEXT_SECTION_RE = re.compile(
    r"(?:licenses?|licensing|legal|terms(?: of use)?|acceptable use(?: policy)?|"
    r"aup|use policy|citations?|references?|community|contact|contributing|"
    r"installation|getting started|quick ?start|how to use|inference(?: examples?)?|"
    r"generation (?:settings?|configuration|parameters?)|configuration|sampling|"
    r"decoding|prompt format|weights?|downloads?)"
)
_LEGAL_CONTEXT_VALUE_RE = re.compile(
    r"\b(?:licenses?|acceptable use policy|terms(?: of use)?)\b",
    re.IGNORECASE,
)
_INLINE_FIELD_LABEL_RE = re.compile(
    r"^(?:(?:\*\*|__)(?P<bold>intended\s+use(?:\s+cases?)?s?|"
    r"out[-\s]+of[-\s]+scope(?:\s+uses?)?|limitations?|mitigations?)"
    r"(?:\s*:)?(?:\*\*|__)|(?P<colon>intended\s+use(?:\s+cases?)?s?|"
    r"out[-\s]+of[-\s]+scope(?:\s+uses?)?|limitations?|mitigations?)\s*:)"
    r"\s*(?P<body>\S.*)$",
    re.IGNORECASE,
)
_MIXED_VARIANT_RE = re.compile(
    r"\b(?:(?:instruction[-\s]+tuned|instruct)\b[^.!?]{0,180}\b"
    r"(?:whereas|while|but)\b[^.!?]{0,180}\bpretrained\b|"
    r"pretrained\b[^.!?]{0,180}\b(?:whereas|while|but)\b[^.!?]{0,180}\b"
    r"(?:instruction[-\s]+tuned|instruct)\b)",
    re.IGNORECASE,
)
_ANAPHORIC_LIMITATION_RE = re.compile(
    r"^it\s+(?:cannot|can't|does\s+not|is\s+unable\s+to|"
    r"is\s+limited\s+(?:to|by|in)|may\s+not|suffers?\s+from|"
    r"struggles?\s+with|has\s+difficulty\s+with|"
    r"(?:may|can|could)\s+(?:produce|generate|expose|fail|hallucinate|omit|"
    r"misclassify|provide|return|repeat))\b",
    re.IGNORECASE,
)
_ANTECEDENT_MODEL_SUBJECT_RE = re.compile(
    r"^(?:the\s+)?(?P<name>[A-Za-z0-9][A-Za-z0-9._ -]{1,100}?)\s+"
    r"(?:model|checkpoint)\b",
    re.IGNORECASE,
)
_LLAMA_31_TARGET_RE = re.compile(
    r"^meta-llama/Llama-3\.1-(?:8B|70B|405B)(?P<instruct>-Instruct)?$",
    re.IGNORECASE,
)
_LLAMA_31_MIXED_INTENDED_USE_RE = re.compile(
    r"^(?P<instruct>Instruction tuned text only models are intended for "
    r"assistant-like chat), whereas (?P<pretrained>pretrained models can be "
    r"adapted for a variety of natural language generation tasks\.)$"
)
_DEEPSEEK_LICENSE_TITLE = "DEEPSEEK LICENSE AGREEMENT"
_DEEPSEEK_LICENSE_ATTACHMENT = "Attachment A"
_DEEPSEEK_LICENSE_USE_RESTRICTIONS = "Use Restrictions"
_DEEPSEEK_LICENSE_SCOPE = (
    "You agree not to use the Model or Derivatives of the Model:"
)
_DEEPSEEK_LICENSE_BULLET_RE = re.compile(r"^[ \t]*-[ \t]+(\S.*?)[ \t]*$")


class ExtractionError(ValueError):
    """Extraction material is malformed, stale, unbounded, or non-replayable."""


class ProposalStatus(str, Enum):
    MATERIALIZED = "materialized"
    SOURCE_UNAVAILABLE = "source_unavailable"
    SOURCE_KIND_MISMATCH = "source_kind_mismatch"


@dataclass(frozen=True)
class ProviderProposalRejection:
    """Hash-only record for one provider item rejected before materialization."""

    proposal_index: int
    proposal_sha256: str
    reason: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.proposal_index, int)
            or isinstance(self.proposal_index, bool)
            or not 0 <= self.proposal_index < MAX_EXTRACTION_BATCH_PROPOSALS
        ):
            raise ExtractionError("provider rejection index is invalid")
        if not _DIGEST_RE.fullmatch(self.proposal_sha256):
            raise ExtractionError("provider rejection digest is invalid")
        if self.reason not in {
            "duplicate_proposal",
            "proposal_contract_invalid",
            "source_identifier_mismatch",
        }:
            raise ExtractionError("provider rejection reason is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_index": self.proposal_index,
            "proposal_sha256": self.proposal_sha256,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ProviderProposalRejection":
        item = _strict(
            value,
            {"proposal_index", "proposal_sha256", "reason"},
            "provider proposal rejection",
        )
        return cls(**item)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ExtractionError("extraction values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ExtractionError(f"{label} has an invalid closed shape")
    return value


def publisher_risk_proposal_schema() -> dict[str, Any]:
    """Return the bounded provider shape for one publisher-reported risk.

    Provider output contains only substantive, source-stated text.  Stable IDs,
    source references, grounds, provenance, review state, and mitigation-link
    state are computed locally after quote coordinates have been replayed.
    """

    return {
        "type": "object",
        "required": list(PUBLISHER_RISK_PROPOSAL_FIELDS),
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_PROVIDER_RISK_NAME_CHARS,
            },
            "description": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_PROVIDER_RISK_DESCRIPTION_CHARS,
            },
            "applicability_rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_PROVIDER_RISK_RATIONALE_CHARS,
            },
        },
        "additionalProperties": False,
        "description": (
            "Publisher-stated risk text only; deterministic wrapper metadata is "
            "constructed locally and must not be proposed"
        ),
    }


def _publisher_risk_proposal_value(value: Any) -> dict[str, JsonValue]:
    item = _strict(
        value,
        set(PUBLISHER_RISK_PROPOSAL_FIELDS),
        "publisher risk proposal",
    )
    bounds = {
        "name": MAX_PROVIDER_RISK_NAME_CHARS,
        "description": MAX_PROVIDER_RISK_DESCRIPTION_CHARS,
        "applicability_rationale": MAX_PROVIDER_RISK_RATIONALE_CHARS,
    }
    for key in PUBLISHER_RISK_PROPOSAL_FIELDS:
        text = item[key]
        if (
            not isinstance(text, str)
            or not normalize_ws(text)
            or len(text) > bounds[key]
            or normalize_ws(text).casefold() in {"not specified", "not applicable"}
        ):
            raise ExtractionError(f"publisher risk proposal {key} is invalid")
    return {key: deepcopy(item[key]) for key in PUBLISHER_RISK_PROPOSAL_FIELDS}


@dataclass(frozen=True)
class SourceWindow:
    """Ephemeral bounded provider view; intentionally has no serializer."""

    window_id: str
    source_id: str
    source_uri: str
    source_revision: str
    source_role: str
    normalized_source_sha256: str
    normalized_start: int
    normalized_end: int
    excerpt: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"window-[0-9a-f]{24}", self.window_id):
            raise ExtractionError("source window_id is invalid")
        if not self.source_id or not self.source_uri.startswith("https://"):
            raise ExtractionError("source window identity is invalid")
        if not _DIGEST_RE.fullmatch(self.normalized_source_sha256):
            raise ExtractionError("source window normalized-source digest is invalid")
        if self.normalized_start < 0 or self.normalized_end <= self.normalized_start:
            raise ExtractionError("source window coordinates are invalid")
        if not self.excerpt or len(self.excerpt) != self.normalized_end - self.normalized_start:
            raise ExtractionError("source window excerpt is empty or unbounded")


def build_source_windows(
    source: SourceDocument,
    *,
    window_chars: int = DEFAULT_WINDOW_CHARS,
    overlap: int = DEFAULT_WINDOW_OVERLAP,
    max_windows: int = DEFAULT_MAX_WINDOWS,
) -> tuple[SourceWindow, ...]:
    """Build deterministic bounded windows without persisting source content."""

    if source.text is None:
        raise ExtractionError("quote extraction windows require a text source")
    if not 500 <= window_chars <= 50_000:
        raise ExtractionError("window_chars is outside the bounded range")
    if not 0 <= overlap < window_chars:
        raise ExtractionError("window overlap is invalid")
    if not 1 <= max_windows <= 64:
        raise ExtractionError("max_windows is outside the bounded range")
    text = normalize_ws(source.text)
    if not text:
        raise ExtractionError("quote extraction source has no normalized text")
    normalized_source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    windows: list[SourceWindow] = []
    start = 0
    step = window_chars - overlap
    while start < len(text) and len(windows) < max_windows:
        end = min(len(text), start + window_chars)
        excerpt = text[start:end]
        payload = {
            "source_id": source.source_id,
            "source_sha256": source.sha256,
            "start": start,
            "end": end,
            "window_chars": window_chars,
            "overlap": overlap,
        }
        windows.append(
            SourceWindow(
                window_id="window-" + _digest(payload)[:24],
                source_id=source.source_id,
                source_uri=source.source_uri,
                source_revision=source.source_revision,
                source_role=source.role.value,
                normalized_source_sha256=normalized_source_sha256,
                normalized_start=start,
                normalized_end=end,
                excerpt=excerpt,
            )
        )
        if end == len(text):
            break
        start += step
    return tuple(windows)


def build_use_risk_windows(
    source: SourceDocument,
    *,
    windows: Iterable[SourceWindow] | None = None,
) -> tuple[SourceWindow, ...]:
    """Select bounded windows that can contain publisher use/risk evidence.

    Selection is deterministic and deliberately recall-oriented: a window is
    retained when it overlaps a structurally classified limitation/risk
    section, has a use/risk heading, or contains one of the closed, strong
    lexical signals.  Provider output is still quote-replayed and passes all
    downstream claim gates, so this routing step never creates evidence.
    """

    if source.text is None:
        raise ExtractionError("use/risk extraction windows require a text source")
    candidates = tuple(build_source_windows(source) if windows is None else windows)
    if not candidates:
        return ()
    normalized_source = normalize_ws(source.text)
    normalized_source_sha256 = hashlib.sha256(
        normalized_source.encode("utf-8")
    ).hexdigest()
    index = build_document_index(source.text)
    if (
        index.normalized_sha256 != normalized_source_sha256
        or index.normalized_length != len(normalized_source)
    ):
        raise ExtractionError("document index uses a different coordinate space")
    for window in candidates:
        if (
            window.source_id != source.source_id
            or window.source_uri != source.source_uri
            or window.source_revision != source.source_revision
            or window.source_role != source.role.value
            or window.normalized_source_sha256 != normalized_source_sha256
        ):
            raise ExtractionError("use/risk window does not belong to the source")
        if (
            window.normalized_end > index.normalized_length
            or normalized_source[
                window.normalized_start : window.normalized_end
            ]
            != window.excerpt
        ):
            raise ExtractionError("use/risk window coordinates do not replay")
    spans = tuple(
        (section.char_start, section.char_end)
        for section in index.sections
        if section.region in {"limitations", "risk"}
        or _USE_RISK_SIGNAL_RE.search(section.title)
    )
    selected = tuple(
        window
        for window in candidates
        if _USE_RISK_SIGNAL_RE.search(window.excerpt)
        or any(
            window.normalized_start < end and start < window.normalized_end
            for start, end in spans
        )
    )
    return selected


@dataclass(frozen=True)
class QuoteProposal:
    """Untrusted provider proposal whose coordinates are computed locally."""

    source_id: str
    field_path: str
    value: JsonValue
    quote: str
    claim_entity: str
    relation: RelationToTarget
    benchmark_scope: dict[str, JsonValue] | None = None
    origin: str = "source_stated"
    proposal_id: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        validate_field_path(self.field_path)
        if len(self.field_path) > MAX_PROVIDER_FIELD_PATH_CHARS:
            raise ExtractionError("quote proposal field_path exceeds its bound")
        base = canonical_field_path(self.field_path)
        if base in LIST_FIELDS and self.field_path == base:
            raise ExtractionError("list field proposals require one item index")
        proposal_value: JsonValue = self.value
        if base == PUBLISHER_RISK_FIELD:
            proposal_value = _publisher_risk_proposal_value(self.value)
        elif base in _CONTEXT_FIELDS or base == "use_and_risk.mitigations":
            if not isinstance(self.value, str) or not self.value.strip():
                raise ExtractionError("publisher context and mitigation proposals use descriptions")
        else:
            validate_field_value(self.field_path, self.value)
        object.__setattr__(self, "value", deepcopy(proposal_value))
        if (
            not isinstance(self.source_id, str)
            or not self.source_id
            or len(self.source_id) > 128
        ):
            raise ExtractionError("quote proposal source_id is invalid")
        normalized_quote = normalize_ws(self.quote) if isinstance(self.quote, str) else ""
        if (
            not normalized_quote
            or len(self.quote) > MAX_PROVIDER_QUOTE_CHARS
            or len(normalized_quote) > MAX_PROVIDER_QUOTE_CHARS
        ):
            raise ExtractionError("quote proposal quote is empty")
        object.__setattr__(self, "quote", normalized_quote)
        if (
            not isinstance(self.claim_entity, str)
            or not self.claim_entity.strip()
            or len(self.claim_entity) > MAX_PROVIDER_ENTITY_CHARS
        ):
            raise ExtractionError("quote proposal claim_entity is empty")
        if len(_canonical(self.value)) > MAX_PROVIDER_VALUE_JSON_CHARS:
            raise ExtractionError("quote proposal value exceeds its bound")
        if isinstance(self.value, str) and normalize_ws(self.value).casefold() in {
            "not specified",
            "not applicable",
        }:
            raise ExtractionError("quote proposal cannot assert an absence marker")
        try:
            object.__setattr__(self, "relation", RelationToTarget(self.relation))
        except (TypeError, ValueError) as exc:
            raise ExtractionError("quote proposal relation is invalid") from exc
        if self.benchmark_scope is not None:
            if not isinstance(self.benchmark_scope, dict):
                raise ExtractionError("quote proposal benchmark scope must be an object")
            if len(_canonical(self.benchmark_scope)) > MAX_PROVIDER_SCOPE_JSON_CHARS:
                raise ExtractionError("quote proposal benchmark scope exceeds its bound")
            object.__setattr__(self, "benchmark_scope", deepcopy(self.benchmark_scope))
        if not isinstance(self.origin, str) or not _CODE_RE.fullmatch(self.origin):
            raise ExtractionError("quote proposal origin is invalid")
        if self.origin not in {"source_stated", "source_derived"}:
            raise ExtractionError("quote proposal origin is unsupported")
        if (
            base in {"use_and_risk.mitigations", PUBLISHER_RISK_FIELD}
            and self.origin != "source_stated"
        ):
            raise ExtractionError(
                "mitigation and publisher-risk proposals require publisher-stated evidence"
            )
        object.__setattr__(self, "proposal_id", "proposal-" + _digest(self._payload())[:24])

    def _payload(self) -> dict[str, Any]:
        return {
            "kind": "quote",
            "source_id": self.source_id,
            "field_path": self.field_path,
            "value": deepcopy(self.value),
            "quote": normalize_ws(self.quote),
            "claim_entity": self.claim_entity,
            "relation": self.relation.value,
            "benchmark_scope": deepcopy(self.benchmark_scope),
            "origin": self.origin,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"proposal_id": self.proposal_id, **self._payload()}

    @classmethod
    def from_dict(cls, value: Any) -> "QuoteProposal":
        item = _strict(
            value,
            {
                "proposal_id",
                "kind",
                "source_id",
                "field_path",
                "value",
                "quote",
                "claim_entity",
                "relation",
                "benchmark_scope",
                "origin",
            },
            "quote proposal",
        )
        if item["kind"] != "quote":
            raise ExtractionError("quote proposal kind is invalid")
        result = cls(
            source_id=item["source_id"],
            field_path=item["field_path"],
            value=item["value"],
            quote=item["quote"],
            claim_entity=item["claim_entity"],
            relation=item["relation"],
            benchmark_scope=item["benchmark_scope"],
            origin=item["origin"],
        )
        if item["quote"] != result.quote:
            raise ExtractionError("quote proposal quote is not canonical")
        if result.proposal_id != item["proposal_id"]:
            raise ExtractionError("quote proposal_id does not match content")
        return result


@dataclass(frozen=True)
class ExtractionBatch:
    extraction_version: str
    target: TargetIdentity
    source_catalog_sha256: str
    inference_model: str
    provider: str
    inference_config_sha256: str
    proposals: tuple[QuoteProposal, ...]
    rejections: tuple[ProviderProposalRejection, ...]
    batch_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "proposals", tuple(self.proposals))
        object.__setattr__(self, "rejections", tuple(self.rejections))
        if (
            len(self.proposals) + len(self.rejections)
            > MAX_EXTRACTION_BATCH_PROPOSALS
        ):
            raise ExtractionError("extraction batch exceeds its proposal bound")
        if self.extraction_version != EXTRACTION_VERSION:
            raise ExtractionError("extraction batch version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise ExtractionError("extraction batch target is invalid")
        if not _DIGEST_RE.fullmatch(self.source_catalog_sha256):
            raise ExtractionError("source catalog digest is invalid")
        if self.inference_model != INFERENCE_MODEL:
            raise ExtractionError("extraction used an unauthorized inference model")
        if not isinstance(self.provider, str) or not _PROVIDER_RE.fullmatch(self.provider):
            raise ExtractionError("extraction provider is invalid")
        if not _DIGEST_RE.fullmatch(self.inference_config_sha256):
            raise ExtractionError("extraction config digest is invalid")
        identifiers = [item.proposal_id for item in self.proposals]
        if identifiers != sorted(identifiers) or len(identifiers) != len(set(identifiers)):
            raise ExtractionError("extraction proposals must be sorted and unique")
        if not all(
            isinstance(item, ProviderProposalRejection) for item in self.rejections
        ):
            raise ExtractionError("provider proposal rejections are not canonical")
        rejection_indexes = [item.proposal_index for item in self.rejections]
        item_count = len(self.proposals) + len(self.rejections)
        if (
            rejection_indexes != sorted(rejection_indexes)
            or len(rejection_indexes) != len(set(rejection_indexes))
            or any(index >= item_count for index in rejection_indexes)
        ):
            raise ExtractionError("provider proposal rejections are not canonical")
        if self.batch_sha256 != _digest(self._payload()):
            raise ExtractionError("extraction batch digest is inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "extraction_version": self.extraction_version,
            "target": self.target.to_dict(),
            "source_catalog_sha256": self.source_catalog_sha256,
            "inference_model": self.inference_model,
            "provider": self.provider,
            "inference_config_sha256": self.inference_config_sha256,
            "proposals": [item.to_dict() for item in self.proposals],
            "rejections": [item.to_dict() for item in self.rejections],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "batch_sha256": self.batch_sha256}

    @classmethod
    def build(
        cls,
        *,
        target: TargetIdentity,
        source_catalog_sha256: str,
        provider: str,
        inference_config_sha256: str,
        proposals: Iterable[QuoteProposal],
        rejections: Iterable[ProviderProposalRejection] = (),
    ) -> "ExtractionBatch":
        values = tuple(sorted(tuple(proposals), key=lambda item: item.proposal_id))
        rejected = tuple(
            sorted(tuple(rejections), key=lambda item: item.proposal_index)
        )
        payload = {
            "extraction_version": EXTRACTION_VERSION,
            "target": target.to_dict(),
            "source_catalog_sha256": source_catalog_sha256,
            "inference_model": INFERENCE_MODEL,
            "provider": provider,
            "inference_config_sha256": inference_config_sha256,
            "proposals": [item.to_dict() for item in values],
            "rejections": [item.to_dict() for item in rejected],
        }
        return cls(
            extraction_version=EXTRACTION_VERSION,
            target=target,
            source_catalog_sha256=source_catalog_sha256,
            inference_model=INFERENCE_MODEL,
            provider=provider,
            inference_config_sha256=inference_config_sha256,
            proposals=values,
            rejections=rejected,
            batch_sha256=_digest(payload),
        )

    @classmethod
    def from_dict(cls, value: Any) -> "ExtractionBatch":
        item = _strict(
            value,
            {
                "extraction_version",
                "target",
                "source_catalog_sha256",
                "inference_model",
                "provider",
                "inference_config_sha256",
                "proposals",
                "rejections",
                "batch_sha256",
            },
            "extraction batch",
        )
        if not isinstance(item["proposals"], list):
            raise ExtractionError("extraction proposals must be an array")
        if not isinstance(item["rejections"], list):
            raise ExtractionError("extraction rejections must be an array")
        return cls(
            extraction_version=item["extraction_version"],
            target=TargetIdentity.from_dict(item["target"]),
            source_catalog_sha256=item["source_catalog_sha256"],
            inference_model=item["inference_model"],
            provider=item["provider"],
            inference_config_sha256=item["inference_config_sha256"],
            proposals=tuple(QuoteProposal.from_dict(entry) for entry in item["proposals"]),
            rejections=tuple(
                ProviderProposalRejection.from_dict(entry)
                for entry in item["rejections"]
            ),
            batch_sha256=item["batch_sha256"],
        )


@dataclass(frozen=True)
class ProposalOutcome:
    proposal_id: str
    status: ProposalStatus
    reason: str
    candidate_id: str | None

    def __post_init__(self) -> None:
        if not _PROPOSAL_ID_RE.fullmatch(self.proposal_id):
            raise ExtractionError("proposal outcome identifier is invalid")
        object.__setattr__(self, "status", ProposalStatus(self.status))
        if not _CODE_RE.fullmatch(self.reason):
            raise ExtractionError("proposal outcome reason is invalid")
        if self.status is ProposalStatus.MATERIALIZED:
            if not isinstance(self.candidate_id, str) or not re.fullmatch(
                r"claim-[0-9a-f]{24}", self.candidate_id
            ):
                raise ExtractionError("materialized proposal requires a candidate_id")
        elif self.candidate_id is not None:
            raise ExtractionError("unmaterialized proposal cannot claim a candidate_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "status": self.status.value,
            "reason": self.reason,
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True)
class ExtractionResult:
    extraction_version: str
    target: TargetIdentity
    input_sha256: str
    candidates: tuple[ClaimCandidate, ...]
    outcomes: tuple[ProposalOutcome, ...]
    result_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "outcomes", tuple(self.outcomes))
        if self.extraction_version != EXTRACTION_VERSION:
            raise ExtractionError("extraction result version is unsupported")
        if not _DIGEST_RE.fullmatch(self.input_sha256):
            raise ExtractionError("extraction result input digest is invalid")
        candidate_ids = [item.candidate_id for item in self.candidates]
        if candidate_ids != sorted(candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
            raise ExtractionError("extraction candidates must be sorted and unique")
        outcome_ids = [item.proposal_id for item in self.outcomes]
        if outcome_ids != sorted(outcome_ids) or len(outcome_ids) != len(set(outcome_ids)):
            raise ExtractionError("extraction outcomes must be sorted and unique")
        materialized = sorted(
            item.candidate_id
            for item in self.outcomes
            if item.status is ProposalStatus.MATERIALIZED
        )
        if materialized != candidate_ids:
            raise ExtractionError("extraction outcomes and candidates diverge")
        if self.result_sha256 != _digest(self._payload()):
            raise ExtractionError("extraction result digest is inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "extraction_version": self.extraction_version,
            "target": self.target.to_dict(),
            "input_sha256": self.input_sha256,
            "candidate_ids": [item.candidate_id for item in self.candidates],
            "candidate_sha256": [item.content_sha256 for item in self.candidates],
            "outcomes": [item.to_dict() for item in self.outcomes],
        }


def materialize_quote_batch(
    batch: ExtractionBatch,
    catalog: SourceDocumentCatalog,
) -> ExtractionResult:
    """Recompute all coordinates/context and retain even nonmatching quote candidates."""

    if batch.target != catalog.target or batch.source_catalog_sha256 != catalog.catalog_sha256:
        raise ExtractionError("extraction batch is stale for this source catalog")
    by_id = catalog.by_id
    candidates: list[ClaimCandidate] = []
    outcomes: list[ProposalOutcome] = []
    for proposal in batch.proposals:
        source = by_id.get(proposal.source_id)
        if source is None:
            outcomes.append(
                ProposalOutcome(
                    proposal.proposal_id,
                    ProposalStatus.SOURCE_UNAVAILABLE,
                    "source_unavailable",
                    None,
                )
            )
            continue
        if source.text is None:
            outcomes.append(
                ProposalOutcome(
                    proposal.proposal_id,
                    ProposalStatus.SOURCE_KIND_MISMATCH,
                    "quote_source_not_text",
                    None,
                )
            )
            continue
        evidence = _quote_evidence(source, proposal.quote)
        value: JsonValue = deepcopy(proposal.value)
        base = canonical_field_path(proposal.field_path)
        if base in _CONTEXT_FIELDS:
            value = make_context_statement_value(
                field_path=proposal.field_path,
                description=str(proposal.value),
                origin=(
                    "publisher_reported"
                    if proposal.origin == "source_stated"
                    else "source_derived"
                ),
                evidence=(evidence,),
            )
        elif base == "use_and_risk.mitigations":
            value = make_mitigation_value(
                description=str(proposal.value), evidence=(evidence,)
            )
        elif base == PUBLISHER_RISK_FIELD:
            if (
                not isinstance(proposal.value, dict)
                or any(
                    not isinstance(proposal.value.get(key), str)
                    for key in PUBLISHER_RISK_PROPOSAL_FIELDS
                )
            ):  # guarded by QuoteProposal; keep materialization fail-closed
                raise ExtractionError("publisher risk proposal is invalid")
            value = make_publisher_risk_value(
                name=proposal.value["name"],
                description=proposal.value["description"],
                applicability_rationale=proposal.value["applicability_rationale"],
                evidence=(evidence,),
            )
        binding = _binding_from_quote_evidence(batch.target, proposal, value, evidence)
        candidate = ClaimCandidate.from_binding(batch.target, binding)
        candidates.append(candidate)
        outcomes.append(
            ProposalOutcome(
                proposal.proposal_id,
                ProposalStatus.MATERIALIZED,
                "candidate_materialized",
                candidate.candidate_id,
            )
        )
    candidates_tuple = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    outcomes_tuple = tuple(sorted(outcomes, key=lambda item: item.proposal_id))
    return _make_result(batch.target, batch.batch_sha256, candidates_tuple, outcomes_tuple)


def deterministic_structured_candidates(
    catalog: SourceDocumentCatalog,
    *,
    registry: PointerFieldRegistry = DEFAULT_POINTER_FIELD_REGISTRY,
) -> ExtractionResult:
    """Enumerate only pointer/field pairs already present in the closed registry."""

    candidates: dict[str, ClaimCandidate] = {}
    outcomes: list[ProposalOutcome] = []
    try:
        selected_family = select_config_model_family_derivation(
            catalog.target, catalog.documents
        )
    except ModelFamilyDerivationError as exc:
        raise ExtractionError(
            "config model-family derivation failed closed"
        ) from exc
    for source in catalog.documents:
        if source.data is None:
            continue
        for rule in registry.rules:
            if rule.source_role is not source.role:
                continue
            try:
                fragment = resolve_json_pointer(source.data, rule.pointer)
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            lookup = registry.lookup(
                source_role=source.role,
                pointer=rule.pointer,
                field_path=rule.field_path,
                fragment=fragment,
            )
            if lookup.matched_rule != rule:
                continue
            try:
                binding = structured_binding(
                    target=catalog.target,
                    source=source,
                    field_path=rule.field_path,
                    pointer=rule.pointer,
                    claim_entity=f"{catalog.target.model_id}@{catalog.target.revision}",
                    relation=RelationToTarget.EXACT_TARGET,
                )
                candidate = ClaimCandidate.from_binding(catalog.target, binding)
            except (TypeError, ValueError):
                # Registered pointer shape can still be incompatible with the public
                # field's exact type; conversion is never invented here.
                continue
            candidates[candidate.candidate_id] = candidate
            proposal_id = "proposal-" + _digest(
                {
                    "kind": "structured",
                    "source_id": source.source_id,
                    "pointer": rule.pointer,
                    "field_path": rule.field_path,
                    "candidate_id": candidate.candidate_id,
                }
            )[:24]
            outcomes.append(
                ProposalOutcome(
                    proposal_id,
                    ProposalStatus.MATERIALIZED,
                    "candidate_materialized",
                    candidate.candidate_id,
                )
            )
        family_derivation = (
            selected_family[1]
            if selected_family is not None and selected_family[0] is source
            else None
        )
        if family_derivation is not None:
            try:
                binding = structured_binding(
                    target=catalog.target,
                    source=source,
                    field_path="lineage.model_family",
                    pointer=family_derivation.pointer,
                    claim_entity=(
                        f"{catalog.target.model_id}@{catalog.target.revision}"
                    ),
                    relation=RelationToTarget.EXACT_TARGET,
                )
                candidate = ClaimCandidate.from_binding(catalog.target, binding)
            except (TypeError, ValueError) as exc:
                raise ExtractionError(
                    "allowlisted config model-family candidate is invalid"
                ) from exc
            candidates[candidate.candidate_id] = candidate
            proposal_id = "proposal-" + _digest(
                {
                    "kind": "registered_config_model_family",
                    "candidate_id": candidate.candidate_id,
                    "derivation_sha256": family_derivation.derivation_sha256,
                }
            )[:24]
            outcomes.append(
                ProposalOutcome(
                    proposal_id,
                    ProposalStatus.MATERIALIZED,
                    "candidate_materialized",
                    candidate.candidate_id,
                )
            )
    candidate_values = tuple(sorted(candidates.values(), key=lambda item: item.candidate_id))
    # Multiple registry aliases can resolve to the same candidate. Keep one outcome
    # per final candidate so coverage remains one-to-one and deterministic.
    outcome_by_candidate = {
        item.candidate_id: item for item in sorted(outcomes, key=lambda item: item.proposal_id)
    }
    outcome_values = tuple(
        sorted(outcome_by_candidate.values(), key=lambda item: item.proposal_id)
    )
    input_digest = _digest(
        {
            "mode": "closed_pointer_registry",
            "catalog_sha256": catalog.catalog_sha256,
            "registry_sha256": registry.sha256,
            "config_model_family_registry_sha256": (
                CONFIG_MODEL_FAMILY_REGISTRY_SHA256
            ),
        }
    )
    return _make_result(catalog.target, input_digest, candidate_values, outcome_values)


@dataclass(frozen=True)
class _PublisherTextSegment:
    description: str
    section_path: tuple[str, ...]
    inline_field: str | None
    complete_clause_without_terminal_punctuation: bool = False
    antecedent_description: str | None = None


def _target_scoped_publisher_segments(
    segment: _PublisherTextSegment,
    source: SourceDocument,
    target: TargetIdentity,
) -> tuple[_PublisherTextSegment, ...]:
    """Split one exact publisher sentence only when its checkpoint scope is closed.

    The Llama 3.1 publisher describes the base and instruction-tuned checkpoints in
    two clauses of one sentence.  The general mixed-variant guard must continue to
    reject that sentence as a whole.  This narrow registered rule instead selects
    one exact contiguous clause from the exact-target README after the target name
    establishes which checkpoint the clause concerns.  Unknown families and stages
    keep the original segment and therefore still fail the mixed-variant guard.
    """

    pinned_root_uris = {
        f"https://huggingface.co/{target.model_id}/{route}/"
        f"{target.revision}/README.md"
        for route in ("resolve", "blob")
    }
    is_pinned_root_readme = (
        source.role is SourceRole.HUGGING_FACE_SNAPSHOT
        and source.target == target
        and source.source_uri in pinned_root_uris
    )
    if (
        not is_pinned_root_readme
        or segment.inline_field != "use_and_risk.intended_uses"
    ):
        return (segment,)
    sentence = _LLAMA_31_MIXED_INTENDED_USE_RE.fullmatch(segment.description)
    checkpoint = _LLAMA_31_TARGET_RE.fullmatch(target.model_id)
    if sentence is None or checkpoint is None:
        return (segment,)
    group = "instruct" if checkpoint.group("instruct") else "pretrained"
    return (
        _PublisherTextSegment(
            description=sentence.group(group),
            section_path=segment.section_path,
            inline_field=segment.inline_field,
            complete_clause_without_terminal_punctuation=(group == "instruct"),
        ),
    )


def _normalized_heading(title: str) -> str:
    value = normalize_ws(title).casefold().replace("&", " and ")
    value = re.sub(r"[`*_~]", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _publisher_structural_fields(
    section_path: Sequence[str],
) -> frozenset[str]:
    """Return fields permitted by the nearest recognized safety/use ancestry."""

    headings = tuple(_normalized_heading(item) for item in section_path)
    if not headings or any(
        _FORBIDDEN_CONTEXT_SECTION_RE.search(item) for item in headings
    ):
        return frozenset()
    for title in reversed(headings):
        if re.fullmatch(
            r"(?:out of scope(?: uses?)?|non intended uses?|not intended(?: uses?)?|"
            r"prohibited uses?|disallowed uses?|restricted uses?|misuse(?: cases?)?)",
            title,
        ):
            return frozenset({"use_and_risk.out_of_scope_uses"})
        if re.fullmatch(
            r"(?:(?:intended|primary|direct|supported|downstream) uses?|"
            r"intended usage|uses?|"
            r"use cases?|intended applications?)",
            title,
        ):
            return frozenset(
                {
                    "use_and_risk.intended_uses",
                    "use_and_risk.out_of_scope_uses",
                }
            )
        if re.fullmatch(
            r"(?:(?:known )?(?:limitations?|issues?|failure modes?|shortcomings?))",
            title,
        ):
            return frozenset(
                {
                    "use_and_risk.limitations",
                    "use_and_risk.known_biases",
                    "use_and_risk.mitigations",
                }
            )
        if re.fullmatch(r"(?:(?:known )?bias(?:es)?)", title):
            return frozenset({"use_and_risk.known_biases"})
        if re.fullmatch(
            r"(?:mitigations?|safety recommendations?|safety guidelines?|"
            r"safeguards?)",
            title,
        ):
            return frozenset({"use_and_risk.mitigations"})
        if re.fullmatch(
            r"(?:risks?|safety(?: and security)?|responsible use|"
            r"ethical considerations?|ethical considerations? and risks?|"
            r"safety risks and limitations|bias(?:es)? risks and limitations|"
            r"risks? and limitations|hazards?)",
            title,
        ):
            return frozenset(
                {
                    "use_and_risk.limitations",
                    "use_and_risk.known_biases",
                    "use_and_risk.mitigations",
                }
            )
        # The nearest heading controls the paragraph. Walking past an unknown
        # child heading can reassign a sibling/model-specific subsection to a
        # broader Limitation or Risk ancestor.
        return frozenset()
    return frozenset()


def _inline_label_field(label: str) -> str | None:
    normalized = _normalized_heading(label)
    if re.fullmatch(r"out of scope(?: uses?)?", normalized):
        return "use_and_risk.out_of_scope_uses"
    if re.fullmatch(r"intended use(?: cases?)?s?", normalized):
        return "use_and_risk.intended_uses"
    if re.fullmatch(r"limitations?", normalized):
        return "use_and_risk.limitations"
    if re.fullmatch(r"mitigations?", normalized):
        return "use_and_risk.mitigations"
    return None


def _strip_segment_prefix(value: str) -> tuple[str, str | None]:
    text = normalize_ws(value)
    match = _MARKDOWN_LIST_RE.fullmatch(text)
    if match is not None:
        text = normalize_ws(match.group(1))
    match = _INLINE_FIELD_LABEL_RE.fullmatch(text)
    if match is not None:
        label = match.group("bold") or match.group("colon")
        text = normalize_ws(match.group("body"))
        return text, _inline_label_field(label)
    return text, None


def _publisher_text_segments(text: str) -> tuple[_PublisherTextSegment, ...]:
    """Return exact substrings with locally reconstructed Markdown ancestry."""

    lines = text.splitlines()
    stack: list[tuple[int, str]] = []
    paragraph: list[str] = []
    paragraph_path: tuple[str, ...] = ()
    raw_segments: list[tuple[str, tuple[str, ...]]] = []
    in_fence = False
    in_frontmatter = False
    first_content_seen = False
    list_indent: int | None = None

    def flush() -> None:
        nonlocal paragraph, list_indent
        if paragraph:
            raw_segments.append((" ".join(paragraph), paragraph_path))
            paragraph = []
        list_indent = None

    for line in lines:
        stripped = line.strip()
        if not first_content_seen and not stripped:
            continue
        if not first_content_seen:
            first_content_seen = True
            if stripped == "---":
                in_frontmatter = True
                continue
        if in_frontmatter:
            if stripped in {"---", "..."}:
                in_frontmatter = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _MARKDOWN_HEADING_RE.fullmatch(stripped)
        if heading is not None:
            flush()
            level = len(heading.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading.group(2).strip()))
            continue
        if not stripped:
            flush()
            continue
        if stripped.startswith(">") or stripped.startswith("|"):
            flush()
            continue
        list_item = _MARKDOWN_LIST_RE.fullmatch(line)
        if list_item is not None:
            flush()
            paragraph_path = tuple(item[1] for item in stack)
            paragraph = [list_item.group(1)]
            list_indent = len(line) - len(line.lstrip())
            continue
        indentation = len(line) - len(line.lstrip())
        if list_indent is not None and indentation > list_indent:
            paragraph.append(stripped)
            continue
        if line.startswith("    "):
            flush()
            continue
        current_path = tuple(item[1] for item in stack)
        if paragraph and paragraph_path != current_path:
            flush()
        if not paragraph:
            paragraph_path = current_path
        paragraph.append(stripped)
    flush()

    results: list[_PublisherTextSegment] = []
    seen: set[tuple[str, tuple[str, ...], str | None, str | None]] = set()
    for raw, path in raw_segments:
        scoped_text, inline_field = _strip_segment_prefix(raw)
        antecedent: str | None = None
        for sentence in _SENTENCE_BOUNDARY_RE.split(scoped_text):
            description, nested_field = _strip_segment_prefix(sentence)
            field = inline_field or nested_field
            key = (description, path, field, antecedent)
            if description and key not in seen:
                seen.add(key)
                results.append(
                    _PublisherTextSegment(
                        description,
                        path,
                        field,
                        antecedent_description=antecedent,
                    )
                )
            if description:
                antecedent = description
    return tuple(results)


def _publisher_statement_fields(
    description: str, target: TargetIdentity
) -> frozenset[str]:
    model_id = re.escape(target.model_id)
    model_name = re.escape(target.model_id.split("/", 1)[1])
    subject = (
        rf"(?:(?:this|the|our)\s+(?:model|checkpoint|system)|the\s+exact\s+target|"
        rf"{model_id}|{model_name})"
    )
    explicit_model_reference = re.search(
        rf"(?:\b{subject}\b|\b(?:model|checkpoint|system)\s+"
        r"(?:outputs?|responses?|generations?|predictions?)\b)",
        description,
        re.IGNORECASE,
    )
    fields: set[str] = set()
    if re.search(
        rf"(?:\b{subject}\s+(?:is|was)\s+not\s+(?:intended|designed|developed|"
        rf"built|suitable|recommended)\s+for\b|\b{subject}\s+(?:should|must)\s+"
        rf"not\s+be\s+(?:used|deployed)\b|\b(?:do\s+not|never)\s+"
        rf"(?:use|deploy)\s+{subject}\b)",
        description,
        re.IGNORECASE,
    ):
        fields.add("use_and_risk.out_of_scope_uses")
    if re.search(
        rf"(?:\b{subject}\s+(?:is|was)\s+(?:intended|designed|developed|built)\s+"
        rf"(?:for|to)\b|\b{subject}\s+can\s+be\s+used\s+for\b|"
        rf"\b(?:publisher|developers?)\s+(?:intends?|designed|developed)\s+"
        rf"(?:this|the)\s+(?:model|checkpoint)\s+for\b)",
        description,
        re.IGNORECASE,
    ):
        fields.add("use_and_risk.intended_uses")
    if re.search(
        rf"(?:\b{subject}\s+(?:cannot|can't|does\s+not|is\s+unable\s+to|"
        rf"is\s+limited\s+(?:to|by|in)|may\s+not|suffers?\s+from|"
        rf"struggles?\s+with|has\s+difficulty\s+with|"
        rf"(?:may|can|could)\s+(?:produce|generate|expose|fail|hallucinate|omit|"
        rf"misclassify|provide|return|repeat))\b|\b(?:a|one)\s+limitation\s+of\s+"
        rf"{subject}\s+(?:is|are)\b)",
        description,
        re.IGNORECASE,
    ):
        fields.add("use_and_risk.limitations")
    if re.search(
        rf"(?:\b{subject}\b[^.!?]{{0,120}}\b(?:known\s+)?bias(?:es|ed)?\b|"
        rf"\b(?:known\s+)?bias(?:es)?\s+(?:of|in)\s+{subject}\b)",
        description,
        re.IGNORECASE,
    ):
        fields.add("use_and_risk.known_biases")
    if (
        "use_and_risk.out_of_scope_uses" not in fields
        and _MITIGATION_ACTION_RE.search(description)
        and _MITIGATION_HARM_RE.search(description)
        and explicit_model_reference is not None
    ):
        fields.add("use_and_risk.mitigations")
    return frozenset(fields)


def _heading_scoped_anaphoric_fields(
    segment: _PublisherTextSegment,
    target: TargetIdentity,
) -> frozenset[str]:
    """Resolve one local pronoun only from an exact checkpoint heading.

    Model cards sometimes put an exact checkpoint in the root heading, name a
    shortened form of that same checkpoint in one sentence, and use ``It`` in
    the immediately following sentence.  Sentence-only extraction otherwise
    loses the antecedent (for example, Mistral's moderation limitation).  The
    bridge is deliberately fail-closed: the heading must name the full target,
    the immediately preceding sentence must name a target-token prefix rather
    than a family or sibling, and only a limitation predicate is admitted.
    """

    antecedent = segment.antecedent_description
    if antecedent is None or _ANAPHORIC_LIMITATION_RE.search(segment.description) is None:
        return frozenset()
    target_tokens = tuple(
        _normalized_heading(target.model_id.split("/", 1)[1]).split()
    )
    exact_heading = any(
        tuple(
            token
            for token in _normalized_heading(title).split()
            if token not in _SCOPE_HEADING_GENERIC_TOKENS
        )
        == target_tokens
        for title in segment.section_path
    )
    if not exact_heading:
        return frozenset()
    normalized_antecedent = _normalized_heading(antecedent)
    if (
        _FAMILY_SCOPE_PROSE_RE.search(normalized_antecedent)
        or _MIXED_VARIANT_RE.search(antecedent)
        or any(
            match.group(0).casefold() != target.model_id.casefold()
            for match in _MODEL_ID_IN_PROSE_RE.finditer(antecedent)
        )
    ):
        return frozenset()
    subject = _ANTECEDENT_MODEL_SUBJECT_RE.search(antecedent)
    if subject is None:
        return frozenset()
    subject_tokens = tuple(_normalized_heading(subject.group("name")).split())
    if (
        len(subject_tokens) < 2
        or len(subject_tokens) > len(target_tokens)
        or subject_tokens != target_tokens[: len(subject_tokens)]
    ):
        return frozenset()
    return frozenset({"use_and_risk.limitations"})


def _publisher_statement_is_substantive(
    description: str,
    *,
    complete_clause_without_terminal_punctuation: bool = False,
) -> bool:
    normalized = normalize_ws(description)
    if not 20 <= len(normalized) <= MAX_PROVIDER_QUOTE_CHARS:
        return False
    if len(_WORD_RE.findall(normalized)) < 5:
        return False
    if (
        normalized[-1] not in ".?!"
        and not complete_clause_without_terminal_punctuation
    ):
        return False
    folded = normalized.casefold().strip(" .:;-_")
    if folded in {
        "n/a",
        "n a",
        "none",
        "not applicable",
        "not specified",
        "tbd",
        "todo",
        "unknown",
    }:
        return False
    return True


def _publisher_statement_has_exact_scope(
    description: str,
    section_path: Sequence[str],
    target: TargetIdentity,
) -> bool:
    scope_text = " ".join((*section_path, description))
    if _RELATED_MODEL_RE.search(scope_text) or _MIXED_VARIANT_RE.search(
        description
    ):
        return False
    target_name_tokens = tuple(
        _normalized_heading(target.model_id.split("/", 1)[1]).split()
    )
    normalized_description = _normalized_heading(description)
    if _FAMILY_SCOPE_PROSE_RE.search(normalized_description):
        return False
    # A publisher can name a family without saying "family", as in
    # "The OLMo-2 models ..." on an exact-checkpoint card.  A proper prefix of
    # the target name followed by plural ``models`` is still family evidence,
    # not exact-checkpoint evidence.  Reject the complete mixed-scope sentence;
    # do not turn its later singular anaphor into an exact-target claim.
    for token_count in range(1, len(target_name_tokens)):
        family_phrase = " ".join((*target_name_tokens[:token_count], "models"))
        if re.search(
            rf"(?:^|\s){re.escape(family_phrase)}(?:\s|$)",
            normalized_description,
        ):
            return False
    for title in section_path:
        if _FAMILY_SCOPE_HEADING_RE.search(title):
            return False
        heading_tokens = tuple(
            token
            for token in _normalized_heading(title).split()
            if token not in _SCOPE_HEADING_GENERIC_TOKENS
        )
        # A heading that names only a proper prefix of the exact checkpoint is
        # family/release scope, not evidence for the exact target.  Exact names
        # remain admissible; generic structural headings contribute no tokens.
        if (
            heading_tokens
            and len(heading_tokens) < len(target_name_tokens)
            and heading_tokens == target_name_tokens[: len(heading_tokens)]
        ):
            return False
        # A sibling checkpoint title can contain every token in the target
        # name plus a variant marker (for example, ``Mistral 7B Instruct
        # v0.3`` while the target is ``Mistral-7B-v0.3``).  It is neither a
        # simple family prefix nor an explicit ``org/model`` identifier, so
        # the guards above do not catch it.  Treat any model-like heading that
        # overlaps at least two exact-target tokens but is not the exact token
        # sequence as conflicting scope.  Generic structural headings have no
        # such overlap and remain admissible.
        if (
            heading_tokens
            and heading_tokens != target_name_tokens
            and len(set(heading_tokens).intersection(target_name_tokens)) >= 2
        ):
            return False
    target_id = target.model_id.casefold()
    if not all(
        match.group(0).casefold() == target_id
        for match in _MODEL_ID_IN_PROSE_RE.finditer(scope_text)
    ):
        return False
    return True


def _accepted_publisher_context_fields(
    gate_records: Iterable[ClaimGateRecord],
) -> tuple[tuple[ClaimGateRecord, ...], frozenset[str]]:
    values = tuple(gate_records)
    if not all(isinstance(item, ClaimGateRecord) for item in values):
        raise ExtractionError(
            "existing publisher-context gate records must be typed"
        )
    for item in values:
        item.validate_integrity()
    populated = frozenset(
        canonical_field_path(item.candidate.field_path)
        for item in values
        if item.projection_eligible
        and item.candidate.relation is RelationToTarget.EXACT_TARGET
        and canonical_field_path(item.candidate.field_path)
        in _PUBLISHER_CONTEXT_FIELDS
    )
    return values, populated


def _publisher_context_source_is_eligible(
    source: SourceDocument, target: TargetIdentity
) -> bool:
    if (
        source.text is None
        or source.synthetic
        or source.target != target
    ):
        return False
    # The frozen, root model-card README is publisher documentation bound to the
    # exact Hub revision. Other declared Markdown/text snapshots and developer
    # reports require provider-assisted semantic binding because the document
    # type alone does not prove checkpoint scope.
    if source.role is not SourceRole.HUGGING_FACE_SNAPSHOT:
        return False
    parsed = urlsplit(source.source_uri)
    return (
        parsed.scheme == "https"
        and parsed.netloc.casefold() == "huggingface.co"
        and parsed.path
        in {
            f"/{target.model_id}/resolve/{target.revision}/README.md",
            f"/{target.model_id}/blob/{target.revision}/README.md",
        }
        and not parsed.query
        and not parsed.fragment
    )


def _publisher_license_source_is_eligible(
    source: SourceDocument, target: TargetIdentity
) -> bool:
    """Return whether a bundled model license is pinned to the exact target."""

    if (
        source.text is None
        or source.synthetic
        or source.target != target
        or source.source_revision != target.revision
        or source.role is not SourceRole.HUGGING_FACE_SNAPSHOT
    ):
        return False
    parsed = urlsplit(source.source_uri)
    return (
        parsed.scheme == "https"
        and parsed.netloc.casefold() == "huggingface.co"
        and parsed.path
        in {
            f"/{target.model_id}/resolve/{target.revision}/LICENSE-MODEL",
            f"/{target.model_id}/blob/{target.revision}/LICENSE-MODEL",
        }
        and not parsed.query
        and not parsed.fragment
    )


def _deepseek_license_restrictions(source: SourceDocument) -> tuple[str, ...]:
    """Parse the one closed, explicitly model-scoped DeepSeek restriction block.

    This is intentionally not a general license parser. Every anchor must be a
    unique complete line, Attachment A must directly contain the named section
    and applicability clause, and the remainder must be one contiguous list of
    complete restrictions. Any structural ambiguity withholds the whole block.
    """

    lines = source.text.splitlines() if source.text is not None else []
    normalized_lines = tuple(normalize_ws(line) for line in lines)
    nonempty = tuple(index for index, line in enumerate(normalized_lines) if line)
    if not nonempty or normalized_lines[nonempty[0]] != _DEEPSEEK_LICENSE_TITLE:
        return ()

    anchors = (
        _DEEPSEEK_LICENSE_TITLE,
        _DEEPSEEK_LICENSE_ATTACHMENT,
        _DEEPSEEK_LICENSE_USE_RESTRICTIONS,
        _DEEPSEEK_LICENSE_SCOPE,
    )
    positions: list[int] = []
    for anchor in anchors:
        matches = tuple(
            index for index, line in enumerate(normalized_lines) if line == anchor
        )
        if len(matches) != 1:
            return ()
        positions.append(matches[0])
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        return ()

    def next_nonempty(index: int) -> int | None:
        return next(
            (
                candidate
                for candidate in range(index + 1, len(normalized_lines))
                if normalized_lines[candidate]
            ),
            None,
        )

    if (
        next_nonempty(positions[1]) != positions[2]
        or next_nonempty(positions[2]) != positions[3]
    ):
        return ()

    restrictions: list[str] = []
    seen: set[str] = set()
    normalized_source = normalize_ws(source.text or "")
    for index in range(positions[3] + 1, len(lines)):
        if not normalized_lines[index]:
            continue
        match = _DEEPSEEK_LICENSE_BULLET_RE.fullmatch(lines[index])
        if match is None:
            return ()
        description = normalize_ws(match.group(1))
        folded = description.casefold()
        if (
            not 20 <= len(description) <= MAX_PROVIDER_QUOTE_CHARS
            or len(_WORD_RE.findall(description)) < 5
            or description[-1] not in ".;!?"
            or folded in seen
            or normalized_source.count(description) != 1
        ):
            return ()
        seen.add(folded)
        restrictions.append(description)
    return tuple(restrictions)


def deterministic_publisher_context_candidates(
    catalog: SourceDocumentCatalog,
    *,
    existing_gate_records: Iterable[ClaimGateRecord] = (),
) -> ExtractionResult:
    """Extract exact context from closed, revision-pinned publisher sources.

    This pass does not infer risks and never invents prose. It admits only an
    exact substring from an exact-target, non-synthetic publisher source. Root
    README statements require closed structural ancestry and an exact-subject
    predicate. A bundled ``LICENSE-MODEL`` uses a separate, strict DeepSeek
    restriction-block parser; the generic README path still excludes legal text.
    A field already populated by a provider candidate that passed the complete
    claim gate is left untouched, preserving the provider's list indices. Mere
    materialization is not sufficient: an unverified or semantically rejected
    provider proposal cannot suppress stronger deterministic evidence.
    """

    existing, populated_fields = _accepted_publisher_context_fields(
        existing_gate_records
    )
    material: list[
        tuple[str, int, str, str, QuoteProposal, Evidence]
    ] = []
    for source in sorted(catalog.documents, key=lambda item: item.source_id):
        if _publisher_license_source_is_eligible(source, catalog.target):
            for description in _deepseek_license_restrictions(source):
                evidence = _quote_evidence(source, description)
                if not evidence.verified or evidence.char_start is None:
                    continue
                field_path = "use_and_risk.out_of_scope_uses"
                if field_path in populated_fields:
                    continue
                proposal = QuoteProposal(
                    source_id=source.source_id,
                    field_path=f"{field_path}[0]",  # stable index assigned below
                    value=description,
                    quote=description,
                    claim_entity=(
                        f"{catalog.target.model_id}@{catalog.target.revision}"
                    ),
                    relation=RelationToTarget.EXACT_TARGET,
                    origin="source_stated",
                )
                material.append(
                    (
                        source.source_id,
                        evidence.char_start,
                        field_path,
                        description,
                        proposal,
                        evidence,
                    )
                )
            continue
        if not _publisher_context_source_is_eligible(source, catalog.target):
            continue
        for raw_segment in _publisher_text_segments(source.text):
            for segment in _target_scoped_publisher_segments(
                raw_segment, source, catalog.target
            ):
                if not _publisher_statement_is_substantive(
                    segment.description,
                    complete_clause_without_terminal_punctuation=(
                        segment.complete_clause_without_terminal_punctuation
                    ),
                ):
                    continue
                structural_fields = _publisher_structural_fields(
                    segment.section_path
                )
                if not structural_fields:
                    continue
                if not _publisher_statement_has_exact_scope(
                    segment.description,
                    segment.section_path,
                    catalog.target,
                ):
                    continue
                explicit_fields = _publisher_statement_fields(
                    segment.description, catalog.target
                )
                if not explicit_fields:
                    explicit_fields = _heading_scoped_anaphoric_fields(
                        segment, catalog.target
                    )
                if segment.inline_field is not None:
                    field_path = segment.inline_field
                    if explicit_fields and explicit_fields != {field_path}:
                        continue
                else:
                    if len(explicit_fields) != 1:
                        continue
                    field_path = next(iter(explicit_fields))
                if (
                    field_path not in structural_fields
                    or field_path in populated_fields
                ):
                    continue
                if (
                    field_path != "use_and_risk.out_of_scope_uses"
                    and _LEGAL_CONTEXT_VALUE_RE.search(segment.description)
                ):
                    continue
                if (
                    field_path == "use_and_risk.mitigations"
                    and not _MITIGATION_ACTION_RE.search(segment.description)
                ):
                    continue
                evidence = _quote_evidence(source, segment.description)
                if (
                    not evidence.verified
                    or evidence.char_start is None
                    or evidence.section_path != segment.section_path
                ):
                    # Ambiguous duplicate prose can otherwise replay to a related-model
                    # section. Omission is safer than accepting a different occurrence.
                    continue
                proposal = QuoteProposal(
                    source_id=source.source_id,
                    field_path=f"{field_path}[0]",  # replaced after stable grouping
                    value=segment.description,
                    quote=segment.description,
                    claim_entity=(
                        f"{catalog.target.model_id}@{catalog.target.revision}"
                    ),
                    relation=RelationToTarget.EXACT_TARGET,
                    origin="source_stated",
                )
                material.append(
                    (
                        source.source_id,
                        evidence.char_start,
                        field_path,
                        segment.description,
                        proposal,
                        evidence,
                    )
                )

    candidates: list[ClaimCandidate] = []
    outcomes: list[ProposalOutcome] = []
    counts = {field_path: 0 for field_path in _PUBLISHER_CONTEXT_FIELDS}
    seen: set[tuple[str, str]] = set()
    for _source_id, _start, field_path, description, prototype, evidence in sorted(
        material, key=lambda item: (item[0], item[1], item[2], item[3])
    ):
        key = (field_path, normalize_ws(description).casefold())
        if key in seen:
            continue
        index = counts[field_path]
        if index >= MAX_DETERMINISTIC_PUBLISHER_CONTEXTS_PER_FIELD:
            continue
        seen.add(key)
        counts[field_path] += 1
        proposal = QuoteProposal(
            source_id=prototype.source_id,
            field_path=f"{field_path}[{index}]",
            value=prototype.value,
            quote=prototype.quote,
            claim_entity=prototype.claim_entity,
            relation=prototype.relation,
            origin=prototype.origin,
        )
        if field_path == "use_and_risk.mitigations":
            value: JsonValue = make_mitigation_value(
                description=description, evidence=(evidence,)
            )
        else:
            value = make_context_statement_value(
                field_path=proposal.field_path,
                description=description,
                origin="publisher_reported",
                evidence=(evidence,),
            )
        binding = _binding_from_quote_evidence(
            catalog.target, proposal, value, evidence
        )
        candidate = ClaimCandidate.from_binding(catalog.target, binding)
        candidates.append(candidate)
        outcomes.append(
            ProposalOutcome(
                proposal.proposal_id,
                ProposalStatus.MATERIALIZED,
                "candidate_materialized",
                candidate.candidate_id,
            )
        )

    input_digest = _digest(
        {
            "mode": DETERMINISTIC_PUBLISHER_CONTEXT_VERSION,
            "catalog_sha256": catalog.catalog_sha256,
            "existing_gate_records": [
                {
                    "candidate_id": item.candidate.candidate_id,
                    "candidate_sha256": item.candidate.content_sha256,
                    "gate_record_sha256": item.content_sha256,
                }
                for item in sorted(
                    existing, key=lambda item: item.candidate.candidate_id
                )
            ],
            "populated_fields": sorted(populated_fields),
        }
    )
    return _make_result(
        catalog.target,
        input_digest,
        tuple(sorted(candidates, key=lambda item: item.candidate_id)),
        tuple(sorted(outcomes, key=lambda item: item.proposal_id)),
    )


def _quote_proposal_item_schema(field_path_pattern: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "source_id",
            "field_path",
            "value_json",
            "quote",
            "claim_entity",
            "relation",
            "origin",
        ],
        "properties": {
            "source_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128,
            },
            "field_path": {
                "type": "string",
                "pattern": field_path_pattern,
                "maxLength": MAX_PROVIDER_FIELD_PATH_CHARS,
            },
            "value_json": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_PROVIDER_VALUE_JSON_CHARS,
                "description": (
                    "JSON text encoding the exact field value; preserve stated units "
                    "and satisfy the supplied field contract"
                ),
            },
            "quote": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_PROVIDER_QUOTE_CHARS,
            },
            "claim_entity": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_PROVIDER_ENTITY_CHARS,
            },
            "relation": {"enum": [item.value for item in RelationToTarget]},
            "origin": {"enum": ["source_stated", "source_derived"]},
        },
        "additionalProperties": False,
    }


def _response_schema(
    *,
    name: str,
    max_proposals: int,
    field_path_pattern: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "strict": True,
        "schema": {
            "type": "object",
            "required": ["proposals"],
            "properties": {
                "proposals": {
                    "type": "array",
                    "maxItems": max_proposals,
                    "items": _quote_proposal_item_schema(field_path_pattern),
                }
            },
            "additionalProperties": False,
        },
    }


def extraction_response_schema() -> dict[str, Any]:
    """Strict server schema for the general quote-extraction response.

    Benchmark scope is intentionally absent from provider output.  For a
    benchmark-score row, the three scope coordinates are copied locally from
    the already typed row, eliminating a redundant provider-controlled value.
    """

    return _response_schema(
        name=EXTRACTION_SCHEMA_NAME,
        max_proposals=MAX_PROVIDER_PROPOSALS,
        field_path_pattern=_PROVIDER_FIELD_PATH_PATTERN,
    )


def use_risk_extraction_response_schema() -> dict[str, Any]:
    """Strict schema for the bounded publisher use/risk recovery pass."""

    return _response_schema(
        name=USE_RISK_EXTRACTION_SCHEMA_NAME,
        max_proposals=MAX_USE_RISK_PROVIDER_PROPOSALS,
        field_path_pattern=_USE_RISK_FIELD_PATH_PATTERN,
    )


def proposals_from_provider_value(value: Any) -> tuple[QuoteProposal, ...]:
    """Normalize one already-schema-validated response without retaining its envelope."""

    item = _strict(value, {"proposals"}, "extraction response")
    if (
        not isinstance(item["proposals"], list)
        or len(item["proposals"]) > MAX_PROVIDER_PROPOSALS
    ):
        raise ExtractionError("extraction response proposal count is invalid")
    proposals: list[QuoteProposal] = []
    for raw in item["proposals"]:
        entry = _strict(
            raw,
            {
                "source_id",
                "field_path",
                "value_json",
                "quote",
                "claim_entity",
                "relation",
                "origin",
            },
            "provider quote proposal",
        )
        try:
            proposed_value = json.loads(
                entry["value_json"],
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except ExtractionError as exc:
            # Duplicate keys and non-finite values are ambiguous and must never
            # be repaired into a different claim.
            raise ExtractionError("provider proposal contains invalid canonical JSON") from exc
        except json.JSONDecodeError as exc:
            # Some structured-output providers obey the outer schema but return
            # unquoted prose in the nested JSON-string field. Recover only plain
            # scalar fields and the closed set of description-only publisher
            # use/risk list fields. The exact bytes still face quote replay,
            # field fit, value support, and schema validation; all structured
            # list items remain fail-closed.
            base = canonical_field_path(entry["field_path"])
            raw_value = entry["value_json"]
            if (
                (
                    base in LIST_FIELDS
                    and base not in _CONTEXT_FIELDS
                    and base != "use_and_risk.mitigations"
                )
                or not isinstance(raw_value, str)
                or not normalize_ws(raw_value)
            ):
                raise ExtractionError(
                    "provider proposal contains invalid canonical JSON"
                ) from exc
            proposed_value = raw_value

        base = canonical_field_path(entry["field_path"])
        scope = None
        if base == "evaluation.benchmark_scores" and isinstance(proposed_value, dict):
            if all(key in proposed_value for key in ("benchmark", "metric", "setting")):
                scope = {
                    key: deepcopy(proposed_value[key])
                    for key in ("benchmark", "metric", "setting")
                }
        proposals.append(
            QuoteProposal(
                source_id=entry["source_id"],
                field_path=entry["field_path"],
                value=proposed_value,
                quote=entry["quote"],
                claim_entity=entry["claim_entity"],
                relation=entry["relation"],
                benchmark_scope=scope,
                origin=entry["origin"],
            )
        )
    values = tuple(sorted(proposals, key=lambda proposal: proposal.proposal_id))
    if len({item.proposal_id for item in values}) != len(values):
        raise ExtractionError("provider returned duplicate quote proposals")
    return values


def normalize_provider_proposals(
    value: Any,
    *,
    expected_source_id: str,
) -> tuple[tuple[QuoteProposal, ...], tuple[ProviderProposalRejection, ...]]:
    """Fail closed per schema-shaped provider item without discarding its peers."""

    if not isinstance(expected_source_id, str) or not expected_source_id:
        raise ExtractionError("expected provider source identifier is invalid")
    item = _strict(value, {"proposals"}, "extraction response")
    raw_values = item["proposals"]
    if (
        not isinstance(raw_values, list)
        or len(raw_values) > MAX_PROVIDER_PROPOSALS
    ):
        raise ExtractionError("extraction response proposal count is invalid")
    accepted: dict[str, QuoteProposal] = {}
    rejections: list[ProviderProposalRejection] = []
    for index, raw in enumerate(raw_values):
        raw_sha256 = _digest(raw)
        try:
            proposal = proposals_from_provider_value({"proposals": [raw]})[0]
        except (ExtractionError, TypeError, ValueError):
            rejections.append(
                ProviderProposalRejection(
                    proposal_index=index,
                    proposal_sha256=raw_sha256,
                    reason="proposal_contract_invalid",
                )
            )
            continue
        if proposal.source_id != expected_source_id:
            rejections.append(
                ProviderProposalRejection(
                    proposal_index=index,
                    proposal_sha256=raw_sha256,
                    reason="source_identifier_mismatch",
                )
            )
            continue
        if proposal.proposal_id in accepted:
            rejections.append(
                ProviderProposalRejection(
                    proposal_index=index,
                    proposal_sha256=raw_sha256,
                    reason="duplicate_proposal",
                )
            )
            continue
        accepted[proposal.proposal_id] = proposal
    return (
        tuple(sorted(accepted.values(), key=lambda proposal: proposal.proposal_id)),
        tuple(rejections),
    )


def _quote_evidence(source: SourceDocument, quote: str) -> Evidence:
    normalized_quote = normalize_ws(quote)
    match = match_quote(quote, source.text or "")
    section_path: tuple[str, ...] = ()
    table_id = None
    if match is not None:
        context = build_document_index(source.text or "").context_at(
            match.char_start, match.char_end
        )
        section_path = context.section_path
        table_id = context.table_id
    return Evidence(
        kind=EvidenceKind.QUOTE,
        source_id=source.source_id,
        source_uri=source.source_uri,
        source_role=source.role,
        source_revision=source.source_revision,
        source_sha256=source.sha256,
        source_target=source.target,
        synthetic=source.synthetic,
        verified=match is not None,
        quote=match.quote if match else normalized_quote,
        char_start=match.char_start if match else None,
        char_end=match.char_end if match else None,
        section_path=section_path,
        table_id=table_id,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExtractionError("provider JSON value contains a duplicate key")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ExtractionError(f"provider JSON value contains a non-finite number: {value}")


def _binding_from_quote_evidence(
    target: TargetIdentity,
    proposal: QuoteProposal,
    value: JsonValue,
    evidence: Evidence,
) -> Binding:
    evidence_values = (evidence,)
    disposition, reason = decide_binding(
        target=target,
        field_path=proposal.field_path,
        value=value,
        claim_entity=proposal.claim_entity,
        relation=proposal.relation,
        origin=BindingOrigin.QUOTED,
        evidence=evidence_values,
    )
    return Binding(
        binding_id=binding_id_for(
            target=target,
            field_path=proposal.field_path,
            value=value,
            claim_entity=proposal.claim_entity,
            relation=proposal.relation,
            origin=BindingOrigin.QUOTED,
            evidence=evidence_values,
            benchmark_scope=proposal.benchmark_scope,
        ),
        field_path=proposal.field_path,
        value=value,
        claim_entity=proposal.claim_entity,
        relation=proposal.relation,
        origin=BindingOrigin.QUOTED,
        evidence=evidence_values,
        disposition=Disposition(disposition),
        reason=reason,
        benchmark_scope=proposal.benchmark_scope,
    )


def _make_result(
    target: TargetIdentity,
    input_sha256: str,
    candidates: tuple[ClaimCandidate, ...],
    outcomes: tuple[ProposalOutcome, ...],
) -> ExtractionResult:
    payload = {
        "extraction_version": EXTRACTION_VERSION,
        "target": target.to_dict(),
        "input_sha256": input_sha256,
        "candidate_ids": [item.candidate_id for item in candidates],
        "candidate_sha256": [item.content_sha256 for item in candidates],
        "outcomes": [item.to_dict() for item in outcomes],
    }
    return ExtractionResult(
        extraction_version=EXTRACTION_VERSION,
        target=target,
        input_sha256=input_sha256,
        candidates=candidates,
        outcomes=outcomes,
        result_sha256=_digest(payload),
    )


__all__ = [
    "DETERMINISTIC_PUBLISHER_CONTEXT_VERSION",
    "DEFAULT_MAX_WINDOWS",
    "DEFAULT_WINDOW_CHARS",
    "DEFAULT_WINDOW_OVERLAP",
    "EXTRACTION_SCHEMA_NAME",
    "EXTRACTION_VERSION",
    "USE_RISK_EXTRACTION_SCHEMA_NAME",
    "ExtractionBatch",
    "ExtractionError",
    "ExtractionResult",
    "MAX_PROVIDER_ENTITY_CHARS",
    "MAX_EXTRACTION_BATCH_PROPOSALS",
    "MAX_DETERMINISTIC_PUBLISHER_CONTEXTS_PER_FIELD",
    "MAX_PROVIDER_FIELD_PATH_CHARS",
    "MAX_PROVIDER_PROPOSALS",
    "MAX_PROVIDER_QUOTE_CHARS",
    "MAX_PROVIDER_RISK_DESCRIPTION_CHARS",
    "MAX_PROVIDER_RISK_NAME_CHARS",
    "MAX_PROVIDER_RISK_RATIONALE_CHARS",
    "MAX_PROVIDER_SCOPE_JSON_CHARS",
    "MAX_PROVIDER_VALUE_JSON_CHARS",
    "MAX_USE_RISK_PROVIDER_PROPOSALS",
    "PUBLISHER_RISK_FIELD",
    "PUBLISHER_RISK_PROPOSAL_FIELDS",
    "ProposalOutcome",
    "ProposalStatus",
    "ProviderProposalRejection",
    "QuoteProposal",
    "SourceWindow",
    "build_source_windows",
    "build_use_risk_windows",
    "deterministic_publisher_context_candidates",
    "deterministic_structured_candidates",
    "extraction_response_schema",
    "materialize_quote_batch",
    "normalize_provider_proposals",
    "publisher_risk_proposal_schema",
    "proposals_from_provider_value",
    "use_risk_extraction_response_schema",
]
