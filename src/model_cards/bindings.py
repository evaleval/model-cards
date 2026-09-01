"""Deterministic construction of evidence bindings from typed source inputs."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

from .models import (
    Binding,
    BindingOrigin,
    Evidence,
    EvidenceKind,
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from .policy import decide_binding
from .quote import match_quote, normalize_ws


_ARRAY_INDEX_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve a non-root RFC 6901 JSON Pointer against an in-memory document."""

    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("pointer must be a non-root JSON Pointer")
    value = document
    for encoded in pointer[1:].split("/"):
        if re.search(r"~(?![01])", encoded):
            raise ValueError(f"invalid JSON Pointer escape: {encoded}")
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not _ARRAY_INDEX_RE.fullmatch(token):
                raise ValueError(f"list pointer token is not a canonical index: {token}")
            index = int(token)
            value = value[index]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ValueError(f"pointer continues through a scalar at {token}")
    return value


def binding_id_for(
    *,
    target: TargetIdentity,
    field_path: str,
    value: Any,
    claim_entity: str,
    relation: RelationToTarget,
    origin: BindingOrigin,
    evidence: tuple[Evidence, ...],
    benchmark_scope: dict[str, Any] | None,
) -> str:
    payload = {
        "target": target.to_dict(),
        "field_path": field_path,
        "value": value,
        "claim_entity": claim_entity,
        "relation": relation.value,
        "origin": origin.value,
        "evidence": [item.to_dict() for item in evidence],
        "benchmark_scope": benchmark_scope,
    }
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "binding-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _finish_binding(
    *,
    target: TargetIdentity,
    field_path: str,
    value: Any,
    claim_entity: str,
    relation: RelationToTarget | str,
    origin: BindingOrigin,
    evidence: tuple[Evidence, ...],
    benchmark_scope: dict[str, Any] | None = None,
) -> Binding:
    relation = RelationToTarget(relation)
    disposition, reason = decide_binding(
        target=target,
        field_path=field_path,
        value=value,
        claim_entity=claim_entity,
        relation=relation,
        origin=origin,
        evidence=evidence,
    )
    return Binding(
        binding_id=binding_id_for(
            target=target,
            field_path=field_path,
            value=value,
            claim_entity=claim_entity,
            relation=relation,
            origin=origin,
            evidence=evidence,
            benchmark_scope=benchmark_scope,
        ),
        field_path=field_path,
        value=value,
        claim_entity=claim_entity,
        relation=relation,
        origin=origin,
        evidence=evidence,
        disposition=disposition,
        reason=reason,
        benchmark_scope=benchmark_scope,
    )


def quote_binding(
    *,
    target: TargetIdentity,
    source: SourceDocument,
    field_path: str,
    value: Any,
    quote: str,
    claim_entity: str,
    relation: RelationToTarget | str,
    benchmark_scope: dict[str, Any] | None = None,
) -> Binding:
    """Create a visible accepted, withheld, or rejected quoted binding."""

    if source.text is None:
        raise ValueError("quote candidates require a text source")
    normalized_quote = normalize_ws(quote)
    if not normalized_quote:
        raise ValueError("quote candidates must be non-empty")
    match = match_quote(quote, source.text)
    evidence = Evidence(
        kind=EvidenceKind.QUOTE,
        source_id=source.source_id,
        source_role=source.role,
        source_revision=source.source_revision,
        source_sha256=source.sha256,
        source_target=source.target,
        synthetic=source.synthetic,
        verified=match is not None,
        quote=match.quote if match else normalized_quote,
        char_start=match.char_start if match else None,
        char_end=match.char_end if match else None,
    )
    return _finish_binding(
        target=target,
        field_path=field_path,
        value=value,
        claim_entity=claim_entity,
        relation=relation,
        origin=BindingOrigin.QUOTED,
        evidence=(evidence,),
        benchmark_scope=benchmark_scope,
    )


def structured_binding(
    *,
    target: TargetIdentity,
    source: SourceDocument,
    field_path: str,
    pointer: str,
    claim_entity: str,
    relation: RelationToTarget | str,
    benchmark_scope: dict[str, Any] | None = None,
) -> Binding:
    """Create a binding whose value is replayed from a structured pointer."""

    if source.data is None:
        raise ValueError("structured candidates require a structured source")
    fragment = resolve_json_pointer(source.data, pointer)
    evidence = Evidence(
        kind=EvidenceKind.STRUCTURED,
        source_id=source.source_id,
        source_role=source.role,
        source_revision=source.source_revision,
        source_sha256=source.sha256,
        source_target=source.target,
        synthetic=source.synthetic,
        verified=True,
        pointer=pointer,
        fragment=fragment,
    )
    return _finish_binding(
        target=target,
        field_path=field_path,
        value=fragment,
        claim_entity=claim_entity,
        relation=relation,
        origin=BindingOrigin.STRUCTURED,
        evidence=(evidence,),
        benchmark_scope=benchmark_scope,
    )


def source_from_dict(value: dict[str, Any]) -> SourceDocument:
    target = value.get("target")
    return SourceDocument(
        source_id=value["source_id"],
        role=SourceRole(value["role"]),
        source_revision=value["source_revision"],
        target=TargetIdentity.from_dict(target) if target else None,
        text=value.get("text"),
        data=value.get("data"),
        synthetic=value.get("synthetic", False),
    )


def build_artifact(specification: dict[str, Any]):
    """Build an artifact from a compact offline JSON-compatible specification."""

    from .artifact import CardArtifact

    target = TargetIdentity.from_dict(specification["target"])
    sources: dict[str, SourceDocument] = {}
    for source_value in specification.get("sources", []):
        source = source_from_dict(source_value)
        if source.source_id in sources:
            raise ValueError(f"duplicate source_id: {source.source_id}")
        sources[source.source_id] = source

    bindings: list[Binding] = []
    for candidate in specification.get("candidates", []):
        source_id = candidate["source_id"]
        if source_id not in sources:
            raise ValueError(f"candidate references unknown source: {source_id}")
        common = {
            "target": target,
            "source": sources[source_id],
            "field_path": candidate["field_path"],
            "claim_entity": candidate["claim_entity"],
            "relation": candidate["relation"],
            "benchmark_scope": candidate.get("benchmark_scope"),
        }
        kind = candidate["kind"]
        if kind == "quote":
            binding = quote_binding(
                **common,
                value=candidate["value"],
                quote=candidate["quote"],
            )
        elif kind == "structured":
            binding = structured_binding(**common, pointer=candidate["pointer"])
        else:
            raise ValueError(f"unknown candidate kind: {kind}")
        bindings.append(binding)

    artifact = CardArtifact(target=target, bindings=tuple(bindings))
    verify_artifact_sources(artifact, sources.values())
    return artifact


def verify_artifact_sources(artifact, sources: Iterable[SourceDocument]) -> None:
    """Replay every evidence coordinate against separately supplied source content."""

    artifact.validate_integrity()
    by_id: dict[str, SourceDocument] = {}
    for source in sources:
        if source.source_id in by_id:
            raise ValueError(f"duplicate source_id during replay: {source.source_id}")
        by_id[source.source_id] = source

    def canonical(value: Any) -> str:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    for binding in artifact.bindings:
        for evidence in binding.evidence:
            source = by_id.get(evidence.source_id)
            if source is None:
                raise ValueError(f"missing replay source: {evidence.source_id}")
            if (
                source.role is not evidence.source_role
                or source.source_revision != evidence.source_revision
                or source.target != evidence.source_target
                or source.synthetic != evidence.synthetic
                or source.sha256 != evidence.source_sha256
            ):
                raise ValueError(f"replay source identity mismatch: {evidence.source_id}")
            if evidence.kind is EvidenceKind.QUOTE:
                if source.text is None:
                    raise ValueError(f"quote replay requires text: {evidence.source_id}")
                match = match_quote(evidence.quote or "", source.text)
                if evidence.verified:
                    if (
                        match is None
                        or match.char_start != evidence.char_start
                        or match.char_end != evidence.char_end
                    ):
                        raise ValueError(f"quote replay failed: {binding.binding_id}")
                elif match is not None:
                    raise ValueError(f"unverified quote now matches: {binding.binding_id}")
            else:
                if source.data is None:
                    raise ValueError(f"structured replay requires data: {evidence.source_id}")
                fragment = resolve_json_pointer(source.data, evidence.pointer or "")
                if canonical(fragment) != canonical(evidence.fragment):
                    raise ValueError(f"structured replay failed: {binding.binding_id}")


def all_source_roles() -> Iterable[str]:
    """Expose the supported role vocabulary for CLI inspection."""

    return (role.value for role in SourceRole)
