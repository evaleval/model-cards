"""Closed exact-target derivation of model-family membership from config data.

``config.json:model_type`` is primarily an implementation discriminator.  It
is not, by itself, evidence that an arbitrary repository belongs to the named
publisher family.  This module permits that projection only for a small,
versioned registry that binds an exact publisher model-id pattern, an exact
``model_type`` value, and the resulting family identifier.  For gated
repositories, the same discriminator may be read from the revision-pinned
Hugging Face model-metadata response, but only when that response embeds the
exact target repository and commit.

Unknown publishers, derivative namespaces, aliases, and newly introduced
model names abstain until the registry is deliberately reviewed and versioned.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
import hashlib
import json
import re
from typing import Any, Iterable
from urllib.parse import urlsplit

from .models import Evidence, EvidenceKind, SourceDocument, SourceRole, TargetIdentity


CONFIG_MODEL_FAMILY_REGISTRY_VERSION = "config-model-family-registry/v2"

CONFIG_MODEL_FAMILY_EVIDENCE_POINTERS = frozenset(
    {"/model_type", "/config/model_type"}
)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_RULE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_FAMILY_ID_RE = re.compile(r"^[a-z][a-z0-9._-]{1,127}$")
_MODEL_TYPE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,127}$")


class ModelFamilyDerivationError(ValueError):
    """A config-family derivation is malformed, ambiguous, or stale."""


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
        raise ModelFamilyDerivationError(
            "model-family derivation values must be finite JSON"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConfigModelFamilyRule:
    rule_id: str
    model_id_pattern: str
    config_model_type: str
    family_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, str) or not _RULE_ID_RE.fullmatch(
            self.rule_id
        ):
            raise ModelFamilyDerivationError("model-family rule id is invalid")
        if (
            not isinstance(self.model_id_pattern, str)
            or not self.model_id_pattern
        ):
            raise ModelFamilyDerivationError(
                "model-family target pattern is invalid"
            )
        try:
            re.compile(self.model_id_pattern)
        except re.error as exc:
            raise ModelFamilyDerivationError(
                "model-family target pattern is invalid"
            ) from exc
        if not isinstance(self.config_model_type, str) or not _MODEL_TYPE_RE.fullmatch(
            self.config_model_type
        ):
            raise ModelFamilyDerivationError(
                "model-family config model_type is invalid"
            )
        if not isinstance(self.family_id, str) or not _FAMILY_ID_RE.fullmatch(
            self.family_id
        ):
            raise ModelFamilyDerivationError("model-family identifier is invalid")

    def matches(self, target: TargetIdentity, config_model_type: str) -> bool:
        return (
            config_model_type == self.config_model_type
            and re.fullmatch(self.model_id_pattern, target.model_id) is not None
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "model_id_pattern": self.model_id_pattern,
            "config_model_type": self.config_model_type,
            "family_id": self.family_id,
        }


# These rules intentionally cover only publisher-owned releases whose naming
# and config discriminator were inspected for the current cohort.  The model-id
# constraint is as important as the model_type constraint: an unrelated or
# derivative repository that merely reuses (for example) ``llama`` abstains.
CONFIG_MODEL_FAMILY_RULES = (
    ConfigModelFamilyRule(
        "deepseek_v3",
        r"deepseek-ai/DeepSeek-V3(?:-Base)?",
        "deepseek_v3",
        "deepseek_v3",
    ),
    ConfigModelFamilyRule(
        "gemma3",
        r"google/gemma-3-(?:1b|4b|12b|27b)-(?:pt|it)",
        "gemma3",
        "gemma3",
    ),
    ConfigModelFamilyRule(
        "llama31",
        r"meta-llama/Llama-3\.1-(?:8B|70B|405B)(?:-Instruct)?",
        "llama",
        "llama",
    ),
    ConfigModelFamilyRule(
        "mistral_7b_v03",
        r"mistralai/Mistral-7B-(?:Instruct-)?v0\.3",
        "mistral",
        "mistral",
    ),
    ConfigModelFamilyRule(
        "olmo2_1124",
        r"allenai/OLMo-2-1124-(?:7B|13B)(?:-(?:Instruct|SFT|DPO|RM))?",
        "olmo2",
        "olmo2",
    ),
    ConfigModelFamilyRule(
        "qwen3",
        r"Qwen/Qwen3-(?:0\.6B|1\.7B|4B|8B|14B|32B|30B-A3B|235B-A22B)"
        r"(?:-Base)?",
        "qwen3",
        "qwen3",
    ),
)


def _registry_payload() -> dict[str, Any]:
    return {
        "registry_version": CONFIG_MODEL_FAMILY_REGISTRY_VERSION,
        "rules": [item.to_dict() for item in CONFIG_MODEL_FAMILY_RULES],
    }


CONFIG_MODEL_FAMILY_REGISTRY_SHA256 = _digest(_registry_payload())


@dataclass(frozen=True)
class ConfigModelFamilyDerivation:
    target: TargetIdentity
    source_id: str
    source_uri: str
    source_revision: str
    source_sha256: str
    pointer: str
    config_model_type: str
    family_id: str
    rule_id: str
    registry_version: str = CONFIG_MODEL_FAMILY_REGISTRY_VERSION
    registry_sha256: str = CONFIG_MODEL_FAMILY_REGISTRY_SHA256
    derivation_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.target, TargetIdentity):
            raise ModelFamilyDerivationError(
                "model-family derivation target is invalid"
            )
        if (
            not isinstance(self.source_id, str)
            or not self.source_id
            or len(self.source_id) > 128
        ):
            raise ModelFamilyDerivationError(
                "model-family derivation source id is invalid"
            )
        if not isinstance(self.source_uri, str) or not self.source_uri.startswith(
            "https://"
        ):
            raise ModelFamilyDerivationError(
                "model-family derivation source URI is invalid"
            )
        if self.source_revision != self.target.revision:
            raise ModelFamilyDerivationError(
                "model-family derivation is not revision-bound"
            )
        if not isinstance(self.source_sha256, str) or not _DIGEST_RE.fullmatch(
            self.source_sha256
        ):
            raise ModelFamilyDerivationError(
                "model-family derivation source digest is invalid"
            )
        if self.pointer not in CONFIG_MODEL_FAMILY_EVIDENCE_POINTERS:
            raise ModelFamilyDerivationError(
                "model-family derivation pointer is invalid"
            )
        if self.pointer == "/model_type" and not _exact_config_uri(
            self.target, self.source_uri
        ):
            raise ModelFamilyDerivationError(
                "config model-family derivation source URI is not exact"
            )
        if self.pointer == "/config/model_type" and not _exact_metadata_uri(
            self.target, self.source_uri
        ):
            raise ModelFamilyDerivationError(
                "metadata model-family derivation source URI is not exact"
            )
        if (
            self.registry_version != CONFIG_MODEL_FAMILY_REGISTRY_VERSION
            or self.registry_sha256 != CONFIG_MODEL_FAMILY_REGISTRY_SHA256
        ):
            raise ModelFamilyDerivationError(
                "model-family derivation registry is stale"
            )
        matches = tuple(
            rule
            for rule in CONFIG_MODEL_FAMILY_RULES
            if rule.matches(self.target, self.config_model_type)
        )
        if len(matches) != 1:
            raise ModelFamilyDerivationError(
                "model-family derivation is not uniquely allowlisted"
            )
        rule = matches[0]
        if rule.rule_id != self.rule_id or rule.family_id != self.family_id:
            raise ModelFamilyDerivationError(
                "model-family derivation differs from its allowlist rule"
            )
        object.__setattr__(self, "derivation_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "registry_version": self.registry_version,
            "registry_sha256": self.registry_sha256,
            "target": self.target.to_dict(),
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "pointer": self.pointer,
            "config_model_type": self.config_model_type,
            "family_id": self.family_id,
            "rule_id": self.rule_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "derivation_sha256": self.derivation_sha256}


def _exact_config_uri(target: TargetIdentity, source_uri: str) -> bool:
    parsed = urlsplit(source_uri)
    return (
        parsed.scheme == "https"
        and parsed.netloc.casefold() == "huggingface.co"
        and parsed.path
        == f"/{target.model_id}/resolve/{target.revision}/config.json"
        and not parsed.query
        and not parsed.fragment
    )


def _exact_metadata_uri(target: TargetIdentity, source_uri: str) -> bool:
    parsed = urlsplit(source_uri)
    return (
        parsed.scheme == "https"
        and parsed.netloc.casefold() == "huggingface.co"
        and parsed.path
        == f"/api/models/{target.model_id}/revision/{target.revision}"
        and not parsed.query
        and not parsed.fragment
    )


def _metadata_matches_target(target: TargetIdentity, data: dict[str, Any]) -> bool:
    identifiers = tuple(
        data[key] for key in ("id", "modelId") if key in data
    )
    return (
        bool(identifiers)
        and all(value == target.model_id for value in identifiers)
        and data.get("sha") == target.revision
    )


def derive_config_model_family_from_evidence(
    target: TargetIdentity,
    evidence: Evidence,
) -> ConfigModelFamilyDerivation | None:
    """Return one typed derivation or abstain for an unregistered target."""

    if not isinstance(target, TargetIdentity) or not isinstance(evidence, Evidence):
        raise ModelFamilyDerivationError(
            "model-family derivation requires typed target and evidence"
        )
    config_evidence = (
        evidence.source_role is SourceRole.HUGGING_FACE_SNAPSHOT
        and evidence.pointer == "/model_type"
        and _exact_config_uri(target, evidence.source_uri)
    )
    metadata_evidence = (
        evidence.source_role is SourceRole.HUGGING_FACE_METADATA
        and evidence.pointer == "/config/model_type"
        and _exact_metadata_uri(target, evidence.source_uri)
    )
    if (
        evidence.kind is not EvidenceKind.STRUCTURED
        or evidence.source_target != target
        or evidence.source_revision != target.revision
        or evidence.synthetic
        or not evidence.verified
        or not (config_evidence or metadata_evidence)
        or not isinstance(evidence.fragment, str)
    ):
        return None
    matches = tuple(
        rule
        for rule in CONFIG_MODEL_FAMILY_RULES
        if rule.matches(target, evidence.fragment)
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise ModelFamilyDerivationError(
            "model-family registry matches the target ambiguously"
        )
    rule = matches[0]
    return ConfigModelFamilyDerivation(
        target=target,
        source_id=evidence.source_id,
        source_uri=evidence.source_uri,
        source_revision=evidence.source_revision,
        source_sha256=evidence.source_sha256,
        pointer=evidence.pointer,
        config_model_type=evidence.fragment,
        family_id=rule.family_id,
        rule_id=rule.rule_id,
    )


def replay_config_model_family_from_evidence(
    target: TargetIdentity,
    evidence: Evidence,
    source: SourceDocument,
) -> ConfigModelFamilyDerivation | None:
    """Replay one evidence-only derivation against its complete source payload.

    A revision-pinned Hugging Face metadata URI is not sufficient evidence by
    itself: the response body must also identify the exact repository and commit.
    ``Evidence`` intentionally retains only the selected JSON fragment, so claim
    gate replay must join it back to the immutable ``SourceDocument`` before a
    metadata-derived family claim can be accepted.
    """

    if (
        not isinstance(target, TargetIdentity)
        or not isinstance(evidence, Evidence)
        or not isinstance(source, SourceDocument)
    ):
        raise ModelFamilyDerivationError(
            "model-family replay requires typed target, evidence, and source"
        )
    if (
        source.source_id != evidence.source_id
        or source.source_uri != evidence.source_uri
        or source.role is not evidence.source_role
        or source.source_revision != evidence.source_revision
        or source.target != evidence.source_target
        or source.sha256 != evidence.source_sha256
        or source.target != target
    ):
        raise ModelFamilyDerivationError(
            "model-family evidence differs from its retained source"
        )
    derivation = derive_config_model_family(target, source)
    if derivation is None:
        return None
    if (
        derivation.source_id != evidence.source_id
        or derivation.source_uri != evidence.source_uri
        or derivation.source_revision != evidence.source_revision
        or derivation.source_sha256 != evidence.source_sha256
        or derivation.pointer != evidence.pointer
        or derivation.config_model_type != evidence.fragment
    ):
        raise ModelFamilyDerivationError(
            "model-family evidence fragment does not replay from its source"
        )
    return derivation


def derive_config_model_family(
    target: TargetIdentity,
    source: SourceDocument,
) -> ConfigModelFamilyDerivation | None:
    """Derive membership from one verified exact config source, or abstain."""

    if not isinstance(target, TargetIdentity) or not isinstance(
        source, SourceDocument
    ):
        raise ModelFamilyDerivationError(
            "model-family derivation requires typed target and source"
        )
    if (
        source.target != target
        or source.source_revision != target.revision
        or source.synthetic
        or not isinstance(source.data, dict)
    ):
        return None
    if (
        source.role is SourceRole.HUGGING_FACE_SNAPSHOT
        and _exact_config_uri(target, source.source_uri)
    ):
        pointer = "/model_type"
        model_type = source.data.get("model_type")
    elif (
        source.role is SourceRole.HUGGING_FACE_METADATA
        and _exact_metadata_uri(target, source.source_uri)
        and _metadata_matches_target(target, source.data)
        and isinstance(source.data.get("config"), dict)
    ):
        pointer = "/config/model_type"
        model_type = source.data["config"].get("model_type")
    else:
        return None
    if not isinstance(model_type, str):
        return None
    matches = tuple(
        rule for rule in CONFIG_MODEL_FAMILY_RULES if rule.matches(target, model_type)
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise ModelFamilyDerivationError(
            "model-family registry matches the target ambiguously"
        )
    rule = matches[0]
    return ConfigModelFamilyDerivation(
        target=target,
        source_id=source.source_id,
        source_uri=source.source_uri,
        source_revision=source.source_revision,
        source_sha256=source.sha256,
        pointer=pointer,
        config_model_type=model_type,
        family_id=rule.family_id,
        rule_id=rule.rule_id,
    )


def select_config_model_family_derivation(
    target: TargetIdentity,
    sources: Iterable[SourceDocument],
) -> tuple[SourceDocument, ConfigModelFamilyDerivation] | None:
    """Select one exact family source, preferring a direct config document.

    A revision-pinned metadata document is used only when no direct
    ``config.json`` derivation is available.  Multiple sources at the selected
    authority tier fail closed instead of being resolved by iteration order.
    """

    if not isinstance(target, TargetIdentity):
        raise ModelFamilyDerivationError(
            "model-family selection requires a typed target"
        )
    matches: list[tuple[SourceDocument, ConfigModelFamilyDerivation]] = []
    for source in tuple(sources):
        if not isinstance(source, SourceDocument):
            raise ModelFamilyDerivationError(
                "model-family selection sources are malformed"
            )
        derivation = derive_config_model_family(target, source)
        if derivation is not None:
            matches.append((source, derivation))
    if not matches:
        return None
    family_ids = {derivation.family_id for _source, derivation in matches}
    if len(family_ids) != 1:
        raise ModelFamilyDerivationError(
            "model-family sources disagree on family membership"
        )
    direct = tuple(
        item for item in matches if item[1].pointer == "/model_type"
    )
    selected = direct or tuple(
        item for item in matches if item[1].pointer == "/config/model_type"
    )
    if len(selected) != 1:
        raise ModelFamilyDerivationError(
            "model-family source authority is ambiguous"
        )
    return selected[0]


__all__ = [
    "CONFIG_MODEL_FAMILY_REGISTRY_SHA256",
    "CONFIG_MODEL_FAMILY_REGISTRY_VERSION",
    "CONFIG_MODEL_FAMILY_RULES",
    "CONFIG_MODEL_FAMILY_EVIDENCE_POINTERS",
    "ConfigModelFamilyDerivation",
    "ConfigModelFamilyRule",
    "ModelFamilyDerivationError",
    "derive_config_model_family",
    "derive_config_model_family_from_evidence",
    "replay_config_model_family_from_evidence",
    "select_config_model_family_derivation",
]
