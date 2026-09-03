"""Conservative discovery of publisher-declared official-source candidates.

Discovery operates only on a verified, replayed source bundle.  It does not
fetch candidates and therefore never turns a link (including an apparently
official link) into evidence.  Publisher declarations, secondary hints,
rejections, and unavailable classes remain explicit immutable records.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Sequence
from urllib.parse import (
    parse_qsl,
    quote,
    unquote,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

from .source_bundle import (
    BundleIntegrityError,
    CollectionStatus,
    ReplayedSource,
    ReplayedSourceBundle,
    SourceKind,
    TargetIdentity,
)


DISCOVERY_VERSION = "official-source-discovery/v1"
POLICY_VERSION = "official-source-policy/v1"
DEFAULT_MAX_CANDIDATES = 32
MAX_SCAN_LINKS = 256

_BUNDLE_ID_RE = re.compile(r"^hf_bundle_[0-9a-f]{32}$")
_DISCOVERY_ID_RE = re.compile(r"^official_discovery_[0-9a-f]{32}$")
_RECORD_ID_RE = re.compile(r"^official_source_[0-9a-f]{24}$")
_SOURCE_ID_RE = re.compile(r"^src_[0-9a-f]{24}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_ARXIV_ID_RE = re.compile(r"^(?:arxiv:)?([0-9]{4}\.[0-9]{4,5})(?:v[0-9]+)?$", re.I)
_MARKDOWN_LINK_RE = re.compile(
    r"\[([^\]\n]{1,160})\]\(\s*([^\s)]+)(?:\s+['\"][^'\"]*['\"])?\s*\)"
)
_HTML_LINK_RE = re.compile(
    r"<a\s+[^>]*href\s*=\s*['\"]([^'\"]+)['\"][^>]*>(.*?)</a>",
    re.I | re.S,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_TEXT_MODEL_ID_RE = re.compile(
    r"(?<![A-Za-z0-9._-])"
    r"([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?![A-Za-z0-9._-])"
)
_FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_AMBIGUOUS_DECLARATION_RE = re.compile(
    r"\b(?:family|series|variants?|shared|multiple)\b|"
    r"\ball\s+(?:of\s+)?(?:the\s+)?models\b|"
    r"\bbase\s*(?:/|and|or|&)\s*instruct\b",
    re.I,
)


class OfficialDiscoveryError(BundleIntegrityError):
    """Raised when discovery input or replayed output fails closed validation."""


class OfficialSourceKind(str, Enum):
    PAPER = "paper"
    SYSTEM_CARD = "system_card"
    CODE = "code"


class DiscoveryStatus(str, Enum):
    DISCOVERED = "discovered"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"


class DiscoveryProvenance(str, Enum):
    PUBLISHER_DECLARED = "publisher_declared"
    SECONDARY_HINT = "secondary_hint"
    AVAILABILITY = "availability"


@dataclass(frozen=True)
class OfficialSourcePolicy:
    policy_version: str
    publication_hosts: tuple[str, ...]
    code_hosts: tuple[str, ...]
    owned_hosts: tuple[str, ...]
    publisher_owners: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.policy_version != POLICY_VERSION:
            raise OfficialDiscoveryError("official-source policy version is unsupported")
        for name in ("publication_hosts", "code_hosts", "owned_hosts"):
            values = tuple(getattr(self, name))
            if values != tuple(sorted(set(values))):
                raise OfficialDiscoveryError(f"policy {name} must be sorted and unique")
            for host in values:
                if host != _normalize_host(host):
                    raise OfficialDiscoveryError(f"policy {name} contains an invalid host")
            object.__setattr__(self, name, values)
        owners = tuple(self.publisher_owners)
        if owners != tuple(sorted(set(owners))):
            raise OfficialDiscoveryError("publisher owners must be sorted and unique")
        for owner in owners:
            if (
                not isinstance(owner, str)
                or _normalize_owner(owner) != owner
            ):
                raise OfficialDiscoveryError("publisher owner is invalid")
        object.__setattr__(self, "publisher_owners", owners)

    @classmethod
    def for_target(
        cls,
        target: TargetIdentity,
        *,
        publisher_owners: Sequence[str] = (),
        owned_hosts: Sequence[str] = (),
    ) -> "OfficialSourcePolicy":
        namespace = target.model_id.split("/", 1)[0].casefold()
        owners = {namespace}
        owners.update(_normalize_owner(item) for item in publisher_owners)
        return cls(
            policy_version=POLICY_VERSION,
            publication_hosts=tuple(
                sorted(
                    {
                        "aclanthology.org",
                        "arxiv.org",
                        "doi.org",
                        "openreview.net",
                        "proceedings.mlr.press",
                    }
                )
            ),
            code_hosts=tuple(
                sorted({"codeberg.org", "github.com", "gitlab.com", "huggingface.co"})
            ),
            owned_hosts=tuple(sorted({_normalize_host(item) for item in owned_hosts})),
            publisher_owners=tuple(sorted(owners)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "publication_hosts": list(self.publication_hosts),
            "code_hosts": list(self.code_hosts),
            "owned_hosts": list(self.owned_hosts),
            "publisher_owners": list(self.publisher_owners),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "OfficialSourcePolicy":
        item = _strict_object(
            value,
            {
                "policy_version",
                "publication_hosts",
                "code_hosts",
                "owned_hosts",
                "publisher_owners",
            },
            "official-source policy",
        )
        for name in ("publication_hosts", "code_hosts", "owned_hosts", "publisher_owners"):
            if not isinstance(item[name], list) or not all(
                isinstance(entry, str) for entry in item[name]
            ):
                raise OfficialDiscoveryError(f"policy {name} must be a string list")
        return cls(
            policy_version=item["policy_version"],
            publication_hosts=tuple(item["publication_hosts"]),
            code_hosts=tuple(item["code_hosts"]),
            owned_hosts=tuple(item["owned_hosts"]),
            publisher_owners=tuple(item["publisher_owners"]),
        )


@dataclass(frozen=True)
class OfficialSourceRecord:
    record_id: str
    kind: OfficialSourceKind
    status: DiscoveryStatus
    provenance: DiscoveryProvenance
    declared_url: str | None
    normalized_url: str | None
    declaring_source_id: str | None
    declaration_locator: str
    reason_code: str
    evidence_eligible: bool = False

    def __post_init__(self) -> None:
        for name, enum_type in (
            ("kind", OfficialSourceKind),
            ("status", DiscoveryStatus),
            ("provenance", DiscoveryProvenance),
        ):
            try:
                object.__setattr__(self, name, enum_type(getattr(self, name)))
            except (TypeError, ValueError) as exc:
                raise OfficialDiscoveryError(f"official source {name} is invalid") from exc
        if not isinstance(self.record_id, str) or not _RECORD_ID_RE.fullmatch(self.record_id):
            raise OfficialDiscoveryError("official source record_id is invalid")
        if not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(self.reason_code):
            raise OfficialDiscoveryError("official source reason_code is invalid")
        if (
            not isinstance(self.declaration_locator, str)
            or not self.declaration_locator
            or len(self.declaration_locator) > 256
            or not _portable_text(self.declaration_locator)
        ):
            raise OfficialDiscoveryError("official source declaration locator is invalid")
        if self.evidence_eligible is not False:
            raise OfficialDiscoveryError("discovery candidates can never be evidence")
        if self.declared_url is not None:
            _validate_serialized_url(self.declared_url, allow_unsupported=True)
        if self.normalized_url is not None:
            _validate_serialized_url(self.normalized_url, allow_unsupported=False)

        if self.status is DiscoveryStatus.UNAVAILABLE:
            if (
                self.provenance is not DiscoveryProvenance.AVAILABILITY
                or self.declared_url is not None
                or self.normalized_url is not None
                or self.declaring_source_id is not None
            ):
                raise OfficialDiscoveryError("unavailable source record is inconsistent")
        else:
            if (
                self.provenance is DiscoveryProvenance.AVAILABILITY
                or self.declaring_source_id is None
                or not _SOURCE_ID_RE.fullmatch(self.declaring_source_id)
            ):
                raise OfficialDiscoveryError("declared source record is inconsistent")
        if self.status is DiscoveryStatus.DISCOVERED:
            if (
                self.provenance is not DiscoveryProvenance.PUBLISHER_DECLARED
                or self.declared_url is None
                or self.normalized_url is None
                or self.reason_code != "verified_publisher_declaration"
            ):
                raise OfficialDiscoveryError("discovered source must be publisher verified")
        if self.provenance is DiscoveryProvenance.SECONDARY_HINT:
            if (
                self.status is not DiscoveryStatus.REJECTED
                or self.reason_code != "secondary_hint_only"
            ):
                raise OfficialDiscoveryError("secondary sources must remain hint-only")

        expected_id = _record_id(
            kind=self.kind,
            status=self.status,
            provenance=self.provenance,
            declared_url=self.declared_url,
            normalized_url=self.normalized_url,
            declaring_source_id=self.declaring_source_id,
            declaration_locator=self.declaration_locator,
            reason_code=self.reason_code,
        )
        if self.record_id != expected_id:
            raise OfficialDiscoveryError("official source record_id does not match content")

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "provenance": self.provenance.value,
            "declared_url": self.declared_url,
            "normalized_url": self.normalized_url,
            "declaring_source_id": self.declaring_source_id,
            "declaration_locator": self.declaration_locator,
            "reason_code": self.reason_code,
            "evidence_eligible": self.evidence_eligible,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "OfficialSourceRecord":
        item = _strict_object(
            value,
            {
                "record_id",
                "kind",
                "status",
                "provenance",
                "declared_url",
                "normalized_url",
                "declaring_source_id",
                "declaration_locator",
                "reason_code",
                "evidence_eligible",
            },
            "official source record",
        )
        return cls(**item)


@dataclass(frozen=True)
class OfficialDiscoveryManifest:
    discovery_version: str
    discovery_id: str
    target: TargetIdentity
    source_bundle_id: str
    policy: OfficialSourcePolicy
    candidate_limit: int
    truncated: bool
    records: tuple[OfficialSourceRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        if self.discovery_version != DISCOVERY_VERSION:
            raise OfficialDiscoveryError("official discovery version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise OfficialDiscoveryError("official discovery target is invalid")
        if not isinstance(self.source_bundle_id, str) or not _BUNDLE_ID_RE.fullmatch(
            self.source_bundle_id
        ):
            raise OfficialDiscoveryError("official discovery bundle id is invalid")
        if not isinstance(self.policy, OfficialSourcePolicy):
            raise OfficialDiscoveryError("official discovery policy is invalid")
        if (
            isinstance(self.candidate_limit, bool)
            or not isinstance(self.candidate_limit, int)
            or not 3 <= self.candidate_limit <= 64
        ):
            raise OfficialDiscoveryError("candidate limit must be between 3 and 64")
        if not isinstance(self.truncated, bool):
            raise OfficialDiscoveryError("truncated must be boolean")
        if len(self.records) > self.candidate_limit:
            raise OfficialDiscoveryError("official discovery exceeds its candidate limit")
        if not all(isinstance(item, OfficialSourceRecord) for item in self.records):
            raise OfficialDiscoveryError("official discovery records are invalid")
        record_ids = [item.record_id for item in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise OfficialDiscoveryError("official discovery has duplicate record ids")
        normalized_keys = [
            (item.kind, item.normalized_url)
            for item in self.records
            if item.normalized_url is not None
        ]
        if len(normalized_keys) != len(set(normalized_keys)):
            raise OfficialDiscoveryError("official discovery has duplicate normalized URLs")
        for kind in OfficialSourceKind:
            kind_records = [item for item in self.records if item.kind is kind]
            if not kind_records:
                raise OfficialDiscoveryError("official discovery must cover every source kind")
            if not any(item.status is DiscoveryStatus.DISCOVERED for item in kind_records):
                unavailable = [
                    item for item in kind_records if item.status is DiscoveryStatus.UNAVAILABLE
                ]
                if len(unavailable) != 1:
                    raise OfficialDiscoveryError(
                        "undiscovered source kind needs one availability record"
                    )
            elif any(item.status is DiscoveryStatus.UNAVAILABLE for item in kind_records):
                raise OfficialDiscoveryError(
                    "discovered source kind cannot also be unavailable"
                )
        for record in self.records:
            if record.status is DiscoveryStatus.DISCOVERED:
                reason = _verify_url(record.kind, record.normalized_url, self.policy)
                if reason is not None:
                    raise OfficialDiscoveryError("discovered URL does not satisfy policy")
        expected_id = _discovery_id(
            target=self.target,
            source_bundle_id=self.source_bundle_id,
            policy=self.policy,
            candidate_limit=self.candidate_limit,
            truncated=self.truncated,
            records=self.records,
        )
        if not isinstance(self.discovery_id, str) or not _DISCOVERY_ID_RE.fullmatch(
            self.discovery_id
        ):
            raise OfficialDiscoveryError("official discovery id is invalid")
        if self.discovery_id != expected_id:
            raise OfficialDiscoveryError("official discovery id does not match content")

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovery_version": self.discovery_version,
            "discovery_id": self.discovery_id,
            "target": self.target.to_dict(),
            "source_bundle_id": self.source_bundle_id,
            "policy": self.policy.to_dict(),
            "candidate_limit": self.candidate_limit,
            "truncated": self.truncated,
            "records": [item.to_dict() for item in self.records],
        }

    @classmethod
    def from_dict(cls, value: Any) -> "OfficialDiscoveryManifest":
        item = _strict_object(
            value,
            {
                "discovery_version",
                "discovery_id",
                "target",
                "source_bundle_id",
                "policy",
                "candidate_limit",
                "truncated",
                "records",
            },
            "official discovery manifest",
        )
        if not isinstance(item["records"], list):
            raise OfficialDiscoveryError("official discovery records must be a list")
        try:
            target = TargetIdentity.from_dict(item["target"])
            policy = OfficialSourcePolicy.from_dict(item["policy"])
            records = tuple(
                OfficialSourceRecord.from_dict(entry) for entry in item["records"]
            )
        except OfficialDiscoveryError:
            raise
        except Exception as exc:
            raise OfficialDiscoveryError("official discovery members are invalid") from exc
        return cls(
            discovery_version=item["discovery_version"],
            discovery_id=item["discovery_id"],
            target=target,
            source_bundle_id=item["source_bundle_id"],
            policy=policy,
            candidate_limit=item["candidate_limit"],
            truncated=item["truncated"],
            records=records,
        )


@dataclass(frozen=True)
class _Candidate:
    kind: OfficialSourceKind
    raw_url: str
    source_id: str
    locator: str
    provenance: DiscoveryProvenance
    base_url: str | None
    relation_context: str


def discover_official_sources(
    bundle: ReplayedSourceBundle,
    *,
    policy: OfficialSourcePolicy | None = None,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> OfficialDiscoveryManifest:
    """Discover bounded official-source candidates from one frozen bundle."""

    _validate_bundle(bundle)
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise OfficialDiscoveryError("max_candidates must be an integer")
    if not 3 <= max_candidates <= 64:
        raise OfficialDiscoveryError("max_candidates must be between 3 and 64")
    target = bundle.manifest.target
    effective_policy = policy or OfficialSourcePolicy.for_target(target)
    if target.model_id.split("/", 1)[0].casefold() not in effective_policy.publisher_owners:
        raise OfficialDiscoveryError("policy does not cover the target publisher namespace")

    candidates, publisher_source_available, scan_truncated = _extract_candidates(bundle)
    evaluated = [_evaluate_candidate(item, effective_policy) for item in candidates]
    deduplicated = _deduplicate_records(evaluated)
    covered = {
        item.kind
        for item in deduplicated
        if item.status is DiscoveryStatus.DISCOVERED
    }
    unavailable_reason = (
        "not_declared" if publisher_source_available else "publisher_source_unavailable"
    )
    for kind in OfficialSourceKind:
        if kind not in covered:
            deduplicated.append(
                _make_record(
                    kind=kind,
                    status=DiscoveryStatus.UNAVAILABLE,
                    provenance=DiscoveryProvenance.AVAILABILITY,
                    declared_url=None,
                    normalized_url=None,
                    source_id=None,
                    locator="availability",
                    reason_code=unavailable_reason,
                )
            )
    ordered = sorted(deduplicated, key=_record_sort_key)
    retained, limit_truncated = _bounded_records(ordered, max_candidates)
    truncated = scan_truncated or limit_truncated
    records = tuple(retained)
    discovery_id = _discovery_id(
        target=target,
        source_bundle_id=bundle.manifest.bundle_id,
        policy=effective_policy,
        candidate_limit=max_candidates,
        truncated=truncated,
        records=records,
    )
    return OfficialDiscoveryManifest(
        discovery_version=DISCOVERY_VERSION,
        discovery_id=discovery_id,
        target=target,
        source_bundle_id=bundle.manifest.bundle_id,
        policy=effective_policy,
        candidate_limit=max_candidates,
        truncated=truncated,
        records=records,
    )


def serialize_official_discovery(manifest: OfficialDiscoveryManifest) -> bytes:
    if not isinstance(manifest, OfficialDiscoveryManifest):
        raise OfficialDiscoveryError("manifest must be an OfficialDiscoveryManifest")
    return _canonical_json(manifest.to_dict())


def load_official_discovery(payload: bytes | str) -> OfficialDiscoveryManifest:
    if isinstance(payload, str):
        encoded = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        encoded = payload
    else:
        raise OfficialDiscoveryError("official discovery payload must be bytes or text")
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OfficialDiscoveryError):
        raise OfficialDiscoveryError("official discovery payload is not strict JSON") from None
    if encoded != _canonical_json(value):
        raise OfficialDiscoveryError("official discovery payload is stale or non-canonical")
    return OfficialDiscoveryManifest.from_dict(value)


def replay_official_discovery(
    bundle: ReplayedSourceBundle, payload: bytes | str
) -> OfficialDiscoveryManifest:
    """Strictly replay serialized discovery against the same frozen bundle."""

    manifest = load_official_discovery(payload)
    _validate_bundle(bundle)
    if manifest.source_bundle_id != bundle.manifest.bundle_id:
        raise OfficialDiscoveryError("official discovery references another source bundle")
    if manifest.target != bundle.manifest.target:
        raise OfficialDiscoveryError("official discovery target drifts from the source bundle")
    recomputed = discover_official_sources(
        bundle,
        policy=manifest.policy,
        max_candidates=manifest.candidate_limit,
    )
    if manifest.to_dict() != recomputed.to_dict():
        raise OfficialDiscoveryError("official discovery does not replay deterministically")
    return manifest


def exact_target_declaration_record_ids(
    bundle: ReplayedSourceBundle,
    manifest: OfficialDiscoveryManifest,
) -> tuple[str, ...]:
    """Return declarations that independently identify this exact checkpoint.

    Transport allowlisting is not relation proof.  A link is admitted only
    when its bounded publisher declaration uses an explicit resource-to-model
    relation, names exactly one model identifier, and names this target.  Code
    must additionally point at a full immutable commit URL.  Bare repository
    paths, moving branches, family links, and mere same-line co-occurrence
    deliberately remain unresolved.
    """

    if not isinstance(manifest, OfficialDiscoveryManifest):
        raise OfficialDiscoveryError("relation inference requires a discovery manifest")
    replayed = replay_official_discovery(bundle, serialize_official_discovery(manifest))
    candidates, _, _ = _extract_candidates(bundle)
    retained = {
        item.record_id
        for item in replayed.records
        if item.status is DiscoveryStatus.DISCOVERED
    }
    result = {
        evaluated.record_id
        for candidate in candidates
        for evaluated in (_evaluate_candidate(candidate, replayed.policy),)
        if evaluated.record_id in retained
        and _declaration_identifies_exact_target(candidate, replayed.target)
    }
    return tuple(sorted(result))


def _extract_candidates(
    bundle: ReplayedSourceBundle,
) -> tuple[list[_Candidate], bool, bool]:
    candidates: list[_Candidate] = []
    publisher_available = False
    truncated = False
    for source in bundle.sources:
        record = source.record
        if record.status is not CollectionStatus.COLLECTED or source.content is None:
            continue
        if record.kind is SourceKind.MODEL_METADATA:
            publisher_available = True
            metadata = _strict_json(source.content)
            card_data = metadata.get("cardData")
            if not isinstance(card_data, dict):
                card_data = metadata.get("card_data")
            if isinstance(card_data, dict):
                candidates.extend(
                    _structured_candidates(
                        card_data,
                        source_id=record.source_id,
                        provenance=DiscoveryProvenance.PUBLISHER_DECLARED,
                        locator_prefix="metadata.cardData",
                    )
                )
            candidates.extend(
                _structured_candidates(
                    metadata,
                    source_id=record.source_id,
                    provenance=DiscoveryProvenance.SECONDARY_HINT,
                    locator_prefix="metadata",
                    skip_keys={"cardData", "card_data"},
                )
            )
            candidates.extend(_metadata_tag_hints(metadata, record.source_id))
        elif record.kind in {SourceKind.README, SourceKind.DECLARED_FILE} and _is_markdown(
            record.repository_path
        ):
            publisher_available = True
            try:
                text = source.content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise OfficialDiscoveryError("frozen publisher markdown is not UTF-8") from exc
            candidates.extend(
                _markdown_candidates(
                    text,
                    source_id=record.source_id,
                    base_url=record.source_url,
                    locator_prefix=record.repository_path or "README.md",
                )
            )
        if len(candidates) >= MAX_SCAN_LINKS:
            candidates = candidates[:MAX_SCAN_LINKS]
            truncated = True
            break
    return candidates, publisher_available, truncated


_STRUCTURED_FIELDS = {
    "paper": OfficialSourceKind.PAPER,
    "paper_url": OfficialSourceKind.PAPER,
    "arxiv": OfficialSourceKind.PAPER,
    "arxiv_url": OfficialSourceKind.PAPER,
    "system_card": OfficialSourceKind.SYSTEM_CARD,
    "system_card_url": OfficialSourceKind.SYSTEM_CARD,
    "model_card_url": OfficialSourceKind.SYSTEM_CARD,
    "code": OfficialSourceKind.CODE,
    "code_url": OfficialSourceKind.CODE,
    "repository": OfficialSourceKind.CODE,
    "repository_url": OfficialSourceKind.CODE,
}


def _structured_candidates(
    value: dict[str, Any],
    *,
    source_id: str,
    provenance: DiscoveryProvenance,
    locator_prefix: str,
    skip_keys: set[str] | None = None,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    skipped = skip_keys or set()
    for key, kind in _STRUCTURED_FIELDS.items():
        if key in skipped or key not in value:
            continue
        for index, raw in enumerate(_flatten_urls(value[key])):
            if key in {"arxiv", "arxiv_url"}:
                matched = _ARXIV_ID_RE.fullmatch(raw.strip())
                if matched:
                    raw = f"https://arxiv.org/abs/{matched.group(1)}"
            candidates.append(
                _Candidate(
                    kind=kind,
                    raw_url=raw,
                    source_id=source_id,
                    locator=f"{locator_prefix}.{key}[{index}]",
                    provenance=provenance,
                    base_url=None,
                    relation_context=f"{locator_prefix}.{key}",
                )
            )
    return candidates


def _flatten_urls(value: Any) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, str):
        if value and len(value) <= 4096 and _portable_text(value):
            values.append(value.strip())
    elif isinstance(value, list):
        for item in value[:64]:
            values.extend(_flatten_urls(item))
    elif isinstance(value, dict):
        for key in ("url", "href", "link"):
            if key in value:
                values.extend(_flatten_urls(value[key]))
                break
    return tuple(item for item in values if item)


def _metadata_tag_hints(metadata: dict[str, Any], source_id: str) -> list[_Candidate]:
    tags = metadata.get("tags")
    if not isinstance(tags, list):
        return []
    candidates: list[_Candidate] = []
    for index, tag in enumerate(tags[:128]):
        if not isinstance(tag, str):
            continue
        match = _ARXIV_ID_RE.fullmatch(tag.strip())
        if match:
            candidates.append(
                _Candidate(
                    kind=OfficialSourceKind.PAPER,
                    raw_url=f"https://arxiv.org/abs/{match.group(1)}",
                    source_id=source_id,
                    locator=f"metadata.tags[{index}]",
                    provenance=DiscoveryProvenance.SECONDARY_HINT,
                    base_url=None,
                    relation_context="metadata.tags",
                )
            )
    return candidates


def _markdown_candidates(
    text: str,
    *,
    source_id: str,
    base_url: str,
    locator_prefix: str,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for index, match in enumerate(_MARKDOWN_LINK_RE.finditer(text)):
        if len(candidates) >= MAX_SCAN_LINKS:
            break
        label, raw_url = match.groups()
        kind = _classify_link(label, raw_url)
        if kind is None or raw_url.startswith(("#", "?")):
            continue
        candidates.append(
            _Candidate(
                kind=kind,
                raw_url=raw_url,
                source_id=source_id,
                locator=f"{locator_prefix}.markdown_link[{index}]",
                provenance=DiscoveryProvenance.PUBLISHER_DECLARED,
                base_url=base_url,
                relation_context=_markdown_relation_context(text, match, label),
            )
        )
    offset = len(candidates)
    for index, match in enumerate(_HTML_LINK_RE.finditer(text)):
        if len(candidates) >= MAX_SCAN_LINKS:
            break
        raw_url, label = match.groups()
        label = _HTML_TAG_RE.sub("", label)
        kind = _classify_link(label, raw_url)
        if kind is None or raw_url.startswith(("#", "?")):
            continue
        candidates.append(
            _Candidate(
                kind=kind,
                raw_url=raw_url,
                source_id=source_id,
                locator=f"{locator_prefix}.html_link[{offset + index}]",
                provenance=DiscoveryProvenance.PUBLISHER_DECLARED,
                base_url=base_url,
                relation_context=_markdown_relation_context(text, match, label),
            )
        )
    remaining = MAX_SCAN_LINKS - len(candidates)
    candidates.extend(
        _frontmatter_candidates(text, source_id, base_url, locator_prefix)[:remaining]
    )
    return candidates[:MAX_SCAN_LINKS]


def _frontmatter_candidates(
    text: str, source_id: str, base_url: str, locator_prefix: str
) -> list[_Candidate]:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    end = next(
        (index for index, line in enumerate(lines[1:512], 1) if line.strip() in {"---", "..."}),
        None,
    )
    if end is None:
        return []
    candidates: list[_Candidate] = []
    for index, line in enumerate(lines[1:end], 1):
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        normalized_key = key.strip().casefold()
        kind = _STRUCTURED_FIELDS.get(normalized_key)
        raw = raw.strip().strip("'\"")
        if kind is None or not raw:
            continue
        matched = _ARXIV_ID_RE.fullmatch(raw) if normalized_key.startswith("arxiv") else None
        if matched:
            raw = f"https://arxiv.org/abs/{matched.group(1)}"
        candidates.append(
            _Candidate(
                kind=kind,
                raw_url=raw,
                source_id=source_id,
                locator=f"{locator_prefix}.frontmatter[{index}]",
                provenance=DiscoveryProvenance.PUBLISHER_DECLARED,
                base_url=base_url,
                relation_context=line[:512],
            )
        )
    return candidates


def _classify_link(label: str, raw_url: str) -> OfficialSourceKind | None:
    lowered = f"{label} {raw_url}".casefold()
    if any(token in lowered for token in ("system card", "system-card", "model card")):
        return OfficialSourceKind.SYSTEM_CARD
    if any(
        token in lowered
        for token in ("paper", "technical report", "arxiv", "openreview", "doi.org")
    ):
        return OfficialSourceKind.PAPER
    if any(
        token in lowered
        for token in ("code", "repository", "github.com", "gitlab.com", "codeberg.org")
    ):
        return OfficialSourceKind.CODE
    return None


def _markdown_relation_context(text: str, match: re.Match[str], label: str) -> str:
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    # Do not use an enclosing heading as relation proof: a target README often
    # lists family papers and independent comparisons under its own title.
    # If a line contains more than one link, its surrounding prose cannot be
    # attributed to any particular destination.  Keep only this link's label
    # so an exact declaration beside it cannot accidentally promote a sibling.
    link_count = len(_MARKDOWN_LINK_RE.findall(line)) + len(
        _HTML_LINK_RE.findall(line)
    )
    if link_count > 1:
        return label.strip()[:1024]
    return "\n".join(item for item in (label.strip(), line) if item)[:1024]


def _human_declaration_text(value: str) -> str:
    """Remove link destinations before evaluating publisher prose.

    A target-shaped repository URL is transport metadata, not a natural-
    language assertion that the linked resource documents this checkpoint.
    """

    without_markdown_destinations = re.sub(
        r"\]\(\s*[^)\s]+(?:\s+['\"][^'\"]*['\"])?\s*\)",
        "]",
        value,
    )
    without_html_destinations = re.sub(
        r"\s+href\s*=\s*(['\"])[^'\"]*\1",
        "",
        without_markdown_destinations,
        flags=re.I,
    )
    return re.sub(r"https?://[^\s<>)]+", "", without_html_destinations).casefold()


def _explicit_resource_relation(
    context: str,
    *,
    kind: OfficialSourceKind,
    target_model_id: str,
) -> bool:
    declaration = _human_declaration_text(context)
    ambiguity_context = declaration.replace(target_model_id.casefold(), " ")
    if _AMBIGUOUS_DECLARATION_RE.search(ambiguity_context):
        return False

    mentioned_models = {
        match.group(1).casefold() for match in _TEXT_MODEL_ID_RE.finditer(declaration)
    }
    if mentioned_models != {target_model_id.casefold()}:
        return False

    resources = {
        OfficialSourceKind.PAPER: (
            r"technical\s+report",
            r"model\s+report",
            r"paper",
        ),
        OfficialSourceKind.SYSTEM_CARD: (
            r"system\s+card",
            r"model\s+card",
            r"safety\s+card",
        ),
        OfficialSourceKind.CODE: (
            r"code\s+repository",
            r"source\s+repository",
            r"source\s+code",
            r"repository",
            r"codebase",
            r"code",
        ),
    }[kind]
    resource = "(?:" + "|".join(resources) + ")"
    target = re.escape(target_model_id.casefold())
    forward = re.compile(
        rf"\b{resource}\b\s+(?:(?:published|released|provided)\s+)?(?:for|of)\s+"
        rf"[`'\"]*{target}(?![A-Za-z0-9._-])"
    )
    reverse = re.compile(
        rf"(?<![A-Za-z0-9._-]){target}[`'\"]*"
        rf"(?:['’]s|\s+(?:has|provides|publishes|releases))\s+"
        rf"(?:an?\s+|the\s+)?(?:official\s+)?{resource}\b"
    )
    return (
        forward.search(declaration) is not None
        or reverse.search(declaration) is not None
    )


def _immutable_code_commit_url(normalized_url: str) -> bool:
    """Return whether a supported code URL is pinned to a full commit hash."""

    if not isinstance(normalized_url, str):
        return False
    parsed = urlsplit(normalized_url)
    host = (parsed.hostname or "").casefold()
    parts = [unquote(item) for item in parsed.path.split("/") if item]

    if host == "github.com" and len(parts) >= 4:
        return parts[2].casefold() in {"blob", "commit", "tree"} and bool(
            _FULL_COMMIT_RE.fullmatch(parts[3].casefold())
        )
    if host == "gitlab.com":
        for index in range(len(parts) - 2):
            if parts[index] == "-" and parts[index + 1].casefold() in {
                "blob",
                "commit",
                "tree",
            }:
                return bool(_FULL_COMMIT_RE.fullmatch(parts[index + 2].casefold()))
        return False
    if host == "codeberg.org" and len(parts) >= 4:
        if parts[2].casefold() == "commit":
            return bool(_FULL_COMMIT_RE.fullmatch(parts[3].casefold()))
        return (
            len(parts) >= 5
            and parts[2].casefold() == "src"
            and parts[3].casefold() == "commit"
            and bool(_FULL_COMMIT_RE.fullmatch(parts[4].casefold()))
        )
    if host == "huggingface.co" and len(parts) >= 4:
        return parts[2].casefold() in {"blob", "resolve", "tree"} and bool(
            _FULL_COMMIT_RE.fullmatch(parts[3].casefold())
        )
    return False


def _declaration_identifies_exact_target(
    candidate: _Candidate,
    target: TargetIdentity,
) -> bool:
    if candidate.provenance is not DiscoveryProvenance.PUBLISHER_DECLARED:
        return False
    normalized_url, _, reason = _normalize_url(candidate.raw_url, candidate.base_url)
    if reason is not None or normalized_url is None:
        return False
    if not _explicit_resource_relation(
        candidate.relation_context,
        kind=candidate.kind,
        target_model_id=target.model_id,
    ):
        return False
    return (
        candidate.kind is not OfficialSourceKind.CODE
        or _immutable_code_commit_url(normalized_url)
    )


def _evaluate_candidate(
    candidate: _Candidate, policy: OfficialSourcePolicy
) -> OfficialSourceRecord:
    normalized, serialized, normalization_reason = _normalize_url(
        candidate.raw_url, candidate.base_url
    )
    if normalization_reason is not None:
        return _make_record(
            kind=candidate.kind,
            status=DiscoveryStatus.REJECTED,
            provenance=candidate.provenance,
            declared_url=serialized,
            normalized_url=None,
            source_id=candidate.source_id,
            locator=candidate.locator,
            reason_code=(
                "secondary_hint_only"
                if candidate.provenance is DiscoveryProvenance.SECONDARY_HINT
                else normalization_reason
            ),
        )
    assert normalized is not None and serialized is not None
    if candidate.provenance is DiscoveryProvenance.SECONDARY_HINT:
        return _make_record(
            kind=candidate.kind,
            status=DiscoveryStatus.REJECTED,
            provenance=candidate.provenance,
            declared_url=serialized,
            normalized_url=normalized,
            source_id=candidate.source_id,
            locator=candidate.locator,
            reason_code="secondary_hint_only",
        )
    policy_reason = _verify_url(candidate.kind, normalized, policy)
    if policy_reason is not None:
        return _make_record(
            kind=candidate.kind,
            status=DiscoveryStatus.REJECTED,
            provenance=candidate.provenance,
            declared_url=serialized,
            normalized_url=normalized,
            source_id=candidate.source_id,
            locator=candidate.locator,
            reason_code=policy_reason,
        )
    return _make_record(
        kind=candidate.kind,
        status=DiscoveryStatus.DISCOVERED,
        provenance=candidate.provenance,
        declared_url=serialized,
        normalized_url=normalized,
        source_id=candidate.source_id,
        locator=candidate.locator,
        reason_code="verified_publisher_declaration",
    )


def _normalize_url(
    raw_url: str, base_url: str | None
) -> tuple[str | None, str | None, str | None]:
    raw = raw_url.strip()
    if not raw or len(raw) > 4096 or not _portable_text(raw):
        return None, None, "malformed_url"
    candidate = urljoin(base_url, raw) if base_url is not None else raw
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except (TypeError, ValueError, UnicodeError):
        return None, None, "malformed_url"
    if parsed.scheme.casefold() != "https":
        serialized = _safe_rejected_url(parsed)
        return None, serialized, "unsupported_scheme"
    if parsed.username is not None or parsed.password is not None:
        return None, None, "credentials_rejected"
    if port not in (None, 443):
        return None, None, "untrusted_port"
    try:
        host = _normalize_host(parsed.hostname or "")
    except OfficialDiscoveryError:
        return None, None, "malformed_url"
    decoded_path = unquote(parsed.path)
    if (
        "\\" in decoded_path
        or any(part in {".", ".."} for part in decoded_path.split("/"))
        or any(ord(character) < 32 or ord(character) == 127 for character in decoded_path)
    ):
        return None, None, "unsafe_path"
    path = quote(decoded_path or "/", safe="/%:@-._~!$&'()*+,;=")
    if path != "/":
        path = path.rstrip("/") or "/"
    query = ""
    if host == "openreview.net":
        retained = sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=False)
            if key == "id" and value
        )
        query = urlencode(retained)
    normalized = urlunsplit(("https", host, path, query, ""))
    return normalized, normalized, None


def _safe_rejected_url(parsed) -> str | None:  # noqa: ANN001
    if parsed.username is not None or parsed.password is not None:
        return None
    scheme = parsed.scheme.casefold()
    if not scheme or len(scheme) > 20 or not re.fullmatch(r"[a-z][a-z0-9+.-]*", scheme):
        return None
    value = urlunsplit((scheme, parsed.netloc, parsed.path, "", ""))
    if len(value) > 2048 or not _portable_text(value):
        return None
    return value


def _verify_url(
    kind: OfficialSourceKind, normalized_url: str | None, policy: OfficialSourcePolicy
) -> str | None:
    if normalized_url is None:
        return "malformed_url"
    parsed = urlsplit(normalized_url)
    host = _normalize_host(parsed.hostname or "")
    if host in policy.owned_hosts:
        return None
    if kind is OfficialSourceKind.PAPER:
        if host in policy.publication_hosts:
            return _publication_reason(host, parsed.path, parsed.query)
        if host in policy.code_hosts:
            return _ownership_reason(parsed.path, policy.publisher_owners)
        return "untrusted_host"
    if kind is OfficialSourceKind.SYSTEM_CARD and host in policy.publication_hosts:
        return _publication_reason(host, parsed.path, parsed.query)
    if host not in policy.code_hosts:
        return "untrusted_host"
    return _ownership_reason(parsed.path, policy.publisher_owners)


def _ownership_reason(path: str, publisher_owners: Sequence[str]) -> str | None:
    parts = [unquote(item).casefold() for item in path.split("/") if item]
    if len(parts) < 2:
        return "ownership_unverified"
    if parts[0] not in set(publisher_owners):
        return "ownership_mismatch"
    return None


def _publication_reason(host: str, path: str, query: str) -> str | None:
    decoded_path = unquote(path)
    if host == "arxiv.org":
        if re.fullmatch(r"/(?:abs|pdf)/[0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?(?:\.pdf)?", decoded_path):
            return None
        return "resource_unverified"
    if host == "openreview.net":
        parameters = dict(parse_qsl(query, keep_blank_values=False))
        if decoded_path in {"/forum", "/pdf", "/attachment"} and parameters.get("id"):
            return None
        return "resource_unverified"
    if decoded_path in {"", "/"}:
        return "resource_unverified"
    return None


def _deduplicate_records(
    records: Iterable[OfficialSourceRecord],
) -> list[OfficialSourceRecord]:
    selected: dict[tuple[OfficialSourceKind, str], OfficialSourceRecord] = {}
    unnormalized: dict[tuple[OfficialSourceKind, str, str], OfficialSourceRecord] = {}
    for record in records:
        if record.normalized_url is not None:
            key = (record.kind, record.normalized_url)
            existing = selected.get(key)
            if existing is None or (
                existing.provenance is DiscoveryProvenance.SECONDARY_HINT
                and record.provenance is DiscoveryProvenance.PUBLISHER_DECLARED
            ):
                selected[key] = record
        else:
            key = (record.kind, record.declared_url or "", record.reason_code)
            unnormalized.setdefault(key, record)
    return [*selected.values(), *unnormalized.values()]


def _bounded_records(
    records: Sequence[OfficialSourceRecord], limit: int
) -> tuple[list[OfficialSourceRecord], bool]:
    if len(records) <= limit:
        return list(records), False
    required: list[OfficialSourceRecord] = []
    for kind in OfficialSourceKind:
        kind_records = [item for item in records if item.kind is kind]
        discovered = [item for item in kind_records if item.status is DiscoveryStatus.DISCOVERED]
        required.append(discovered[0] if discovered else next(
            item for item in kind_records if item.status is DiscoveryStatus.UNAVAILABLE
        ))
    required_ids = {item.record_id for item in required}
    retained = list(required)
    retained.extend(item for item in records if item.record_id not in required_ids)
    retained = sorted(retained[:limit], key=_record_sort_key)
    return retained, True


def _record_sort_key(record: OfficialSourceRecord) -> tuple[Any, ...]:
    status_order = {
        DiscoveryStatus.DISCOVERED: 0,
        DiscoveryStatus.REJECTED: 1,
        DiscoveryStatus.UNAVAILABLE: 2,
    }
    provenance_order = {
        DiscoveryProvenance.PUBLISHER_DECLARED: 0,
        DiscoveryProvenance.SECONDARY_HINT: 1,
        DiscoveryProvenance.AVAILABILITY: 2,
    }
    return (
        record.kind.value,
        status_order[record.status],
        provenance_order[record.provenance],
        record.normalized_url or record.declared_url or "",
        record.declaration_locator,
    )


def _make_record(
    *,
    kind: OfficialSourceKind,
    status: DiscoveryStatus,
    provenance: DiscoveryProvenance,
    declared_url: str | None,
    normalized_url: str | None,
    source_id: str | None,
    locator: str,
    reason_code: str,
) -> OfficialSourceRecord:
    return OfficialSourceRecord(
        record_id=_record_id(
            kind=kind,
            status=status,
            provenance=provenance,
            declared_url=declared_url,
            normalized_url=normalized_url,
            declaring_source_id=source_id,
            declaration_locator=locator,
            reason_code=reason_code,
        ),
        kind=kind,
        status=status,
        provenance=provenance,
        declared_url=declared_url,
        normalized_url=normalized_url,
        declaring_source_id=source_id,
        declaration_locator=locator,
        reason_code=reason_code,
        evidence_eligible=False,
    )


def _record_id(
    *,
    kind: OfficialSourceKind,
    status: DiscoveryStatus,
    provenance: DiscoveryProvenance,
    declared_url: str | None,
    normalized_url: str | None,
    declaring_source_id: str | None,
    declaration_locator: str,
    reason_code: str,
) -> str:
    payload = {
        "kind": OfficialSourceKind(kind).value,
        "status": DiscoveryStatus(status).value,
        "provenance": DiscoveryProvenance(provenance).value,
        "declared_url": declared_url,
        "normalized_url": normalized_url,
        "declaring_source_id": declaring_source_id,
        "declaration_locator": declaration_locator,
        "reason_code": reason_code,
        "evidence_eligible": False,
    }
    return "official_source_" + hashlib.sha256(_canonical_json(payload)).hexdigest()[:24]


def _discovery_id(
    *,
    target: TargetIdentity,
    source_bundle_id: str,
    policy: OfficialSourcePolicy,
    candidate_limit: int,
    truncated: bool,
    records: Sequence[OfficialSourceRecord],
) -> str:
    payload = {
        "discovery_version": DISCOVERY_VERSION,
        "target": target.to_dict(),
        "source_bundle_id": source_bundle_id,
        "policy": policy.to_dict(),
        "candidate_limit": candidate_limit,
        "truncated": truncated,
        "records": [item.to_dict() for item in records],
    }
    return "official_discovery_" + hashlib.sha256(_canonical_json(payload)).hexdigest()[:32]


def _validate_bundle(bundle: ReplayedSourceBundle) -> None:
    if not isinstance(bundle, ReplayedSourceBundle):
        raise OfficialDiscoveryError("discovery requires a replayed source bundle")
    if len(bundle.sources) != len(bundle.manifest.sources):
        raise OfficialDiscoveryError("replayed source bundle is incomplete")
    source_ids = [item.record.source_id for item in bundle.sources]
    if source_ids != [item.source_id for item in bundle.manifest.sources]:
        raise OfficialDiscoveryError("replayed source ordering drifts from its manifest")


def _strict_json(content: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OfficialDiscoveryError):
        raise OfficialDiscoveryError("frozen model metadata is not strict JSON") from None
    if not isinstance(value, dict):
        raise OfficialDiscoveryError("frozen model metadata must be an object")
    return value


def _is_markdown(path: str | None) -> bool:
    return isinstance(path, str) and path.casefold().endswith(".md")


def _normalize_owner(owner: str) -> str:
    if not isinstance(owner, str):
        raise OfficialDiscoveryError("publisher owner is invalid")
    normalized = owner.strip().casefold()
    if (
        not normalized
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?", normalized)
    ):
        raise OfficialDiscoveryError("publisher owner is invalid")
    return normalized


def _normalize_host(host: str) -> str:
    if not isinstance(host, str) or not host or host.strip() != host:
        raise OfficialDiscoveryError("host is invalid")
    try:
        normalized = host.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise OfficialDiscoveryError("host is invalid") from exc
    if (
        not normalized
        or "/" in normalized
        or ":" in normalized
        or ".." in normalized
        or any(character.isspace() for character in normalized)
    ):
        raise OfficialDiscoveryError("host is invalid")
    if normalized.startswith("www."):
        normalized = normalized[4:]
    labels = normalized.split(".")
    if any(
        not label
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    ):
        raise OfficialDiscoveryError("host is invalid")
    return normalized


def _validate_serialized_url(value: str, *, allow_unsupported: bool) -> None:
    if not isinstance(value, str) or not value or len(value) > 2048 or not _portable_text(value):
        raise OfficialDiscoveryError("serialized discovery URL is invalid")
    try:
        parsed = urlsplit(value)
        parsed.port
    except (TypeError, ValueError, UnicodeError) as exc:
        raise OfficialDiscoveryError("serialized discovery URL is malformed") from exc
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise OfficialDiscoveryError("serialized discovery URL is not sanitized")
    if not allow_unsupported and parsed.scheme != "https":
        raise OfficialDiscoveryError("normalized discovery URL must use HTTPS")


def _portable_text(value: str) -> bool:
    return all(ord(character) >= 32 and ord(character) != 127 for character in value)


def _strict_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise OfficialDiscoveryError(f"{name} is not a closed object")
    return value


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise OfficialDiscoveryError("official discovery contains non-JSON data") from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise OfficialDiscoveryError("official discovery JSON has duplicate keys")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise OfficialDiscoveryError(f"official discovery JSON has non-finite value {value!r}")


__all__ = [
    "DEFAULT_MAX_CANDIDATES",
    "DISCOVERY_VERSION",
    "DiscoveryProvenance",
    "DiscoveryStatus",
    "OfficialDiscoveryError",
    "OfficialDiscoveryManifest",
    "OfficialSourceKind",
    "OfficialSourcePolicy",
    "OfficialSourceRecord",
    "discover_official_sources",
    "exact_target_declaration_record_ids",
    "load_official_discovery",
    "replay_official_discovery",
    "serialize_official_discovery",
]
