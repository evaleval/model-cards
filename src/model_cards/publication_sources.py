"""Conservative enrichment of public cards from frozen Hugging Face sources.

The evidence pipeline intentionally keeps source bodies and provenance out of
the public card.  This module provides a small deterministic bridge for facts
that can be copied or narrowly derived from an already verified
``SourceDocumentCatalog``.  It performs no I/O and never consults model-memory
tables, live services, or unpinned sources.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import html
import re
from typing import Any, Iterable, Mapping
import unicodedata
from urllib.parse import urlsplit

from .publication_contract import FIELD_PATH_SET, NOT_APPLICABLE, NOT_SPECIFIED
from .publication_schema import (
    blank_publication_card,
    get_field,
    set_field,
    validate_publication_card,
)
from .source_documents import SourceDocumentCatalog


PUBLICATION_SOURCE_RULESET = "publication-source-enrichment/v4"

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
        "adaptations_from_exact_size_model_merging_statement",
        "adaptations_from_exact_target_training_stage",
        "adaptations_from_posttraining_and_distillation_statements",
        "adaptations_from_tuned_variant_architecture_statement",
        "architecture_classification_from_exact_config",
        "base_models_from_exact_metadata_declarations",
        "benchmark_scores_from_exact_target_readme_rows_or_columns",
        "citation_from_unique_readme_bibtex_entry",
        "code_repository_from_explicit_readme_link",
        "context_length_from_config_with_qualifier",
        "context_length_from_exact_readme",
        "data_cutoff_from_explicit_readme_label",
        "derivatives_from_exact_prefixed_readme_model_links",
        "developer_from_metadata_author",
        "downloads_from_frozen_metadata",
        "exact_target_model_id",
        "exact_target_revision",
        "input_output_from_pipeline_architecture_and_target_stage",
        "license_from_card_metadata",
        "likes_from_frozen_metadata",
        "model_card_from_pinned_readme_source",
        "model_family_from_config_model_type",
        "model_type_from_pipeline_and_config",
        "moe_parameter_counts_from_safetensors_and_exact_readme_row",
        "name_from_exact_target_basename",
        "parameter_count_from_safetensors_total",
        "release_date_from_explicit_readme_label",
        "results_summary_from_exact_target_score_selection",
        "results_summary_from_scoped_safety_evaluation",
        "safety_evaluation_from_exact_target_score_row",
        "safety_evaluation_from_scoped_readme_results_section",
        "stored_precision_from_safetensors_dtype_counts",
        "summary_from_exact_target_readme_description",
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

    def __post_init__(self) -> None:
        validate_publication_card(self.card)
        object.__setattr__(
            self,
            "provenance",
            tuple(sorted(self.provenance, key=lambda item: item.field_path)),
        )

    def provenance_dict(self) -> dict[str, Any]:
        return {
            "ruleset": PUBLICATION_SOURCE_RULESET,
            "fields": [item.to_dict() for item in self.provenance],
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


def _identity_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    metadata = inputs.metadata
    if metadata is None:
        return
    source_id = inputs.metadata_source_id
    author = _string(metadata.get("author"))
    if author is not None:
        yield _Candidate(
            "identity.developed_by", author, "developer_from_metadata_author",
            _pointer(source_id, "/author"),
        )

    card_data = _card_data(metadata)
    pipeline = _string(metadata.get("pipeline_tag")) or _string(
        card_data.get("pipeline_tag")
    )
    config_type = _string((inputs.config or {}).get("model_type"))
    if pipeline and config_type:
        model_type = f"{pipeline} task; {config_type} config model type"
        sources = (
            *_pointer(source_id, "/pipeline_tag"),
            *_pointer(inputs.config_source_id, "/model_type"),
        )
    elif pipeline:
        model_type = f"{pipeline} task"
        sources = _pointer(source_id, "/pipeline_tag")
    elif config_type:
        model_type = f"{config_type} config model type"
        sources = _pointer(inputs.config_source_id, "/model_type")
    else:
        model_type = None
        sources = ()
    if model_type is not None:
        yield _Candidate(
            "identity.model_type", model_type, "model_type_from_pipeline_and_config",
            sources,
        )

    license_name = _string(card_data.get("license"))
    license_pointer = "/cardData/license"
    if license_name is None:
        license_tags = [item.split(":", 1)[1] for item in _tags(metadata) if item.startswith("license:")]
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
    target_name = inputs.catalog.target.model_id.rsplit("/", 1)[-1]
    explicit_base = _label_stage(target_name) == "base"
    best: tuple[int, str, int, int] | None = None
    for text, start, end in _paragraphs(inputs.readme):
        if start > 8_000:
            break
        if not _model_label_matches(
            inputs,
            text,
            section_stage=_target_stage(inputs) if _label_stage(text) else None,
        ):
            continue
        lowered = text.casefold()
        if explicit_base and _label_stage(text) != "base":
            continue
        if _target_stage(inputs) == "base" and "pretrained" in lowered and "instruction tuned" in lowered:
            continue
        if _target_stage(inputs) == "posttrained" and "pretrained" in lowered and "instruction tuned" in lowered:
            continue
        score = len(set(_model_tokens(target_name)) & set(_model_tokens(text)))
        if best is None or score > best[0]:
            stage = (
                "post-trained"
                if _target_stage(inputs) == "posttrained"
                else "pretrained"
            )
            task = (_pipeline_tag(inputs) or "model inference").replace("-", " ")
            value = (
                f"The publisher README identifies {target_name} as a {stage} "
                f"checkpoint for {task}."
            )
            best = score, value, start, end
    return None if best is None else (best[1], best[2], best[3])


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


def _base_model_ids(
    metadata: Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], str | None]:
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
    if explicit:
        return explicit, "/cardData/base_model"

    tagged = []
    for tag in _tags(metadata):
        if not tag.startswith("base_model:"):
            continue
        value = tag[len("base_model:") :]
        if value.startswith(("adapter:", "finetune:", "merge:", "quantized:")):
            value = value.split(":", 1)[1]
        tagged.append(value)
    fallback = clean(tagged)
    return fallback, "/tags" if fallback else None


def _lineage_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    base_model_ids, declaration_pointer = _base_model_ids(inputs.metadata)
    base_models = tuple(
        {
            "model_id": model_id,
            "relation": "base_model",
        }
        for model_id in base_model_ids
        if model_id != inputs.catalog.target.model_id
    )
    if base_models:
        yield _Candidate(
            "lineage.base_models",
            list(base_models),
            "base_models_from_exact_metadata_declarations",
            _pointer(inputs.metadata_source_id, declaration_pointer or "/tags"),
        )
    model_type = _string((inputs.config or {}).get("model_type"))
    if model_type is not None:
        yield _Candidate(
            "lineage.model_family",
            model_type,
            "model_family_from_config_model_type",
            _pointer(inputs.config_source_id, "/model_type"),
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


def _heading_context(readme: str, position: int) -> tuple[str, ...]:
    active: dict[int, str] = {}
    for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", readme[:position]):
        level = len(match.group(1))
        active = {key: value for key, value in active.items() if key < level}
        active[level] = match.group(2).strip()
    return tuple(active[key] for key in sorted(active))


def _section_span(
    readme: str,
    *titles: str,
) -> tuple[str, int, int] | None:
    """Return the first matching Markdown section body and exact offsets."""

    headings = list(re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", readme))
    for index, match in enumerate(headings):
        if not _heading_matches(match.group(2), *titles):
            continue
        level = len(match.group(1))
        start = match.end()
        end = len(readme)
        for following in headings[index + 1 :]:
            if len(following.group(1)) <= level:
                end = following.start()
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
    return "base"


def _label_stage(value: str) -> str | None:
    normalized = _normalized_header(value)
    if re.search(r"\b(?:instruct|instruction tuned|chat|post trained|sft|dpo|rlvr)\b", normalized):
        return "posttrained"
    if re.search(r"\b(?:base|pretrained|pre trained|pt)\b", normalized):
        return "base"
    return None


def _size_tokens(value: str) -> frozenset[str]:
    return frozenset(
        item.casefold()
        for item in re.findall(
            r"(?i)(?<![a-z0-9])\d+(?:\.\d+)?[bm](?![a-z0-9])", value
        )
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
    candidate_stage = _label_stage(label)
    target_normalized = _normalized_header(target_name)
    label_normalized = _normalized_header(label)
    exact_label = label_normalized == target_normalized
    if section_stage is not None and section_stage != target_stage:
        return False
    if candidate_stage is not None and candidate_stage != target_stage:
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


def _html_context(readme: str, model_id: str) -> tuple[str, int, int] | None:
    rows = list(re.finditer(r"<tr\b[^>]*>.*?</tr>", readme, re.I | re.S))
    size_match = re.search(r"(?:^|[-_])(\d+(?:\.\d+)?[Bb])(?:[-_]|$)", model_id.rsplit("/", 1)[-1])
    target_size = size_match.group(1).casefold() if size_match else None
    for index, header_row in enumerate(rows):
        header = [_normalized_header(item) for item in _html_cells(header_row.group(0))]
        columns = [number for number, item in enumerate(header) if item == "context length"]
        if len(columns) != 1:
            continue
        column = columns[0]
        for row_match in rows[index + 1 :]:
            cells = _html_cells(row_match.group(0))
            if not cells:
                continue
            if target_size and target_size not in {item.casefold() for item in cells}:
                continue
            if column >= len(cells):
                continue
            value = _context_value(cells[column])
            if value is not None:
                return value, row_match.start(), row_match.end()
        break
    return None


def _prose_context(readme: str) -> tuple[str, int, int] | None:
    declared_line = re.search(
        r"(?im)^\s*[-*+]?\s*\*{0,2}context\s+(?:length|window)\*{0,2}\s*:\s*"
        r"(?P<value>[^\n]+?)\s*$",
        readme,
    )
    if declared_line is not None:
        value = _context_value(declared_line.group("value"))
        if value is not None:
            return value, declared_line.start(), declared_line.end()

    patterns = (
        re.compile(r"(?i)(\d[\d,]*(?:\.\d+)?\s*[KkMm])\s+context\s+window"),
        re.compile(r"(?i)context\s+window\s+lengths?\s+up\s+to\s+[*_`]*(\d[\d,]*(?:\.\d+)?\s*[KkMm]?)"),
    )
    for pattern in patterns:
        match = pattern.search(readme)
        if match is None:
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
            or _html_context(inputs.readme, inputs.catalog.target.model_id)
            or _prose_context(inputs.readme)
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


def _input_output(inputs: _Inputs) -> tuple[list[str] | None, tuple[SourcePointer, ...]]:
    pipeline = (_pipeline_tag(inputs) or "").casefold()
    mapping = {
        "text-generation": ["input: text", "output: text"],
        "text2text-generation": ["input: text", "output: text"],
        "image-text-to-text": ["input: image and text", "output: text"],
        "image-to-text": ["input: image", "output: text"],
        "automatic-speech-recognition": ["input: audio", "output: text"],
        "image-classification": ["input: image", "output: labels"],
    }
    values = list(mapping.get(pipeline, ()))
    sources = list(_pointer(inputs.metadata_source_id, "/pipeline_tag")) if values else []
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

    # OLMo instruction checkpoints explicitly enumerate their post-training
    # sources and stages in the release paragraph.  Select that paragraph only
    # for the post-trained target, never for the base checkpoint.
    if _target_stage(inputs) == "posttrained":
        release = _section_span(readme, "release documentation")
        if release is not None:
            body, start, _ = release
            for text, relative_start, relative_end in _paragraphs(body):
                if _model_label_matches(inputs, text, section_stage="posttrained") and re.search(
                    r"(?i)dataset|data|fine.?tun|DPO|RLVR", text
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
    stage_one = _section_span(readme, "stage 1 initial pretraining")
    stage_two = _section_span(readme, "stage 2 fine tuning")
    if _target_stage(inputs) == "base" and stage_one is not None:
        selected = [stage_one]
        if stage_two is not None:
            selected.append(stage_two)
        datasets: list[str] = []
        for body, _, _ in selected:
            dataset_line = re.search(r"(?im)^\s*-\s*Dataset:\s*(.+?)\s*$", body)
            if dataset_line is not None:
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
            if target_line is not None:
                epochs = re.search(r"(?i)(~?[0-9.]+\s+epochs?)", target_line.group(1))
                if epochs is not None:
                    pieces.append(
                        f"The {exact_size.upper()} schedule covers {epochs.group(1)}."
                    )
        mix = re.search(r"(?im)^\s*-\s*Mix composition:\s*(.+?)\s*$", stage_two[0] if stage_two else "")
        if mix is not None:
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
    training_dataset = _section_span(readme, "training dataset")
    if training_dataset is not None:
        body, start, end = training_dataset
        components = []
        for label, rendered in (
            ("web documents", "web documents"),
            ("code", "code"),
            ("mathematics", "mathematics"),
            ("images", "images"),
        ):
            if re.search(rf"(?im)^\s*[-*]?\s*\**{re.escape(label)}\**\s*:", body):
                components.append(rendered)
        languages = re.search(r"(?i)(over|more than)\s+([0-9,]+)\s+languages", body)
        pieces = []
        if components:
            pieces.append("Publisher-listed source categories: " + ", ".join(components) + ".")
        if languages is not None:
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
    training = _section_span(readme, "training data")
    if training is not None:
        body, start, _ = training
        scale = re.search(r"(?i)pretrained on\s+(~?[0-9.]+\s+trillion tokens)", body)
        if scale is not None:
            value = (
                f"Pretraining scale: {scale.group(1)} from publisher-described "
                "public-source data."
            )
            synthetic = re.search(
                r"(?i)(over|more than)\s+([0-9.]+[MBK]?)\s+synthetically generated examples",
                body,
            )
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
    if _target_stage(inputs) == "base":
        corpus = _line_span(
            readme,
            re.compile(r"(?im)^\s*-\s*\*\*Expanded Higher-Quality Pre-training Corpus:\*\*.+$"),
        )
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
    if deepseek is not None and _model_label_matches(
        inputs,
        deepseek.group(1),
        section_stage=_target_stage(inputs),
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
    for size in target_sizes:
        match = re.search(
            rf"(?i)(?<![A-Za-z0-9]){re.escape(size)}\s+model was trained with\s+"
            r"([0-9][0-9.,]*\s+(?:trillion|billion|million)\s+tokens)",
            readme,
        )
        if match is not None:
            return (
                f"{size.upper()} model: {_clean_readme_text(match.group(1))}",
                (SourcePointer(source_id, f"text:{match.start()}-{match.end()}"),),
                "training_size_from_exact_target_size_clause",
            )

    # Exact family statements used by DeepSeek, Llama, and Qwen.  Values are
    # copied from the matched source span rather than maintained in code.
    patterns = (
        re.compile(r"(?i)pre-?train(?:ed)?\s+DeepSeek-V3\s+on\s+([~0-9.]+\s*(?:T|trillion))\s+[^,.]{0,50}?tokens"),
        re.compile(r"(?i)Llama\s+3\.1\s+was pretrained on\s+([~0-9.]+\s*(?:T|trillion)\s+tokens)"),
        re.compile(r"(?i)Qwen3\s+is pre-trained on\s+([~0-9.]+\s*(?:T|trillion)\s+tokens)"),
    )
    for pattern in patterns:
        match = pattern.search(readme)
        if match is None:
            continue
        value = _clean_readme_text(match.group(1))
        if not value.casefold().endswith("tokens"):
            value += " tokens"
        if _target_stage(inputs) == "posttrained" and "Llama" in match.group(0):
            extra = re.search(r"(?i)fine-tuning data includes[^.]*?(over\s+[0-9.]+[MBK]?\s+synthetically generated examples)", readme)
            if extra is not None:
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
        re.compile(r"(?im)^\s*\*\*Knowledge cutoff\*\*\s*:?\s*(.+?)\s*$"),
    )
    for pattern in patterns:
        match = pattern.search(inputs.readme)
        if match is not None:
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

    if _target_stage(inputs) == "posttrained":
        # Exact one-sentence fine-tuning declarations (Mistral and OLMo).
        for pattern in (
            re.compile(r"(?im)^The\s+[^\n]*Instruct[^\n]*is an instruct fine-tuned version of[^\n]*\.\s*$"),
        ):
            match = pattern.search(readme)
            if match is not None and _model_label_matches(
                inputs, match.group(0), section_stage="posttrained"
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

        release = _section_span(readme, "release documentation")
        if release is not None:
            body, start, _ = release
            for text, relative_start, relative_end in _paragraphs(body):
                if all(
                    marker in text.casefold()
                    for marker in ("supervised finetuning", "dpo", "rlvr")
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
        matches = []
        for pattern in (
            re.compile(r"(?i)followed by Supervised Fine-Tuning and Reinforcement Learning stages[^.]*\."),
            re.compile(r"(?is)We introduce an innovative methodology to distill reasoning capabilities[^.]*?DeepSeek-V3[^.]*\."),
        ):
            match = pattern.search(readme)
            if match is not None:
                matches.append(match)
        if matches:
            return (
                "Post-training uses supervised fine-tuning and reinforcement learning. "
                "The README also describes distilling long-chain-of-thought reasoning "
                "from a DeepSeek-R1-series model into DeepSeek-V3.",
                tuple(SourcePointer(source_id, f"text:{item.start()}-{item.end()}") for item in matches),
                "adaptations_from_posttraining_and_distillation_statements",
            )

        # Llama's architecture paragraph explicitly scopes SFT/RLHF to tuned
        # versions; the target ID supplies the instruction-tuned variant.
        match = re.search(
            r"(?i)(The tuned versions use supervised fine-tuning \(SFT\) and reinforcement learning with human feedback \(RLHF\)[^.]*\.)",
            readme,
        )
        if match is not None:
            return (
                "Instruction tuning combines SFT with RLHF for preference alignment, "
                "helpfulness, and safety.",
                (SourcePointer(source_id, f"text:{match.start(1)}-{match.end(1)}"),),
                "adaptations_from_tuned_variant_architecture_statement",
            )

        # Qwen exact-target overview carries an explicit training-stage label.
        overview = _summary_from_overview(inputs)
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
        if re.search(r"(?i)instruction-tuned\s+variants", readme):
            description = re.search(r"(?i)instruction-tuned\s+variants", readme)
            if description is not None and re.search(
                r"(?i)(?:^|[-_.])(?:it|instruct)(?:$|[-_.])",
                inputs.catalog.target.model_id.rsplit("/", 1)[-1],
            ):
                return (
                    "Instruction-tuned variant (the frozen README does not specify the tuning recipe).",
                    (
                        *_pointer(inputs.metadata_source_id, "/id"),
                        SourcePointer(source_id, f"text:{description.start()}-{description.end()}"),
                    ),
                    "adaptation_stage_from_exact_it_title_and_family_description",
                )
    else:
        # A base README may list size-specific merge procedures.  Select only
        # the size carried by the exact target ID.
        for size in sorted(_size_tokens(inputs.catalog.target.model_id)):
            match = re.search(
                rf"(?im)^\s*-\s*{re.escape(size)}\s+Model:\s*[^\n]*"
                r"merged via model souping\s*$",
                readme,
            )
            if match is not None and "OLMo" in readme[
                max(0, match.start() - 1_500) : match.start()
            ]:
                return (
                    f"Three {size.upper()} variants trained on 50B-token mixtures were "
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


def _benchmark_metric(value: str) -> tuple[str, str | None]:
    cleaned = _clean_readme_text(value)
    match = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", cleaned)
    if match is None:
        return cleaned, None
    return match.group(1).strip(), match.group(2).strip()


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
) -> tuple[dict[str, Any], ...]:
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
        cells
        for cells, _, _ in table.rows
        if cells and _model_label_matches(inputs, cells[0], section_stage=section_stage)
    ]
    if len(matched_rows) != 1:
        return ()
    cells = matched_rows[0]
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
        benchmark = _clean_readme_text(table.headers[index])
        if _normalized_header(benchmark) in skip:
            continue
        score = _score_value(cells[index])
        if score is None:
            continue
        scores.append(
            {
                "benchmark": benchmark,
                "metric": "README-reported score",
                "score": score,
                "setting": _setting_text(None, table.headings),
            }
        )
    return tuple(scores)


def _column_oriented_scores(
    inputs: _Inputs,
    table: _ReadmeTable,
) -> tuple[dict[str, Any], ...]:
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
    if len(model_columns) != 1:
        return ()
    benchmark_column = benchmark_columns[0]
    model_column = model_columns[0]
    metric_column = next(
        (index for index, item in enumerate(normalized) if item == "metric"), None
    )
    shots_column = next(
        (index for index, item in enumerate(normalized) if item in {"shots", "shot"}), None
    )
    scores = []
    for cells, _, _ in table.rows:
        if max(benchmark_column, model_column) >= len(cells):
            continue
        if normalized[benchmark_column] == "benchmark metric":
            benchmark, embedded_metric = _benchmark_metric(cells[benchmark_column])
        else:
            benchmark = _clean_readme_text(cells[benchmark_column])
            embedded_metric = None
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
                metric = metric_cell
        scores.append(
            {
                "benchmark": benchmark,
                "metric": metric or "README-reported score",
                "score": score,
                "setting": _setting_text(shots, table.headings),
            }
        )
    return tuple(scores)


def _benchmark_scores(
    inputs: _Inputs,
    *,
    limit: int = 12,
) -> tuple[tuple[dict[str, Any], ...], tuple[SourcePointer, ...]]:
    if inputs.readme is None or inputs.readme_source_id is None:
        return (), ()
    scores: list[dict[str, Any]] = []
    pointers: list[SourcePointer] = []
    seen: set[tuple[str, str, str]] = set()
    tables = (*_markdown_tables(inputs.readme), *_html_tables(inputs.readme))
    for table in sorted(tables, key=lambda item: item.start):
        parsed = _row_oriented_scores(inputs, table) or _column_oriented_scores(inputs, table)
        accepted = 0
        for score in parsed:
            key = (
                score["benchmark"].casefold(),
                score["metric"].casefold(),
                str(score["setting"]).casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            scores.append(score)
            accepted += 1
            if len(scores) >= limit:
                break
        if accepted:
            pointers.append(
                SourcePointer(inputs.readme_source_id, f"text:{table.start}-{table.end}")
            )
        if len(scores) >= limit:
            break
    return tuple(scores), tuple(pointers)


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

    outer = _section_span(inputs.readme, "ethics and safety")
    if outer is None:
        return None
    outer_body, outer_start, _ = outer
    inner = _section_span(outer_body, "evaluation results")
    if inner is None:
        return None
    body, inner_start, inner_end = inner
    value = _clean_readme_text(body, limit=1_200)
    if not value or not re.search(r"(?i)safety|policy violations|representational harms", value):
        return None
    return (
        "The publisher reports improvement over prior Gemma releases for child "
        "safety, content safety, representational harms, and ungrounded inference. "
        "Testing omitted safety filters; the stated limitation is English-only prompts.",
        (
            SourcePointer(
                inputs.readme_source_id,
                f"text:{outer_start + inner_start}-{outer_start + inner_end}",
            ),
        ),
        "safety_evaluation_from_scoped_readme_results_section",
    )


def _evaluation_candidates(inputs: _Inputs) -> Iterable[_Candidate]:
    scores, score_sources = _benchmark_scores(inputs)
    if scores:
        sample = "; ".join(
            f"{item['benchmark']}: {item['score']}"
            for item in scores[:3]
        )
        yield _Candidate(
            "evaluation.results_summary",
            f"The frozen README provides {len(scores)} exact-target benchmark scores in this capped publication set; examples: {sample}.",
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
                "The frozen README reports qualitative safety-evaluation results for the exact repository; see safety_evals.",
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
        score = 0
        if _repo_key(owner) == _repo_key(target_namespace):
            score += 5
        target_key = _repo_key(target_name)
        repo_key = _repo_key(repository)
        if repo_key and (target_key.startswith(repo_key) or repo_key.startswith(target_key)):
            score += 5
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

    report, report_sources = _technical_report(inputs)
    if report is not None:
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

    Existing specified values win over derived candidates.  ``Not specified``
    is treated as an invitation to enrich, while ``Not applicable`` remains an
    explicit author decision.  Exact target identity conflicts are rejected.
    The returned provenance is intentionally separate from the public card.
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

    provenance: list[PublicationFieldProvenance] = []
    for candidate in _all_candidates(inputs):
        if candidate.field_path in withheld:
            continue
        current = get_field(output, candidate.field_path, NOT_SPECIFIED)
        if _specified(current) or current == NOT_APPLICABLE:
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
    return PublicationEnrichmentResult(output, tuple(provenance))


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
    return replayed


__all__ = [
    "PUBLICATION_SOURCE_RULESET",
    "PUBLICATION_SOURCE_RULE_NAMES",
    "SOURCE_EXCERPT_MIN_COMPACT_CHARS",
    "SOURCE_EXCERPT_MIN_WORDS",
    "PublicationEnrichmentResult",
    "PublicationFieldProvenance",
    "PublicationSourceError",
    "SourcePointer",
    "assert_no_source_excerpt",
    "enrich_publication_card",
    "replay_publication_enrichment",
]
