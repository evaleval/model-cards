"""The public card contract as a composer CardSchema.

This is the model-card counterpart of the benchmark schema the adjacent composer
carries as its default. The paths and their order come from schema.py (the seven
published sections plus the private provenance_and_quality); this module adds what the
composer needs on top: which source each field is extracted from, the per-field hints
and negative guidelines, the enum
vocabularies, which fields are deterministic (structured channel: config.json, hub
model_info, safetensors, model-index) and therefore only echoed by Stage B, and the
Stage-B group split. The contract is not reopened here: no field is added, removed or
renamed in this module.

Deterministic-only section: provenance_and_quality is written after composition from
the ledger, never authored by the model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from auto_benchmarkcard.tools.composer.field_spec import CardSchema

from .schema import NOT_APPLICABLE, NOT_SPECIFIED, CARD_FIELD_PATHS, CARD_SECTIONS


def _coerce_list(v):
    return [v] if isinstance(v, str) else v


class Identity(BaseModel):
    model_id: str = Field(..., description="The canonical identifier: the Hugging Face repo id when one exists, otherwise the developer's API model name")
    name: str = Field(..., description="The official display name of the model")
    developed_by: str = Field(..., description="The organization or people who built it")
    model_type: str = Field(..., description="The primary task the model performs")
    license: str = Field(..., description="The license governing the weights, or the terms of use for API-only models, with a link")
    release_date: str = Field(..., description="When the model was first published, naming which date it is (hub creation vs developer announcement)")
    version: str = Field(..., description="The model version or revision this metadata describes")
    summary: str = Field(..., description="A one-line description of what the model is")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None


class Lineage(BaseModel):
    base_models: Union[List[Any], str] = Field(default=NOT_SPECIFIED, description="The parent model or models it was derived from, and the relation to them, as {model_id, relation} rows from the hub tags")
    model_family: str = Field(default=NOT_SPECIFIED, description="The developer-stated family it belongs to")
    derivatives: str = Field(default=NOT_SPECIFIED, description="How many models on the Hub derive from this one, with a link to the model tree")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None


class Specifications(BaseModel):
    architecture_type: str = Field(default=NOT_SPECIFIED, description="The high-level type: dense decoder-only, mixture-of-experts, state-space, encoder-decoder, or diffusion, read from config.json")
    num_parameters: str = Field(default=NOT_SPECIFIED, description="The total number of parameters, and for MoE models also the active parameters per token")
    context_length: str = Field(default=NOT_SPECIFIED, description="The maximum input length the model accepts")
    precision: str = Field(default=NOT_SPECIFIED, description="The numerical precision of the released weights")
    model_size: str = Field(default=NOT_SPECIFIED, description="The size of the released weights on disk, with the precision they are stored in")
    input_output: List[str] = Field(default_factory=lambda: [NOT_SPECIFIED], description="The input and output modalities")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None

    @field_validator("input_output", mode="before")
    @classmethod
    def _coerce(cls, v):
        return _coerce_list(v)


class TrainingContext(BaseModel):
    training_data: str = Field(default=NOT_SPECIFIED, description="The datasets or corpora it was trained on, relevant for interpreting evaluations")
    training_data_size: str = Field(default=NOT_SPECIFIED, description="The total amount of training data, as reported by the developer")
    data_cutoff: str = Field(default=NOT_SPECIFIED, description="The training data cutoff date, when reported")
    adaptations: str = Field(default=NOT_SPECIFIED, description="Any post-training or alignment applied, or that the model is a merge")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None


class AccessAndAdoption(BaseModel):
    access_type: str = Field(default=NOT_SPECIFIED, description="Whether the model is open-weight, gated, or API-only")
    downloads: str = Field(default=NOT_SPECIFIED, description="How often the model is downloaded on the Hub, as a dated snapshot")
    likes: str = Field(default=NOT_SPECIFIED, description="How many likes the model has on the Hub, as a dated snapshot")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None


class Evaluation(BaseModel):
    results_summary: str = Field(default=NOT_SPECIFIED, description="A short plain-language summary of the developer-reported headline results")
    benchmark_scores: Union[List[Dict[str, Any]], str] = Field(default=NOT_SPECIFIED, description="The model's headline scores across benchmarks as rows {benchmark, metric, score, setting}, with the reported evaluation setting (shots, reasoning mode)")
    human_evals: str = Field(default=NOT_SPECIFIED, description="Human evaluation results reported by the developer, for example preference win rates or expert ratings")
    safety_evals: str = Field(default=NOT_SPECIFIED, description="The model's reported scores on safety evaluations, jailbreak resistance, refusal of harmful requests, prompt injection")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None


class Links(BaseModel):
    model_card: str = Field(default=NOT_SPECIFIED, description="Link to the full Hugging Face model card")
    system_card: str = Field(default=NOT_SPECIFIED, description="Link to the system or safety card, if any")
    tech_report: str = Field(default=NOT_SPECIFIED, description="Link to the technical report or paper that introduces THIS model")
    code_repository: str = Field(default=NOT_SPECIFIED, description="Link to the model's code repository")
    citation: str = Field(default=NOT_SPECIFIED, description="The citation the developer asks for, as the BibTeX key or the reference line")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None


class Risks(BaseModel):
    possible_risks: Union[List[Any], str] = Field(default=NOT_SPECIFIED, description="AI Risk Atlas entries selected for THIS checkpoint from what the card itself says, as {category, description, url, justification} rows; filled by the risk stage, never authored from prose")
    provenance: Optional[Dict[str, Dict[str, Any]]] = None


class ProvenanceAndQuality(BaseModel):
    provenance: Union[Dict[str, Any], str] = Field(default=NOT_SPECIFIED)
    flagged_fields: Union[Dict[str, Any], str] = Field(default=NOT_SPECIFIED)
    missing_fields: Union[List[str], str] = Field(default=NOT_SPECIFIED)
    coverage_score: Union[float, str] = Field(default=NOT_SPECIFIED)
    card_info: Union[Dict[str, Any], str] = Field(default=NOT_SPECIFIED)


SECTION_MODELS: Dict[str, Any] = {
    "identity": Identity,
    "lineage": Lineage,
    "specifications": Specifications,
    "training_context": TrainingContext,
    "access_and_adoption": AccessAndAdoption,
    "evaluation": Evaluation,
    "links": Links,
    "risks": Risks,
    "provenance_and_quality": ProvenanceAndQuality,
}

PAPER, HF, GITHUB, HTML = "paper", "hf", "github", "html"

# Stage-A extraction table: which source calls ask for the field, the retrieval query
# for the paper gap-fill, and the hint shown next to the field in the prompt.
# Deterministic fields (identity.model_id/version, lineage.base_models/derivatives,
# the config- and safetensors-derived specifications, access_and_adoption and
# links.model_card) are NOT in this table: they come from the structured channel and
# Stage B only echoes them.
CURATOR_FIELDS: Dict[str, Dict[str, Any]] = {
    "identity.developed_by": {"sources": frozenset({PAPER, HF, GITHUB}), "gap_query": None,
                              "hint": "The organization or people who built it"},
    "identity.model_type": {"sources": frozenset({PAPER, HF}), "gap_query": None,
                            "hint": "The primary task the model performs (e.g. text generation, embedding)"},
    "identity.summary": {"sources": frozenset({PAPER, HF, HTML}), "gap_query": None,
                         "hint": "The one sentence that says what the model is"},
    "lineage.model_family": {"sources": frozenset({PAPER, HF}), "gap_query": "family series suite of models",
                             "hint": "The developer-stated family name; only as stated, never inferred"},
    "specifications.num_parameters": {"sources": frozenset({PAPER, HF}), "gap_query": "parameters billion active parameters per token",
                                      "hint": "Total parameter count as stated; active parameters per token for MoE models when stated"},
    "specifications.context_length": {"sources": frozenset({PAPER, HF}), "gap_query": "context length context window tokens maximum sequence length",
                                      "hint": "The maximum input length, as stated"},
    "specifications.precision": {"sources": frozenset({HF}), "gap_query": None,
                                 "hint": "The numerical precision of the released weights (bf16, fp8, int4)"},
    "specifications.input_output": {"sources": frozenset({PAPER, HF}), "gap_query": None,
                                  "hint": "Input and output modalities (text, image, audio, video)"},
    "training_context.training_data": {"sources": frozenset({PAPER, HF, GITHUB}), "gap_query": "trained on pretraining data corpus tokens mixture",
                                       "hint": "The datasets or corpora THIS checkpoint was trained on (pretraining for a base, post-training data for a fine-tune)"},
    "training_context.training_data_size": {"sources": frozenset({PAPER, HF}), "gap_query": "trillion tokens training tokens billion tokens data size",
                                            "hint": "The total amount of training data, as reported, naming the entity it was reported for"},
    "training_context.data_cutoff": {"sources": frozenset({PAPER, HF, HTML}), "gap_query": "knowledge cutoff data cutoff date",
                                     "hint": "The training data cutoff date, when reported"},
    "training_context.adaptations": {"sources": frozenset({PAPER, HF, GITHUB}), "gap_query": "fine-tuned instruction tuning RLHF DPO alignment post-training merge distilled",
                                     "hint": "Post-training or alignment applied to THIS checkpoint, or that it is a merge"},
    "evaluation.results_summary": {"sources": frozenset({PAPER, HF, HTML}), "gap_query": "results outperforms achieves state of the art headline",
                                   "hint": "The developer's own headline claim about results"},
    "evaluation.benchmark_scores": {"sources": frozenset({PAPER, HF, GITHUB}), "gap_query": "benchmark accuracy score table results MMLU GSM8K HumanEval",
                                    "hint": "Table rows or sentences giving THIS model's score on a named benchmark with the metric and the evaluation setting (shots, reasoning mode)"},
    "evaluation.human_evals": {"sources": frozenset({PAPER, HF, HTML}), "gap_query": "human evaluation preference win rate raters annotators judged",
                               "hint": "Human evaluation results reported by the developer"},
    "evaluation.safety_evals": {"sources": frozenset({PAPER, HF, HTML}), "gap_query": "safety evaluation jailbreak refusal harmful prompt injection red team",
                                "hint": "Reported safety, jailbreak, refusal or prompt-injection results"},
    "links.system_card": {"sources": frozenset({HF, HTML}), "gap_query": None,
                          "hint": "URL of a system or safety card for THIS model"},
    "links.tech_report": {"sources": frozenset({HF, GITHUB, HTML}), "gap_query": None,
                          "hint": "URL of the technical report or paper that introduces THIS model"},
    "links.code_repository": {"sources": frozenset({HF, HTML, PAPER}), "gap_query": None,
                              "hint": "URL of the developer's code repository for THIS model"},
    "links.citation": {"sources": frozenset({HF, GITHUB}), "gap_query": None,
                       "hint": "The reference the developer asks to be cited, as stated"},
}

# Negative guidelines: what a field must not be filled with.
FIELD_CAPS: Dict[str, str] = {
    "lineage.base_models": "hub metadata only (base_model tags); NEVER inferred from README prose, which fine-tunes copy from the base card",
    "lineage.model_family": "the developer-stated family name only; no fact may be inherited through family membership",
    "specifications.num_parameters": "the total for THIS checkpoint; MoE active parameters only when explicitly stated, never swapped for the total",
    "specifications.context_length": "the config value; an advertised extended-context claim only with its citation",
    "training_context.training_data": "the data THIS checkpoint was trained on, naming the entity (base pretraining vs this fine-tune); NEVER a base model's pretraining data attributed to a derivative",
    "training_context.training_data_size": "as reported and for which entity; NOT a figure reported for a different checkpoint or the base",
    "evaluation.benchmark_scores": "only rows whose model label is THIS model; NEVER a comparison model's row, a base model's row, or a different checkpoint's row; keep the metric and the evaluation setting",
    "evaluation.human_evals": "developer-reported only; NOT community arenas or third-party leaderboards",
    "evaluation.safety_evals": "developer-reported only; expected sparse for open-weight models, Not specified is the honest default",
    "links.tech_report": "the paper or report that introduces THIS model (name in title or abstract); a derivative card usually carries the BASE model's paper, which does not qualify",
    "access_and_adoption.downloads": "a dated snapshot with its window (hub default is 30 days); never an undated count",
    "specifications.model_size": "the bytes of THIS revision's weight files, with the precision they are stored in; never a size quoted for another checkpoint",
    "links.citation": "the citation the developer asks for; never a citation of the base model's paper on a derivative's card",
}

ARCHITECTURE_VOCAB = {"dense decoder-only", "mixture-of-experts", "state-space", "encoder-decoder", "diffusion"}
ACCESS_TYPE_VOCAB = {"open-weight", "gated", "api-only"}

ENUM_REGISTRY = {
    "specifications.architecture_type": lambda: ARCHITECTURE_VOCAB,
    "access_and_adoption.access_type": lambda: ACCESS_TYPE_VOCAB,
}

# Structured-channel fields (Stage B echoes; the ledger records them as structured_explicit).
ESTABLISHED_FIELDS = {
    "identity.model_id", "identity.version", "identity.name", "identity.license",
    "identity.release_date", "lineage.base_models", "lineage.derivatives",
    "specifications.architecture_type", "specifications.num_parameters",
    "specifications.context_length", "specifications.precision",
    "specifications.model_size",
    "access_and_adoption.access_type", "access_and_adoption.downloads",
    "access_and_adoption.likes", "links.model_card",
}

STAGE_B_RULES = (
    "RULES:\n"
    "1. Use ONLY the evidence items below. No outside knowledge. No source text is shown to you on "
    "purpose; work from the quotes only.\n"
    "1b. Evidence-line annotations (machine-derived, trustworthy): 'about:' names the entity the "
    "quote describes. A quote about the BASE model, a sibling checkpoint, a different size or "
    "variant, or a comparison model supports only statements about THAT entity; it never fills a "
    "field of the target checkpoint. 'role: secondary' marks cited or comparison content and "
    "'role: illustration' an example; neither may become the target's own facts. 'reg:' is the "
    "document region (related_work, ablation or appendix content is weak support); 'sec:' and "
    "'tab:' name the section and source table.\n"
    "2. If a field has no supporting evidence and is not already established, output exactly "
    "\"Not specified\". A field that cannot apply to this model class (weight-derived "
    "specifications of an API-only model) is exactly \"Not applicable\".\n"
    "3. Controlled (enum) fields: pick from the allowed vocabulary; if nothing fits use \"other:<short text>\".\n"
    "4. Prose (non-list) fields: 1-3 sentences, third person, your own synthesis of the cited "
    "quotes; no vocabulary.\n"
    "4a. Write the sentence yourself. A prose value must not reproduce twelve consecutive "
    "words of any quote: name the fact and drop the source's phrasing. A value that copies "
    "a run that long is discarded and the field is left empty, so a shorter sentence in "
    "your own words is always worth more than a longer one in the source's.\n"
    "4b. List fields: enumerate atomic items, one discrete item per array element.\n"
    "5. benchmark_scores is a list of objects {\"benchmark\", \"metric\", \"score\", \"setting\"}, one per "
    "cited row or sentence that names THIS model; never a row of another model.\n"
    "6. PROVENANCE (required for every filled, non-\"Not specified\", non-established field): add "
    "provenance[field] = {\"source\": \"<doc>\", \"evidence\": \"<the quote>\", \"evidence_ids\": [\"E..\"]}. "
    "Cite only evidence ids that appear in the evidence items; never invent ids.\n"
    "7. Never output an evidence id (e.g. E01) as a field value; evidence ids belong only in "
    "provenance.evidence_ids."
)

EXTRACTION_SYSTEM = (
    "You are a precise extraction assistant. You read one source document about a named model "
    "checkpoint and return verbatim supporting quotes as JSON. You never paraphrase a quote, "
    "never use knowledge from outside the document, and only extract facts stated for the target "
    "checkpoint itself, not for its base model, other sizes or variants, or the models it is "
    "compared against."
)

GROUPS = [
    ("identity_lineage", ["identity", "lineage"]),
    ("specs_training_access", ["specifications", "training_context", "access_and_adoption"]),
    ("evaluation_links", ["evaluation", "links"]),
]

# Bare-value fields: the validator rejects a sentence here ("The official display name
# is OLMo-2-1124-7B-Instruct." was seen on the smoke) and the repair loop fixes it.
VALUE_FIELDS = {
    "identity.name", "identity.developed_by", "identity.model_type", "identity.license",
    "identity.release_date", "identity.version", "lineage.model_family",
    "specifications.num_parameters", "specifications.context_length", "specifications.precision",
    "specifications.model_size", "training_context.training_data_size",
    "training_context.data_cutoff", "access_and_adoption.access_type",
    "access_and_adoption.downloads", "access_and_adoption.likes",
}

# EAV audits these first: numbers, data and lineage splice silently across checkpoints.
# The high-stakes list, plus the two fields whose value is a
# family statement often enough to matter.
HIGH_STAKES_FIELDS = frozenset({
    "specifications.num_parameters", "specifications.context_length",
    "training_context.training_data", "training_context.training_data_size",
    "training_context.data_cutoff", "evaluation.benchmark_scores",
    "evaluation.safety_evals", "lineage.base_models", "identity.license",
    "evaluation.human_evals", "lineage.model_family", "identity.release_date",
})


def model_card_schema() -> CardSchema:
    """The v5 model-card CardSchema (38 fields, 8 sections, provenance_and_quality det-only)."""
    return CardSchema(
        name="model",
        entity_noun="model",
        card_noun="model card",
        other_entities_phrase="models, checkpoints, sizes, or variants",
        sections=list(CARD_SECTIONS),
        curator_fields=CURATOR_FIELDS,
        field_caps=FIELD_CAPS,
        enum_registry=ENUM_REGISTRY,
        enum_multi=set(),
        enum_comma_joined=set(),
        b_authored_enums=set(),
        established_enums={"specifications.architecture_type", "access_and_adoption.access_type"},
        display_fields=set(),
        established_fields=ESTABLISHED_FIELDS,
        collapse_fields={"evaluation.benchmark_scores"},
        structured_fields={"evaluation.benchmark_scores"},
        evidence_exempt=ESTABLISHED_FIELDS | {"identity.model_id", "identity.version",
                                              "links.model_card", "links.system_card",
                                              "links.tech_report", "links.code_repository"},
        list_fields={"input_output"},
        list_caps={"specifications.input_output": 6},
        groups=GROUPS,
        det_only_sections={"risks", "provenance_and_quality"},
        stage_b_rules=STAGE_B_RULES,
        extraction_system=EXTRACTION_SYSTEM,
        not_applicable=NOT_APPLICABLE,
        section_models=SECTION_MODELS,
        value_fields=VALUE_FIELDS,
    )


def field_paths(schema: CardSchema) -> List[str]:
    """Every section.field path of the schema, in section order (provenance excluded)."""
    out: List[str] = []
    for sec in schema.sections:
        for fname in schema.section_models[sec].model_fields:
            if fname != "provenance" or sec == "provenance_and_quality":
                out.append(f"{sec}.{fname}")
    return out


assert tuple(field_paths(model_card_schema())) == CARD_FIELD_PATHS, \
    "the composer schema must carry exactly the 38 frozen v5 paths"


def prompts_fingerprint() -> str:
    """A digest over everything that shapes a prompt, for the run manifest.

    Two runs with the same fingerprint asked the model the same questions. It covers the
    extraction table, the negative guidelines, the enum vocabularies, the Stage B rules,
    the extraction system message, the group split and the per-stage token caps, because
    a cap change alters what comes back as surely as a wording change does.
    """
    import hashlib
    import json

    from .calls import EAV_MAX_TOKENS, STAGE_A_MAX_TOKENS
    from .model_frame import FRAME_MAX_TOKENS

    payload = {
        "curator_fields": {k: {"sources": sorted(v["sources"]), "gap_query": v["gap_query"],
                               "hint": v["hint"]} for k, v in sorted(CURATOR_FIELDS.items())},
        "field_caps": dict(sorted(FIELD_CAPS.items())),
        "enums": {k: sorted(v()) for k, v in sorted(ENUM_REGISTRY.items())},
        "established_fields": sorted(ESTABLISHED_FIELDS),
        "value_fields": sorted(VALUE_FIELDS),
        "high_stakes_fields": sorted(HIGH_STAKES_FIELDS),
        "groups": [[name, list(sections)] for name, sections in GROUPS],
        "stage_b_rules": STAGE_B_RULES,
        "extraction_system": EXTRACTION_SYSTEM,
        "token_caps": {"frame": FRAME_MAX_TOKENS, "stage_a": STAGE_A_MAX_TOKENS,
                       "eav": EAV_MAX_TOKENS},
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
