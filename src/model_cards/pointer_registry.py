"""Closed structured pointer-to-field registry for Claim Support Gate v1.

Pointer presence and source role are not evidence that a structured value fits a
Model Card field.  This module names the small, versioned set of pointer,
source-role, and fragment-shape combinations that the public gate understands.
Anything outside the set is withheld until the registry is deliberately
versioned and extended.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable

from .models import SourceRole
from .schema import canonical_field_path


POINTER_REGISTRY_NAME = "model-cards-structured-pointer-field-registry"
POINTER_REGISTRY_VERSION = "v1"

_POINTER_RE = re.compile(r"^/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class FragmentShape(str, Enum):
    """Closed fragment shapes used to disambiguate reused JSON pointers."""

    STRING = "string"
    NUMBER = "number"
    OBJECT = "object"
    ARRAY = "array"
    BOOLEAN = "boolean"


@dataclass(frozen=True)
class PointerFieldRule:
    """One immutable pointer, role, shape, and destination field rule."""

    source_role: SourceRole
    pointer: str
    field_path: str
    fragment_shape: FragmentShape
    required_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_role", SourceRole(self.source_role))
        object.__setattr__(self, "fragment_shape", FragmentShape(self.fragment_shape))
        if not isinstance(self.pointer, str) or not _POINTER_RE.fullmatch(self.pointer):
            raise ValueError("registry pointer must be a canonical non-root JSON Pointer")
        object.__setattr__(self, "field_path", canonical_field_path(self.field_path))
        keys = tuple(self.required_keys)
        if len(keys) != len(set(keys)) or any(
            not isinstance(item, str) or not _TOKEN_RE.fullmatch(item) for item in keys
        ):
            raise ValueError("registry required_keys must be unique stable identifiers")
        if keys and self.fragment_shape is not FragmentShape.OBJECT:
            raise ValueError("only object-shaped registry rules may require keys")
        object.__setattr__(self, "required_keys", tuple(sorted(keys)))

    def matches_fragment(self, fragment: Any) -> bool:
        if self.fragment_shape is FragmentShape.STRING:
            return isinstance(fragment, str) and bool(fragment)
        if self.fragment_shape is FragmentShape.NUMBER:
            return isinstance(fragment, (int, float)) and not isinstance(fragment, bool)
        if self.fragment_shape is FragmentShape.OBJECT:
            return isinstance(fragment, dict) and set(self.required_keys) <= set(fragment)
        if self.fragment_shape is FragmentShape.ARRAY:
            return isinstance(fragment, list)
        return isinstance(fragment, bool)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_role": self.source_role.value,
            "pointer": self.pointer,
            "field_path": self.field_path,
            "fragment_shape": self.fragment_shape.value,
            "required_keys": list(self.required_keys),
        }


class PointerLookupStatus(str, Enum):
    MATCHED = "matched"
    UNREGISTERED = "unregistered"
    WRONG_FIELD = "wrong_field"
    SHAPE_MISMATCH = "shape_mismatch"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class PointerLookup:
    status: PointerLookupStatus
    matched_rule: PointerFieldRule | None = None


@dataclass(frozen=True)
class PointerFieldRegistry:
    """Named immutable closed registry with deterministic content digest."""

    name: str
    version: str
    rules: tuple[PointerFieldRule, ...]

    def __post_init__(self) -> None:
        if self.name != POINTER_REGISTRY_NAME:
            raise ValueError("pointer registry name is not recognized")
        if self.version != POINTER_REGISTRY_VERSION:
            raise ValueError("pointer registry version is not recognized")
        rules = tuple(self.rules)
        if not rules:
            raise ValueError("pointer registry cannot be empty")
        if not all(isinstance(item, PointerFieldRule) for item in rules):
            raise ValueError("pointer registry contains a malformed rule")
        canonical = tuple(
            sorted(
                rules,
                key=lambda item: (
                    item.source_role.value,
                    item.pointer,
                    item.field_path,
                    item.fragment_shape.value,
                    item.required_keys,
                ),
            )
        )
        if len({json.dumps(item.to_dict(), sort_keys=True) for item in canonical}) != len(
            canonical
        ):
            raise ValueError("pointer registry contains a duplicate rule")
        object.__setattr__(self, "rules", canonical)

    @property
    def sha256(self) -> str:
        payload = {
            "name": self.name,
            "version": self.version,
            "rules": [item.to_dict() for item in self.rules],
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def lookup(
        self,
        *,
        source_role: SourceRole,
        pointer: str,
        field_path: str,
        fragment: Any,
    ) -> PointerLookup:
        """Classify a structured candidate without guessing or fallback."""

        role = SourceRole(source_role)
        field = canonical_field_path(field_path)
        same_pointer = tuple(
            rule
            for rule in self.rules
            if rule.source_role is role and rule.pointer == pointer
        )
        if not same_pointer:
            return PointerLookup(PointerLookupStatus.UNREGISTERED)
        shaped = tuple(rule for rule in same_pointer if rule.matches_fragment(fragment))
        if not shaped:
            return PointerLookup(PointerLookupStatus.SHAPE_MISMATCH)
        fitting = tuple(rule for rule in shaped if rule.field_path == field)
        if not fitting:
            return PointerLookup(PointerLookupStatus.WRONG_FIELD)
        if len(fitting) != 1:
            return PointerLookup(PointerLookupStatus.AMBIGUOUS)
        return PointerLookup(PointerLookupStatus.MATCHED, fitting[0])


def _rule(
    role: SourceRole,
    pointer: str,
    field_path: str,
    shape: FragmentShape = FragmentShape.STRING,
    required_keys: Iterable[str] = (),
) -> PointerFieldRule:
    return PointerFieldRule(
        source_role=role,
        pointer=pointer,
        field_path=field_path,
        fragment_shape=shape,
        required_keys=tuple(required_keys),
    )


_HF = SourceRole.HUGGING_FACE_METADATA
_HF_SNAPSHOT = SourceRole.HUGGING_FACE_SNAPSHOT
_EEE = SourceRole.EEE_INDEX

DEFAULT_POINTER_FIELD_REGISTRY = PointerFieldRegistry(
    name=POINTER_REGISTRY_NAME,
    version=POINTER_REGISTRY_VERSION,
    rules=(
        _rule(_HF, "/model_id", "identity.model_id"),
        _rule(_HF, "/id", "identity.model_id"),
        _rule(_HF, "/revision", "identity.revision"),
        _rule(_HF, "/sha", "identity.revision"),
        _rule(_HF, "/display_name", "identity.name"),
        _rule(_HF, "/name", "identity.name"),
        _rule(_HF, "/author", "identity.developed_by"),
        _rule(_HF, "/pipeline_tag", "identity.model_type"),
        _rule(_HF, "/license", "identity.license"),
        _rule(_HF, "/created_at", "identity.release_date"),
        _rule(
            _HF,
            "/base_model",
            "lineage.base_models",
            FragmentShape.OBJECT,
            ("model_id", "relation"),
        ),
        _rule(_HF, "/model_family", "lineage.model_family"),
        _rule(_HF, "/config/architecture_type", "model_details.architecture_type"),
        _rule(_HF, "/config/model_type", "model_details.architecture_type"),
        _rule(_HF, "/config/num_parameters", "model_details.num_parameters"),
        _rule(
            _HF,
            "/config/advertised_context_length",
            "model_details.context_length",
        ),
        _rule(_HF, "/config/torch_dtype", "model_details.precision"),
        _rule(_HF, "/model_card", "model_details.model_card"),
        _rule(_HF, "/system_card", "model_details.system_card"),
        _rule(_HF, "/technical_report", "model_details.technical_report"),
        _rule(_HF, "/code_repository", "model_details.code_repository"),
        # Direct config.json objects are replayed as snapshot sources.  These
        # two string-valued declarations are semantically direct.  Numeric
        # max_position_embeddings is deliberately not registered as a text
        # context-length claim: that conversion needs an explicit new
        # candidate and additional architectural qualification.
        _rule(_HF_SNAPSHOT, "/model_type", "model_details.architecture_type"),
        _rule(_HF_SNAPSHOT, "/torch_dtype", "model_details.precision"),
        _rule(
            _EEE,
            "/record",
            "evaluation.evaluation_sources",
            FragmentShape.STRING,
        ),
        _rule(
            _EEE,
            "/record",
            "evaluation.related_model_scores",
            FragmentShape.OBJECT,
            ("link", "model_id"),
        ),
    ),
)


__all__ = [
    "DEFAULT_POINTER_FIELD_REGISTRY",
    "FragmentShape",
    "POINTER_REGISTRY_NAME",
    "POINTER_REGISTRY_VERSION",
    "PointerFieldRegistry",
    "PointerFieldRule",
    "PointerLookup",
    "PointerLookupStatus",
]
