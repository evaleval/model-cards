"""Conservative enrichment of public cards from frozen Hugging Face sources.

The evidence pipeline intentionally keeps source bodies and provenance out of
the public card.  This module provides a small deterministic bridge for facts
that can be copied or narrowly derived from an already verified
``SourceDocumentCatalog``.  It performs no I/O and never consults model-memory
tables, live services, or unpinned sources.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import html
import json
import re
from typing import Any, Iterable, Mapping
import unicodedata
from urllib.parse import urljoin, urlsplit

from .publication_contract import FIELD_PATH_SET, NOT_APPLICABLE, NOT_SPECIFIED
from .publication_schema import (
    blank_publication_card,
    get_field,
    set_field,
    validate_publication_card,
)
from .model_family import (
    ModelFamilyDerivationError,
    select_config_model_family_derivation,
)
from .source_documents import SourceDocumentCatalog


PUBLICATION_SOURCE_RULESET = "publication-source-enrichment/v13"
PUBLICATION_CONFLICT_VERSION = "publication-conflict-record/v1"

_PUBLICATION_CONFLICT_REASONS = frozenset(
    {
        "benchmark_coordinate_scores_disagree",
        "metadata_base_model_declarations_disagree",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Public prose may summarize facts from frozen sources, but it must not become
# a quotation channel.  Twelve consecutive normalized source words is a
# conservative boundary: structured labels, identifiers, and short factual
# phrases remain usable while source paragraphs fail closed.
SOURCE_EXCERPT_MIN_WORDS = 12
# Scripts such as Chinese, Japanese, Korean, Thai, Lao, Khmer, and Myanmar do
# not reliably delimit words with ASCII whitespace.  Use a separate compact
# character boundary for those scripts instead of pretending one unbroken
# sentence is a single safe "word".  Twenty-four characters is deliberately
# longer than a short label or factual value while still catching copied prose.
SOURCE_EXCERPT_MIN_COMPACT_CHARS = 24
_SOURCE_EXCERPT_MIN_COMPACT_SCRIPT_CHARS = 12
_SOURCE_EXCERPT_GUARDED_FIELDS = frozenset(
    {
        "identity.summary",
        "training_context.training_data",
        "training_context.adaptations",
        "evaluation.results_summary",
        "evaluation.human_evals",
        "evaluation.safety_evals",
    }
)

_COMPACT_SCRIPT_RANGES = (
    (0x0E00, 0x0E7F),  # Thai
    (0x0E80, 0x0EFF),  # Lao
    (0x1000, 0x109F),  # Myanmar
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x1780, 0x17FF),  # Khmer
    (0x3040, 0x30FF),  # Hiragana and Katakana
    (0x3130, 0x318F),  # Hangul Compatibility Jamo
    (0x31F0, 0x31FF),  # Katakana Phonetic Extensions
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xAC00, 0xD7AF),  # Hangul Syllables
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0x20000, 0x2FA1F),  # Supplementary CJK ideographs
)

# This is deliberately a closed registry rather than a prefix convention.  A
# provenance record is useful only when its derivation names code that this
# module can deterministically replay from the frozen source catalog.
_PUBLICATION_SOURCE_RULE_SUFFIXES = frozenset(
    {
        "access_from_repository_flags_and_weight_listing",
        "adaptation_stage_from_exact_it_title_and_family_description",
        "adaptations_from_exact_posttraining_release_paragraph",
        "adaptations_from_exact_posttraining_statement",
        "adaptations_from_exact_readme_base_relation",
        "adaptations_from_exact_size_model_merging_statement",
        "adaptations_from_exact_target_training_stage",
        "adaptations_from_posttraining_and_distillation_statements",
        "adaptations_from_tuned_variant_architecture_statement",
        "architecture_classification_from_exact_config",
        "base_models_from_exact_metadata_declarations",
        "base_models_from_exact_readme_relation",
        "benchmark_scores_from_exact_target_readme_rows_or_columns",
        "citation_from_unique_readme_bibtex_entry",
        "code_repository_from_explicit_readme_link",
        "context_length_from_config_with_qualifier",
        "context_length_from_exact_readme",
        "data_cutoff_from_explicit_readme_label",
        "developer_from_explicit_readme_label",
        "derivatives_from_exact_prefixed_readme_model_links",
        "developer_from_metadata_author",
        "downloads_from_frozen_metadata",
        "exact_target_model_id",
        "exact_target_revision",
        "input_output_from_pipeline_architecture_and_target_stage",
        "license_from_card_metadata",
        "license_from_explicit_readme_statement",
        "likes_from_frozen_metadata",
        "model_card_from_pinned_readme_source",
        "model_family_from_registered_config_model_type",
        "model_type_from_pipeline_and_config",
        "moe_parameter_counts_from_safetensors_and_exact_readme_row",
        "name_from_exact_target_basename",
        "parameter_count_from_safetensors_total",
        "release_date_from_explicit_readme_label",
        "results_summary_from_exact_target_score_selection",
        "results_summary_from_scoped_safety_evaluation",
        "safety_evaluation_from_exact_target_score_row",
        "safety_evaluation_from_scoped_family_risk_sections",
        "safety_evaluation_from_scoped_readme_results_section",
        "stored_precision_from_safetensors_dtype_counts",
        "summary_from_exact_target_readme_description",
        "technical_report_from_explicit_readme_link",
        "technical_report_from_tagged_readme_bibtex",
        "tensor_payload_from_safetensors_dtype_counts",
        "training_data_from_dedicated_readme_section",
        "training_data_from_exact_family_pretraining_statement",
        "training_data_from_exact_posttraining_readme_paragraph",
        "training_data_from_explicit_pretraining_corpus_bullet",
        "training_data_from_stage_scoped_readme_overview",
        "training_data_from_staged_pretraining_sections",
        "training_datasets_from_card_metadata",
        "training_size_from_exact_model_table_row",
        "training_size_from_exact_target_size_clause",
        "training_size_from_explicit_family_statement",
    }
)
PUBLICATION_SOURCE_RULE_NAMES = frozenset(
    f"{PUBLICATION_SOURCE_RULESET}/{suffix}"
    for suffix in _PUBLICATION_SOURCE_RULE_SUFFIXES
)

_MODEL_ID_RE = re.compile(r"^[^/@\s]+(?:/[^/@\s]+)+$")
_ARXIV_ID_RE = re.compile(r"(?<![0-9.])([0-9]{4}\.[0-9]{4,5})(?![0-9.])")
_MARKDOWN_LINK_RE = re.compile(r"\[([^]\n]+)\]\((https?://[^)\s]+)\)", re.I)
_BARE_GITHUB_RE = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?",
    re.I,
)
_BIBTEX_START_RE = re.compile(
    r"@(?:article|book|incollection|inproceedings|misc|phdthesis|"
    r"proceedings|software|techreport)\s*\{",
    re.I,
)
_AFFIRMATIVE_COMMERCIAL_USE_RE = re.compile(
    r"\b(?:supports?|permits?|allows?)\s+commercial\s+use\b|"
    r"\bcommercial\s+use\s+(?:is|remains)\s+"
    r"(?:supported|permitted|allowed)\b",
    re.IGNORECASE,
)
_COMMERCIAL_USE_NEGATION_MARKER_RE = re.compile(
    r"\b(?:not|no|never|without|cannot|unsupported|unpermitted|unauthorized|"
    r"prohibit(?:s|ed|ing)?|forbid(?:s|den|ding)?|"
    r"disallow(?:s|ed|ing)?|exclude(?:s|d|ing)?|restrict(?:s|ed|ing)?)\b|"
    r"\b(?:doesn|don|isn|aren|can|won|mustn|shouldn|wouldn|couldn)"
    r"['’]t\b",
    re.IGNORECASE,
)


def _affirmative_commercial_use(body: str) -> re.Match[str] | None:
    """Return an affirmative phrase only when its sentence has no negation marker."""

    for match in _AFFIRMATIVE_COMMERCIAL_USE_RE.finditer(body):
        start = max(
            body.rfind(".", 0, match.start()),
            body.rfind("!", 0, match.start()),
            body.rfind("?", 0, match.start()),
            body.rfind("\n", 0, match.start()),
        ) + 1
        following = tuple(
            index
            for marker in (".", "!", "?", "\n")
            for index in (body.find(marker, match.end()),)
            if index >= 0
        )
        end = min(following) + 1 if following else len(body)
        sentence = body[start:end]
        if _COMMERCIAL_USE_NEGATION_MARKER_RE.search(sentence) is None:
            return match
    return None

_DTYPE_BITS: dict[str, int] = {
    "BOOL": 8,
    "U8": 8,
    "I8": 8,
    "I16": 16,
    "U16": 16,
    "F16": 16,
    "BF16": 16,
    "I32": 32,
    "U32": 32,
    "F32": 32,
    "I64": 64,
    "U64": 64,
    "F64": 64,
}

_DTYPE_NAMES: dict[str, str] = {
    "BF16": "bfloat16",
    "F16": "float16",
    "F32": "float32",
    "F64": "float64",
    "F8_E4M3": "FP8 E4M3",
    "F8_E4M3FN": "FP8 E4M3FN",
    "F8_E5M2": "FP8 E5M2",
}


class PublicationSourceError(ValueError):
    """Frozen source evidence cannot be safely projected into a public card."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PublicationSourceError(
            "publication source values must be finite JSON"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True, order=True)
class SourcePointer:
    """One local-only pointer into a frozen catalog document."""

    source_id: str
    pointer: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id:
            raise PublicationSourceError("provenance source_id must be non-empty")
        if not isinstance(self.pointer, str) or not self.pointer:
            raise PublicationSourceError("provenance pointer must be non-empty")
        if self.pointer == "source_uri" or self.pointer.startswith("/"):
            return
        match = re.fullmatch(r"text:([0-9]+)-([0-9]+)", self.pointer)
        if match is None or int(match.group(1)) > int(match.group(2)):
            raise PublicationSourceError(
                "provenance pointer must be source_uri, a JSON pointer, or "
                "an ordered nonnegative text span"
            )

    def to_dict(self) -> dict[str, str]:
        return {"source_id": self.source_id, "pointer": self.pointer}

    @classmethod
    def from_dict(cls, value: Any) -> "SourcePointer":
        if not isinstance(value, dict) or set(value) != {"source_id", "pointer"}:
            raise PublicationSourceError("serialized source pointer is malformed")
        return cls(source_id=value["source_id"], pointer=value["pointer"])


@dataclass(frozen=True)
class PublicationConflictRecord:
    """Local-only evidence that competing source values were withheld.

    The record deliberately stores hashes instead of the conflicting values.
    Exact source coordinates stay available for local audit without adding a
    conflict channel to the seven-section public card.
    """

    field_path: str
    reason: str
    sources: tuple[SourcePointer, ...]
    value_sha256s: tuple[str, ...]
    conflict_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.field_path, str)
            or self.field_path not in FIELD_PATH_SET
        ):
            raise PublicationSourceError("conflict field_path is invalid")
        if self.reason not in _PUBLICATION_CONFLICT_REASONS:
            raise PublicationSourceError("conflict reason is invalid")
        expected_field = {
            "benchmark_coordinate_scores_disagree": "evaluation.benchmark_scores",
            "metadata_base_model_declarations_disagree": "lineage.base_models",
        }[self.reason]
        if self.field_path != expected_field:
            raise PublicationSourceError(
                "conflict reason does not match its publication field"
            )
        raw_sources = tuple(self.sources)
        if not raw_sources or not all(
            isinstance(item, SourcePointer) for item in raw_sources
        ):
            raise PublicationSourceError("conflict sources are invalid")
        sources = tuple(sorted(set(raw_sources)))
        raw_digests = tuple(self.value_sha256s)
        if any(
            not isinstance(item, str) or _SHA256_RE.fullmatch(item) is None
            for item in raw_digests
        ):
            raise PublicationSourceError(
                "conflict value hashes must contain at least two distinct digests"
            )
        digests = tuple(sorted(set(raw_digests)))
        if len(digests) < 2:
            raise PublicationSourceError(
                "conflict value hashes must contain at least two distinct digests"
            )
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "value_sha256s", digests)
        object.__setattr__(self, "conflict_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "conflict_version": PUBLICATION_CONFLICT_VERSION,
            "field_path": self.field_path,
            "reason": self.reason,
            "sources": [item.to_dict() for item in self.sources],
            "value_sha256s": list(self.value_sha256s),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "conflict_sha256": self.conflict_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "PublicationConflictRecord":
        if not isinstance(value, dict) or set(value) != {
            "conflict_version",
            "field_path",
            "reason",
            "sources",
            "value_sha256s",
            "conflict_sha256",
        }:
            raise PublicationSourceError("serialized publication conflict is malformed")
        if value["conflict_version"] != PUBLICATION_CONFLICT_VERSION or not isinstance(
            value["sources"], list
        ) or not isinstance(value["value_sha256s"], list):
            raise PublicationSourceError(
                "serialized publication conflict version or arrays are invalid"
            )
        result = cls(
            field_path=value["field_path"],
            reason=value["reason"],
            sources=tuple(SourcePointer.from_dict(item) for item in value["sources"]),
            value_sha256s=tuple(value["value_sha256s"]),
        )
        if value["conflict_sha256"] != result.conflict_sha256:
            raise PublicationSourceError("publication conflict digest is inconsistent")
        return result


@dataclass(frozen=True)
class PublicationFieldProvenance:
    """Local summary of the rule and frozen source coordinates for one field."""

    field_path: str
    rule_name: str
    sources: tuple[SourcePointer, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(sorted(set(self.sources))))
        if (
            not isinstance(self.field_path, str)
            or self.field_path not in FIELD_PATH_SET
        ):
            raise PublicationSourceError("provenance field_path is invalid")
        if (
            not isinstance(self.rule_name, str)
            or self.rule_name not in PUBLICATION_SOURCE_RULE_NAMES
        ):
            raise PublicationSourceError("provenance rule_name is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "rule_name": self.rule_name,
            "sources": [item.to_dict() for item in self.sources],
        }


@dataclass(frozen=True)
class PublicationEnrichmentResult:
    """A schema-valid public card and its non-public source summary."""

    card: dict[str, dict[str, Any]]
    provenance: tuple[PublicationFieldProvenance, ...]
    conflicts: tuple[PublicationConflictRecord, ...] = ()

    def __post_init__(self) -> None:
        validate_publication_card(self.card)
        object.__setattr__(
            self,
            "provenance",
            tuple(sorted(self.provenance, key=lambda item: item.field_path)),
        )
        raw_conflicts = tuple(self.conflicts)
        if not all(
            isinstance(item, PublicationConflictRecord) for item in raw_conflicts
        ):
            raise PublicationSourceError("publication conflicts must be typed records")
        conflicts = tuple(
            sorted(
                raw_conflicts,
                key=lambda item: (
                    item.field_path,
                    item.reason,
                    item.conflict_sha256,
                ),
            )
        )
        if len({item.conflict_sha256 for item in conflicts}) != len(conflicts):
            raise PublicationSourceError("publication conflicts are duplicated")
        object.__setattr__(self, "conflicts", conflicts)

    def provenance_dict(self) -> dict[str, Any]:
        return {
            "ruleset": PUBLICATION_SOURCE_RULESET,
            "fields": [item.to_dict() for item in self.provenance],
        }

    @property
    def conflicts_sha256(self) -> str:
        return _digest(self._conflicts_payload())

    def _conflicts_payload(self) -> dict[str, Any]:
        return {
            "conflict_version": PUBLICATION_CONFLICT_VERSION,
            "ruleset": PUBLICATION_SOURCE_RULESET,
            "records": [item.to_dict() for item in self.conflicts],
        }

    def conflicts_dict(self) -> dict[str, Any]:
        return {
            **self._conflicts_payload(),
            "conflict_count": len(self.conflicts),
            "conflicts_sha256": self.conflicts_sha256,
        }


@dataclass(frozen=True)
class _Candidate:
    field_path: str
    value: Any
    rule: str
    sources: tuple[SourcePointer, ...]


@dataclass(frozen=True)
class _Inputs:
    catalog: SourceDocumentCatalog
    metadata: Mapping[str, Any] | None
    metadata_source_id: str | None
    readme: str | None
    readme_source_id: str | None
    readme_uri: str | None
    config: Mapping[str, Any] | None
    config_source_id: str | None


@dataclass(frozen=True)
class _ReadmeTable:
    """One parsed README table with exact source coordinates."""

    headers: tuple[str, ...]
    rows: tuple[tuple[tuple[str, ...], int, int], ...]
    start: int
    end: int
    headings: tuple[str, ...]


@dataclass(frozen=True)
class _ScoreCandidate:
    value: dict[str, Any]
    start: int
    end: int


@dataclass(frozen=True)
class _DownloadTableFacts:
    """Exact-target facts from one README model-download table row."""

    name: str
    values: Mapping[str, str]
    start: int
    end: int


def _rule(name: str) -> str:
    if name not in _PUBLICATION_SOURCE_RULE_SUFFIXES:
        raise PublicationSourceError(f"unknown publication source rule: {name}")
    return f"{PUBLICATION_SOURCE_RULESET}/{name}"


def _pointer(source_id: str | None, pointer: str) -> tuple[SourcePointer, ...]:
    if source_id is None:
        return ()
    return (SourcePointer(source_id, pointer),)


def _specified(value: Any) -> bool:
    return value not in (None, NOT_SPECIFIED)


def _string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _integer(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _metadata_matches_target(data: Mapping[str, Any], catalog: SourceDocumentCatalog) -> bool:
    model_id = data.get("id", data.get("modelId"))
    revision = data.get("sha")
    return model_id == catalog.target.model_id and revision == catalog.target.revision


def _catalog_inputs(catalog: SourceDocumentCatalog) -> _Inputs:
    if not isinstance(catalog, SourceDocumentCatalog):
        raise TypeError("catalog must be a verified SourceDocumentCatalog")
    records = {item.source_id: item for item in catalog.records}

    def select(kind: str, *, text: bool) -> tuple[Any, str | None, str | None]:
        matches = []
        for document in catalog.documents:
            record = records.get(document.source_id)
            if record is None or record.source_kind != kind:
                continue
            value = document.text if text else document.data
            if value is not None:
                matches.append((value, document.source_id, document.source_uri))
        if len(matches) != 1:
            return None, None, None
        return matches[0]

    metadata, metadata_id, _ = select("model_metadata", text=False)
    if not isinstance(metadata, Mapping) or not _metadata_matches_target(metadata, catalog):
        metadata, metadata_id = None, None
    readme, readme_id, readme_uri = select("readme", text=True)
    if not isinstance(readme, str):
        readme, readme_id, readme_uri = None, None, None
    config, config_id, _ = select("config", text=False)
    if not isinstance(config, Mapping):
        config, config_id = None, None
    return _Inputs(
        catalog=catalog,
        metadata=metadata,
        metadata_source_id=metadata_id,
        readme=readme,
        readme_source_id=readme_id,
        readme_uri=readme_uri,
        config=config,
        config_source_id=config_id,
    )


def _is_exact_target_root_readme(inputs: _Inputs) -> bool:
    """Return whether the README URI is the pinned root file for this target."""

    if inputs.readme_uri is None:
        return False
    parsed = urlsplit(inputs.readme_uri)
    target = inputs.catalog.target
    expected = {
        f"/{target.model_id}/resolve/{target.revision}/README.md",
        f"/{target.model_id}/blob/{target.revision}/README.md",
    }
    return (
        parsed.scheme == "https"
        and parsed.netloc.casefold() == "huggingface.co"
        and parsed.path in expected
        and not parsed.query
        and not parsed.fragment
    )


_FAMILY_TARGET_PATTERNS = {
    "deepseek_v3": re.compile(
        r"deepseek-ai/DeepSeek-V3(?:-Base)?", re.IGNORECASE
    ),
    "gemma3": re.compile(
        r"google/gemma-3-(?:1b|4b|12b|27b)-(?:pt|it)", re.IGNORECASE
    ),
    "llama31": re.compile(
        r"meta-llama/Llama-3\.1-(?:8B|70B|405B)(?:-Instruct)?",
        re.IGNORECASE,
    ),
    "olmo2_1124": re.compile(
        r"allenai/OLMo-2-1124-(?:7B|13B)(?:-(?:Instruct|SFT|DPO|RM))?",
        re.IGNORECASE,
    ),
    "qwen3": re.compile(
        r"Qwen/Qwen3-(?:0\.6B|1\.7B|4B|8B|14B|32B|30B-A3B|235B-A22B)"
        r"(?:-Base)?",
        re.IGNORECASE,
    ),
}


def _is_exact_family_target(inputs: _Inputs, family: str) -> bool:
    """Gate family-specific prose rules to their documented publisher target."""

    pattern = _FAMILY_TARGET_PATTERNS.get(family)
    return (
        pattern is not None
        and pattern.fullmatch(inputs.catalog.target.model_id) is not None
        and _is_exact_target_root_readme(inputs)
    )


def _target_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    target = inputs.catalog.target
    target_source = _pointer(inputs.metadata_source_id, "/id")
    yield _Candidate(
        "identity.model_id",
        target.model_id,
        "exact_target_model_id",
        target_source,
    )
    yield _Candidate(
        "identity.name",
        target.model_id.rsplit("/", 1)[-1],
        "name_from_exact_target_basename",
        target_source,
    )
    yield _Candidate(
        "identity.version",
        target.revision,
        "exact_target_revision",
        _pointer(inputs.metadata_source_id, "/sha"),
    )


def _card_data(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if metadata is None:
        return {}
    value = metadata.get("cardData")
    return value if isinstance(value, Mapping) else {}


def _tags(metadata: Mapping[str, Any] | None) -> tuple[str, ...]:
    if metadata is None or not isinstance(metadata.get("tags"), list):
        return ()
    return tuple(item for item in metadata["tags"] if isinstance(item, str))


def _resolved_readme_link(inputs: _Inputs, href: str) -> str | None:
    """Resolve one explicit README link against its pinned source URI."""

    value = html.unescape(href).strip().rstrip(".,;")
    if not value or value.startswith(("#", "mailto:")):
        return None
    if inputs.readme_uri is None:
        parsed = urlsplit(value)
        return value if parsed.scheme == "https" and parsed.netloc else None
    resolved = urljoin(inputs.readme_uri, value)
    parsed = urlsplit(resolved)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return resolved.replace("/resolve/", "/blob/", 1)


def _link_label_matches_target(inputs: _Inputs, label: str) -> bool:
    """Require an explicit resource label to identify the target release/family."""

    target_name = inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    target_label = _normalized_header(target_name)
    label_normalized = _normalized_header(label)
    if target_label in label_normalized:
        return True
    identity_tokens = tuple(
        item
        for item in _model_tokens(target_name)
        if item not in {"base", "pt", "it", "instruct", "chat"}
        and item not in _size_tokens(target_name)
        and not (item.isdigit() and len(item) == 4)
    )
    if (
        not identity_tokens
        or (len(identity_tokens) < 2 and not any(
            any(character.isdigit() for character in item)
            for item in identity_tokens
        ))
        or not set(identity_tokens) <= set(_model_tokens(label))
    ):
        return False
    label_sizes = _size_tokens(label)
    target_sizes = _size_tokens(target_name)
    if target_sizes and label_sizes and target_sizes.isdisjoint(label_sizes):
        return False
    label_stage = _label_stage(label)
    return label_stage is None or label_stage == _target_stage(inputs)


def _readme_prose_start(readme: str) -> int:
    """Return the first byte after optional Hugging Face YAML front matter."""

    if not readme.startswith("---"):
        return 0
    marker = readme.find("\n---", 3)
    return marker + 4 if marker >= 0 else 0


def _explicit_developer(
    inputs: _Inputs,
) -> tuple[str, tuple[SourcePointer, ...]] | None:
    if inputs.readme is None or inputs.readme_source_id is None:
        return None
    prose_start = _readme_prose_start(inputs.readme)
    prose = inputs.readme[prose_start:]
    match = re.search(
        r"(?im)^\s*\*{0,2}(?:model\s+developer|authors?)\*{0,2}\s*:\s*"
        r"(?P<value>[^\n]{1,240})\s*$",
        prose,
    )
    if match is None:
        return None
    absolute_start = prose_start + match.start()
    if not _position_is_target_scoped(inputs, absolute_start):
        return None
    value = _clean_readme_text(match.group("value")).strip().rstrip(".")
    if not value or len(value) > 200:
        return None
    return value, (
        SourcePointer(
            inputs.readme_source_id,
            f"text:{absolute_start}-{prose_start + match.end()}",
        ),
    )


def _explicit_license(
    inputs: _Inputs,
) -> tuple[str, tuple[SourcePointer, ...]] | None:
    """Return an explicitly labeled model/weights license, never a code license."""

    if inputs.readme is None or inputs.readme_source_id is None:
        return None
    readme = inputs.readme
    source_id = inputs.readme_source_id
    prose_start = _readme_prose_start(readme)
    prose = readme[prose_start:]

    labeled = re.search(
        r"(?im)^\s*\*{0,2}license\*{0,2}\s*:\s*(?P<body>[^\n]{1,800})\s*$",
        prose,
    )
    if labeled is not None and not _position_is_target_scoped(
        inputs,
        prose_start + labeled.start(),
    ):
        labeled = None
    if labeled is not None:
        body = labeled.group("body")
        if (
            re.search(r"(?i)\b(?:models?|weights?|checkpoints?)\b", body) is None
            and not _prose_scope_matches_target(
                inputs,
                body,
                allow_family_size_omission=True,
            )
        ):
            labeled = None
    if labeled is not None:
        body = labeled.group("body")
        cleaned = _clean_readme_text(body).strip().rstrip(".")
        link = next(
            (
                _resolved_readme_link(inputs, item.group(2))
                for item in _MARKDOWN_LINK_RE.finditer(body)
            ),
            None,
        )
        value = (
            f"{cleaned}: {link}"
            if cleaned and link and link not in cleaned
            else cleaned
        )
        if value:
            return value, (
                SourcePointer(
                    source_id,
                    f"text:{prose_start + labeled.start()}-"
                    f"{prose_start + labeled.end()}",
                ),
            )

    section = _section_span(readme, "license")
    if section is None:
        return None
    body, start, _end = section
    statement = re.search(
        r"(?is)(?P<sentence>[^.\n]{0,400}\bmodels?\b[^.\n]{0,300}?"
        r"\bsubject\s+to\s+\[(?P<label>[^]\n]*model[^]\n]*license[^]\n]*)\]"
        r"\((?P<href>[^)\s]+)\)[^.\n]*\.)",
        body,
    )
    if statement is None:
        return None
    sentence = statement.group("sentence")
    family_tokens = tuple(
        item
        for item in _model_tokens(inputs.catalog.target.model_id.rsplit("/", 1)[-1])
        if any(character.isalpha() for character in item)
        and item not in {"base", "chat", "instruct", "it", "pt"}
    )
    if not family_tokens or family_tokens[0] not in set(_model_tokens(sentence)):
        return None
    link = _resolved_readme_link(inputs, statement.group("href"))
    if link is None:
        return None
    label = _clean_readme_text(statement.group("label")).strip()
    commercial_match = _affirmative_commercial_use(body)
    commercial = commercial_match is not None
    qualifier = "; commercial use supported" if commercial else ""
    value = f"{label}{qualifier}: {link}"
    pointers = [
        SourcePointer(
            source_id,
            f"text:{start + statement.start()}-{start + statement.end()}",
        )
    ]
    if commercial and commercial_match is not None:
        pointers.append(
            SourcePointer(
                source_id,
                f"text:{start + commercial_match.start()}-"
                f"{start + commercial_match.end()}",
            )
        )
    return value, tuple(pointers)


def _identity_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    metadata = inputs.metadata
    source_id = inputs.metadata_source_id
    explicit_developer = _explicit_developer(inputs)
    if explicit_developer is not None:
        yield _Candidate(
            "identity.developed_by",
            explicit_developer[0],
            "developer_from_explicit_readme_label",
            explicit_developer[1],
        )
    else:
        author = _string((metadata or {}).get("author"))
        if author is not None:
            yield _Candidate(
                "identity.developed_by", author, "developer_from_metadata_author",
                _pointer(source_id, "/author"),
            )

    card_data = _card_data(metadata)
    pipeline = _string((metadata or {}).get("pipeline_tag")) or _string(
        card_data.get("pipeline_tag")
    )
    architectures = _architectures(inputs.config)
    if pipeline:
        model_type = pipeline
        sources = _pointer(source_id, "/pipeline_tag")
    elif any("forcausallm" in item.casefold() for item in architectures):
        model_type = "text-generation"
        sources = _pointer(inputs.config_source_id, "/architectures")
    else:
        model_type = None
        sources = ()
    if model_type is not None:
        yield _Candidate(
            "identity.model_type", model_type, "model_type_from_pipeline_and_config",
            sources,
        )

    explicit_license = _explicit_license(inputs)
    if explicit_license is not None:
        yield _Candidate(
            "identity.license",
            explicit_license[0],
            "license_from_explicit_readme_statement",
            explicit_license[1],
        )
    else:
        license_name = _string(card_data.get("license"))
        license_pointer = "/cardData/license"
        if license_name is None:
            license_tags = [
                item.split(":", 1)[1]
                for item in _tags(metadata)
                if item.startswith("license:")
            ]
            if len(set(license_tags)) == 1:
                license_name = license_tags[0]
                license_pointer = "/tags"
        if license_name is not None:
            yield _Candidate(
                "identity.license", license_name, "license_from_card_metadata",
                _pointer(source_id, license_pointer),
            )


def _summary_from_overview(inputs: _Inputs) -> tuple[str, int, int] | None:
    readme = inputs.readme
    if readme is None:
        return None
    pattern = re.compile(
        r"\*\*(?P<name>[^*\n]+)\*\*\s+has the following features:\s*"
        r"(?P<features>(?:\n\s*-\s+[^\n]+){1,8})",
        re.I,
    )
    for match in pattern.finditer(readme):
        if not _model_label_matches(inputs, match.group("name"), section_stage=_target_stage(inputs)):
            continue
        features: dict[str, str] = {}
        for line in match.group("features").splitlines():
            cleaned = _clean_readme_text(line)
            feature = re.match(
                r"(?i)(type|training stage|number of parameters|context length)\s*:\s*(.+)",
                cleaned,
            )
            if feature is not None:
                features[_normalized_header(feature.group(1))] = feature.group(2).rstrip(".")
        if features:
            name = _clean_readme_text(match.group("name"))
            details: list[str] = []
            parameters = features.get("number of parameters")
            context = features.get("context length")
            if parameters is not None:
                details.append(f"{parameters} parameters")
            if context is not None:
                details.append(f"a {context} context window")
            labels: list[str] = []
            model_type = features.get("type")
            training_stage = features.get("training stage")
            if model_type is not None:
                labels.append(f"model class {model_type}")
            if training_stage is not None:
                labels.append(f"repository stage {training_stage}")
            if details and labels:
                value = (
                    f"{name} is listed with " + " and ".join(details) + "; "
                    + "; ".join(labels) + "."
                )
            elif details:
                value = f"{name} is listed with " + " and ".join(details) + "."
            else:
                value = f"{name} repository labels: " + "; ".join(labels) + "."
            return (
                value,
                match.start(),
                match.end(),
            )
    return None


def _download_table_facts(inputs: _Inputs) -> _DownloadTableFacts | None:
    if inputs.readme is None:
        return None
    for table in _markdown_tables(inputs.readme):
        headers = tuple(_normalized_header(item) for item in table.headers)
        label_columns = [
            index for index, item in enumerate(headers) if item in {"model", "size"}
        ]
        if len(label_columns) != 1:
            continue
        section_stage = _target_stage(inputs)
        for cells, start, end in table.rows:
            label_column = label_columns[0]
            if (
                label_column >= len(cells)
                or not _model_label_matches(
                    inputs, cells[label_column], section_stage=section_stage
                )
            ):
                continue
            values = {headers[index]: cells[index] for index in range(min(len(headers), len(cells)))}
            return _DownloadTableFacts(
                name=_clean_readme_text(cells[label_column]),
                values=values,
                start=start,
                end=end,
            )
    return None


def _summary_from_download_table(inputs: _Inputs) -> tuple[str, int, int] | None:
    facts = _download_table_facts(inputs)
    if facts is None:
        return None
    total = next(
        (value for key, value in facts.values.items() if "total params" in key),
        None,
    )
    active = next(
        (value for key, value in facts.values.items() if "activated params" in key),
        None,
    )
    context = next(
        (value for key, value in facts.values.items() if "context length" in key),
        None,
    )
    training_tokens = facts.values.get("training tokens")
    layers = facts.values.get("layers")
    pieces = []
    if total:
        pieces.append(f"{total} total parameters")
    if active:
        pieces.append(f"{active} activated parameters per token")
    if training_tokens:
        pieces.append(f"{training_tokens} training tokens")
    if layers:
        pieces.append(f"{layers} layers")
    if context:
        pieces.append(f"{context} context length")
    if not pieces:
        return None
    return (
        f"{facts.name} is listed with " + ", ".join(pieces) + ".",
        facts.start,
        facts.end,
    )


def _summary_from_prose(inputs: _Inputs) -> tuple[str, int, int] | None:
    if inputs.readme is None:
        return None
    readme = inputs.readme
    target_name = inputs.catalog.target.model_id.rsplit("/", 1)[-1]

    escaped_target = re.escape(target_name)
    instruct_relation = re.search(
        rf"(?im)^The\s+{escaped_target}\s+Large\s+Language\s+Model\s+\(LLM\)\s+"
        r"is\s+an?\s+instruct\s+fine-tuned\s+version\s+of\s+(?:the\s+)?"
        r"(?P<base>[A-Za-z0-9._-]+)\.\s*$",
        readme,
    )
    if instruct_relation is not None:
        base = instruct_relation.group("base")
        return (
            f"{target_name} is the publisher-documented instruction-fine-tuned "
            f"version of {base}.",
            instruct_relation.start(),
            instruct_relation.end(),
        )

    base_relation = re.search(
        rf"(?im)^The\s+{escaped_target}\s+Large\s+Language\s+Model\s+\(LLM\)\s+"
        r"is\s+an?\s+(?P<base>[A-Za-z0-9._-]+)\s+with\s+extended\s+vocabulary\.\s*$",
        readme,
    )
    if base_relation is not None:
        base = base_relation.group("base")
        return (
            f"{target_name} is the publisher-documented {base} successor with an "
            "extended vocabulary.",
            base_relation.start(),
            base_relation.end(),
        )

    section = _section_span(readme, "description") or _section_span(
        readme, "model information"
    )
    section_body, section_start = (section[0], section[1]) if section else (readme, 0)
    family_tokens = tuple(
        item
        for item in _model_tokens(target_name)
        if any(character.isalpha() for character in item)
        and item not in {"base", "chat", "instruct", "it", "pt"}
    )
    candidates: list[tuple[int, str, int, int]] = []
    for _paragraph, relative_start, relative_end in _paragraphs(section_body):
        if relative_start > 8_000 or not family_tokens:
            continue
        raw = section_body[relative_start:relative_end]
        for text, start, end in _sentence_spans(
            raw,
            offset=section_start + relative_start,
        ):
            tokens = set(_model_tokens(text))
            if (
                family_tokens[0] not in tokens
                or "model" not in text.casefold()
                or not _prose_scope_matches_target(
                    inputs,
                    text,
                    allow_family_size_omission=True,
                )
            ):
                continue
            lowered = text.casefold()
            descriptors: list[str] = []
            target_stage = _label_stage(target_name)
            source_stage = _label_stage(text)
            if target_stage == "posttrained" and (
                source_stage == "posttrained" or "instruction-tuned variants" in lowered
            ):
                descriptors.append("instruction-tuned")
            elif target_stage == "base" and (
                source_stage == "base" or "pre-trained variants" in lowered
            ):
                descriptors.append("pretrained")
            if "multimodal" in lowered:
                descriptors.append("multimodal")
            if "multilingual" in lowered:
                descriptors.append("multilingual")
            if "open weights" in lowered or "open-weight" in lowered:
                descriptors.append("open-weight")

            capabilities: list[str] = []
            if re.search(r"(?i)(?:text\s+and\s+image|image\s+and\s+text)\s+input", text):
                capabilities.append("text-and-image input")
            if re.search(r"(?i)text\s+in\s*/\s*text\s+out", text):
                capabilities.append("text input and output")
            elif re.search(r"(?i)(?:generat(?:e|ing)\s+text\s+output|text\s+out)", text):
                capabilities.append("text output")

            if not descriptors and not capabilities and source_stage is None:
                continue
            descriptor_text = ", ".join(dict.fromkeys(descriptors))
            article = "an" if descriptor_text[:1].casefold() in {"a", "e", "i", "o", "u"} else "a"
            value = f"The publisher describes {target_name} as {article}"
            value += f" {descriptor_text} model" if descriptor_text else " model"
            if capabilities:
                value += " with " + " and ".join(dict.fromkeys(capabilities))
            value += "."
            score = len(set(_model_tokens(target_name)) & tokens) + len(descriptors) + len(capabilities)
            candidates.append((score, value, start, end))
    if not candidates:
        return None
    _score, value, start, end = max(candidates, key=lambda item: (item[0], -item[2]))
    return value, start, end


def _readme_identity_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    if inputs.readme is None or inputs.readme_source_id is None:
        return
    summary = (
        _summary_from_overview(inputs)
        or _summary_from_download_table(inputs)
        or _summary_from_prose(inputs)
    )
    if summary is not None:
        value, start, end = summary
        yield _Candidate(
            "identity.summary",
            value,
            "summary_from_exact_target_readme_description",
            (SourcePointer(inputs.readme_source_id, f"text:{start}-{end}"),),
        )

    release = _line_span(
        inputs.readme,
        re.compile(r"(?im)^\s*\*{0,2}Model Release Date\*{0,2}\s*:\s*.+$"),
    )
    if release is not None:
        raw, start, end = release
        value = re.sub(r"(?i)^.*?Model Release Date\**\s*:\s*", "", _clean_readme_text(raw)).strip().rstrip(".")
        if value:
            yield _Candidate(
                "identity.release_date",
                value,
                "release_date_from_explicit_readme_label",
                (SourcePointer(inputs.readme_source_id, f"text:{start}-{end}"),),
            )


def _base_model_surfaces(
    metadata: Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    def clean(values: Iterable[Any]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.strip()
                    for item in values
                    if isinstance(item, str)
                    and _MODEL_ID_RE.fullmatch(item.strip())
                }
            )
        )

    card_data = _card_data(metadata)
    declared = card_data.get("base_model")
    explicit = clean(list(declared) if isinstance(declared, list) else [declared])

    tagged = []
    for tag in _tags(metadata):
        if not tag.startswith("base_model:"):
            continue
        value = tag[len("base_model:") :]
        if value.startswith(("adapter:", "finetune:", "merge:", "quantized:")):
            value = value.split(":", 1)[1]
        tagged.append(value)
    fallback = clean(tagged)
    return explicit, fallback


def _base_model_ids(
    metadata: Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], str | None]:
    explicit, fallback = _base_model_surfaces(metadata)

    # Hugging Face exposes the same relation through two metadata surfaces.
    # Neither surface is authoritative when they disagree: publishing either
    # identifier would turn a visible source conflict into a silent choice.
    if explicit and fallback and explicit != fallback:
        return (), None
    if explicit:
        return explicit, "/cardData/base_model"
    return fallback, "/tags" if fallback else None


def _readme_base_relation(
    inputs: _Inputs,
) -> tuple[str, tuple[SourcePointer, ...], str | None] | None:
    """Resolve an exact README-declared predecessor through its Hub link."""

    if inputs.readme is None or inputs.readme_source_id is None:
        return None
    target_name = inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    relation = re.search(
        rf"(?im)^The\s+{re.escape(target_name)}\s+Large\s+Language\s+Model\s+"
        r"\(LLM\)\s+is\s+an?\s+(?P<base>[A-Za-z0-9._-]+)\s+with\s+"
        r"(?P<change>extended\s+vocabulary)\.\s*$",
        inputs.readme,
    )
    if relation is None:
        return None
    base_label = relation.group("base")
    target_namespace = inputs.catalog.target.model_id.split("/", 1)[0]
    link_match = next(
        (
            item
            for item in _MARKDOWN_LINK_RE.finditer(inputs.readme)
            if _normalized_header(item.group(1)) == _normalized_header(base_label)
        ),
        None,
    )
    if link_match is None:
        return None
    parsed = urlsplit(link_match.group(2))
    parts = [item for item in parsed.path.split("/") if item]
    if (
        parsed.scheme != "https"
        or parsed.netloc.casefold() != "huggingface.co"
        or len(parts) < 2
    ):
        return None
    model_id = "/".join(parts[:2])
    if (
        model_id.split("/", 1)[0] != target_namespace
        or _normalized_header(model_id.rsplit("/", 1)[-1])
        != _normalized_header(base_label)
        or not _MODEL_ID_RE.fullmatch(model_id)
    ):
        return None
    vocabulary = re.search(
        r"(?im)^\s*[-*+]\s*Extended\s+vocabulary\s+to\s+"
        r"(?P<count>[0-9][0-9,]*)\s*$",
        inputs.readme,
    )
    change = None
    pointers = [
        SourcePointer(
            inputs.readme_source_id,
            f"text:{relation.start()}-{relation.end()}",
        ),
        SourcePointer(
            inputs.readme_source_id,
            f"text:{link_match.start()}-{link_match.end()}",
        ),
    ]
    if vocabulary is not None:
        count = int(vocabulary.group("count").replace(",", ""))
        change = f"vocabulary extended to {count:,} entries"
        pointers.append(
            SourcePointer(
                inputs.readme_source_id,
                f"text:{vocabulary.start()}-{vocabulary.end()}",
            )
        )
    return model_id, tuple(pointers), change


def _lineage_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    explicit_bases, tagged_bases = _base_model_surfaces(inputs.metadata)
    metadata_bases_conflict = (
        bool(explicit_bases)
        and bool(tagged_bases)
        and explicit_bases != tagged_bases
    )
    base_model_ids, declaration_pointer = _base_model_ids(inputs.metadata)
    # A README predecessor cannot resolve a disagreement between the two
    # official metadata surfaces.  Treat the relation as unresolved until the
    # metadata conflict itself is adjudicated rather than silently changing
    # the evidence channel used for publication.
    readme_relation = (
        None if metadata_bases_conflict else _readme_base_relation(inputs)
    )
    if not base_model_ids and readme_relation is not None:
        base_model_ids = (readme_relation[0],)
        declaration_pointer = None
    base_models = tuple(
        {
            "model_id": model_id,
            "relation": "base_model",
        }
        for model_id in base_model_ids
        if model_id != inputs.catalog.target.model_id
    )
    if base_models:
        sources = (
            readme_relation[1]
            if declaration_pointer is None and readme_relation is not None
            else _pointer(inputs.metadata_source_id, declaration_pointer or "/tags")
        )
        yield _Candidate(
            "lineage.base_models",
            list(base_models),
            (
                "base_models_from_exact_readme_relation"
                if declaration_pointer is None and readme_relation is not None
                else "base_models_from_exact_metadata_declarations"
            ),
            sources,
        )
    try:
        selected_family = select_config_model_family_derivation(
            inputs.catalog.target, inputs.catalog.documents
        )
    except ModelFamilyDerivationError as exc:
        raise PublicationSourceError(
            "config model-family derivation failed closed"
        ) from exc
    if selected_family is not None:
        family_source, family_derivation = selected_family
        yield _Candidate(
            "lineage.model_family",
            family_derivation.family_id,
            "model_family_from_registered_config_model_type",
            _pointer(family_source.source_id, family_derivation.pointer),
        )

    if (
        inputs.readme is not None
        and inputs.readme_source_id is not None
        and _target_stage(inputs) == "base"
    ):
        target = inputs.catalog.target.model_id
        matches: dict[str, tuple[int, int]] = {}
        pattern = re.compile(
            r"https://huggingface\.co/([^/\s)]+/[^\s)#?]+)", re.I
        )
        for match in pattern.finditer(inputs.readme):
            model_id = match.group(1).rstrip("/.,;")
            if model_id == target or not model_id.startswith(target + "-"):
                continue
            if not _MODEL_ID_RE.fullmatch(model_id):
                continue
            matches.setdefault(model_id, (match.start(), match.end()))
        if matches:
            yield _Candidate(
                "lineage.derivatives",
                [
                    {"model_id": model_id, "relation": "derivative_model"}
                    for model_id in sorted(matches)
                ],
                "derivatives_from_exact_prefixed_readme_model_links",
                tuple(
                    SourcePointer(inputs.readme_source_id, f"text:{start}-{end}")
                    for _, (start, end) in sorted(matches.items())
                ),
            )


def _architectures(config: Mapping[str, Any] | None) -> tuple[str, ...]:
    if config is None or not isinstance(config.get("architectures"), list):
        return ()
    return tuple(item for item in config["architectures"] if isinstance(item, str))


def _pipeline_tag(inputs: _Inputs) -> str | None:
    metadata = inputs.metadata or {}
    return _string(metadata.get("pipeline_tag")) or _string(
        _card_data(inputs.metadata).get("pipeline_tag")
    )


def _architecture(inputs: _Inputs) -> tuple[str | None, tuple[SourcePointer, ...]]:
    config = inputs.config or {}
    pipeline = (_pipeline_tag(inputs) or "").casefold()
    architectures = _architectures(inputs.config)
    joined = " ".join(architectures).casefold()
    model_type = str(config.get("model_type") or "").casefold()
    expert_keys = (
        "num_local_experts",
        "num_experts",
        "expert_num",
        "n_routed_experts",
        "n_shared_experts",
        "num_experts_per_tok",
    )
    experts = tuple(
        key
        for key in expert_keys
        if isinstance(config.get(key), (int, float))
        and not isinstance(config.get(key), bool)
        and config[key] > 0
    )
    config_sources = (
        *_pointer(inputs.config_source_id, "/architectures"),
        *_pointer(inputs.config_source_id, "/model_type"),
    )
    if experts:
        return (
            "mixture-of-experts",
            (*config_sources, *tuple(SourcePointer(inputs.config_source_id, f"/{key}") for key in experts if inputs.config_source_id)),
        )
    if pipeline in {"image-text-to-text", "image-to-text", "visual-question-answering"}:
        return (
            "multimodal (topology unspecified)",
            (*config_sources, *_pointer(inputs.metadata_source_id, "/pipeline_tag")),
        )
    if "mamba" in model_type or "mamba" in joined:
        return "state-space", config_sources
    if "forcausallm" in joined:
        return "dense decoder-only", config_sources
    if config.get("is_encoder_decoder") is True or "encoderdecoder" in joined:
        return "encoder-decoder", config_sources
    if "forconditionalgeneration" in joined:
        return "conditional-generation (topology unspecified)", config_sources
    if "diffusion" in model_type or "diffusion" in joined:
        return "diffusion", config_sources
    return None, ()


def _safetensors(inputs: _Inputs) -> tuple[Mapping[str, Any], tuple[SourcePointer, ...]]:
    metadata = inputs.metadata or {}
    value = metadata.get("safetensors")
    if not isinstance(value, Mapping):
        return {}, ()
    return value, _pointer(inputs.metadata_source_id, "/safetensors")


def _dtype_counts(inputs: _Inputs) -> tuple[dict[str, int], tuple[SourcePointer, ...]]:
    safetensors, _ = _safetensors(inputs)
    parameters = safetensors.get("parameters")
    if not isinstance(parameters, Mapping) or not parameters:
        return {}, ()
    counts: dict[str, int] = {}
    for dtype, count in parameters.items():
        if (
            not isinstance(dtype, str)
            or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", dtype)
            or _integer(count) is None
        ):
            return {}, ()
        if count > 0:
            counts[dtype] = count
    if not counts:
        return {}, ()
    return counts, _pointer(inputs.metadata_source_id, "/safetensors/parameters")


def _dtype_name(dtype: str) -> str:
    return _DTYPE_NAMES.get(dtype, dtype)


def _precision(inputs: _Inputs) -> tuple[str | None, tuple[SourcePointer, ...]]:
    counts, sources = _dtype_counts(inputs)
    if not counts:
        return None, ()
    total = sum(counts.values())
    if len(counts) == 1:
        dtype = next(iter(counts))
        return (
            f"{_dtype_name(dtype)} stored tensor weights (safetensors parameter-count metadata)",
            sources,
        )
    majority = next(
        (dtype for dtype, count in counts.items() if count * 2 > total), None
    )
    if majority is not None:
        others = ", ".join(
            _dtype_name(dtype) for dtype in sorted(counts) if dtype != majority
        )
        return (
            f"Predominantly {_dtype_name(majority)} stored tensor weights; "
            f"additional dtypes: {others} (safetensors parameter-count metadata)",
            sources,
        )
    names = ", ".join(_dtype_name(dtype) for dtype in sorted(counts))
    return f"Mixed {names} stored tensor weights (safetensors parameter-count metadata)", sources


def _dtype_bits(dtype: str) -> int | None:
    if dtype in _DTYPE_BITS:
        return _DTYPE_BITS[dtype]
    if dtype.startswith("F8_"):
        return 8
    return None


def _model_size(inputs: _Inputs) -> tuple[str | None, tuple[SourcePointer, ...]]:
    counts, sources = _dtype_counts(inputs)
    if not counts:
        return None, ()
    total_bits = 0
    for dtype, count in counts.items():
        bits = _dtype_bits(dtype)
        if bits is None:
            return None, ()
        total_bits += bits * count
    total_bytes = (total_bits + 7) // 8
    if total_bytes >= 1024**3:
        quantity = (Decimal(total_bytes) / Decimal(1024**3)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        display = f"{quantity} GiB"
    else:
        quantity = (Decimal(total_bytes) / Decimal(1024**2)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        display = f"{quantity} MiB"
    return (
        f"{display} estimated tensor payload ({total_bytes:,} bytes; "
        "from safetensors dtype counts)",
        sources,
    )


def _markdown_cells(line: str) -> list[str]:
    cells = []
    for raw in line.strip().strip("|").split("|"):
        value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", raw)
        value = re.sub(r"\[([^]]+)\]\[[^]]+\]", r"\1", value)
        value = re.sub(r"[*`]", "", value)
        cells.append(re.sub(r"\s+", " ", value).strip())
    return cells


def _normalized_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _clean_readme_text(value: str, *, limit: int | None = None) -> str:
    """Collapse one source span to readable text without inventing content."""

    value = re.sub(r"```(?:[A-Za-z0-9_+-]+)?\s*", "", value)
    value = value.replace("```", "")
    value = re.sub(r"\[([^]\n]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^]\n]+)\]\[[^]\n]+\]", r"\1", value)
    value = re.sub(r"<br\s*/?>", "; ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"(?m)^#{1,6}\s*", "", value)
    value = re.sub(r"(?m)^\s*[-*+]\s+", "", value)
    value = re.sub(r"[*`]", "", value)
    value = re.sub(r"\s+", " ", html.unescape(value)).strip()
    if limit is not None and len(value) > limit:
        boundary = value.rfind(". ", 0, limit)
        if boundary < limit // 2:
            boundary = value.rfind("; ", 0, limit)
        if boundary < limit // 2:
            boundary = value.rfind(" ", 0, limit)
        value = value[: max(boundary + 1, 1)].rstrip() + " …"
    return value


def _normalized_unicode_text(value: str) -> str:
    return unicodedata.normalize("NFKC", html.unescape(value)).casefold()


def _normalized_source_words(value: str) -> tuple[str, ...]:
    # Include Unicode combining marks after a letter or number.  For ASCII this
    # preserves the prior ``[a-z0-9]+`` behavior exactly, while retaining
    # accented, Cyrillic, and other Unicode words instead of deleting them.
    words: list[str] = []
    current: list[str] = []
    for character in _normalized_unicode_text(value):
        if character.isalnum() or (
            current and unicodedata.category(character).startswith("M")
        ):
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return tuple(words)


def _is_compact_script_char(value: str) -> bool:
    codepoint = ord(value)
    return any(start <= codepoint <= end for start, end in _COMPACT_SCRIPT_RANGES)


def _normalized_compact_stream(value: str) -> str:
    # Preserve every alphanumeric character so embedded model names or numbers
    # remain part of the comparison.  Only spacing and punctuation are ignored.
    characters: list[str] = []
    accepts_mark = False
    for character in _normalized_unicode_text(value):
        if character.isalnum():
            characters.append(character)
            accepts_mark = True
        elif accepts_mark and unicodedata.category(character).startswith("M"):
            characters.append(character)
        else:
            accepts_mark = False
    return "".join(characters)


def _compact_script_needles(value: str) -> Iterable[str]:
    compact = _normalized_compact_stream(value)
    if len(compact) < SOURCE_EXCERPT_MIN_COMPACT_CHARS:
        return
    for offset in range(len(compact) - SOURCE_EXCERPT_MIN_COMPACT_CHARS + 1):
        needle = compact[offset : offset + SOURCE_EXCERPT_MIN_COMPACT_CHARS]
        if sum(_is_compact_script_char(character) for character in needle) >= (
            _SOURCE_EXCERPT_MIN_COMPACT_SCRIPT_CHARS
        ):
            yield needle


def assert_no_source_excerpt(
    card: Mapping[str, Any], catalog: SourceDocumentCatalog
) -> None:
    """Reject public prose that reproduces a long frozen-source run."""

    text_documents = tuple(
        document.text
        for document in catalog.documents
        if document.text is not None
    )
    source_word_streams = tuple(
        " " + " ".join(_normalized_source_words(document.text)) + " "
        for document in catalog.documents
        if document.text is not None
    )
    source_compact_streams = tuple(
        _normalized_compact_stream(text) for text in text_documents
    )
    if not source_word_streams:
        return
    for field_path in sorted(_SOURCE_EXCERPT_GUARDED_FIELDS):
        value = get_field(card, field_path, NOT_SPECIFIED)
        if not isinstance(value, str) or value in {NOT_SPECIFIED, NOT_APPLICABLE}:
            continue
        words = _normalized_source_words(value)
        if len(words) >= SOURCE_EXCERPT_MIN_WORDS:
            for offset in range(len(words) - SOURCE_EXCERPT_MIN_WORDS + 1):
                needle = (
                    " "
                    + " ".join(words[offset : offset + SOURCE_EXCERPT_MIN_WORDS])
                    + " "
                )
                if any(needle in source for source in source_word_streams):
                    raise PublicationSourceError(
                        f"{field_path} contains a prohibited frozen-source excerpt"
                    )
        for needle in _compact_script_needles(value):
            if any(needle in source for source in source_compact_streams):
                raise PublicationSourceError(
                    f"{field_path} contains a prohibited frozen-source excerpt"
                )


def _heading_matches(value: str, *needles: str) -> bool:
    normalized = _normalized_header(value)
    return any(_normalized_header(item) in normalized for item in needles)


def _markdown_headings(readme: str) -> tuple[tuple[int, str, int, int], ...]:
    """Return ATX headings outside fenced code blocks with exact offsets."""

    headings: list[tuple[int, str, int, int]] = []
    fence_character: str | None = None
    fence_length = 0
    offset = 0
    for line in readme.splitlines(keepends=True):
        fence = re.match(r"^ {0,3}(?P<marker>`{3,}|~{3,})", line)
        if fence is not None:
            marker = fence.group("marker")
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = None
                fence_length = 0
            offset += len(line)
            continue
        if fence_character is None:
            heading = re.match(r"^(#{1,6})[ \t]+(.+?)[ \t]*(?:\r?\n)?$", line)
            if heading is not None:
                headings.append(
                    (
                        len(heading.group(1)),
                        heading.group(2).strip(),
                        offset + heading.start(),
                        offset + heading.end(),
                    )
                )
        offset += len(line)
    return tuple(headings)


def _heading_context(readme: str, position: int) -> tuple[str, ...]:
    active: dict[int, str] = {}
    for level, title, start, _end in _markdown_headings(readme):
        if start >= position:
            break
        active = {key: value for key, value in active.items() if key < level}
        active[level] = title
    return tuple(active[key] for key in sorted(active))


def _section_span(
    readme: str,
    *titles: str,
) -> tuple[str, int, int] | None:
    """Return the first matching Markdown section body and exact offsets."""

    headings = _markdown_headings(readme)
    for index, (level, title, _heading_start, heading_end) in enumerate(headings):
        if not _heading_matches(title, *titles):
            continue
        start = heading_end
        end = len(readme)
        for following_level, _following_title, following_start, _following_end in headings[index + 1 :]:
            if following_level <= level:
                end = following_start
                break
        return readme[start:end], start, end
    return None


def _line_span(readme: str, pattern: re.Pattern[str]) -> tuple[str, int, int] | None:
    match = pattern.search(readme)
    if match is None:
        return None
    start = readme.rfind("\n", 0, match.start()) + 1
    newline = readme.find("\n", match.end())
    end = len(readme) if newline < 0 else newline
    return readme[start:end], start, end


def _paragraphs(readme: str) -> tuple[tuple[str, int, int], ...]:
    """Return prose-like Markdown blocks, excluding tables, code, and metadata."""

    blocks: list[tuple[str, int, int]] = []
    in_fence = False
    frontmatter_end = 0
    if readme.startswith("---"):
        marker = readme.find("\n---", 3)
        if marker >= 0:
            frontmatter_end = marker + 4
    for match in re.finditer(r"(?ms)(?:^|\n\s*\n)([^\n].*?)(?=\n\s*\n|\Z)", readme):
        raw = match.group(1)
        start, end = match.start(1), match.end(1)
        fences = raw.count("```")
        if in_fence:
            if fences % 2:
                in_fence = False
            continue
        if fences:
            if fences % 2:
                in_fence = True
            continue
        stripped = raw.strip()
        if (
            start < frontmatter_end
            or not stripped
            or stripped.startswith(("#", "|", "<", "!", "[!"))
            or re.match(r"^(?:[-: ]+\|)+", stripped)
        ):
            continue
        cleaned = _clean_readme_text(raw)
        if len(cleaned) >= 24:
            blocks.append((cleaned, start, end))
    return tuple(blocks)


def _sentence_spans(text: str, *, offset: int = 0) -> tuple[tuple[str, int, int], ...]:
    """Return conservative sentence spans with coordinates in the parent text."""

    spans: list[tuple[str, int, int]] = []
    start = 0
    for boundary in re.finditer(r"[.!?](?=\s|$)", text):
        end = boundary.end()
        raw = text[start:end]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        if raw.strip():
            spans.append(
                (
                    _clean_readme_text(raw),
                    offset + start + leading,
                    offset + start + trailing,
                )
            )
        start = end
    raw = text[start:]
    leading = len(raw) - len(raw.lstrip())
    trailing = len(raw.rstrip())
    if raw.strip():
        spans.append(
            (
                _clean_readme_text(raw),
                offset + start + leading,
                offset + start + trailing,
            )
        )
    return tuple(spans)


def _sentence_containing(
    readme: str,
    start: int,
    end: int,
) -> tuple[str, int, int] | None:
    """Return the one prose sentence containing an extracted source span."""

    for _paragraph, paragraph_start, paragraph_end in _paragraphs(readme):
        if paragraph_start <= start and end <= paragraph_end:
            raw = readme[paragraph_start:paragraph_end]
            for sentence, sentence_start, sentence_end in _sentence_spans(
                raw,
                offset=paragraph_start,
            ):
                if sentence_start <= start and end <= sentence_end:
                    return sentence, sentence_start, sentence_end
    return None


def _model_tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z]+\d*|\d+(?:\.\d+)?[a-z]*", value.casefold()))


def _target_stage(inputs: _Inputs) -> str:
    name = inputs.catalog.target.model_id.rsplit("/", 1)[-1].casefold()
    if "base" in name or re.search(r"(?:^|[-_.])pt(?:$|[-_.])", name):
        return "base"
    if (
        "instruct" in name
        or "chat" in name
        or re.search(r"(?:^|[-_.])it(?:$|[-_.])", name)
        or "conversational" in {item.casefold() for item in _tags(inputs.metadata)}
    ):
        return "posttrained"
    declared_bases, _pointer_name = _base_model_ids(inputs.metadata)
    if declared_bases:
        return "posttrained"
    if inputs.readme is not None:
        chat_section = _section_span(inputs.readme, "chat model")
        if chat_section is not None and _normalized_header(name) in _normalized_header(
            chat_section[0]
        ):
            return "posttrained"
    return "base"


def _label_stage(value: str) -> str | None:
    normalized = _normalized_header(value)
    if re.search(r"\b(?:instruct|instruction tuned|chat|post trained|sft|dpo|rlvr)\b", normalized):
        return "posttrained"
    if re.search(r"\b(?:base|pretrained|pre trained|pt)\b", normalized):
        return "base"
    return None


def _label_stages(value: str) -> frozenset[str]:
    """Return every explicitly named training stage in a prose span."""

    normalized = _normalized_header(value)
    stages: set[str] = set()
    if re.search(r"\b(?:base|pretrained|pre trained|pre training|pt)\b", normalized):
        stages.add("base")
    if re.search(
        r"\b(?:instruct|instruction tuned|chat|post trained|post training|sft|dpo|rlvr)\b",
        normalized,
    ):
        stages.add("posttrained")
    return frozenset(stages)


def _size_tokens(value: str) -> frozenset[str]:
    return frozenset(
        item.casefold()
        for item in re.findall(
            r"(?i)(?<![a-z0-9])\d+(?:\.\d+)?[bm](?![a-z0-9])", value
        )
    )


def _prose_scope_matches_target(
    inputs: _Inputs,
    text: str,
    *,
    allow_family_size_omission: bool = False,
) -> bool:
    """Require prose descriptors to identify the target family and stage.

    A README is an exact source file, not proof that every sentence in it is
    about the target.  This check permits an exact target label or a genuinely
    family-scoped statement, while rejecting sibling/comparison and stage
    leakage.
    """

    if not _is_exact_target_root_readme(inputs):
        return False
    if re.search(
        r"\b(?:while|whereas|however|in contrast|on the other hand|"
        r"compared (?:with|to)|for comparison|other models?)\b",
        text,
        re.IGNORECASE,
    ):
        return False
    target_name = inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    if _model_label_matches(
        inputs,
        text,
        section_stage=_target_stage(inputs),
    ):
        return True

    target_tokens = _model_tokens(target_name)
    text_tokens = set(_model_tokens(text))
    target_sizes = _size_tokens(target_name)
    text_sizes = _size_tokens(text)
    if target_sizes and text_sizes and target_sizes.isdisjoint(text_sizes):
        return False
    if target_sizes and not target_sizes <= text_sizes:
        if not allow_family_size_omission:
            return False
        if re.search(
            r"\b(?:models?|family|collection|series|variants?)\b",
            text,
            re.IGNORECASE,
        ) is None and not any(
            any(character.isdigit() for character in item)
            for item in target_tokens
            if item not in target_sizes
            and item not in {"base", "pt", "it", "instruct", "chat"}
        ):
            return False

    identity_tokens = tuple(
        item
        for item in target_tokens
        if item not in {"base", "pt", "it", "instruct", "chat"}
        and item not in target_sizes
        and not (item.isdigit() and len(item) == 4)
    )
    if not identity_tokens or not set(identity_tokens) <= text_tokens:
        return False

    # Reject a second named assertion subject in the same sentence.  Merely
    # mentioning the target elsewhere in a sentence cannot bind descriptors
    # or numeric values asserted about another model.
    for assertion in re.finditer(
        r"\b(?P<subject>[A-Z][A-Za-z0-9._-]{2,}(?:\s+[A-Z0-9][A-Za-z0-9._-]*){0,3})\s+"
        r"(?:is|are|has|offers|supports|provides)\b",
        text,
    ):
        subject_tokens = set(_model_tokens(assertion.group("subject")))
        if not set(identity_tokens) & subject_tokens:
            return False

    stages = _label_stages(text)
    if stages and _target_stage(inputs) not in stages:
        return False

    # A one-token family name without a size/version is too weak to establish
    # which checkpoint a prose descriptor concerns.  Require the exact target
    # label in that ambiguous case.
    if not target_sizes and len(identity_tokens) < 2:
        target_label = _normalized_header(target_name)
        if target_label not in _normalized_header(text):
            return False
    return True


_GENERIC_TARGET_SCOPE_HEADINGS = frozenset(
    {
        "architecture",
        "benchmark results",
        "critical and other risks",
        "description",
        "ethics and safety",
        "evaluation",
        "evaluation results",
        "evaluations",
        "inference",
        "introduction",
        "intended use",
        "intended uses",
        "license",
        "limitations",
        "model card",
        "model data",
        "model details",
        "model description",
        "model information",
        "model merging",
        "model overview",
        "model summary",
        "overview",
        "pretraining",
        "release documentation",
        "responsibility safety",
        "results",
        "safety",
        "specifications",
        "stage 1 initial pretraining",
        "stage 2 fine tuning",
        "supported languages",
        "technical specifications",
        "training",
        "training data",
        "training dataset",
        "use and risk",
    }
)


def _position_is_target_scoped(inputs: _Inputs, position: int) -> bool:
    """Fail closed when an unqualified label sits under a sibling heading."""

    if inputs.readme is None or not _is_exact_target_root_readme(inputs):
        return False
    headings = _heading_context(inputs.readme, position)
    if not headings:
        return True
    for heading in reversed(headings):
        normalized = _normalized_header(heading)
        normalized = re.sub(r"^\d+\s+", "", normalized)
        if normalized in _GENERIC_TARGET_SCOPE_HEADINGS:
            continue
        if _prose_scope_matches_target(
            inputs,
            heading,
            allow_family_size_omission=True,
        ):
            return True
        return False
    return True


def _target_scoped_section_span(
    inputs: _Inputs,
    *titles: str,
    text: str | None = None,
    offset: int = 0,
) -> tuple[str, int, int] | None:
    """Return a section only when its parent heading path remains target-scoped.

    Family rules recognize the section titles in the closed structural-heading
    registry. Their enclosing path, however, must not name a sibling or comparison
    model. ``offset`` maps a nested text slice back to the full README coordinates.
    """

    readme = inputs.readme if text is None else text
    if readme is None:
        return None
    section = _section_span(readme, *titles)
    if section is None:
        return None
    _body, body_start, _body_end = section
    if not _position_is_target_scoped(inputs, offset + body_start):
        return None
    return section


def _markers_are_target_scoped(
    inputs: _Inputs,
    text: str,
    offset: int,
    markers: Iterable[str],
) -> bool:
    """Require each semantic marker to occur in target-scoped prose."""

    folded = text.casefold()
    return all(
        any(
            _position_is_target_scoped(inputs, offset + match.start())
            for match in re.finditer(re.escape(marker.casefold()), folded)
        )
        for marker in markers
    )


def _model_label_matches(
    inputs: _Inputs,
    label: str,
    *,
    section_stage: str | None = None,
) -> bool:
    """Conservatively match a README row/column to the exact target variant."""

    target_name = inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    target_tokens = _model_tokens(target_name)
    label_tokens = set(_model_tokens(label))
    target_sizes = _size_tokens(target_name)
    label_sizes = _size_tokens(label)
    if target_sizes and label_sizes and target_sizes.isdisjoint(label_sizes):
        return False
    family_tokens = [
        item
        for item in target_tokens
        if any(character.isalpha() for character in item)
        and item not in {"base", "pt", "it", "instruct", "chat"}
    ]
    if not family_tokens or family_tokens[0] not in label_tokens:
        return False
    if target_sizes and not target_sizes <= label_sizes:
        return False
    target_stage = _target_stage(inputs)
    explicit_target_stage = _label_stage(target_name)
    candidate_stage = _label_stage(label)
    target_normalized = _normalized_header(target_name)
    label_normalized = _normalized_header(label)
    exact_label = label_normalized == target_normalized
    # Some publisher READMEs accidentally nest an exact, unmarked base-model
    # table below an instruction heading.  Permit only that narrow override.
    # A post-trained target still obeys an explicit Base Model section because
    # some family READMEs reuse the same column label for base and chat tables.
    exact_base_override = (
        exact_label
        and explicit_target_stage is None
        and target_stage == "base"
    )
    if (
        section_stage is not None
        and section_stage != target_stage
        and not exact_base_override
    ):
        return False
    if candidate_stage is not None and explicit_target_stage is None and not exact_label:
        return False
    if candidate_stage is not None and candidate_stage != target_stage:
        return False
    if (
        explicit_target_stage is not None
        and candidate_stage is None
        and not exact_label
        and section_stage != target_stage
    ):
        return False
    if (
        target_stage == "posttrained"
        and candidate_stage is None
        and section_stage is None
        and not exact_label
    ):
        return False
    if "instruct" in target_normalized and "instruct" not in label_normalized:
        return False
    if re.search(r"\bchat\b", target_normalized) and not re.search(r"\bchat\b", label_normalized):
        return False
    if re.search(r"\bit\b", target_normalized) and not re.search(
        r"\b(?:it|instruction tuned|instruct)\b", label_normalized
    ):
        return False

    # Require the stable family/version tokens, but permit compact release codes
    # such as "1124" to be rendered as a month/year in prose and omitted in
    # README table labels.
    required = {
        item
        for item in target_tokens
        if item not in {"base", "pt", "it", "instruct", "chat"}
        and not (item.isdigit() and len(item) == 4)
        and item not in target_sizes
    }
    return required <= label_tokens


def _table_section_stage(headings: Iterable[str]) -> str | None:
    for heading in reversed(tuple(headings)):
        stage = _label_stage(heading)
        if stage is not None:
            return stage
    return None


def _is_markdown_separator(cells: Iterable[str]) -> bool:
    values = tuple(cells)
    return bool(values) and all(
        re.fullmatch(r":?-{3,}:?", re.sub(r"\s+", "", item)) is not None
        for item in values
    )


def _markdown_tables(readme: str) -> tuple[_ReadmeTable, ...]:
    lines = readme.splitlines(keepends=True)
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line)
    tables: list[_ReadmeTable] = []
    index = 0
    while index + 1 < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        headers = tuple(_markdown_cells(lines[index]))
        separator = tuple(_markdown_cells(lines[index + 1]))
        if len(headers) < 2 or len(separator) != len(headers) or not _is_markdown_separator(separator):
            index += 1
            continue
        start = offsets[index]
        rows: list[tuple[tuple[str, ...], int, int]] = []
        row_index = index + 2
        while row_index < len(lines) and lines[row_index].lstrip().startswith("|"):
            cells = tuple(_markdown_cells(lines[row_index]))
            row_start = offsets[row_index]
            row_end = row_start + len(lines[row_index].rstrip("\n"))
            rows.append((cells, row_start, row_end))
            row_index += 1
        end = offsets[row_index] if row_index < len(lines) else len(readme)
        tables.append(
            _ReadmeTable(
                headers=headers,
                rows=tuple(rows),
                start=start,
                end=end,
                headings=_heading_context(readme, start),
            )
        )
        index = row_index
    return tuple(tables)


def _html_tables(readme: str) -> tuple[_ReadmeTable, ...]:
    tables: list[_ReadmeTable] = []
    for table_match in re.finditer(r"<table\b[^>]*>(.*?)</table>", readme, re.I | re.S):
        raw_rows = list(re.finditer(r"<tr\b[^>]*>(.*?)</tr>", table_match.group(1), re.I | re.S))
        expanded_rows: list[tuple[tuple[str, ...], int, int]] = []
        pending: dict[int, tuple[str, int]] = {}
        for row_match in raw_rows:
            carried = dict(pending)
            pending = {
                column: (value, remaining - 1)
                for column, (value, remaining) in carried.items()
                if remaining > 1
            }
            values: dict[int, str] = {column: value for column, (value, _) in carried.items()}
            column = 0
            for cell_match in re.finditer(
                r"<(?:td|th)\b([^>]*)>(.*?)</(?:td|th)>",
                row_match.group(1),
                re.I | re.S,
            ):
                while column in values:
                    column += 1
                attributes, body = cell_match.groups()
                cleaned = _clean_readme_text(body)
                colspan_match = re.search(r"\bcolspan\s*=\s*[\"']?(\d+)", attributes, re.I)
                rowspan_match = re.search(r"\browspan\s*=\s*[\"']?(\d+)", attributes, re.I)
                colspan = int(colspan_match.group(1)) if colspan_match else 1
                rowspan = int(rowspan_match.group(1)) if rowspan_match else 1
                for offset in range(colspan):
                    values[column + offset] = cleaned
                    if rowspan > 1:
                        pending[column + offset] = (cleaned, rowspan - 1)
                column += colspan
            if not values:
                continue
            width = max(values) + 1
            row_start = table_match.start(1) + row_match.start()
            row_end = table_match.start(1) + row_match.end()
            expanded_rows.append(
                (tuple(values.get(number, "") for number in range(width)), row_start, row_end)
            )
        if len(expanded_rows) < 2:
            continue
        headers = expanded_rows[0][0]
        tables.append(
            _ReadmeTable(
                headers=headers,
                rows=tuple(expanded_rows[1:]),
                start=table_match.start(),
                end=table_match.end(),
                headings=_heading_context(readme, table_match.start()),
            )
        )
    return tuple(tables)


def _context_value(raw: str) -> str | None:
    cleaned = _clean_readme_text(raw)

    def normalize(token: str) -> str | None:
        token = re.sub(r"\s+", "", token)
        if token[-1:].upper() in {"K", "M"}:
            return token[:-1] + token[-1].upper()
        try:
            return f"{int(token.replace(',', '')):,}"
        except ValueError:
            return None

    qualified = re.search(
        r"(?i)(?<![\d.])(\d[\d,]*(?:\.\d+)?\s*[KkMm]?)\s+"
        r"(?:tokens?\s+)?natively\b.*?"
        r"(?<![\d.])(\d[\d,]*(?:\.\d+)?\s*[KkMm]?)\s+tokens?\s+"
        r"with\s+YaRN\b",
        cleaned,
    )
    if qualified is not None:
        native = normalize(qualified.group(1))
        extended = normalize(qualified.group(2))
        if native is not None and extended is not None:
            return (
                f"{native} tokens natively; {extended} tokens with YaRN "
                "(README-declared context length)"
            )

    match = re.search(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?\s*[KkMm]?)(?![A-Za-z0-9])", cleaned)
    if match is None:
        return None
    token = normalize(match.group(1))
    if token is None:
        return None
    return f"{token} tokens (README-declared context length)"


def _markdown_context(inputs: _Inputs) -> tuple[str, int, int] | None:
    readme = inputs.readme
    if readme is None:
        return None
    for table in _markdown_tables(readme):
        header = tuple(_normalized_header(item) for item in table.headers)
        context_columns = [
            number
            for number, item in enumerate(header)
            if item in {"context length", "context window"}
        ]
        model_columns = [
            number
            for number, item in enumerate(header)
            if item in {"model", "model name", "size"}
        ]
        if len(context_columns) != 1 or len(model_columns) != 1:
            continue
        context_column = context_columns[0]
        model_column = model_columns[0]
        section_stage = _table_section_stage(table.headings)
        for cells, start, end in table.rows:
            if max(context_column, model_column) >= len(cells):
                continue
            if not _model_label_matches(
                inputs,
                cells[model_column],
                section_stage=section_stage,
            ):
                continue
            value = _context_value(cells[context_column])
            if value is not None:
                return value, start, end
    return None


def _html_cells(row: str) -> list[str]:
    cells = []
    for match in re.finditer(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>", row, re.I | re.S):
        value = re.sub(r"<[^>]+>", " ", match.group(1))
        cells.append(re.sub(r"\s+", " ", html.unescape(value)).strip())
    return cells


def _html_context(inputs: _Inputs) -> tuple[str, int, int] | None:
    if inputs.readme is None:
        return None
    for table in _html_tables(inputs.readme):
        headers = tuple(_normalized_header(item) for item in table.headers)
        context_columns = [
            index
            for index, item in enumerate(headers)
            if item in {"context length", "context window"}
        ]
        model_columns = [
            index
            for index, item in enumerate(headers)
            if item in {
                "model",
                "model name",
                "size",
                "model size",
                "params",
                "parameters",
            }
        ]
        if headers and not headers[0]:
            model_columns.insert(0, 0)
        if len(context_columns) != 1 or not model_columns:
            continue
        context_column = context_columns[0]
        section_stage = _table_section_stage(table.headings)
        if section_stage is not None and section_stage != _target_stage(inputs):
            continue
        for cells, start, end in table.rows:
            if context_column >= len(cells):
                continue
            label = " ".join(
                cells[index]
                for index in model_columns
                if index < len(cells) and cells[index]
            )
            if not label or not _prose_scope_matches_target(inputs, label):
                continue
            value = _context_value(cells[context_column])
            if value is not None:
                return value, start, end
    return None


def _prose_context(inputs: _Inputs) -> tuple[str, int, int] | None:
    if inputs.readme is None:
        return None
    readme = inputs.readme
    declared_line = re.search(
        r"(?im)^\s*[-*+]?\s*\*{0,2}context\s+(?:length|window)\*{0,2}\s*:\s*"
        r"(?P<value>[^\n]+?)\s*$",
        readme,
    )
    if declared_line is not None:
        headings = " ".join(_heading_context(readme, declared_line.start())).casefold()
        value = _context_value(declared_line.group("value"))
        if (
            value is not None
            and _position_is_target_scoped(inputs, declared_line.start())
            and not re.search(
                r"\b(?:benchmark|comparison|compared|other models?|baselines?)\b",
                headings,
            )
        ):
            return value, declared_line.start(), declared_line.end()

    patterns = (
        re.compile(r"(?i)(\d[\d,]*(?:\.\d+)?\s*[KkMm])\s+context\s+window"),
        re.compile(r"(?i)context\s+window\s+lengths?\s+up\s+to\s+[*_`]*(\d[\d,]*(?:\.\d+)?\s*[KkMm]?)"),
    )
    for pattern in patterns:
        for match in pattern.finditer(readme):
            sentence = _sentence_containing(readme, match.start(), match.end())
            if sentence is None or not _prose_scope_matches_target(
                inputs,
                sentence[0],
                allow_family_size_omission=True,
            ):
                continue
            value = _context_value(match.group(1))
            if value is not None:
                return value, match.start(), match.end()
    return None


def _config_context(inputs: _Inputs) -> tuple[str, tuple[SourcePointer, ...]] | None:
    config = inputs.config or {}
    candidates = (
        (config.get("max_position_embeddings"), "/max_position_embeddings"),
        (
            config.get("text_config", {}).get("max_position_embeddings")
            if isinstance(config.get("text_config"), Mapping)
            else None,
            "/text_config/max_position_embeddings",
        ),
    )
    for value, pointer in candidates:
        count = _integer(value)
        if count and count > 0:
            return (
                f"{count:,} positions (config max_position_embeddings; "
                "implementation limit, not an independently verified context window)",
                _pointer(inputs.config_source_id, pointer),
            )
    return None


def _context(inputs: _Inputs) -> tuple[str | None, str, tuple[SourcePointer, ...]]:
    if inputs.readme is not None and inputs.readme_source_id is not None:
        found = (
            _markdown_context(inputs)
            or _html_context(inputs)
            or _prose_context(inputs)
        )
        if found is not None:
            value, start, end = found
            return (
                value,
                "context_length_from_exact_readme",
                (SourcePointer(inputs.readme_source_id, f"text:{start}-{end}"),),
            )
    fallback = _config_context(inputs)
    if fallback is not None:
        return fallback[0], "context_length_from_config_with_qualifier", fallback[1]
    return None, "context_length_unavailable", ()


def _stage(model_id: str) -> str | None:
    name = model_id.rsplit("/", 1)[-1].casefold()
    if "instruct" in name or re.search(r"(?:^|[-_.])it(?:$|[-_.])", name):
        return "model stage: instruction-tuned"
    if "base" in name or re.search(r"(?:^|[-_.])pt(?:$|[-_.])", name):
        return "model stage: pretrained/base"
    if "chat" in name:
        return "model stage: chat/post-trained"
    return None


def _readme_input_output(
    inputs: _Inputs,
) -> tuple[list[str], tuple[SourcePointer, ...]] | None:
    """Read exact-target modality cells from a model-information table."""

    if inputs.readme is None or inputs.readme_source_id is None:
        return None
    for table in (*_markdown_tables(inputs.readme), *_html_tables(inputs.readme)):
        if not any(_heading_matches(item, "model information") for item in table.headings):
            continue
        headers = tuple(_normalized_header(item) for item in table.headers)
        input_columns = [
            index for index, item in enumerate(headers) if item == "input modalities"
        ]
        output_columns = [
            index for index, item in enumerate(headers) if item == "output modalities"
        ]
        if len(input_columns) != 1 or len(output_columns) != 1:
            continue
        input_column = input_columns[0]
        output_column = output_columns[0]
        model_columns = [
            index
            for index, item in enumerate(headers)
            if item
            in {
                "model",
                "model name",
                "size",
                "model size",
                "params",
                "parameters",
            }
        ]
        if headers and not headers[0]:
            model_columns.insert(0, 0)
        if not model_columns:
            continue
        section_stage = _table_section_stage(table.headings)
        if section_stage is not None and section_stage != _target_stage(inputs):
            continue
        matched: list[tuple[str, str, int, int]] = []
        for cells, start, end in table.rows:
            if max(input_column, output_column) >= len(cells):
                continue
            row_label = " ".join(
                cells[index]
                for index in model_columns
                if index < len(cells) and cells[index]
            )
            if not row_label or not _prose_scope_matches_target(inputs, row_label):
                continue
            input_value = _clean_readme_text(cells[input_column])
            output_value = _clean_readme_text(cells[output_column])
            if input_value and output_value:
                matched.append((input_value, output_value, start, end))
        if len(matched) != 1:
            continue
        input_value, output_value, start, end = matched[0]
        values = [f"input: {input_value}", f"output: {output_value}"]
        pointers = [
            SourcePointer(inputs.readme_source_id, f"text:{start}-{end}")
        ]
        languages = re.search(
            r"(?im)^\s*\*{0,2}supported\s+languages\*{0,2}\s*:\s*"
            r"(?P<value>[^\n]{1,500})\s*$",
            inputs.readme,
        )
        if languages is not None and _position_is_target_scoped(
            inputs,
            languages.start(),
        ):
            value = _clean_readme_text(languages.group("value")).strip().rstrip(".")
            if value:
                values.append(f"supported languages: {value}")
                pointers.append(
                    SourcePointer(
                        inputs.readme_source_id,
                        f"text:{languages.start()}-{languages.end()}",
                    )
                )
        return values, tuple(pointers)
    return None


def _input_output(inputs: _Inputs) -> tuple[list[str] | None, tuple[SourcePointer, ...]]:
    readme_values = _readme_input_output(inputs)
    if readme_values is not None:
        values, readme_sources = readme_values
    else:
        values = []
        readme_sources = ()
    pipeline = (_pipeline_tag(inputs) or "").casefold()
    mapping = {
        "text-generation": ["input: text", "output: text"],
        "text2text-generation": ["input: text", "output: text"],
        "image-text-to-text": ["input: image and text", "output: text"],
        "image-to-text": ["input: image", "output: text"],
        "automatic-speech-recognition": ["input: audio", "output: text"],
        "image-classification": ["input: image", "output: labels"],
    }
    if not values:
        values = list(mapping.get(pipeline, ()))
    sources = list(readme_sources)
    if values and not readme_sources:
        sources.extend(_pointer(inputs.metadata_source_id, "/pipeline_tag"))
    if not values:
        architectures = " ".join(_architectures(inputs.config)).casefold()
        if "forcausallm" in architectures:
            values = ["input: text", "output: text"]
            sources.extend(_pointer(inputs.config_source_id, "/architectures"))
    stage = _stage(inputs.catalog.target.model_id)
    if stage is not None:
        values.append(stage)
        sources.extend(_pointer(inputs.metadata_source_id, "/id"))
    if not values:
        return None, ()
    return list(dict.fromkeys(values)), tuple(sources)


def _specification_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    architecture, architecture_sources = _architecture(inputs)
    if architecture is not None:
        yield _Candidate(
            "specifications.architecture_type",
            architecture,
            "architecture_classification_from_exact_config",
            architecture_sources,
        )

    safetensors, sources = _safetensors(inputs)
    total = _integer(safetensors.get("total"))
    counts, _ = _dtype_counts(inputs)
    if total and total > 0 and (not counts or sum(counts.values()) == total):
        value = f"{total:,} total stored parameters (safetensors metadata)"
        rule = "parameter_count_from_safetensors_total"
        parameter_sources = list(
            _pointer(inputs.metadata_source_id, "/safetensors/total")
        )
        download_facts = _download_table_facts(inputs)
        if download_facts is not None and inputs.readme_source_id is not None:
            reported_total = next(
                (
                    item
                    for key, item in download_facts.values.items()
                    if "total params" in key
                ),
                None,
            )
            active = next(
                (
                    item
                    for key, item in download_facts.values.items()
                    if "activated params" in key
                ),
                None,
            )
            if reported_total and active:
                value += (
                    f"; README architecture row reports {reported_total} total model "
                    f"parameters, {active} activated per token"
                )
                rule = "moe_parameter_counts_from_safetensors_and_exact_readme_row"
                parameter_sources.append(
                    SourcePointer(
                        inputs.readme_source_id,
                        f"text:{download_facts.start}-{download_facts.end}",
                    )
                )
        yield _Candidate(
            "specifications.num_parameters",
            value,
            rule,
            tuple(parameter_sources),
        )

    context, context_rule, context_sources = _context(inputs)
    if context is not None:
        yield _Candidate(
            "specifications.context_length", context, context_rule, context_sources
        )

    precision, precision_sources = _precision(inputs)
    if precision is not None:
        yield _Candidate(
            "specifications.precision",
            precision,
            "stored_precision_from_safetensors_dtype_counts",
            precision_sources,
        )

    size, size_sources = _model_size(inputs)
    if size is not None:
        yield _Candidate(
            "specifications.model_size",
            size,
            "tensor_payload_from_safetensors_dtype_counts",
            size_sources,
        )

    input_output, modality_sources = _input_output(inputs)
    if input_output is not None:
        yield _Candidate(
            "specifications.input_output",
            input_output,
            "input_output_from_pipeline_architecture_and_target_stage",
            modality_sources,
        )


def _readme_training_data(inputs: _Inputs) -> tuple[str, tuple[SourcePointer, ...], str] | None:
    readme = inputs.readme
    source_id = inputs.readme_source_id
    if readme is None or source_id is None:
        return None
    is_olmo = _is_exact_family_target(inputs, "olmo2_1124")
    is_gemma = _is_exact_family_target(inputs, "gemma3")
    is_llama = _is_exact_family_target(inputs, "llama31")
    is_qwen = _is_exact_family_target(inputs, "qwen3")
    is_deepseek = _is_exact_family_target(inputs, "deepseek_v3")

    # OLMo instruction checkpoints explicitly enumerate their post-training
    # sources and stages in the release paragraph.  Select that paragraph only
    # for the post-trained target, never for the base checkpoint.
    if is_olmo and _target_stage(inputs) == "posttrained":
        release = _target_scoped_section_span(inputs, "release documentation")
        if release is not None:
            body, start, _ = release
            for text, relative_start, relative_end in _paragraphs(body):
                absolute_start = start + relative_start
                if (
                    _position_is_target_scoped(inputs, absolute_start)
                    and _model_label_matches(
                        inputs, text, section_stage="posttrained"
                    )
                    and re.search(r"(?i)dataset|data|fine.?tun|DPO|RLVR", text)
                ):
                    raw = body[relative_start:relative_end]
                    dataset_ids = sorted(
                        set(
                            re.findall(
                                r"https://huggingface\.co/datasets/([^\s)#?]+)",
                                raw,
                                re.I,
                            )
                        )
                    )
                    value = (
                        "Post-training dataset IDs named in the exact-target README: "
                        + ", ".join(dataset_ids)
                        if dataset_ids
                        else _clean_readme_text(text, limit=1_400)
                    )
                    return (
                        value,
                        (SourcePointer(source_id, f"text:{start + relative_start}-{start + relative_end}"),),
                        "training_data_from_exact_posttraining_readme_paragraph",
                    )

    # OLMo base checkpoints have narrowly scoped Stage 1/Stage 2 sections.
    stage_one = _target_scoped_section_span(
        inputs, "stage 1 initial pretraining"
    )
    stage_two = _target_scoped_section_span(inputs, "stage 2 fine tuning")
    if is_olmo and _target_stage(inputs) == "base" and stage_one is not None:
        selected = [stage_one]
        if stage_two is not None:
            selected.append(stage_two)
        datasets: list[str] = []
        for body, section_start, _ in selected:
            dataset_line = re.search(r"(?im)^\s*-\s*Dataset:\s*(.+?)\s*$", body)
            if dataset_line is not None and _position_is_target_scoped(
                inputs, section_start + dataset_line.start()
            ):
                datasets.append(_clean_readme_text(dataset_line.group(1)))
        pieces: list[str] = []
        if datasets:
            pieces.append("Named training mixtures: " + "; ".join(datasets) + ".")
        exact_size = next(iter(sorted(_size_tokens(inputs.catalog.target.model_id))), None)
        if exact_size is not None:
            target_line = re.search(
                rf"(?im)^\s*-\s*{re.escape(exact_size)}\s+Model:\s*(.+?)\s*$",
                stage_one[0],
            )
            if target_line is not None and _position_is_target_scoped(
                inputs, stage_one[1] + target_line.start()
            ):
                epochs = re.search(r"(?i)(~?[0-9.]+\s+epochs?)", target_line.group(1))
                if epochs is not None:
                    pieces.append(
                        f"The {exact_size.upper()} schedule covers {epochs.group(1)}."
                    )
        mix = re.search(r"(?im)^\s*-\s*Mix composition:\s*(.+?)\s*$", stage_two[0] if stage_two else "")
        if (
            mix is not None
            and stage_two is not None
            and _position_is_target_scoped(inputs, stage_two[1] + mix.start())
        ):
            percentage = re.search(r"([0-9]+%)", mix.group(1))
            prefix = (
                f"Second-stage allocation assigns {percentage.group(1)} to "
                if percentage is not None
                else "Second-stage allocation includes "
            )
            pieces.append(
                prefix
                + "quality-filtered material alongside academic, Q&A, instruction, "
                "and mathematics content."
            )
        if not pieces:
            return None
        value = " ".join(pieces)
        return (
            value,
            tuple(SourcePointer(source_id, f"text:{item[1]}-{item[2]}") for item in selected),
            "training_data_from_staged_pretraining_sections",
        )

    # Gemma cards expose one dedicated family training-data section.  The
    # exact 4B repository is the source, and the prose explicitly scopes the
    # description to "these models" and lists the target size in the same
    # section.
    training_dataset = _target_scoped_section_span(inputs, "training dataset")
    if is_gemma and training_dataset is not None:
        body, start, end = training_dataset
        components = []
        for label, rendered in (
            ("web documents", "web documents"),
            ("code", "code"),
            ("mathematics", "mathematics"),
            ("images", "images"),
        ):
            component = re.search(
                rf"(?im)^\s*[-*]?\s*\**{re.escape(label)}\**\s*:", body
            )
            if component is not None and _position_is_target_scoped(
                inputs, start + component.start()
            ):
                components.append(rendered)
        languages = re.search(r"(?i)(over|more than)\s+([0-9,]+)\s+languages", body)
        pieces = []
        if components:
            pieces.append("Publisher-listed source categories: " + ", ".join(components) + ".")
        if languages is not None and _position_is_target_scoped(
            inputs, start + languages.start()
        ):
            pieces.append(
                f"Language coverage is reported above {languages.group(2)} languages."
            )
        if not pieces:
            return None
        return (
            " ".join(pieces),
            (SourcePointer(source_id, f"text:{start}-{end}"),),
            "training_data_from_dedicated_readme_section",
        )

    # Llama's dedicated section distinguishes pretraining from fine-tuning in
    # adjacent sentences.  Do not attach fine-tuning data to the base target.
    training = _target_scoped_section_span(inputs, "training data")
    if is_llama and training is not None:
        body, start, _ = training
        scale = re.search(r"(?i)pretrained on\s+(~?[0-9.]+\s+trillion tokens)", body)
        if scale is not None and _position_is_target_scoped(
            inputs, start + scale.start()
        ):
            value = (
                f"Pretraining scale: {scale.group(1)} from publisher-described "
                "public-source data."
            )
            synthetic = re.search(
                r"(?i)(over|more than)\s+([0-9.]+[MBK]?)\s+synthetically generated examples",
                body,
            )
            if synthetic is not None and not _position_is_target_scoped(
                inputs, start + synthetic.start()
            ):
                synthetic = None
            if _target_stage(inputs) == "posttrained":
                value += " Fine-tuning sources include public instruction datasets"
                if synthetic is not None:
                    value += f" and more than {synthetic.group(2)} synthetic examples"
                value += "."
            return (
                value,
                (SourcePointer(source_id, f"text:{start}-{start + len(body)}"),),
                "training_data_from_stage_scoped_readme_overview",
            )

    # Qwen Base provides an explicit corpus bullet with both composition and
    # scale.  It is not projected onto the separate post-trained repository.
    if is_qwen and _target_stage(inputs) == "base":
        corpus = _line_span(
            readme,
            re.compile(r"(?im)^\s*-\s*\*\*Expanded Higher-Quality Pre-training Corpus:\*\*.+$"),
        )
        if corpus is not None:
            raw, start, end = corpus
            if not _position_is_target_scoped(inputs, start):
                corpus = None
        if corpus is not None:
            raw, start, end = corpus
            scale = re.search(r"(?i)([0-9.]+\s+trillion tokens)", raw)
            languages = re.search(r"(?i)([0-9,]+)\s+languages", raw)
            pieces = []
            if scale is not None:
                pieces.append(f"Pretraining scale: {scale.group(1)}")
            if languages is not None:
                pieces.append(f"language coverage: {languages.group(1)}")
            pieces.append(
                "content areas include code, STEM, reasoning, books, multilingual, "
                "and synthetic material"
            )
            return (
                "; ".join(pieces) + ".",
                (SourcePointer(source_id, f"text:{start}-{end}"),),
                "training_data_from_explicit_pretraining_corpus_bullet",
            )

    # DeepSeek's frozen README states the pretraining corpus at the exact V3
    # family level.  Both the base and post-trained checkpoints share that
    # explicitly described pretraining stage.
    deepseek = re.search(
        r"(?is)(We pre-train DeepSeek-V3 on\s+[^,\n]{1,240}?tokens)(?:,|\.)",
        readme,
    )
    if (
        is_deepseek
        and deepseek is not None
        and _position_is_target_scoped(inputs, deepseek.start(1))
    ):
        scale = re.search(r"(?i)([0-9.]+\s+trillion)\s+.*?tokens", deepseek.group(1))
        value = (
            f"Publisher-reported pretraining scale: {scale.group(1)} tokens; "
            "the corpus is described as diverse and quality-filtered."
            if scale is not None
            else "Publisher README reports a diverse, quality-filtered pretraining corpus."
        )
        return (
            value,
            (SourcePointer(source_id, f"text:{deepseek.start(1)}-{deepseek.end(1)}"),),
            "training_data_from_exact_family_pretraining_statement",
        )
    return None


def _training_size(inputs: _Inputs) -> tuple[str, tuple[SourcePointer, ...], str] | None:
    readme = inputs.readme
    source_id = inputs.readme_source_id
    if readme is None or source_id is None:
        return None
    target_name = inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    target_sizes = sorted(_size_tokens(target_name))
    is_gemma = _is_exact_family_target(inputs, "gemma3")

    # A row-oriented specification table, used by OLMo, binds the token count
    # to the exact model-size row.
    for table in _markdown_tables(readme):
        headers = tuple(_normalized_header(item) for item in table.headers)
        token_columns = [index for index, item in enumerate(headers) if item == "training tokens"]
        if len(token_columns) != 1:
            continue
        for cells, start, end in table.rows:
            if (
                len(cells) > token_columns[0]
                and cells
                and _model_label_matches(inputs, cells[0], section_stage="base")
            ):
                value = _clean_readme_text(cells[token_columns[0]])
                if value:
                    return (
                        f"{value} training tokens (exact target row in README)",
                        (SourcePointer(source_id, f"text:{start}-{end}"),),
                        "training_size_from_exact_model_table_row",
                    )

    # Gemma states the count for every size in one sentence; dynamically select
    # only the size token carried by the exact target ID.
    for size in (target_sizes if is_gemma else ()):
        match = re.search(
            rf"(?i)(?<![A-Za-z0-9]){re.escape(size)}\s+model was trained with\s+"
            r"([0-9][0-9.,]*\s+(?:trillion|billion|million)\s+tokens)",
            readme,
        )
        if match is not None and _position_is_target_scoped(inputs, match.start()):
            return (
                f"{size.upper()} model: {_clean_readme_text(match.group(1))}",
                (SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),),
                "training_size_from_exact_target_size_clause",
            )

    # Exact family statements used by DeepSeek, Llama, and Qwen.  Values are
    # copied from the matched source span rather than maintained in code.
    patterns = (
        (
            "deepseek_v3",
            re.compile(r"(?i)pre-?train(?:ed)?\s+DeepSeek-V3\s+on\s+([~0-9.]+\s*(?:T|trillion))\s+[^,.]{0,50}?tokens"),
        ),
        (
            "llama31",
            re.compile(r"(?i)Llama\s+3\.1\s+was pretrained on\s+([~0-9.]+\s*(?:T|trillion)\s+tokens)"),
        ),
        (
            "qwen3",
            re.compile(r"(?i)Qwen3\s+is pre-trained on\s+([~0-9.]+\s*(?:T|trillion)\s+tokens)"),
        ),
    )
    for family, pattern in patterns:
        if not _is_exact_family_target(inputs, family):
            continue
        match = pattern.search(readme)
        if match is None or not _position_is_target_scoped(inputs, match.start()):
            continue
        value = _clean_readme_text(match.group(1))
        if not value.casefold().endswith("tokens"):
            value += " tokens"
        if _target_stage(inputs) == "posttrained" and "Llama" in match.group(0):
            extra = re.search(r"(?i)fine-tuning data includes[^.]*?(over\s+[0-9.]+[MBK]?\s+synthetically generated examples)", readme)
            if extra is not None and _position_is_target_scoped(
                inputs, extra.start()
            ):
                value += "; fine-tuning includes " + _clean_readme_text(extra.group(1))
                sources = (
                    SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),
                    SourcePointer(source_id, f"text:{extra.start()}-{extra.end()}"),
                )
            else:
                sources = (SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),)
        else:
            sources = (SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),)
        return value, sources, "training_size_from_explicit_family_statement"
    return None


def _data_cutoff(inputs: _Inputs) -> tuple[str, tuple[SourcePointer, ...]] | None:
    if inputs.readme is None or inputs.readme_source_id is None:
        return None
    patterns = (
        re.compile(r"(?im)^\s*-?\s*\*\*Date cutoff:\*\*\s*(.+?)\s*$"),
        re.compile(r"(?im)^\s*\*\*Data Freshness:\*\*\s*(.+?)\s*$"),
        re.compile(
            r"(?im)^\s*\*\*Knowledge cutoff\s*:?\*\*\s*:?\s*(.+?)\s*$"
        ),
    )
    for pattern in patterns:
        match = pattern.search(inputs.readme)
        if match is not None and _position_is_target_scoped(inputs, match.start()):
            value = _clean_readme_text(match.group(1)).rstrip(".")
            if value:
                return value, (
                    SourcePointer(inputs.readme_source_id, f"text:{match.start()}-{match.end()}"),
                )
    return None


def _adaptations(inputs: _Inputs) -> tuple[str, tuple[SourcePointer, ...], str] | None:
    readme = inputs.readme
    source_id = inputs.readme_source_id
    if readme is None or source_id is None:
        return None
    is_olmo = _is_exact_family_target(inputs, "olmo2_1124")
    is_gemma = _is_exact_family_target(inputs, "gemma3")
    is_llama = _is_exact_family_target(inputs, "llama31")
    is_qwen = _is_exact_family_target(inputs, "qwen3")
    is_deepseek = _is_exact_family_target(inputs, "deepseek_v3")

    if _target_stage(inputs) == "posttrained":
        # Exact one-sentence fine-tuning declarations (Mistral and OLMo).
        for pattern in (
            re.compile(r"(?im)^The\s+[^\n]*Instruct[^\n]*is an instruct fine-tuned version of[^\n]*\.\s*$"),
        ):
            match = pattern.search(readme)
            if (
                match is not None
                and _position_is_target_scoped(inputs, match.start())
                and _model_label_matches(
                    inputs, match.group(0), section_stage="posttrained"
                )
            ):
                base = re.search(
                    r"(?i)fine-tuned version of\s+(?:the\s+)?(.+?)\.?$",
                    match.group(0).strip(),
                )
                value = (
                    f"Instruction fine-tuning was applied to {_clean_readme_text(base.group(1)).rstrip('.')}."
                    if base is not None
                    else "The exact target is an instruction-fine-tuned family checkpoint."
                )
                return (
                    value,
                    (SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),),
                    "adaptations_from_exact_posttraining_statement",
                )

        release = (
            _target_scoped_section_span(inputs, "release documentation")
            if is_olmo
            else None
        )
        if release is not None:
            body, start, _ = release
            for text, relative_start, relative_end in _paragraphs(body):
                if (
                    _position_is_target_scoped(inputs, start + relative_start)
                    and all(
                        marker in text.casefold()
                        for marker in ("supervised finetuning", "dpo", "rlvr")
                    )
                ):
                    return (
                        "Post-training stages: supervised fine-tuning, DPO, then RLVR.",
                        (
                            SourcePointer(
                                source_id,
                                f"text:{start + relative_start}-{start + relative_end}",
                            ),
                        ),
                        "adaptations_from_exact_posttraining_release_paragraph",
                    )

        # DeepSeek chat/post-trained checkpoint.  The base target is excluded by
        # the stage gate above.
        matches: list[re.Match[str]] = []
        if is_deepseek:
            for pattern in (
                re.compile(r"(?i)followed by Supervised Fine-Tuning and Reinforcement Learning stages[^.]*\."),
                re.compile(r"(?is)We introduce an innovative methodology to distill reasoning capabilities[^.]*?DeepSeek-V3[^.]*\."),
                ):
                match = pattern.search(readme)
                if match is not None and _position_is_target_scoped(
                    inputs, match.start()
                ):
                    matches.append(match)
        if len(matches) == 2:
            return (
                "Post-training uses supervised fine-tuning and reinforcement learning. "
                "The README also describes distilling long-chain-of-thought reasoning "
                "from a DeepSeek-R1-series model into DeepSeek-V3.",
                tuple(SourcePointer(source_id, f"text:{item.start()}-{item.end()}") for item in matches),
                "adaptations_from_posttraining_and_distillation_statements",
            )

        # Llama's architecture paragraph explicitly scopes SFT/RLHF to tuned
        # versions; the target ID supplies the instruction-tuned variant.
        match = (
            re.search(
                r"(?i)(The tuned versions use supervised fine-tuning \(SFT\) and reinforcement learning with human feedback \(RLHF\)[^.]*\.)",
                readme,
            )
            if is_llama
            else None
        )
        if match is not None and _position_is_target_scoped(
            inputs, match.start(1)
        ):
            return (
                "Instruction tuning combines SFT with RLHF for preference alignment, "
                "helpfulness, and safety.",
                (SourcePointer(source_id, f"text:{match.start(1)}-{match.end(1)}"),),
                "adaptations_from_tuned_variant_architecture_statement",
            )

        # Qwen exact-target overview carries an explicit training-stage label.
        overview = _summary_from_overview(inputs) if is_qwen else None
        if overview is not None:
            _, start, end = overview
            raw = readme[start:end]
            stage = re.search(r"(?im)^\s*-\s*Training Stage:\s*(.+?)\s*$", raw)
            if stage is not None and "post-training" in stage.group(1).casefold():
                return (
                    _clean_readme_text(stage.group(1)),
                    (SourcePointer(source_id, f"text:{start + stage.start()}-{start + stage.end()}"),),
                    "adaptations_from_exact_target_training_stage",
                )

        # Gemma exact IT repository plus family description explicitly identify
        # the instruction-tuned variant; no technique is inferred beyond that.
        if is_gemma:
            description = re.search(r"(?i)instruction-tuned\s+variants", readme)
            sentence = (
                _sentence_containing(
                    readme, description.start(), description.end()
                )
                if description is not None
                else None
            )
            if (
                description is not None
                and sentence is not None
                and _position_is_target_scoped(inputs, sentence[1])
                and _prose_scope_matches_target(
                    inputs,
                    sentence[0],
                    allow_family_size_omission=True,
                )
                and re.search(
                    r"(?i)(?:^|[-_.])(?:it|instruct)(?:$|[-_.])",
                    inputs.catalog.target.model_id.rsplit("/", 1)[-1],
                )
            ):
                return (
                    "Instruction-tuned variant (the frozen README does not specify the tuning recipe).",
                    (
                        *_pointer(inputs.metadata_source_id, "/id"),
                        SourcePointer(source_id, f"text:{sentence[1]}-{sentence[2]}"),
                    ),
                    "adaptation_stage_from_exact_it_title_and_family_description",
                )
    else:
        relation = _readme_base_relation(inputs)
        if relation is not None and relation[2] is not None:
            return (
                f"Derived from {relation[0]}; {relation[2]}.",
                relation[1],
                "adaptations_from_exact_readme_base_relation",
            )

        # A base README may list size-specific merge procedures.  Select only
        # the size carried by the exact target ID.
        for size in (
            sorted(_size_tokens(inputs.catalog.target.model_id)) if is_olmo else ()
        ):
            match = re.search(
                rf"(?im)^\s*-\s*{re.escape(size)}\s+Model:\s*"
                r"(?P<count>[0-9]+)\s+versions?\s+trained\s+on\s+"
                r"(?P<tokens>[0-9.]+[KMBT]?)\s+mix,\s*"
                r"merged via model souping\s*$",
                readme,
            )
            if match is not None and _position_is_target_scoped(
                inputs, match.start()
            ):
                return (
                    f"{match.group('count')} {size.upper()} variants trained on a "
                    f"{match.group('tokens')}-token mixture were "
                    "combined using model souping.",
                    (SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),),
                    "adaptations_from_exact_size_model_merging_statement",
                )
    return None


def _training_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    datasets = _card_data(inputs.metadata).get("datasets")
    if isinstance(datasets, str):
        metadata_values = [datasets]
    elif isinstance(datasets, list):
        metadata_values = [item.strip() for item in datasets if isinstance(item, str) and item.strip()]
    else:
        metadata_values = []
    metadata_values = list(dict.fromkeys(metadata_values))

    readme_data = _readme_training_data(inputs)
    if readme_data is not None:
        value, sources, rule = readme_data
        base_model_ids, _base_pointer = _base_model_ids(inputs.metadata)
        if (
            _target_stage(inputs) == "posttrained"
            and base_model_ids
            and rule
            in {
                "training_data_from_dedicated_readme_section",
                "training_data_from_exact_family_pretraining_statement",
            }
        ):
            value = "Publisher-described family/base pretraining context: " + value
        missing_metadata_values = [item for item in metadata_values if item not in value]
        if missing_metadata_values:
            value += " Declared Hugging Face dataset IDs: " + ", ".join(missing_metadata_values) + "."
            sources = (*sources, *_pointer(inputs.metadata_source_id, "/cardData/datasets"))
        yield _Candidate("training_context.training_data", value, rule, tuple(sources))
    elif metadata_values:
        yield _Candidate(
            "training_context.training_data",
            "Hugging Face dataset IDs declared in card metadata: " + ", ".join(metadata_values),
            "training_datasets_from_card_metadata",
            _pointer(inputs.metadata_source_id, "/cardData/datasets"),
        )

    size = _training_size(inputs)
    if size is not None:
        value, sources, rule = size
        base_model_ids, _base_pointer = _base_model_ids(inputs.metadata)
        if (
            _target_stage(inputs) == "posttrained"
            and base_model_ids
            and readme_data is not None
            and readme_data[2] == "training_data_from_dedicated_readme_section"
        ):
            value = "Publisher-described family/base pretraining scale: " + value
        yield _Candidate("training_context.training_data_size", value, rule, sources)

    cutoff = _data_cutoff(inputs)
    if cutoff is not None:
        yield _Candidate(
            "training_context.data_cutoff",
            cutoff[0],
            "data_cutoff_from_explicit_readme_label",
            cutoff[1],
        )

    adaptations = _adaptations(inputs)
    if adaptations is not None:
        value, sources, rule = adaptations
        yield _Candidate("training_context.adaptations", value, rule, sources)


def _score_value(value: str) -> int | float | str | None:
    cleaned = _clean_readme_text(value).strip()
    if not cleaned or cleaned.casefold() in {"-", "n/a", "na", "n/c", "none"}:
        return None
    numeric = cleaned.replace(",", "")
    if re.fullmatch(r"[-+]?\d+", numeric):
        return int(numeric)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)", numeric):
        return float(numeric)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)\s*%", numeric):
        return cleaned
    return None


def _benchmark_qualifiers(
    value: str,
) -> tuple[str, str | None, str | None, str | None]:
    """Split only closed, unambiguous benchmark-name qualifiers.

    README tables commonly place metrics, shot settings, or dataset splits in
    one trailing parenthetical.  Unknown qualifiers stay inside the benchmark
    name so strings such as ``MMLU (Pro COT)``, ``XQuAD (all)``, and
    ``MMMU (pt)`` are not guessed into the wrong schema field.
    """

    cleaned = _clean_readme_text(value)
    match = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", cleaned)
    if match is None:
        return cleaned, None, None, None

    metric: str | None = None
    setting: str | None = None
    split: str | None = None
    pieces = tuple(
        item.strip() for item in match.group(2).split(",") if item.strip()
    )
    if not pieces:
        return cleaned, None, None, None
    for piece in pieces:
        shot_match = re.fullmatch(r"(?i)([0-9]+)\s*[- ]?\s*shots?", piece)
        if shot_match is not None and setting is None:
            setting = f"{int(shot_match.group(1))} shots"
            continue
        if piece.casefold() in {"train", "test", "dev", "val", "validation"} \
                and split is None:
            split = piece
            continue
        if (
            re.fullmatch(
                r"(?i)(?:acc(?:uracy)?\.?|exact match|em|f1|chrf(?:\+\+)?|"
                r"bleu|rouge(?:-[a-z0-9]+)?|pass@[0-9]+|recall(?:@[0-9]+)?|"
                r"precision(?:@[0-9]+)?|bpb|perplexity|ppl|win rate|score)",
                piece,
            )
            or ("/" in piece and re.fullmatch(r"[A-Za-z0-9_.+@/-]+", piece))
        ) and metric is None:
            metric = piece
            continue
        return cleaned, None, None, None
    return match.group(1).strip(), metric, setting, split


def _setting_text(shots: str | None, headings: Iterable[str]) -> str:
    if shots is not None and shots.strip():
        cleaned = _clean_readme_text(shots)
        if cleaned.casefold() not in {"-", "n/a", "na", "none"}:
            if "shot" in cleaned.casefold():
                return cleaned
            return f"{cleaned} shots"
    context = next(
        (
            _clean_readme_text(item)
            for item in reversed(tuple(headings))
            if _heading_matches(item, "benchmark", "performance", "evaluation")
        ),
        "README table",
    )
    return f"{context}; setting not stated"


def _row_oriented_scores(
    inputs: _Inputs,
    table: _ReadmeTable,
) -> tuple[_ScoreCandidate, ...]:
    headers = tuple(_normalized_header(item) for item in table.headers)
    if not headers or headers[0] != "model":
        return ()
    if not (
        any(_heading_matches(item, "evaluation", "performance") for item in table.headings)
        or any("benchmark" in item for item in headers)
    ):
        return ()
    section_stage = _table_section_stage(table.headings)
    matched_rows = [
        (cells, start, end)
        for cells, start, end in table.rows
        if cells and _model_label_matches(inputs, cells[0], section_stage=section_stage)
    ]
    target_label = _normalized_header(
        inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    )
    exact_rows = [
        row
        for row in matched_rows
        if _normalized_header(row[0][0]) == target_label
    ]
    if exact_rows:
        matched_rows = exact_rows
    if len(matched_rows) != 1:
        return ()
    cells, row_start, row_end = matched_rows[0]
    skip = {
        "model",
        "train flops",
        "training flops",
        "params",
        "total params",
        "activated params",
        "context length",
        "download",
        "architecture",
        "average",
        "average score",
        "avg",
        "overall",
    }
    scores = []
    for index in range(1, min(len(table.headers), len(cells))):
        benchmark, metric, setting, split = _benchmark_qualifiers(
            table.headers[index]
        )
        if _normalized_header(benchmark) in skip:
            continue
        score = _score_value(cells[index])
        if score is None:
            continue
        row = {
            "benchmark": benchmark,
            "metric": metric or "README-reported score",
            "score": score,
            "setting": setting or _setting_text(None, table.headings),
        }
        if split is not None:
            row["split"] = split
        scores.append(_ScoreCandidate(row, row_start, row_end))
    return tuple(scores)


def _column_oriented_scores(
    inputs: _Inputs,
    table: _ReadmeTable,
) -> tuple[_ScoreCandidate, ...]:
    normalized = tuple(_normalized_header(item) for item in table.headers)
    benchmark_columns = [
        index for index, item in enumerate(normalized) if item in {"benchmark", "benchmark metric"}
    ]
    if len(benchmark_columns) != 1:
        return ()
    section_stage = _table_section_stage(table.headings)
    model_columns = [
        index
        for index, item in enumerate(table.headers)
        if _model_label_matches(inputs, item, section_stage=section_stage)
    ]
    target_label = _normalized_header(
        inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    )
    exact_model_columns = [
        index
        for index in model_columns
        if _normalized_header(table.headers[index]) == target_label
    ]
    if exact_model_columns:
        model_columns = exact_model_columns
    if len(model_columns) != 1:
        return ()
    benchmark_column = benchmark_columns[0]
    model_column = model_columns[0]
    metric_column = next(
        (index for index, item in enumerate(normalized) if item == "metric"), None
    )
    language_column = next(
        (index for index, item in enumerate(normalized) if item == "language"), None
    )
    shots_column = next(
        (index for index, item in enumerate(normalized) if item in {"shots", "shot"}), None
    )
    split_column = next(
        (index for index, item in enumerate(normalized) if item in {"split", "dataset split"}),
        None,
    )
    scores = []
    for cells, row_start, row_end in table.rows:
        if max(benchmark_column, model_column) >= len(cells):
            continue
        benchmark, embedded_metric, embedded_setting, embedded_split = (
            _benchmark_qualifiers(cells[benchmark_column])
        )
        if not benchmark or _normalized_header(benchmark) in {
            "architecture",
            "activated params",
            "average",
            "average score",
            "avg",
            "overall",
            "total params",
            "params",
        }:
            continue
        score = _score_value(cells[model_column])
        if score is None:
            continue
        metric = embedded_metric
        shots = cells[shots_column] if shots_column is not None and shots_column < len(cells) else None
        if metric_column is not None and metric_column < len(cells):
            metric_cell = _clean_readme_text(cells[metric_column])
            if "shot" in metric_cell.casefold():
                shots = metric_cell
            elif metric_cell:
                if metric is not None and metric.casefold() != metric_cell.casefold():
                    continue
                metric = metric_cell
        explicit_setting = _setting_text(shots, ()) if shots else None
        if (
            embedded_setting is not None
            and explicit_setting is not None
            and embedded_setting.casefold() != explicit_setting.casefold()
        ):
            continue
        setting = embedded_setting or explicit_setting or _setting_text(None, table.headings)
        split = embedded_split
        if split_column is not None and split_column < len(cells):
            explicit_split = _clean_readme_text(cells[split_column])
            if explicit_split:
                if split is not None and split.casefold() != explicit_split.casefold():
                    continue
                split = explicit_split
        if language_column is not None and language_column < len(cells):
            language = _clean_readme_text(cells[language_column])
            if language:
                setting = f"{setting}; language: {language}"
        row = {
            "benchmark": benchmark,
            "metric": metric or "README-reported score",
            "score": score,
            "setting": setting,
        }
        if split is not None:
            row["split"] = split
        scores.append(_ScoreCandidate(row, row_start, row_end))
    return tuple(scores)


def _benchmark_scores(
    inputs: _Inputs,
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[SourcePointer, ...],
    tuple[PublicationConflictRecord, ...],
]:
    if inputs.readme is None or inputs.readme_source_id is None:
        return (), (), ()
    retained: dict[
        tuple[str, str, str, str],
        tuple[int, dict[str, Any], SourcePointer],
    ] = {}
    conflicted: dict[
        tuple[str, str, str, str],
        tuple[set[SourcePointer], set[str]],
    ] = {}
    ordinal = 0
    # The frozen source bundle already bounds README size.  Preserve every
    # qualifying exact-target relation instead of imposing a publication cap.
    tables = (*_markdown_tables(inputs.readme), *_html_tables(inputs.readme))
    for table in sorted(tables, key=lambda item: item.start):
        parsed = _row_oriented_scores(inputs, table) or _column_oriented_scores(inputs, table)
        for parsed_score in parsed:
            score = parsed_score.value
            pointer = SourcePointer(
                inputs.readme_source_id,
                f"text:{parsed_score.start}-{parsed_score.end}",
            )
            key = (
                score["benchmark"].casefold(),
                score["metric"].casefold(),
                str(score["setting"]).casefold(),
                str(score.get("split", "")).casefold(),
            )
            if key in conflicted:
                conflict_sources, conflict_hashes = conflicted[key]
                conflict_sources.add(pointer)
                conflict_hashes.add(_digest(score))
                continue
            previous = retained.get(key)
            if previous is None:
                retained[key] = (ordinal, score, pointer)
                ordinal += 1
                continue
            if previous[1]["score"] == score["score"]:
                # An exact duplicate relation adds no information.
                continue
            # Two values for the same benchmark coordinates are ambiguous. Drop
            # the relation entirely rather than selecting by README order.
            del retained[key]
            conflicted[key] = (
                {previous[2], pointer},
                {_digest(previous[1]), _digest(score)},
            )
    ordered = tuple(sorted(retained.values(), key=lambda item: item[0]))
    scores = tuple(item[1] for item in ordered)
    pointers = tuple(dict.fromkeys(item[2] for item in ordered))
    conflicts = tuple(
        PublicationConflictRecord(
            field_path="evaluation.benchmark_scores",
            reason="benchmark_coordinate_scores_disagree",
            sources=tuple(sources),
            value_sha256s=tuple(value_hashes),
        )
        for _, (sources, value_hashes) in sorted(conflicted.items())
    )
    return scores, pointers, conflicts


def _safety_evaluation(
    inputs: _Inputs,
    scores: Iterable[Mapping[str, Any]],
    score_sources: tuple[SourcePointer, ...],
) -> tuple[str, tuple[SourcePointer, ...], str] | None:
    if inputs.readme is None or inputs.readme_source_id is None:
        return None
    for score in scores:
        if _normalized_header(str(score.get("benchmark", ""))) == "safety":
            return (
                "README performance table reports Safety score "
                f"{score['score']} ({score['metric']}; {score['setting']}).",
                score_sources,
                "safety_evaluation_from_exact_target_score_row",
            )

    outer = (
        _target_scoped_section_span(inputs, "ethics and safety")
        if _is_exact_family_target(inputs, "gemma3")
        else None
    )
    if outer is not None:
        outer_body, outer_start, _ = outer
        inner = _target_scoped_section_span(
            inputs,
            "evaluation results",
            text=outer_body,
            offset=outer_start,
        )
        if inner is not None:
            body, inner_start, inner_end = inner
            value = _clean_readme_text(body, limit=1_200)
            required_markers = (
                "child safety",
                "content safety",
                "representational harms",
                "previous gemma",
                "ungrounded inference",
                "without safety filters",
                "english language prompts",
                "all model sizes",
            )
            absolute_inner_start = outer_start + inner_start
            if (
                value
                and all(marker in value.casefold() for marker in required_markers)
                and _markers_are_target_scoped(
                    inputs,
                    body,
                    absolute_inner_start,
                    required_markers,
                )
            ):
                return (
                    "The README reports Gemma-family, all-model-size improvements over "
                    "earlier releases for child safety, content safety, representational "
                    "harms, and ungrounded inference. The tests omitted safety filters "
                    "and used English prompts; the source does not provide PT/IT- or "
                    "checkpoint-specific results.",
                    (
                        SourcePointer(
                            inputs.readme_source_id,
                            f"text:{outer_start + inner_start}-{outer_start + inner_end}",
                        ),
                    ),
                    "safety_evaluation_from_scoped_readme_results_section",
                )

    responsibility = (
        _target_scoped_section_span(inputs, "responsibility & safety")
        if _is_exact_family_target(inputs, "llama31")
        else None
    )
    if responsibility is None:
        return None
    responsibility_body, responsibility_start, _ = responsibility
    evaluations = _target_scoped_section_span(
        inputs,
        "evaluations",
        text=responsibility_body,
        offset=responsibility_start,
    )
    critical = _target_scoped_section_span(
        inputs,
        "critical and other risks",
        text=responsibility_body,
        offset=responsibility_start,
    )
    if evaluations is None or critical is None:
        return None
    evaluation_body, evaluation_start, evaluation_end = evaluations
    critical_body, critical_start, critical_end = critical
    required_evaluation_markers = (
        "adversarial evaluation",
        "red teaming",
    )
    required_risk_markers = (
        "cbrne",
        "child safety",
        "cyber",
    )
    combined_evaluation = evaluation_body.casefold()
    combined_risks = critical_body.casefold()
    if not all(item in combined_evaluation for item in required_evaluation_markers):
        return None
    if not all(item in combined_risks for item in required_risk_markers):
        return None
    if not _markers_are_target_scoped(
        inputs,
        evaluation_body,
        responsibility_start + evaluation_start,
        required_evaluation_markers,
    ) or not _markers_are_target_scoped(
        inputs,
        critical_body,
        responsibility_start + critical_start,
        required_risk_markers,
    ):
        return None
    return (
        "The publisher reports family/system-level adversarial safety evaluation and "
        "recurring red teaming covering CBRNE, child-safety, and cyber risks; this "
        "section does not state a checkpoint-specific numeric safety score.",
        (
            SourcePointer(
                inputs.readme_source_id,
                f"text:{responsibility_start + evaluation_start}-"
                f"{responsibility_start + evaluation_end}",
            ),
            SourcePointer(
                inputs.readme_source_id,
                f"text:{responsibility_start + critical_start}-"
                f"{responsibility_start + critical_end}",
            ),
        ),
        "safety_evaluation_from_scoped_family_risk_sections",
    )


def _evaluation_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    scores, score_sources, _conflicts = _benchmark_scores(inputs)
    if scores:
        sample = "; ".join(
            f"{item['benchmark']}: {item['score']}"
            for item in scores[:3]
        )
        yield _Candidate(
            "evaluation.results_summary",
            f"The frozen README provides {len(scores)} exact-target benchmark scores; "
            f"examples: {sample}.",
            "results_summary_from_exact_target_score_selection",
            score_sources,
        )
        yield _Candidate(
            "evaluation.benchmark_scores",
            list(scores),
            "benchmark_scores_from_exact_target_readme_rows_or_columns",
            score_sources,
        )

    safety = _safety_evaluation(inputs, scores, score_sources)
    if safety is not None:
        value, sources, rule = safety
        if not scores:
            yield _Candidate(
                "evaluation.results_summary",
                "The frozen README reports family-level qualitative safety-evaluation "
                "results; see safety_evals.",
                "results_summary_from_scoped_safety_evaluation",
                sources,
            )
        yield _Candidate("evaluation.safety_evals", value, rule, sources)


def _weight_files(metadata: Mapping[str, Any] | None) -> tuple[str, ...]:
    if metadata is None or not isinstance(metadata.get("siblings"), list):
        return ()
    names = []
    for item in metadata["siblings"]:
        name = item.get("rfilename") if isinstance(item, Mapping) else item
        if isinstance(name, str) and re.search(r"\.(?:bin|gguf|safetensors)$", name, re.I):
            names.append(name)
    return tuple(sorted(set(names)))


def _access_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    metadata = inputs.metadata
    if metadata is None:
        return
    if not isinstance(metadata.get("private"), bool) or "gated" not in metadata:
        return
    private = metadata.get("private") is True
    gated = metadata.get("gated") not in (None, False, "false")
    weights = _weight_files(metadata)
    if private:
        access = "Private Hugging Face repository"
    elif gated:
        access = "Gated Hugging Face repository"
    else:
        access = "Public Hugging Face repository"
    access += " with declared weight files" if weights else "; no weight file declared in frozen metadata"
    yield _Candidate(
        "access_and_adoption.access_type",
        access,
        "access_from_repository_flags_and_weight_listing",
        (
            *_pointer(inputs.metadata_source_id, "/private"),
            *_pointer(inputs.metadata_source_id, "/gated"),
            *_pointer(inputs.metadata_source_id, "/siblings"),
        ),
    )
    for field in ("downloads", "likes"):
        value = _integer(metadata.get(field))
        if value is not None:
            yield _Candidate(
                f"access_and_adoption.{field}",
                f"{value:,} at frozen Hugging Face metadata snapshot",
                f"{field}_from_frozen_metadata",
                _pointer(inputs.metadata_source_id, f"/{field}"),
            )


def _bibtex_blocks(readme: str) -> tuple[tuple[str, int, int], ...]:
    blocks = []
    for start_match in _BIBTEX_START_RE.finditer(readme):
        depth = 0
        opened = False
        end = None
        for index in range(start_match.start(), min(len(readme), start_match.start() + 20_000)):
            character = readme[index]
            if character == "{":
                depth += 1
                opened = True
            elif character == "}" and opened:
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            continue
        blocks.append((readme[start_match.start() : end].strip(), start_match.start(), end))
    return tuple(blocks)


def _technical_report(inputs: _Inputs) -> tuple[str | None, tuple[SourcePointer, ...]]:
    if inputs.readme is None or inputs.readme_source_id is None:
        return None, ()
    tagged = {
        item.split(":", 1)[1]
        for item in _tags(inputs.metadata)
        if item.startswith("arxiv:") and _ARXIV_ID_RE.fullmatch(item.split(":", 1)[1])
    }
    matches = []
    for block, start, end in _bibtex_blocks(inputs.readme):
        ids = set(_ARXIV_ID_RE.findall(block)) & tagged
        if len(ids) == 1:
            matches.append((next(iter(ids)), start, end))
    unique = {(identifier, start, end) for identifier, start, end in matches}
    identifiers = {item[0] for item in unique}
    if len(identifiers) != 1:
        return None, ()
    identifier = next(iter(identifiers))
    start = min(item[1] for item in unique)
    end = max(item[2] for item in unique)
    return (
        f"https://arxiv.org/abs/{identifier}",
        (
            SourcePointer(inputs.readme_source_id, f"text:{start}-{end}"),
            *_pointer(inputs.metadata_source_id, "/tags"),
        ),
    )


def _explicit_technical_report(
    inputs: _Inputs,
) -> tuple[str, tuple[SourcePointer, ...]] | None:
    """Resolve a uniquely labeled technical-report link in the exact README."""

    if inputs.readme is None or inputs.readme_source_id is None:
        return None
    readme = inputs.readme
    source_id = inputs.readme_source_id
    candidates: dict[str, list[SourcePointer]] = {}

    for match in _MARKDOWN_LINK_RE.finditer(readme):
        if (
            not _heading_matches(match.group(1), "technical report")
            or not _link_label_matches_target(inputs, match.group(1))
        ):
            continue
        url = _resolved_readme_link(inputs, match.group(2))
        if url is not None:
            candidates.setdefault(url, []).append(
                SourcePointer(source_id, f"text:{match.start()}-{match.end()}")
            )

    definitions: dict[str, tuple[str, int, int]] = {}
    for match in re.finditer(
        r"(?im)^\s*\[(?P<key>[^]\n]+)\]\s*:\s*"
        r"(?P<url>https://[^\s]+)\s*$",
        readme,
    ):
        definitions[_normalized_header(match.group("key"))] = (
            match.group("url").rstrip(".,;"),
            match.start(),
            match.end(),
        )
    for match in re.finditer(
        r"\[(?P<label>[^]\n]*technical\s+report[^]\n]*)\]"
        r"\[(?P<key>[^]\n]+)\]",
        readme,
        re.I,
    ):
        if not _link_label_matches_target(inputs, match.group("label")):
            continue
        definition = definitions.get(_normalized_header(match.group("key")))
        if definition is None:
            continue
        url = _resolved_readme_link(inputs, definition[0])
        if url is None:
            continue
        candidates.setdefault(url, []).extend(
            (
                SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),
                SourcePointer(
                    source_id,
                    f"text:{definition[1]}-{definition[2]}",
                ),
            )
        )
    if len(candidates) != 1:
        return None
    url, pointers = next(iter(candidates.items()))
    return url, tuple(sorted(set(pointers)))


def _repo_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _github_repository(inputs: _Inputs) -> tuple[str | None, tuple[SourcePointer, ...]]:
    if inputs.readme is None or inputs.readme_source_id is None:
        return None, ()
    target_namespace, target_name = inputs.catalog.target.model_id.split("/", 1)
    candidates: list[tuple[int, str, int, int]] = []

    def consider(label: str, url: str, start: int, end: int) -> None:
        url = url.rstrip(".,;")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc.casefold() != "github.com":
            return
        parts = [item for item in parsed.path.split("/") if item]
        if len(parts) != 2:
            return
        owner, repository = parts
        repository = repository[:-4] if repository.casefold().endswith(".git") else repository
        canonical = f"https://github.com/{owner}/{repository}"
        owner_score = 0
        if _repo_key(owner) == _repo_key(target_namespace):
            owner_score = 5
        target_key = _repo_key(target_name)
        repo_key = _repo_key(repository)
        relation_score = 0
        # A family repository may be a strict prefix of a checkpoint name
        # (Qwen3 for Qwen3-8B, for example).  The reverse direction denotes an
        # ancillary repository such as ``<target>-evaluation`` and is not the
        # target's code repository.
        if repo_key and target_key.startswith(repo_key):
            relation_score += 5
        elif (
            re.fullmatch(r"mistralai/Mistral-7B(?:-Instruct)?-v0\.3", inputs.catalog.target.model_id, re.I)
            and _repo_key(owner) == "mistralai"
            and repo_key == "mistralinference"
        ):
            relation_score += 4
        if relation_score == 0:
            return
        score = relation_score + owner_score
        if _repo_key(label) in {"github", "code", "repository", "coderepository", "sourcecode"}:
            score += 6
        if score >= 5:
            candidates.append((score, canonical, start, end))

    for match in _MARKDOWN_LINK_RE.finditer(inputs.readme):
        consider(match.group(1).strip(), match.group(2), match.start(), match.end())
    for match in _BARE_GITHUB_RE.finditer(inputs.readme):
        consider("", match.group(0), match.start(), match.end())
    if not candidates:
        return None, ()
    candidates.sort(key=lambda item: (-item[0], len(item[1]), item[1], item[2]))
    _score, url, start, end = candidates[0]
    return url, (SourcePointer(inputs.readme_source_id, f"text:{start}-{end}"),)


def _link_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    if inputs.readme_uri and inputs.readme_source_id:
        pinned = inputs.readme_uri.replace("/resolve/", "/blob/", 1)
        yield _Candidate(
            "links.model_card",
            pinned,
            "model_card_from_pinned_readme_source",
            (SourcePointer(inputs.readme_source_id, "source_uri"),),
        )

    explicit_report = _explicit_technical_report(inputs)
    report: str | None = None
    report_sources: tuple[SourcePointer, ...] = ()
    if explicit_report is not None:
        yield _Candidate(
            "links.tech_report",
            explicit_report[0],
            "technical_report_from_explicit_readme_link",
            explicit_report[1],
        )
    else:
        report, report_sources = _technical_report(inputs)
    if explicit_report is None and report is not None:
        yield _Candidate(
            "links.tech_report",
            report,
            "technical_report_from_tagged_readme_bibtex",
            report_sources,
        )

    repository, repository_sources = _github_repository(inputs)
    if repository is not None:
        yield _Candidate(
            "links.code_repository",
            repository,
            "code_repository_from_explicit_readme_link",
            repository_sources,
        )

    if inputs.readme is not None and inputs.readme_source_id is not None:
        blocks = _bibtex_blocks(inputs.readme)
        if len(blocks) == 1:
            block, start, end = blocks[0]
            yield _Candidate(
                "links.citation",
                block,
                "citation_from_unique_readme_bibtex_entry",
                (SourcePointer(inputs.readme_source_id, f"text:{start}-{end}"),),
            )


def _all_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    yield from _target_candidates(inputs)
    yield from _identity_candidates(inputs)
    yield from _readme_identity_candidates(inputs)
    yield from _lineage_candidates(inputs)
    yield from _specification_candidates(inputs)
    yield from _training_candidates(inputs)
    yield from _evaluation_candidates(inputs)
    yield from _access_candidates(inputs)
    yield from _link_candidates(inputs)


def _publication_conflicts(
    inputs: _Inputs,
) -> tuple[PublicationConflictRecord, ...]:
    conflicts: list[PublicationConflictRecord] = []
    explicit_bases, tagged_bases = _base_model_surfaces(inputs.metadata)
    if explicit_bases and tagged_bases and explicit_bases != tagged_bases:
        if inputs.metadata_source_id is None:
            raise PublicationSourceError(
                "conflicting metadata has no frozen source identity"
            )
        conflicts.append(
            PublicationConflictRecord(
                field_path="lineage.base_models",
                reason="metadata_base_model_declarations_disagree",
                sources=(
                    SourcePointer(
                        inputs.metadata_source_id,
                        "/cardData/base_model",
                    ),
                    SourcePointer(inputs.metadata_source_id, "/tags"),
                ),
                value_sha256s=(
                    _digest(list(explicit_bases)),
                    _digest(list(tagged_bases)),
                ),
            )
        )
    _scores, _score_sources, score_conflicts = _benchmark_scores(inputs)
    conflicts.extend(score_conflicts)
    return tuple(conflicts)


def _validated_withheld_fields(withheld_fields: Iterable[str]) -> tuple[str, ...]:
    if isinstance(withheld_fields, (str, bytes)):
        raise PublicationSourceError(
            "withheld_fields must be a sorted iterable of publication field paths"
        )
    try:
        paths = tuple(withheld_fields)
    except TypeError as exc:
        raise PublicationSourceError(
            "withheld_fields must be a sorted iterable of publication field paths"
        ) from exc
    if any(
        not isinstance(path, str) or path not in FIELD_PATH_SET
        for path in paths
    ):
        raise PublicationSourceError(
            "withheld_fields contains an unknown publication field path"
        )
    if paths != tuple(sorted(set(paths))):
        raise PublicationSourceError(
            "withheld_fields must be sorted and contain no duplicates"
        )
    return paths


def enrich_publication_card(
    catalog: SourceDocumentCatalog,
    card: Mapping[str, Any] | None = None,
    *,
    withheld_fields: Iterable[str] = (),
) -> PublicationEnrichmentResult:
    """Enrich a seven-section card from one verified, frozen source catalog.

    Existing specified values win over derived candidates, except that an exact
    publisher ``Model developer`` label upgrades the matching Hugging Face
    metadata author/namespace to the publisher's display name. ``Not specified``
    is treated as an invitation to enrich, while ``Not applicable`` remains an
    explicit author decision. Exact target identity conflicts are rejected. The
    returned provenance is intentionally separate from the public card.
    """

    inputs = _catalog_inputs(catalog)
    withheld = frozenset(_validated_withheld_fields(withheld_fields))
    if card is None:
        output = blank_publication_card()
    else:
        validate_publication_card(card)
        output = deepcopy(dict(card))

    for field_path, expected in (
        ("identity.model_id", catalog.target.model_id),
        ("identity.version", catalog.target.revision),
    ):
        current = get_field(output, field_path, NOT_SPECIFIED)
        if _specified(current) and current != expected:
            raise PublicationSourceError(
                f"{field_path} conflicts with the verified catalog target"
            )

    conflicts = _publication_conflicts(inputs)
    blocked_fields = {
        conflict.field_path
        for conflict in conflicts
        if conflict.reason == "metadata_base_model_declarations_disagree"
    }
    # Conflicts override both derived candidates and caller-supplied draft
    # values.  Otherwise a pre-populated card could preserve an unresolved
    # relation even though this run correctly recorded the disagreement.
    if "lineage.base_models" in blocked_fields:
        output["lineage"].pop("base_models", None)
    provenance: list[PublicationFieldProvenance] = []
    metadata_author = _string((inputs.metadata or {}).get("author"))
    for candidate in _all_candidates(inputs):
        if candidate.field_path in withheld or candidate.field_path in blocked_fields:
            continue
        current = get_field(output, candidate.field_path, NOT_SPECIFIED)
        explicit_developer_upgrade = (
            candidate.field_path == "identity.developed_by"
            and candidate.rule == "developer_from_explicit_readme_label"
            and metadata_author is not None
            and current == metadata_author
            and candidate.value != current
        )
        if (_specified(current) and not explicit_developer_upgrade) \
                or current == NOT_APPLICABLE:
            continue
        set_field(output, candidate.field_path, candidate.value)
        provenance.append(
            PublicationFieldProvenance(
                field_path=candidate.field_path,
                rule_name=_rule(candidate.rule),
                sources=candidate.sources,
            )
        )
    assert_no_source_excerpt(output, catalog)
    validate_publication_card(output)
    return PublicationEnrichmentResult(output, tuple(provenance), conflicts)


def replay_publication_enrichment(
    catalog: SourceDocumentCatalog,
    base_card: Mapping[str, Any] | None = None,
    *,
    withheld_fields: Iterable[str] = (),
    expected: PublicationEnrichmentResult | None = None,
) -> PublicationEnrichmentResult:
    """Replay deterministic enrichment and optionally verify an exact result.

    ``base_card`` and ``withheld_fields`` are the complete replay inputs beyond
    the frozen catalog.  When ``expected`` is supplied, both its public card
    and its typed provenance must match exactly; a mismatch fails closed.
    """

    if expected is not None and not isinstance(expected, PublicationEnrichmentResult):
        raise TypeError("expected must be a PublicationEnrichmentResult")
    replayed = enrich_publication_card(
        catalog,
        base_card,
        withheld_fields=withheld_fields,
    )
    if expected is not None and replayed.card != expected.card:
        raise PublicationSourceError(
            "publication enrichment replay card does not match the expected card"
        )
    if expected is not None and replayed.provenance != expected.provenance:
        raise PublicationSourceError(
            "publication enrichment replay provenance does not match the expected provenance"
        )
    if expected is not None and replayed.conflicts != expected.conflicts:
        raise PublicationSourceError(
            "publication enrichment replay conflicts do not match the expected conflicts"
        )
    return replayed


__all__ = [
    "PUBLICATION_SOURCE_RULESET",
    "PUBLICATION_SOURCE_RULE_NAMES",
    "PUBLICATION_CONFLICT_VERSION",
    "SOURCE_EXCERPT_MIN_COMPACT_CHARS",
    "SOURCE_EXCERPT_MIN_WORDS",
    "PublicationEnrichmentResult",
    "PublicationConflictRecord",
    "PublicationFieldProvenance",
    "PublicationSourceError",
    "SourcePointer",
    "assert_no_source_excerpt",
    "enrich_publication_card",
    "replay_publication_enrichment",
]
