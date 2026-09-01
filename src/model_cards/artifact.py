"""Immutable artifacts and deterministic projection to the public contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Any

from .bindings import binding_id_for
from .models import (
    Binding,
    Disposition,
    EvidenceKind,
    LifecycleStatus,
    ReviewAction,
    ReviewEvent,
    TaxonomyRiskDerivation,
    TargetIdentity,
    ValidationCheck,
    ValidationCheckStatus,
)
from .policy import decide_binding
from .schema import (
    CONTENT_FIELD_PATHS,
    CONTRACT_VERSION,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    blank_card,
    canonical_field_path,
    get_field,
    parse_field_path,
    set_field,
    validate_public_card,
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def fold_binding(
    target: TargetIdentity,
    binding: Binding,
    events: tuple[ReviewEvent, ...],
) -> Binding:
    """Fold ordered review events over one immutable generated binding."""

    current = binding
    for event in events:
        if event.binding_id != binding.binding_id:
            continue
        if event.action is ReviewAction.WITHHOLD:
            current = replace(current, disposition=Disposition.WITHHELD, reason=event.reason)
        elif event.action is ReviewAction.REASSIGN:
            assert event.field_path is not None
            assert event.relation is not None
            disposition, policy_reason = decide_binding(
                target=target,
                field_path=event.field_path,
                value=event.corrected_value,
                claim_entity=current.claim_entity,
                relation=event.relation,
                origin=current.origin,
                evidence=current.evidence,
            )
            current = replace(
                current,
                field_path=event.field_path,
                value=event.corrected_value,
                relation=event.relation,
                disposition=disposition,
                reason=policy_reason,
            )
        else:
            disposition, policy_reason = decide_binding(
                target=target,
                field_path=current.field_path,
                value=current.value,
                claim_entity=current.claim_entity,
                relation=current.relation,
                origin=current.origin,
                evidence=current.evidence,
            )
            if disposition is not Disposition.ACCEPTED:
                raise ValueError(
                    f"{event.event_id} cannot accept a binding that still fails policy: "
                    f"{policy_reason}"
                )
            current = replace(
                current,
                disposition=Disposition.ACCEPTED,
                reason=event.reason,
            )
    return current


@dataclass(frozen=True)
class CardArtifact:
    """Local evidence artifact whose public projection follows contract version 1."""

    target: TargetIdentity
    bindings: tuple[Binding, ...]
    reviews: tuple[ReviewEvent, ...] = ()
    validation_checks: tuple[ValidationCheck, ...] = ()
    lifecycle_status: LifecycleStatus = LifecycleStatus.GENERATED_UNREVIEWED
    generated_at: str = NOT_SPECIFIED
    validated_at: str = NOT_SPECIFIED
    contract_version: str = CONTRACT_VERSION
    derivations: tuple[TaxonomyRiskDerivation, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "bindings", tuple(self.bindings))
        object.__setattr__(self, "reviews", tuple(self.reviews))
        object.__setattr__(self, "validation_checks", tuple(self.validation_checks))
        object.__setattr__(self, "derivations", tuple(self.derivations))
        try:
            object.__setattr__(self, "lifecycle_status", LifecycleStatus(self.lifecycle_status))
        except (TypeError, ValueError) as exc:
            raise ValueError("artifact lifecycle status is invalid") from exc
        if not isinstance(self.target, TargetIdentity):
            raise ValueError("artifact target must be a TargetIdentity")
        if not all(isinstance(item, Binding) for item in self.bindings):
            raise ValueError("artifact bindings must be Binding records")
        if not all(isinstance(item, ReviewEvent) for item in self.reviews):
            raise ValueError("artifact reviews must be ReviewEvent records")
        if not all(isinstance(item, ValidationCheck) for item in self.validation_checks):
            raise ValueError("artifact validation_checks must be ValidationCheck records")
        if not all(isinstance(item, TaxonomyRiskDerivation) for item in self.derivations):
            raise ValueError("artifact derivations must be taxonomy risk derivation records")
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(f"only contract version {CONTRACT_VERSION} is supported")
        if not isinstance(self.generated_at, str) or not isinstance(self.validated_at, str):
            raise ValueError("artifact lifecycle timestamps must be strings")
        check_ids = [item.check_id for item in self.validation_checks]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("artifact validation check identifiers must be unique")
        if {"binding_policy", "contract_schema"}.intersection(check_ids):
            raise ValueError("computed validation checks cannot be supplied by callers")
        if self.lifecycle_status is LifecycleStatus.GENERATED_VALIDATED:
            by_id = {item.check_id: item for item in self.validation_checks}
            required = {"claim_support", "privacy"}
            if not required.issubset(by_id):
                raise ValueError(
                    "generated_validated requires completed claim_support and privacy checks"
                )
            for check_id in sorted(required):
                check = by_id[check_id]
                if (
                    check.status is not ValidationCheckStatus.COMPLETED
                    or check.failed
                    or check.unavailable
                    or check.passed + check.withheld != check.checked
                ):
                    raise ValueError(
                        f"generated_validated requires a passing {check_id} check"
                    )

        identifiers = [binding.binding_id for binding in self.bindings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("binding identifiers must be unique")
        if [event.sequence for event in self.reviews] != list(range(1, len(self.reviews) + 1)):
            raise ValueError("review events must form one append-only sequence")
        known = set(identifiers)
        if any(event.binding_id not in known for event in self.reviews):
            raise ValueError("review event references an unknown binding")

        source_identities: dict[str, tuple[str, str, str, str]] = {}
        for binding in self.bindings:
            expected_id = binding_id_for(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
                benchmark_scope=binding.benchmark_scope,
            )
            if binding.binding_id != expected_id:
                raise ValueError(f"binding identifier does not match its content: {binding.binding_id}")
            disposition, reason = decide_binding(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
            )
            if (binding.disposition, binding.reason) != (disposition, reason):
                raise ValueError(f"binding policy state is inconsistent: {binding.binding_id}")
            for evidence in binding.evidence:
                identity = (
                    evidence.source_uri,
                    evidence.source_role.value,
                    evidence.source_revision,
                    evidence.source_sha256,
                )
                existing = source_identities.setdefault(evidence.source_id, identity)
                if existing != identity:
                    raise ValueError(f"source identifier has conflicting identity: {evidence.source_id}")
            fold_binding(self.target, binding, self.reviews)
        derivation_ids = [item.derivation_id for item in self.derivations]
        derivation_paths = [item.field_path for item in self.derivations]
        if (
            len(derivation_ids) != len(set(derivation_ids))
            or len(derivation_paths) != len(set(derivation_paths))
            or self.derivations
            != tuple(sorted(self.derivations, key=lambda item: item.field_path))
        ):
            raise ValueError("artifact taxonomy derivations must be sorted and unique")
        binding_paths = {
            item.field_path
            for item in self.bindings
            if fold_binding(self.target, item, self.reviews).disposition
            is Disposition.ACCEPTED
        }
        if binding_paths.intersection(derivation_paths):
            raise ValueError("artifact binding and derivation target the same field path")
        evidence_source_ids = {
            evidence.source_id for binding in self.bindings for evidence in binding.evidence
        }
        for derivation in self.derivations:
            derivation.validate_integrity()
            if derivation.target != self.target:
                raise ValueError("artifact derivation target differs from artifact target")
            if not set(derivation.supporting_source_refs) <= evidence_source_ids:
                raise ValueError("artifact derivation references an unavailable input source")
        for event in self.reviews:
            event.validate_integrity()

        if self.lifecycle_status is LifecycleStatus.GENERATED_VALIDATED:
            claim_support = {
                item.check_id: item for item in self.validation_checks
            }["claim_support"]
            privacy = {
                item.check_id: item for item in self.validation_checks
            }["privacy"]
            included = sum(
                fold_binding(self.target, binding, self.reviews).disposition
                is Disposition.ACCEPTED
                for binding in self.bindings
            )
            if (
                claim_support.checked != included
                or claim_support.passed != included
                or claim_support.withheld
            ):
                raise ValueError(
                    "generated_validated claim_support must pass every included binding"
                )
            if privacy.checked < 1 or privacy.passed < 1:
                raise ValueError("generated_validated requires a non-empty privacy check")
            if self.derivations:
                risk = {
                    item.check_id: item for item in self.validation_checks
                }.get("risk_mapping")
                if (
                    risk is None
                    or risk.status is not ValidationCheckStatus.COMPLETED
                    or risk.failed
                    or risk.unavailable
                    or risk.withheld
                    or risk.passed < len(self.derivations)
                ):
                    raise ValueError(
                        "validated taxonomy derivations require a passing risk_mapping check"
                    )

        # Validate timestamps/status through the exact public schema immediately.
        project_card(self, _skip_integrity=True)

    @property
    def artifact_id(self) -> str:
        payload = {
            "contract_version": self.contract_version,
            "target": self.target.to_dict(),
            "lifecycle": {
                "status": self.lifecycle_status.value,
                "generated_at": self.generated_at,
                "validated_at": self.validated_at,
            },
            "bindings": [binding.to_dict() for binding in self.bindings],
            "reviews": [event.to_dict() for event in self.reviews],
            "validation_checks": [item.to_dict() for item in self.validation_checks],
            "derivations": [item.to_dict() for item in self.derivations],
        }
        return "card_" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:24]

    def binding(self, binding_id: str) -> Binding:
        for binding in self.bindings:
            if binding.binding_id == binding_id:
                return binding
        raise KeyError(f"unknown binding: {binding_id}")

    def effective_bindings(self) -> tuple[Binding, ...]:
        self.validate_integrity()
        return tuple(fold_binding(self.target, binding, self.reviews) for binding in self.bindings)

    def validate_integrity(self) -> None:
        """Detect mutation of nested values before projection or export."""

        identifiers = [binding.binding_id for binding in self.bindings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("binding identifiers must be unique")
        if [event.sequence for event in self.reviews] != list(range(1, len(self.reviews) + 1)):
            raise ValueError("review events must form one append-only sequence")
        known = set(identifiers)
        if any(event.binding_id not in known for event in self.reviews):
            raise ValueError("review event references an unknown binding")
        for binding in self.bindings:
            expected_id = binding_id_for(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
                benchmark_scope=binding.benchmark_scope,
            )
            if binding.binding_id != expected_id:
                raise ValueError(f"binding integrity check failed: {binding.binding_id}")
            disposition, reason = decide_binding(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
            )
            if (binding.disposition, binding.reason) != (disposition, reason):
                raise ValueError(f"binding policy state changed: {binding.binding_id}")
            if binding.origin.value == "structured" and any(
                _canonical(item.fragment) != _canonical(binding.value)
                for item in binding.evidence
            ):
                raise ValueError(f"structured evidence mismatch: {binding.binding_id}")
        for event in self.reviews:
            event.validate_integrity()
        for binding in self.bindings:
            fold_binding(self.target, binding, self.reviews)
        for derivation in self.derivations:
            derivation.validate_integrity()
            if derivation.target != self.target:
                raise ValueError("artifact derivation target integrity failed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "contract_version": self.contract_version,
            "target": self.target.to_dict(),
            "lifecycle": {
                "status": self.lifecycle_status.value,
                "generated_at": self.generated_at,
                "validated_at": self.validated_at,
            },
            "card": project_card(self),
            "bindings": [binding.to_dict() for binding in self.bindings],
            "reviews": [event.to_dict() for event in self.reviews],
            "validation_checks": [item.to_dict() for item in self.validation_checks],
            "derivations": [item.to_dict() for item in self.derivations],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CardArtifact":
        lifecycle = value["lifecycle"]
        artifact = cls(
            contract_version=value["contract_version"],
            target=TargetIdentity.from_dict(value["target"]),
            bindings=tuple(Binding.from_dict(item) for item in value.get("bindings", [])),
            reviews=tuple(ReviewEvent.from_dict(item) for item in value.get("reviews", [])),
            validation_checks=tuple(
                ValidationCheck.from_dict(item) for item in value.get("validation_checks", [])
            ),
            derivations=tuple(
                TaxonomyRiskDerivation.from_dict(item)
                for item in value.get("derivations", [])
            ),
            lifecycle_status=lifecycle["status"],
            generated_at=lifecycle["generated_at"],
            validated_at=lifecycle["validated_at"],
        )
        if value.get("artifact_id") != artifact.artifact_id:
            raise ValueError("serialized artifact_id does not match artifact content")
        if "card" in value:
            validate_public_card(value["card"])
            if value["card"] != project_card(artifact):
                raise ValueError("serialized card does not match its binding projection")
        return artifact


def _field_reference(binding: Binding, evidence: Any) -> dict[str, Any]:
    if evidence.kind is EvidenceKind.QUOTE:
        locator = {
            "kind": "exact_span",
            "start": evidence.char_start,
            "end": evidence.char_end,
        }
    else:
        locator = {"kind": "json_pointer", "pointer": evidence.pointer}
    return {
        "source_id": evidence.source_id,
        "source_uri": evidence.source_uri,
        "source_role": evidence.source_role.value,
        "source_revision": evidence.source_revision,
        "source_sha256": evidence.source_sha256,
        "locator": locator,
        "claimed_entity": binding.claim_entity,
        "relation": binding.relation.value,
    }


def project_card(
    artifact: CardArtifact,
    *,
    _skip_integrity: bool = False,
) -> dict[str, Any]:
    """Project effective bindings and computed summaries to the one public contract."""

    if not _skip_integrity:
        artifact.validate_integrity()
    card = blank_card()
    card["identity"]["model_id"] = artifact.target.model_id
    card["identity"]["revision"] = artifact.target.revision
    effective = tuple(fold_binding(artifact.target, item, artifact.reviews) for item in artifact.bindings)
    accepted: dict[str, list[Binding]] = {}
    flagged: dict[str, list[dict[str, str]]] = {}

    def flag(binding: Binding, reason: str | None = None) -> None:
        flagged.setdefault(binding.field_path, []).append(
            {
                "binding_id": binding.binding_id,
                "disposition": binding.disposition.value,
                "relation": binding.relation.value,
                "reason": reason or binding.reason,
            }
        )

    for binding in effective:
        if binding.disposition is Disposition.ACCEPTED:
            accepted.setdefault(binding.field_path, []).append(binding)
        else:
            flag(binding)

    blocked_bases: set[str] = set()
    shape_by_base: dict[str, set[bool]] = {}
    for field_path in accepted:
        base, indexes = parse_field_path(field_path)
        shape_by_base.setdefault(base, set()).add(bool(indexes))
    for base, shapes in shape_by_base.items():
        if len(shapes) > 1:
            blocked_bases.add(base)
            for field_path, bindings in accepted.items():
                if canonical_field_path(field_path) == base:
                    for binding in bindings:
                        flag(binding, "projection_shape_conflict")

    field_references: dict[str, list[dict[str, Any]]] = {}
    source_manifest: dict[str, dict[str, str]] = {}

    def path_order(item: tuple[str, list[Binding]]) -> tuple[str, tuple[int, ...]]:
        return parse_field_path(item[0])

    for field_path, bindings in sorted(accepted.items(), key=path_order):
        if canonical_field_path(field_path) in blocked_bases:
            continue
        values = {_canonical(binding.value) for binding in bindings}
        if len(values) != 1:
            for binding in bindings:
                flag(binding, "conflicting_accepted_values")
            continue
        try:
            set_field(card, field_path, bindings[0].value)
        except (IndexError, TypeError):
            for binding in bindings:
                flag(binding, "projection_index_conflict")
            continue

        references: dict[str, dict[str, Any]] = {}
        for binding in bindings:
            for evidence in binding.evidence:
                source_manifest[evidence.source_id] = {
                    "source_uri": evidence.source_uri,
                    "source_role": evidence.source_role.value,
                    "source_revision": evidence.source_revision,
                    "source_sha256": evidence.source_sha256,
                }
                reference = _field_reference(binding, evidence)
                references[_canonical(reference)] = reference
        field_references[field_path] = [references[key] for key in sorted(references)]

    derivation_references: dict[str, list[dict[str, Any]]] = {}
    for derivation in artifact.derivations:
        try:
            set_field(card, derivation.field_path, derivation.value)
        except (IndexError, TypeError) as exc:
            raise ValueError(
                f"taxonomy derivation is not contiguously projectable: {derivation.field_path}"
            ) from exc
        derivation_references[derivation.field_path] = [
            derivation.public_reference()
        ]

    missing = [path for path in CONTENT_FIELD_PATHS if get_field(card, path) == NOT_SPECIFIED]
    applicable = [path for path in CONTENT_FIELD_PATHS if get_field(card, path) != NOT_APPLICABLE]
    filled = len(applicable) - len(missing)
    coverage = round(filled / len(applicable), 6) if applicable else 1.0

    counts = {
        disposition.value: sum(item.disposition is disposition for item in effective)
        for disposition in Disposition
    }
    card["provenance"] = {
        "source_manifest": dict(sorted(source_manifest.items())),
        "field_references": field_references,
        "generator": {"name": "evaleval-model-cards"},
    }
    if derivation_references:
        card["provenance"]["derivations"] = derivation_references
    supplied_checks = {
        item.check_id: {
            "status": item.status.value,
            "checked": item.checked,
            "passed": item.passed,
            "withheld": item.withheld,
            "failed": item.failed,
            "unavailable": item.unavailable,
        }
        for item in artifact.validation_checks
    }
    card["validation"] = {
        "overall_status": (
            "passed"
            if artifact.lifecycle_status is LifecycleStatus.GENERATED_VALIDATED
            else "partial"
        ),
        "checks": {
            **supplied_checks,
            "binding_policy": {
                "status": "completed",
                "checked": len(effective),
                "passed": counts["accepted"],
                "withheld": counts["withheld"],
                "failed": counts["rejected"],
            },
            "contract_schema": {"status": "completed", "checked": 1, "passed": 1},
        },
        "flagged_fields": flagged,
        "missing_fields": missing,
        "coverage_score": coverage,
    }
    card["lifecycle"] = {
        "status": artifact.lifecycle_status.value,
        "generated_at": artifact.generated_at,
        "validated_at": artifact.validated_at,
    }
    validate_public_card(card)
    return card
