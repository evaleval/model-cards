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
from typing import Any, Iterable, Mapping

from .bindings import binding_id_for, resolve_json_pointer, structured_binding
from .claim_gate import (
    ClaimCandidate,
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
    TargetIdentity,
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


EXTRACTION_VERSION = "model-card-evidence-extraction/v3"
EXTRACTION_SCHEMA_NAME = "model_card_quote_evidence_extraction_v1"
INFERENCE_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_WINDOW_CHARS = 12_000
DEFAULT_WINDOW_OVERLAP = 500
DEFAULT_MAX_WINDOWS = 16
# Keep one strict-schema response empirically below the provider's 8,192-token
# completion ceiling. Extraction is deliberately selective, and downstream
# field-level omission records keep absent coverage explicit.
MAX_PROVIDER_PROPOSALS = 8
MAX_PROVIDER_FIELD_PATH_CHARS = 160
MAX_PROVIDER_VALUE_JSON_CHARS = 1_600
MAX_PROVIDER_QUOTE_CHARS = 800
MAX_PROVIDER_ENTITY_CHARS = 256
MAX_PROVIDER_SCOPE_JSON_CHARS = 1_000
MAX_PROVIDER_RISK_NAME_CHARS = 256
MAX_PROVIDER_RISK_DESCRIPTION_CHARS = 640
MAX_PROVIDER_RISK_RATIONALE_CHARS = 512

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
            or not 0 <= self.proposal_index < MAX_PROVIDER_PROPOSALS
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
    normalized_start: int
    normalized_end: int
    excerpt: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"window-[0-9a-f]{24}", self.window_id):
            raise ExtractionError("source window_id is invalid")
        if not self.source_id or not self.source_uri.startswith("https://"):
            raise ExtractionError("source window identity is invalid")
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
                normalized_start=start,
                normalized_end=end,
                excerpt=excerpt,
            )
        )
        if end == len(text):
            break
        start += step
    return tuple(windows)


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
        if len(self.proposals) + len(self.rejections) > MAX_PROVIDER_PROPOSALS:
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
        }
    )
    return _make_result(catalog.target, input_digest, candidate_values, outcome_values)


def extraction_response_schema() -> dict[str, Any]:
    """Strict server-side JSON Schema for one provider quote-extraction response."""

    return {
        "name": EXTRACTION_SCHEMA_NAME,
        "strict": True,
        "schema": {
            "type": "object",
            "required": ["proposals"],
            "properties": {
                "proposals": {
                    "type": "array",
                    "maxItems": MAX_PROVIDER_PROPOSALS,
                    "items": {
                        "type": "object",
                        "required": [
                            "source_id",
                            "field_path",
                            "value_json",
                            "quote",
                            "claim_entity",
                            "relation",
                            "benchmark_scope_json",
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
                                "pattern": _PROVIDER_FIELD_PATH_PATTERN,
                                "maxLength": MAX_PROVIDER_FIELD_PATH_CHARS,
                            },
                            "value_json": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": MAX_PROVIDER_VALUE_JSON_CHARS,
                                "description": (
                                    "JSON text encoding the exact field value; preserve "
                                    "stated units and satisfy the supplied field contract"
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
                            "benchmark_scope_json": {
                                "type": ["string", "null"],
                                "maxLength": MAX_PROVIDER_SCOPE_JSON_CHARS,
                                "description": (
                                    "null, or JSON text encoding a benchmark-scope object"
                                ),
                            },
                            "origin": {"enum": ["source_stated", "source_derived"]},
                        },
                        "additionalProperties": False,
                    },
                }
            },
            "additionalProperties": False,
        },
    }


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
                "benchmark_scope_json",
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
            scope = (
                None
                if entry["benchmark_scope_json"] is None
                else json.loads(
                    entry["benchmark_scope_json"],
                    object_pairs_hook=_reject_duplicate_keys,
                    parse_constant=_reject_nonfinite,
                )
            )
        except (json.JSONDecodeError, ExtractionError) as exc:
            raise ExtractionError("provider proposal contains invalid canonical JSON") from exc
        if scope is not None and not isinstance(scope, dict):
            raise ExtractionError("provider benchmark_scope_json must decode to an object")
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
    "DEFAULT_MAX_WINDOWS",
    "DEFAULT_WINDOW_CHARS",
    "DEFAULT_WINDOW_OVERLAP",
    "EXTRACTION_SCHEMA_NAME",
    "EXTRACTION_VERSION",
    "ExtractionBatch",
    "ExtractionError",
    "ExtractionResult",
    "MAX_PROVIDER_ENTITY_CHARS",
    "MAX_PROVIDER_FIELD_PATH_CHARS",
    "MAX_PROVIDER_PROPOSALS",
    "MAX_PROVIDER_QUOTE_CHARS",
    "MAX_PROVIDER_RISK_DESCRIPTION_CHARS",
    "MAX_PROVIDER_RISK_NAME_CHARS",
    "MAX_PROVIDER_RISK_RATIONALE_CHARS",
    "MAX_PROVIDER_SCOPE_JSON_CHARS",
    "MAX_PROVIDER_VALUE_JSON_CHARS",
    "PUBLISHER_RISK_FIELD",
    "PUBLISHER_RISK_PROPOSAL_FIELDS",
    "ProposalOutcome",
    "ProposalStatus",
    "ProviderProposalRejection",
    "QuoteProposal",
    "SourceWindow",
    "build_source_windows",
    "deterministic_structured_candidates",
    "extraction_response_schema",
    "materialize_quote_batch",
    "normalize_provider_proposals",
    "publisher_risk_proposal_schema",
    "proposals_from_provider_value",
]
