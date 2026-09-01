"""Evidence-grounded AI Atlas Nexus risk candidates and applicability gating.

Publisher-reported risks remain ordinary evidence-bound claims.  This module is
only for taxonomy-inferred *candidate* risks: it conditions the supported generic
AI Atlas Nexus use-case interface on accepted Model Card use context, verifies
every returned identifier against one pinned IBM AI Risk Atlas snapshot, and
requires a separate applicability decision before projection.

The optional Nexus dependency is imported lazily because release 1.2.4 requires
Python 3.11 and a sizeable scientific stack.  Core package tests use injected
catalogs/detectors and never call a provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from functools import lru_cache
import hashlib
from importlib import metadata, resources
import json
import logging
import re
from typing import Any, Iterable, Protocol, Sequence

from .schema import canonical_field_path


RISK_MAPPING_VERSION = "model-card-risk-mapping/v1"
APPLICABILITY_GATE_VERSION = "risk-applicability-gate/v1"
NEXUS_PACKAGE_VERSION = "1.2.4"
NEXUS_TAXONOMY_ID = "ibm-risk-atlas"
RISK_ATLAS_NAME = "IBM AI Risk Atlas"
RISK_ATLAS_RELEASE = "ai-atlas-nexus-1.2.4"
RISK_ATLAS_SOURCE_URL = "https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas"
RISK_ATLAS_SNAPSHOT_SHA256 = (
    "7bc4bf5ada7856e0963f5a1b41918a9ac22c246ee1f38b9b99589e9db282ddcb"
)
INFERENCE_MODEL = "deepseek/deepseek-v4-flash-0731"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,255}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._:-]{1,127}$")
_FIELD_PATH_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*(?:\[[0-9]+\])?$")


class RiskMappingError(ValueError):
    """Risk taxonomy, mapping, or applicability material failed closed."""


class MappingStatus(str, Enum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ApplicabilityStatus(str, Enum):
    ACCEPTED = "accepted"
    WITHHELD = "withheld"
    UNAVAILABLE = "unavailable"


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
        raise RiskMappingError("risk mapping values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise RiskMappingError(f"{label} has an invalid closed shape")
    return value


@dataclass(frozen=True)
class TaxonomyRelease:
    taxonomy_id: str = NEXUS_TAXONOMY_ID
    name: str = RISK_ATLAS_NAME
    version: str = RISK_ATLAS_RELEASE
    source_url: str = RISK_ATLAS_SOURCE_URL
    snapshot_sha256: str = RISK_ATLAS_SNAPSHOT_SHA256
    nexus_version: str = NEXUS_PACKAGE_VERSION

    def __post_init__(self) -> None:
        expected = (
            NEXUS_TAXONOMY_ID,
            RISK_ATLAS_NAME,
            RISK_ATLAS_RELEASE,
            RISK_ATLAS_SOURCE_URL,
            RISK_ATLAS_SNAPSHOT_SHA256,
            NEXUS_PACKAGE_VERSION,
        )
        if (
            self.taxonomy_id,
            self.name,
            self.version,
            self.source_url,
            self.snapshot_sha256,
            self.nexus_version,
        ) != expected:
            raise RiskMappingError("taxonomy release is not the pinned IBM AI Risk Atlas")

    def to_dict(self) -> dict[str, str]:
        return {
            "taxonomy_id": self.taxonomy_id,
            "name": self.name,
            "version": self.version,
            "source_url": self.source_url,
            "snapshot_sha256": self.snapshot_sha256,
        }


@dataclass(frozen=True)
class TaxonomyRisk:
    risk_id: str
    name: str
    description: str
    source_url: str
    mitigation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.risk_id, str) or not _ID_RE.fullmatch(self.risk_id):
            raise RiskMappingError("taxonomy risk_id is invalid")
        for name, value in (("name", self.name), ("description", self.description)):
            if not isinstance(value, str) or not value.strip():
                raise RiskMappingError(f"taxonomy risk {name} is invalid")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.source_url, str) or not self.source_url.startswith("https://"):
            raise RiskMappingError("taxonomy risk source_url must be HTTPS")
        mitigations = tuple(sorted(set(self.mitigation_ids)))
        if any(not re.fullmatch(r"mitigation:[a-z0-9][a-z0-9._-]*", item) for item in mitigations):
            raise RiskMappingError("taxonomy mitigation identifier is invalid")
        object.__setattr__(self, "mitigation_ids", mitigations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "name": self.name,
            "description": self.description,
            "source_url": self.source_url,
            "mitigation_ids": list(self.mitigation_ids),
        }


@dataclass(frozen=True)
class RiskCatalog:
    release: TaxonomyRelease
    risks: tuple[TaxonomyRisk, ...]
    catalog_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "risks", tuple(self.risks))
        if not isinstance(self.release, TaxonomyRelease):
            raise RiskMappingError("risk catalog release is invalid")
        if not self.risks:
            raise RiskMappingError("risk catalog cannot be empty")
        identifiers = [item.risk_id for item in self.risks]
        if identifiers != sorted(identifiers) or len(identifiers) != len(set(identifiers)):
            raise RiskMappingError("risk catalog identifiers must be sorted and unique")
        expected = _digest(
            {
                "release": self.release.to_dict(),
                "risks": [item.to_dict() for item in self.risks],
            }
        )
        if self.catalog_sha256 != expected:
            raise RiskMappingError("risk catalog digest is inconsistent")

    @classmethod
    def build(
        cls,
        risks: Iterable[TaxonomyRisk],
        *,
        release: TaxonomyRelease = TaxonomyRelease(),
    ) -> "RiskCatalog":
        values = tuple(sorted(tuple(risks), key=lambda item: item.risk_id))
        digest = _digest(
            {
                "release": release.to_dict(),
                "risks": [item.to_dict() for item in values],
            }
        )
        return cls(release=release, risks=values, catalog_sha256=digest)

    def risk(self, risk_id: str) -> TaxonomyRisk:
        for item in self.risks:
            if item.risk_id == risk_id:
                return item
        raise KeyError(risk_id)


@lru_cache(maxsize=1)
def load_pinned_nexus_catalog() -> RiskCatalog:
    """Load AI Atlas Nexus 1.2.4 and verify its exact Risk Atlas data bytes."""

    try:
        installed = metadata.version("ai-atlas-nexus")
    except metadata.PackageNotFoundError as exc:
        raise RiskMappingError("ai-atlas-nexus 1.2.4 is unavailable") from exc
    if installed != NEXUS_PACKAGE_VERSION:
        raise RiskMappingError("ai-atlas-nexus version differs from the pinned release")
    try:
        snapshot = resources.files("ai_atlas_nexus").joinpath(
            "data", "knowledge_graph", "risk_atlas_data.yaml"
        ).read_bytes()
    except (AttributeError, FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise RiskMappingError("pinned IBM AI Risk Atlas snapshot is unavailable") from exc
    if hashlib.sha256(snapshot).hexdigest() != RISK_ATLAS_SNAPSHOT_SHA256:
        raise RiskMappingError("IBM AI Risk Atlas snapshot digest has drifted")
    try:
        nexus = _new_nexus_instance()
        raw_risks = nexus.get_all_risks(NEXUS_TAXONOMY_ID)
    except Exception as exc:  # dependency boundary; no provider data is echoed
        raise RiskMappingError("AI Atlas Nexus could not load the pinned taxonomy") from exc
    risks: list[TaxonomyRisk] = []
    for raw in raw_risks:
        if getattr(raw, "isDefinedByTaxonomy", None) != NEXUS_TAXONOMY_ID:
            raise RiskMappingError("Nexus returned a risk from another taxonomy")
        risks.append(
            TaxonomyRisk(
                risk_id=str(getattr(raw, "id", "")),
                name=str(getattr(raw, "name", "")),
                description=str(getattr(raw, "description", "")),
                source_url=str(getattr(raw, "url", "")),
                mitigation_ids=(),
            )
        )
    return RiskCatalog.build(risks)


@dataclass(frozen=True)
class UseContext:
    context_id: str
    description: str
    supporting_fields: tuple[str, ...]
    supporting_candidate_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    context_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.context_id, str) or not _ID_RE.fullmatch(self.context_id):
            raise RiskMappingError("use context_id is invalid")
        if not isinstance(self.description, str) or not self.description.strip():
            raise RiskMappingError("use context description is empty")
        fields = tuple(sorted(set(self.supporting_fields)))
        if not fields or any(not _FIELD_PATH_RE.fullmatch(item) for item in fields):
            raise RiskMappingError("use context requires exact supporting card fields")
        candidates = tuple(sorted(set(self.supporting_candidate_ids)))
        if not candidates or any(not re.fullmatch(r"claim-[0-9a-f]{24}", item) for item in candidates):
            raise RiskMappingError("use context requires accepted candidate identifiers")
        refs = tuple(sorted(set(self.source_refs)))
        if not refs or any(not _ID_RE.fullmatch(item) for item in refs):
            raise RiskMappingError("use context requires evidence source references")
        object.__setattr__(self, "supporting_fields", fields)
        object.__setattr__(self, "supporting_candidate_ids", candidates)
        object.__setattr__(self, "source_refs", refs)
        object.__setattr__(self, "context_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "description": self.description,
            "supporting_fields": list(self.supporting_fields),
            "supporting_candidate_ids": list(self.supporting_candidate_ids),
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "context_sha256": self.context_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "UseContext":
        item = _strict(
            value,
            {
                "context_id",
                "description",
                "supporting_fields",
                "supporting_candidate_ids",
                "source_refs",
                "context_sha256",
            },
            "use context",
        )
        result = cls(
            context_id=item["context_id"],
            description=item["description"],
            supporting_fields=tuple(item["supporting_fields"]),
            supporting_candidate_ids=tuple(item["supporting_candidate_ids"]),
            source_refs=tuple(item["source_refs"]),
        )
        if result.context_sha256 != item["context_sha256"]:
            raise RiskMappingError("use context digest is inconsistent")
        return result


@dataclass(frozen=True)
class NexusSelection:
    risk_id: str
    context_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.risk_id, str) or not _ID_RE.fullmatch(self.risk_id):
            raise RiskMappingError("Nexus selection risk_id is invalid")
        contexts = tuple(sorted(set(self.context_ids)))
        if not contexts or any(not _ID_RE.fullmatch(item) for item in contexts):
            raise RiskMappingError("Nexus selection requires use contexts")
        object.__setattr__(self, "context_ids", contexts)


class RiskDetector(Protocol):
    detector_name: str
    detector_version: str
    inference_model: str
    inference_config_sha256: str

    def detect(
        self,
        contexts: tuple[UseContext, ...],
        catalog: RiskCatalog,
    ) -> tuple[NexusSelection, ...]:
        """Return bounded candidate identifiers, never free-form taxonomy entries."""


class NexusGenericRiskDetector:
    """Thin adapter over Nexus's supported generic use-case interface."""

    detector_name = "ai_atlas_nexus.generic_usecase"
    detector_version = NEXUS_PACKAGE_VERSION
    inference_model = INFERENCE_MODEL

    def __init__(self, inference_engine: Any, *, max_risks: int = 5) -> None:
        if not 1 <= max_risks <= 10:
            raise RiskMappingError("max_risks must be between 1 and 10")
        self.inference_engine = inference_engine
        self.max_risks = max_risks
        self.inference_config_sha256 = _digest(
            {
                "interface": "identify_risks_from_usecases",
                "taxonomy": NEXUS_TAXONOMY_ID,
                "max_risks": max_risks,
                "zero_shot_only": True,
                "batch_inference": True,
                "model": INFERENCE_MODEL,
            }
        )

    def detect(
        self,
        contexts: tuple[UseContext, ...],
        catalog: RiskCatalog,
    ) -> tuple[NexusSelection, ...]:
        if catalog.release != TaxonomyRelease():
            raise RiskMappingError("Nexus detector received an unpinned taxonomy")
        if not contexts:
            return ()
        try:
            nexus = _new_nexus_instance()
            results = nexus.identify_risks_from_usecases(
                [item.description for item in contexts],
                self.inference_engine,
                taxonomy=NEXUS_TAXONOMY_ID,
                max_risk=self.max_risks,
                zero_shot_only=True,
                batch_inference=True,
            )
        except Exception as exc:
            raise RiskMappingError("AI Atlas Nexus generic risk detection is unavailable") from exc
        if not isinstance(results, list) or len(results) != len(contexts):
            raise RiskMappingError("AI Atlas Nexus returned incomplete use-case coverage")
        selected: dict[str, set[str]] = {}
        for context, risks in zip(contexts, results):
            if not isinstance(risks, list):
                raise RiskMappingError("AI Atlas Nexus returned a malformed risk list")
            for raw in risks:
                risk_id = str(getattr(raw, "id", ""))
                try:
                    catalog.risk(risk_id)
                except KeyError as exc:
                    raise RiskMappingError("AI Atlas Nexus returned an unknown risk identifier") from exc
                selected.setdefault(risk_id, set()).add(context.context_id)
        return tuple(
            NexusSelection(risk_id, tuple(sorted(context_ids)))
            for risk_id, context_ids in sorted(selected.items())
        )


def _new_nexus_instance() -> Any:
    """Construct Nexus without letting its INFO logger corrupt CLI JSON output."""

    from ai_atlas_nexus.library import AIAtlasNexus

    logger = logging.getLogger("ai_atlas_nexus.library")
    prior_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        return AIAtlasNexus()
    finally:
        logger.setLevel(prior_level)


@dataclass(frozen=True)
class RiskCandidate:
    candidate_id: str
    risk_id: str
    taxonomy: TaxonomyRelease
    name: str
    description: str
    context_ids: tuple[str, ...]
    grounds: tuple[dict[str, str], ...]
    source_refs: tuple[str, ...]
    mapping_method: str
    tool_version: str
    inference_model: str
    inference_config_sha256: str
    candidate_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "context_ids", tuple(self.context_ids))
        object.__setattr__(self, "grounds", tuple(dict(item) for item in self.grounds))
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        if not isinstance(self.taxonomy, TaxonomyRelease):
            raise RiskMappingError("risk candidate taxonomy is invalid")
        if self.mapping_method != "ai_atlas_nexus":
            raise RiskMappingError("risk candidate mapping method is invalid")
        if self.inference_model != INFERENCE_MODEL:
            raise RiskMappingError("risk candidate used an unauthorized inference model")
        if not _DIGEST_RE.fullmatch(self.inference_config_sha256):
            raise RiskMappingError("risk candidate inference config digest is invalid")
        if not self.context_ids or not self.grounds or not self.source_refs:
            raise RiskMappingError("risk candidate must be specifically grounded")
        for ground in self.grounds:
            if set(ground) != {"kind", "ref", "relevance"}:
                raise RiskMappingError("risk ground has an invalid shape")
            if ground["kind"] not in {"card_field", "use_context"}:
                raise RiskMappingError("risk ground kind is invalid")
            if not all(isinstance(value, str) and value for value in ground.values()):
                raise RiskMappingError("risk ground is incomplete")
        expected = _digest(self._payload())
        if self.candidate_sha256 != expected:
            raise RiskMappingError("risk candidate digest is inconsistent")
        if self.candidate_id != "risk-candidate-" + expected[:24]:
            raise RiskMappingError("risk candidate_id is inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "taxonomy": self.taxonomy.to_dict(),
            "name": self.name,
            "description": self.description,
            "context_ids": list(self.context_ids),
            "grounds": list(self.grounds),
            "source_refs": list(self.source_refs),
            "mapping_method": self.mapping_method,
            "tool_version": self.tool_version,
            "inference_model": self.inference_model,
            "inference_config_sha256": self.inference_config_sha256,
        }

    @classmethod
    def build(
        cls,
        risk: TaxonomyRisk,
        contexts: tuple[UseContext, ...],
        detector: RiskDetector,
        release: TaxonomyRelease,
    ) -> "RiskCandidate":
        fields = sorted({field for context in contexts for field in context.supporting_fields})
        grounds = tuple(
            [
                {"kind": "use_context", "ref": item.context_id, "relevance": "nexus_input"}
                for item in contexts
            ]
            + [
                {"kind": "card_field", "ref": field, "relevance": "supports_use_context"}
                for field in fields
            ]
        )
        payload = {
            "risk_id": risk.risk_id,
            "taxonomy": release.to_dict(),
            "name": risk.name,
            "description": risk.description,
            "context_ids": [item.context_id for item in contexts],
            "grounds": list(grounds),
            "source_refs": sorted({ref for item in contexts for ref in item.source_refs}),
            "mapping_method": "ai_atlas_nexus",
            "tool_version": detector.detector_version,
            "inference_model": detector.inference_model,
            "inference_config_sha256": detector.inference_config_sha256,
        }
        digest = _digest(payload)
        return cls(
            candidate_id="risk-candidate-" + digest[:24],
            candidate_sha256=digest,
            risk_id=risk.risk_id,
            taxonomy=release,
            name=risk.name,
            description=risk.description,
            context_ids=tuple(item.context_id for item in contexts),
            grounds=grounds,
            source_refs=tuple(payload["source_refs"]),
            mapping_method="ai_atlas_nexus",
            tool_version=detector.detector_version,
            inference_model=detector.inference_model,
            inference_config_sha256=detector.inference_config_sha256,
        )

    def public_value(
        self,
        decision: "ApplicabilityDecision",
        risk: TaxonomyRisk,
    ) -> dict[str, Any]:
        if decision.candidate_id != self.candidate_id:
            raise RiskMappingError("applicability decision belongs to another candidate")
        if decision.status is not ApplicabilityStatus.ACCEPTED:
            raise RiskMappingError("withheld risk candidate cannot be projected")
        mitigations = list(risk.mitigation_ids)
        return {
            "risk_id": self.risk_id,
            "identification_origin": "taxonomy_identified",
            "taxonomy": self.taxonomy.to_dict(),
            "name": self.name,
            "description": self.description,
            "applicability_rationale": decision.rationale,
            "grounds": list(self.grounds),
            "source_refs": list(self.source_refs),
            "mapping_provenance": {
                "method": "ai_atlas_nexus",
                "tool_version": self.tool_version,
                "inference_model": self.inference_model,
                "inference_config_sha256": self.inference_config_sha256,
            },
            "review_status": "generated_unreviewed",
            "mitigation_assessment": "linked" if mitigations else "none_identified",
            "mitigation_refs": mitigations,
        }


@dataclass(frozen=True)
class ApplicabilityDecision:
    candidate_id: str
    candidate_sha256: str
    status: ApplicabilityStatus
    checker: str
    method: str
    reason: str
    rationale: str
    decision_sha256: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", ApplicabilityStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise RiskMappingError("applicability status is invalid") from exc
        if not re.fullmatch(r"risk-candidate-[0-9a-f]{24}", self.candidate_id):
            raise RiskMappingError("applicability candidate_id is invalid")
        if not _DIGEST_RE.fullmatch(self.candidate_sha256):
            raise RiskMappingError("applicability candidate digest is invalid")
        if not isinstance(self.checker, str) or not self.checker:
            raise RiskMappingError("applicability checker is missing")
        if not isinstance(self.method, str) or not self.method:
            raise RiskMappingError("applicability method is missing")
        if not _REASON_RE.fullmatch(self.reason):
            raise RiskMappingError("applicability reason is invalid")
        if not isinstance(self.rationale, str) or len(self.rationale.strip()) < 20:
            raise RiskMappingError("applicability rationale is not substantive")
        if self.decision_sha256 != _digest(self._payload()):
            raise RiskMappingError("applicability decision digest is inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "gate_version": APPLICABILITY_GATE_VERSION,
            "candidate_id": self.candidate_id,
            "candidate_sha256": self.candidate_sha256,
            "status": self.status.value,
            "checker": self.checker,
            "method": self.method,
            "reason": self.reason,
            "rationale": self.rationale,
        }

    @classmethod
    def for_candidate(
        cls,
        candidate: RiskCandidate,
        *,
        status: ApplicabilityStatus,
        checker: str,
        method: str,
        reason: str,
        rationale: str,
    ) -> "ApplicabilityDecision":
        payload = {
            "gate_version": APPLICABILITY_GATE_VERSION,
            "candidate_id": candidate.candidate_id,
            "candidate_sha256": candidate.candidate_sha256,
            "status": ApplicabilityStatus(status).value,
            "checker": checker,
            "method": method,
            "reason": reason,
            "rationale": rationale,
        }
        return cls(
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.candidate_sha256,
            status=status,
            checker=checker,
            method=method,
            reason=reason,
            rationale=rationale,
            decision_sha256=_digest(payload),
        )


class ApplicabilityChecker(Protocol):
    def assess(
        self,
        candidate: RiskCandidate,
        contexts: tuple[UseContext, ...],
    ) -> ApplicabilityDecision:
        """Assess candidate applicability without rewriting candidate or context."""


@dataclass(frozen=True)
class RiskMappingReport:
    mapping_version: str
    status: MappingStatus
    catalog_sha256: str
    context_sha256: str
    candidates: tuple[RiskCandidate, ...]
    decisions: tuple[ApplicabilityDecision, ...]
    included_risks: tuple[dict[str, Any], ...]
    reason: str
    report_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", MappingStatus(self.status))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(self, "included_risks", tuple(dict(item) for item in self.included_risks))
        if self.mapping_version != RISK_MAPPING_VERSION:
            raise RiskMappingError("risk mapping report version is invalid")
        if not _DIGEST_RE.fullmatch(self.catalog_sha256) or not _DIGEST_RE.fullmatch(
            self.context_sha256
        ):
            raise RiskMappingError("risk mapping report input digest is invalid")
        if not _REASON_RE.fullmatch(self.reason):
            raise RiskMappingError("risk mapping report reason is invalid")
        candidate_ids = [item.candidate_id for item in self.candidates]
        decision_ids = [item.candidate_id for item in self.decisions]
        if candidate_ids != sorted(candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
            raise RiskMappingError("risk mapping candidate order is invalid")
        if decision_ids != candidate_ids:
            raise RiskMappingError("risk mapping decisions do not cover every candidate")
        expected_included = sum(
            item.status is ApplicabilityStatus.ACCEPTED for item in self.decisions
        )
        if len(self.included_risks) != expected_included:
            raise RiskMappingError("risk mapping included-risk count is inconsistent")
        if self.report_sha256 != _digest(self._payload()):
            raise RiskMappingError("risk mapping report digest is inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "mapping_version": self.mapping_version,
            "status": self.status.value,
            "catalog_sha256": self.catalog_sha256,
            "context_sha256": self.context_sha256,
            "candidate_ids": [item.candidate_id for item in self.candidates],
            "candidate_sha256": [item.candidate_sha256 for item in self.candidates],
            "decision_sha256": [item.decision_sha256 for item in self.decisions],
            "included_risks": list(self.included_risks),
            "reason": self.reason,
        }


def map_candidate_risks(
    contexts: Iterable[UseContext],
    catalog: RiskCatalog,
    detector: RiskDetector,
    checker: ApplicabilityChecker,
) -> RiskMappingReport:
    """Run generic Nexus selection and the independent applicability gate."""

    context_values = tuple(sorted(tuple(contexts), key=lambda item: item.context_id))
    if len({item.context_id for item in context_values}) != len(context_values):
        raise RiskMappingError("duplicate use context identifiers")
    context_digest = _digest([item.to_dict() for item in context_values])
    if not context_values:
        return _make_report(
            status=MappingStatus.COMPLETED,
            catalog=catalog,
            context_digest=context_digest,
            candidates=(),
            decisions=(),
            included=(),
            reason="no_grounded_use_context",
        )
    if (
        detector.inference_model != INFERENCE_MODEL
        or detector.detector_name != "ai_atlas_nexus.generic_usecase"
        or detector.detector_version != NEXUS_PACKAGE_VERSION
        or not _DIGEST_RE.fullmatch(detector.inference_config_sha256)
    ):
        raise RiskMappingError("risk detector is not the pinned generic Nexus adapter")
    selections = detector.detect(context_values, catalog)
    if not isinstance(selections, tuple):
        raise RiskMappingError("risk detector output must be an immutable tuple")
    by_context = {item.context_id: item for item in context_values}
    candidates: list[RiskCandidate] = []
    for selection in sorted(selections, key=lambda item: item.risk_id):
        if not isinstance(selection, NexusSelection):
            raise RiskMappingError("risk detector returned a malformed selection")
        try:
            risk = catalog.risk(selection.risk_id)
        except KeyError as exc:
            raise RiskMappingError("risk detector returned an identifier outside the release") from exc
        try:
            selected_contexts = tuple(by_context[item] for item in selection.context_ids)
        except KeyError as exc:
            raise RiskMappingError("risk detector invented a use context") from exc
        candidates.append(RiskCandidate.build(risk, selected_contexts, detector, catalog.release))
    if len({item.risk_id for item in candidates}) != len(candidates):
        raise RiskMappingError("risk detector returned duplicate risk selections")
    candidates_tuple = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    decisions: list[ApplicabilityDecision] = []
    included: list[dict[str, Any]] = []
    for candidate in candidates_tuple:
        selected_contexts = tuple(by_context[item] for item in candidate.context_ids)
        decision = checker.assess(candidate, selected_contexts)
        if not isinstance(decision, ApplicabilityDecision):
            raise RiskMappingError("applicability checker returned a malformed decision")
        if (
            decision.candidate_id != candidate.candidate_id
            or decision.candidate_sha256 != candidate.candidate_sha256
        ):
            raise RiskMappingError("applicability decision is stale or misassigned")
        decisions.append(decision)
        if decision.status is ApplicabilityStatus.ACCEPTED:
            included.append(candidate.public_value(decision, catalog.risk(candidate.risk_id)))
    return _make_report(
        status=MappingStatus.COMPLETED,
        catalog=catalog,
        context_digest=context_digest,
        candidates=candidates_tuple,
        decisions=tuple(decisions),
        included=tuple(included),
        reason="applicability_gate_completed",
    )


def unavailable_risk_report(
    contexts: Iterable[UseContext],
    catalog: RiskCatalog,
    *,
    reason: str = "risk_provider_unavailable",
) -> RiskMappingReport:
    """Record a visible unavailable stage without generating placeholder risks."""

    values = tuple(sorted(tuple(contexts), key=lambda item: item.context_id))
    return _make_report(
        status=MappingStatus.UNAVAILABLE,
        catalog=catalog,
        context_digest=_digest([item.to_dict() for item in values]),
        candidates=(),
        decisions=(),
        included=(),
        reason=reason,
    )


def _make_report(
    *,
    status: MappingStatus,
    catalog: RiskCatalog,
    context_digest: str,
    candidates: tuple[RiskCandidate, ...],
    decisions: tuple[ApplicabilityDecision, ...],
    included: tuple[dict[str, Any], ...],
    reason: str,
) -> RiskMappingReport:
    payload = {
        "mapping_version": RISK_MAPPING_VERSION,
        "status": MappingStatus(status).value,
        "catalog_sha256": catalog.catalog_sha256,
        "context_sha256": context_digest,
        "candidate_ids": [item.candidate_id for item in candidates],
        "candidate_sha256": [item.candidate_sha256 for item in candidates],
        "decision_sha256": [item.decision_sha256 for item in decisions],
        "included_risks": list(included),
        "reason": reason,
    }
    return RiskMappingReport(
        mapping_version=RISK_MAPPING_VERSION,
        status=status,
        catalog_sha256=catalog.catalog_sha256,
        context_sha256=context_digest,
        candidates=candidates,
        decisions=decisions,
        included_risks=included,
        reason=reason,
        report_sha256=_digest(payload),
    )


__all__ = [
    "APPLICABILITY_GATE_VERSION",
    "ApplicabilityDecision",
    "ApplicabilityStatus",
    "INFERENCE_MODEL",
    "MappingStatus",
    "NEXUS_PACKAGE_VERSION",
    "NexusGenericRiskDetector",
    "NexusSelection",
    "RISK_ATLAS_SNAPSHOT_SHA256",
    "RISK_MAPPING_VERSION",
    "RiskCatalog",
    "RiskCandidate",
    "RiskMappingError",
    "RiskMappingReport",
    "TaxonomyRelease",
    "TaxonomyRisk",
    "UseContext",
    "load_pinned_nexus_catalog",
    "map_candidate_risks",
    "unavailable_risk_report",
]
