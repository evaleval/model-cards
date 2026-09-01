"""Typed OpenRouter adapters for extraction and post-extraction gates.

All adapters use the one bounded runtime in :mod:`model_cards.provider`.  The
only provider-visible text is the public-source excerpt or frozen-source chunk
needed for the current decision.  Prompts and raw responses are never returned
or serialized by this module; normalized decisions are stored by the provider
runtime in the caller's private run directory.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator

from .claim_gate import (
    ClaimCandidate,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
)
from .extraction import (
    ExtractionBatch,
    SourceWindow,
    build_source_windows,
    extraction_response_schema,
    proposals_from_provider_value,
)
from .factreasoner import (
    CheckOutcome,
    CheckRequest,
    CheckerResponse,
)
from .models import SourceDocument, TargetIdentity
from .provider import (
    MODEL_ID,
    ProviderTransport,
    StructuredCallSpec,
    structured_json_call,
)
from .risk_mapping import (
    ApplicabilityDecision,
    ApplicabilityStatus,
    RiskCandidate,
    UseContext,
)
from .run_ledger import json_sha256
from .schema import CONTENT_FIELD_PATHS


ADAPTER_VERSION = "model-card-openrouter-adapters/v1"
CLAIM_CHECKER_ID = "openrouter/deepseek-v4-flash-0731"
FACT_CHECKER_ID = "openrouter/deepseek-v4-flash-0731"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/+()-]{0,127}$")


class ProviderAdapterError(ValueError):
    """An adapter input or normalized provider decision is invalid."""


CallFunction = Callable[..., Any]


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
        raise ProviderAdapterError("provider adapter values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ProviderAdapterError(f"{label} has an invalid closed shape")
    return value


def _private_directory(path: str | os.PathLike[str]) -> Path:
    root = Path(path)
    if root.is_symlink():
        raise ProviderAdapterError("provider decision directory cannot be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ProviderAdapterError("provider decision directory is invalid")
    return root


@dataclass(frozen=True)
class _Runtime:
    provider: str
    ledger_path: Path
    decision_dir: Path
    environment: Mapping[str, str] | None
    transport: ProviderTransport | None
    call: CallFunction

    @classmethod
    def build(
        cls,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        environment: Mapping[str, str] | None,
        transport: ProviderTransport | None,
        call: CallFunction,
    ) -> "_Runtime":
        if not isinstance(provider, str) or not _PROVIDER_RE.fullmatch(provider):
            raise ProviderAdapterError("an explicit OpenRouter provider is required")
        ledger = Path(ledger_path)
        if ledger.is_symlink() or ledger.parent.is_symlink():
            raise ProviderAdapterError("usage ledger path is unsafe")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        return cls(
            provider=provider,
            ledger_path=ledger,
            decision_dir=_private_directory(decision_dir),
            environment=environment,
            transport=transport,
            call=call,
        )

    def invoke(
        self,
        spec: StructuredCallSpec,
        *,
        decision_name: str,
        validator: Callable[[Mapping[str, Any]], None],
    ) -> Any:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,191}\.json", decision_name):
            raise ProviderAdapterError("decision sidecar name is invalid")
        return self.call(
            spec,
            ledger_path=self.ledger_path,
            decision_path=self.decision_dir / decision_name,
            validator=validator,
            environment=self.environment,
            transport=self.transport,
        )


class OpenRouterQuoteExtractor:
    """One structured call per bounded text source, followed by local replay."""

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
        )

    def extract_source(
        self,
        source: SourceDocument,
        *,
        target: TargetIdentity,
        source_catalog_sha256: str,
    ) -> ExtractionBatch:
        if source.target != target or source.text is None:
            raise ProviderAdapterError("quote extraction requires exact-target text")
        if not _DIGEST_RE.fullmatch(source_catalog_sha256):
            raise ProviderAdapterError("source catalog digest is invalid")
        windows = build_source_windows(source)
        response = extraction_response_schema()
        configuration = {
            "adapter_version": ADAPTER_VERSION,
            "model": MODEL_ID,
            "provider": self.runtime.provider,
            "schema": response["name"],
            "temperature": 0,
            "window_ids": [item.window_id for item in windows],
            "content_fields": list(CONTENT_FIELD_PATHS),
        }
        config_sha = json_sha256(configuration)
        payload = {
            "target": target.to_dict(),
            "source": {
                "source_id": source.source_id,
                "source_uri": source.source_uri,
                "source_revision": source.source_revision,
                "source_role": source.role.value,
            },
            "allowed_fields": list(CONTENT_FIELD_PATHS),
            "rules": {
                "quote_must_be_verbatim": True,
                "value_must_be_fully_supported_by_quote": True,
                "unknown_or_ambiguous_claims": "omit",
                "base_family_sibling_claims_keep_relation": True,
                "source_id_must_equal": source.source_id,
            },
            "windows": [
                {
                    "window_id": item.window_id,
                    "normalized_start": item.normalized_start,
                    "normalized_end": item.normalized_end,
                    "excerpt": item.excerpt,
                }
                for item in windows
            ],
        }
        logical = f"extract.{source.source_id}.{source_catalog_sha256[:16]}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name=response["name"],
            json_schema=response["schema"],
            system_prompt=(
                "Extract only verbatim, fully supported Model Card evidence from the "
                "provided frozen public-source windows. Return the strict JSON object."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=8192,
            context_metadata={
                "stage": "quote_extraction",
                "source_id": source.source_id,
                "catalog_sha256": source_catalog_sha256,
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            proposals = proposals_from_provider_value(value)
            if any(item.source_id != source.source_id for item in proposals):
                raise ProviderAdapterError("extractor returned another source identifier")

        result = self.runtime.invoke(
            spec,
            decision_name=f"extract-{source.source_id}-{source_catalog_sha256[:16]}.json",
            validator=validate,
        )
        proposals = proposals_from_provider_value(result.decision)
        return ExtractionBatch.build(
            target=target,
            source_catalog_sha256=source_catalog_sha256,
            provider=self.runtime.provider,
            inference_config_sha256=config_sha,
            proposals=proposals,
        )


class OpenRouterClaimChecker:
    """Independent field-fit and complete-value checks for one quote candidate."""

    checker_id = CLAIM_CHECKER_ID
    checker_revision = ADAPTER_VERSION

    _REASONS = {
        GateName.FIELD_FIT: {
            "accepted": ("semantic_field_fit",),
            "withheld": ("wrong_field", "ambiguous_field_fit"),
        },
        GateName.VALUE_SUPPORT: {
            "accepted": ("semantic_value_support",),
            "withheld": ("incomplete_value_support", "contradictory_value"),
        },
    }

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
        )

    def decide(self, candidate: ClaimCandidate, gate: GateName) -> ProseCheckerDecision:
        if not isinstance(candidate, ClaimCandidate):
            raise ProviderAdapterError("claim checker requires a typed candidate")
        gate = GateName(gate)
        if gate not in self._REASONS:
            raise ProviderAdapterError("claim checker can decide only prose gates")
        reasons = self._REASONS[gate]
        allowed_reasons = sorted(reasons["accepted"] + reasons["withheld"])
        schema = {
            "type": "object",
            "required": ["status", "reason"],
            "properties": {
                "status": {"enum": ["accepted", "withheld"]},
                "reason": {"enum": allowed_reasons},
            },
            "additionalProperties": False,
        }
        evidence = [
            {
                "source_id": item.source_id,
                "source_role": item.source_role.value,
                "source_revision": item.source_revision,
                "quote": item.quote,
                "section_path": list(item.section_path),
                "table_id": item.table_id,
            }
            for item in candidate.evidence
        ]
        task = (
            "Decide whether the quoted evidence semantically belongs in exactly the "
            "proposed Model Card field. Do not assess or alter the value."
            if gate is GateName.FIELD_FIT
            else "Decide whether the quoted evidence completely supports every proposed "
            "value and qualification. Do not alter the value, field, entity, or relation."
        )
        payload = {
            "task": task,
            "target": candidate.target.to_dict(),
            "candidate_id": candidate.candidate_id,
            "field_path": candidate.field_path,
            "value": candidate.value,
            "benchmark_scope": candidate.benchmark_scope,
            "claim_entity": candidate.claim_entity,
            "relation": candidate.relation.value,
            "evidence": evidence,
        }
        logical = f"claim.{gate.value}.{candidate.candidate_id}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name=f"model_card_{gate.value}_v1",
            json_schema=schema,
            system_prompt=(
                "Apply only the named Model Card support gate to the supplied frozen "
                "evidence. Accept or withhold; never rewrite any candidate attribute."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=256,
            context_metadata={
                "stage": gate.value,
                "candidate_id": candidate.candidate_id,
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            item = _closed(value, {"status", "reason"}, "claim checker decision")
            if item["status"] not in {"accepted", "withheld"}:
                raise ProviderAdapterError("claim checker status is invalid")
            if item["reason"] not in reasons[item["status"]]:
                raise ProviderAdapterError("claim checker status/reason pair is invalid")

        result = self.runtime.invoke(
            spec,
            decision_name=f"{candidate.candidate_id}-{gate.value}.json",
            validator=validate,
        )
        validate(result.decision)
        return ProseCheckerDecision.for_candidate(
            candidate,
            gate=gate,
            checker=self.checker_id,
            method=f"bounded_openrouter_{gate.value}",
            status=DecisionStatus(result.decision["status"]),
            reason=result.decision["reason"],
        )


class OpenRouterFactChecker:
    """FactReasoner checker using only the request's bounded frozen contexts."""

    checker_id = FACT_CHECKER_ID
    checker_revision = ADAPTER_VERSION

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
        )

    def check(self, request: CheckRequest) -> CheckerResponse:
        if not isinstance(request, CheckRequest):
            raise ProviderAdapterError("FactReasoner checker requires a CheckRequest")
        chunk_ids = [item.chunk.chunk_id for item in request.contexts]
        schema = {
            "type": "object",
            "required": ["outcome", "reason_code", "cited_chunk_ids"],
            "properties": {
                "outcome": {"enum": ["support", "contradiction", "neutral"]},
                "reason_code": {
                    "enum": [
                        "support_in_context",
                        "contradiction_in_context",
                        "no_complete_support",
                    ]
                },
                "cited_chunk_ids": {
                    "type": "array",
                    "items": {"enum": chunk_ids},
                    "uniqueItems": True,
                    "maxItems": len(chunk_ids),
                },
            },
            "additionalProperties": False,
        }
        payload = {
            "hypothesis": request.hypothesis,
            "stage": request.stage.value,
            "fallback_complete": request.fallback_complete,
            "contexts": [
                {"chunk_id": item.chunk.chunk_id, "text": item.text}
                for item in request.contexts
            ],
            "rules": {
                "support_requires_complete_entailment": True,
                "contradiction_requires_explicit_conflict": True,
                "otherwise": "neutral",
            },
        }
        suffix = _digest(
            {
                "atom": request.atom.content_sha256,
                "stage": request.stage.value,
                "chunks": chunk_ids,
            }
        )[:16]
        logical = f"fact.{request.atom.atom_id}.{request.stage.value}.{suffix}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name="model_card_factreasoner_v1",
            json_schema=schema,
            system_prompt=(
                "Assess the explicit hypothesis only against the supplied frozen-source "
                "contexts. Return support, contradiction, or neutral with cited chunk IDs."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=512,
            context_metadata={
                "stage": "factreasoner",
                "atom_id": request.atom.atom_id,
                "check_stage": request.stage.value,
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            item = _closed(
                value,
                {"outcome", "reason_code", "cited_chunk_ids"},
                "FactReasoner decision",
            )
            expected_reason = {
                "support": "support_in_context",
                "contradiction": "contradiction_in_context",
                "neutral": "no_complete_support",
            }
            if item["outcome"] not in expected_reason:
                raise ProviderAdapterError("FactReasoner outcome is invalid")
            if item["reason_code"] != expected_reason[item["outcome"]]:
                raise ProviderAdapterError("FactReasoner outcome/reason pair is invalid")
            cited = item["cited_chunk_ids"]
            if not isinstance(cited, list) or len(cited) != len(set(cited)):
                raise ProviderAdapterError("FactReasoner citations are invalid")
            if not set(cited).issubset(chunk_ids):
                raise ProviderAdapterError("FactReasoner cited an unavailable chunk")
            if item["outcome"] in {"support", "contradiction"} and not cited:
                raise ProviderAdapterError("FactReasoner decisive outcome requires evidence")

        result = self.runtime.invoke(
            spec,
            decision_name=f"{request.atom.atom_id}-{request.stage.value}-{suffix}.json",
            validator=validate,
        )
        validate(result.decision)
        return CheckerResponse(
            outcome=CheckOutcome(result.decision["outcome"]),
            reason_code=result.decision["reason_code"],
            cited_chunk_ids=tuple(result.decision["cited_chunk_ids"]),
        )


class OpenRouterApplicabilityChecker:
    """Independent applicability gate for one taxonomy-grounded risk candidate."""

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
        )

    def assess(
        self,
        candidate: RiskCandidate,
        contexts: tuple[UseContext, ...],
    ) -> ApplicabilityDecision:
        if not isinstance(candidate, RiskCandidate) or not contexts:
            raise ProviderAdapterError("risk applicability requires candidate and contexts")
        if tuple(sorted(item.context_id for item in contexts)) != candidate.context_ids:
            raise ProviderAdapterError("risk applicability contexts are stale")
        schema = {
            "type": "object",
            "required": ["status", "reason", "rationale"],
            "properties": {
                "status": {"enum": ["accepted", "withheld"]},
                "reason": {
                    "enum": ["specific_use_context_supported", "risk_not_specific_to_context"]
                },
                "rationale": {"type": "string", "minLength": 20, "maxLength": 1600},
            },
            "additionalProperties": False,
        }
        payload = {
            "risk": {
                "risk_id": candidate.risk_id,
                "name": candidate.name,
                "description": candidate.description,
                "taxonomy": candidate.taxonomy.to_dict(),
            },
            "use_contexts": [item.to_dict() for item in contexts],
            "rules": {
                "candidate_mapping_is_not_confirmed_harm": True,
                "accept_only_if_specific_to_grounded_context": True,
                "do_not_invent_context_or_mitigation": True,
            },
        }
        logical = f"risk.applicability.{candidate.candidate_id}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name="model_card_risk_applicability_v1",
            json_schema=schema,
            system_prompt=(
                "Assess whether the taxonomy risk may specifically apply to the supplied "
                "evidence-backed use context. Do not treat it as publisher-reported harm."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=768,
            context_metadata={
                "stage": "risk_applicability",
                "risk_candidate_id": candidate.candidate_id,
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            item = _closed(
                value, {"status", "reason", "rationale"}, "risk applicability decision"
            )
            expected = {
                "accepted": "specific_use_context_supported",
                "withheld": "risk_not_specific_to_context",
            }
            if item["status"] not in expected or item["reason"] != expected[item["status"]]:
                raise ProviderAdapterError("risk applicability status/reason pair is invalid")
            if not isinstance(item["rationale"], str) or not 20 <= len(
                item["rationale"].strip()
            ) <= 1600:
                raise ProviderAdapterError("risk applicability rationale is invalid")

        result = self.runtime.invoke(
            spec,
            decision_name=f"{candidate.candidate_id}-applicability.json",
            validator=validate,
        )
        validate(result.decision)
        return ApplicabilityDecision.for_candidate(
            candidate,
            status=ApplicabilityStatus(result.decision["status"]),
            checker=CLAIM_CHECKER_ID,
            method="bounded_openrouter_use_context_applicability",
            reason=result.decision["reason"],
            rationale=result.decision["rationale"],
        )


def build_nexus_openrouter_inference_engine(
    *,
    provider: str,
    ledger_path: str | os.PathLike[str],
    decision_dir: str | os.PathLike[str],
    environment: Mapping[str, str] | None = None,
    transport: ProviderTransport | None = None,
    call: CallFunction = structured_json_call,
) -> Any:
    """Return an optional Nexus ``InferenceEngine`` backed by the exact runtime.

    Nexus performs its supported generic risk-selection flow and supplies the
    taxonomy-constrained response schema.  This adapter wraps root-array schemas
    in a strict object because the provider runtime deliberately accepts only
    closed JSON objects.
    """

    try:
        from ai_atlas_nexus.blocks.inference import (
            InferenceEngine,
            TextGenerationInferenceOutput,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise ProviderAdapterError("ai-atlas-nexus 1.2.4 is unavailable") from exc

    runtime = _Runtime.build(
        provider=provider,
        ledger_path=ledger_path,
        decision_dir=decision_dir,
        environment=environment,
        transport=transport,
        call=call,
    )

    class _OpenRouterNexusEngine(InferenceEngine):
        _inference_engine_type = "openrouter"

        def __init__(self) -> None:
            # Avoid Nexus base initialization: it creates another client and health
            # check, violating the single-runtime/no-hidden-retry invariant.
            self.model_name_or_path = MODEL_ID
            self.credentials = {}
            self.parameters = {"temperature": 0}
            self.concurrency_limit = 1
            self.auto_download_model = False
            self.client = None
            self.backend = self

        def prepare_credentials(self, credentials):
            return {}

        def create_client(self, credentials=None):
            return None

        def ping(self):
            return None

        def generate(
            self,
            prompts,
            response_format=None,
            postprocessors=None,
            verbose=True,
        ):
            if (
                not isinstance(prompts, list)
                or not prompts
                or not all(isinstance(item, str) and item for item in prompts)
            ):
                raise ProviderAdapterError("Nexus prompts are invalid")
            if not isinstance(response_format, dict):
                raise ProviderAdapterError("Nexus must provide a JSON Schema object")
            if postprocessors not in (None, [], ["list_of_str"], ["json_object"]):
                raise ProviderAdapterError("unsupported Nexus postprocessor")
            wrapped = {
                "type": "object",
                "required": ["prediction"],
                "properties": {"prediction": response_format},
                "additionalProperties": False,
            }
            Draft202012Validator.check_schema(wrapped)
            validator = Draft202012Validator(wrapped)
            outputs = []
            for prompt in prompts:
                prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                logical = f"nexus.risk_selection.{prompt_sha[:24]}"
                spec = StructuredCallSpec(
                    logical_call_id=logical,
                    attempt_id=logical + ".attempt1",
                    provider=runtime.provider,
                    schema_name="nexus_generic_risk_selection_v1",
                    json_schema=wrapped,
                    system_prompt=(
                        "Follow the AI Atlas Nexus generic risk-selection instruction and "
                        "return only values permitted by its supplied taxonomy schema."
                    ),
                    user_prompt=prompt,
                    max_output_tokens=2048,
                    context_metadata={
                        "stage": "nexus_risk_selection",
                        "instruction_sha256": prompt_sha,
                    },
                )

                def validate(value: Mapping[str, Any]) -> None:
                    errors = sorted(
                        validator.iter_errors(value),
                        key=lambda item: tuple(str(x) for x in item.absolute_path),
                    )
                    if errors:
                        raise ProviderAdapterError("Nexus decision violates its taxonomy schema")

                result = runtime.invoke(
                    spec,
                    decision_name=f"nexus-{prompt_sha[:24]}.json",
                    validator=validate,
                )
                validate(result.decision)
                receipt = getattr(result, "receipt", None)
                outputs.append(
                    TextGenerationInferenceOutput(
                        prediction=result.decision["prediction"],
                        input_tokens=getattr(receipt, "prompt_tokens", None),
                        output_tokens=getattr(receipt, "completion_tokens", None),
                        stop_reason="structured_output",
                        model_name_or_path=MODEL_ID,
                        inference_engine="openrouter",
                    )
                )
            return outputs

        def chat(
            self,
            messages,
            tools=None,
            response_format=None,
            postprocessors=None,
            verbose=True,
        ):
            if isinstance(messages, str):
                prompts = [messages]
            elif isinstance(messages, list) and all(isinstance(item, str) for item in messages):
                prompts = messages
            else:
                raise ProviderAdapterError("Nexus chat messages are unsupported")
            return self.generate(
                prompts,
                response_format=response_format,
                postprocessors=postprocessors,
                verbose=verbose,
            )

    return _OpenRouterNexusEngine()


__all__ = [
    "ADAPTER_VERSION",
    "CLAIM_CHECKER_ID",
    "FACT_CHECKER_ID",
    "OpenRouterApplicabilityChecker",
    "OpenRouterClaimChecker",
    "OpenRouterFactChecker",
    "OpenRouterQuoteExtractor",
    "ProviderAdapterError",
    "build_nexus_openrouter_inference_engine",
]
