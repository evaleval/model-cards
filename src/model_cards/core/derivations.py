"""Pure deterministic mappings shared by composition and artifact validation."""

from __future__ import annotations

from typing import Any


# Keys that only a mixture-of-experts config carries. num_experts_per_tok and
# n_routed_experts are the DeepSeek and Qwen spellings, num_local_experts the Mixtral
# one, moe_intermediate_size the shared marker of an expert FFN.
_MOE_CONFIG_KEYS = (
    "num_local_experts", "num_experts", "expert_num", "n_routed_experts",
    "num_routed_experts", "num_experts_per_tok", "moe_intermediate_size",
    "moe_num_experts", "n_shared_experts", "num_shared_experts", "ffn_config",
)


def derive_architecture_type(
    config: dict[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    architectures = [str(value) for value in config.get("architectures") or []]
    model_type = str(config.get("model_type") or "").lower()
    inputs: dict[str, Any] = {
        "architectures": architectures,
        "model_type": model_type,
    }
    joined = " ".join(architectures).lower()
    # A config declares a mixture of experts under whichever key its family chose.
    # Reading only three of them called DeepSeek-V3 a dense model on its own card, one
    # field away from an identity.model_type that said 671B total and 37B activated.
    moe_keys = [key for key in _MOE_CONFIG_KEYS if config.get(key)]
    if moe_keys:
        inputs["moe_config_keys"] = sorted(moe_keys)
        return "mixture-of-experts", inputs
    if "mamba" in model_type or "mamba" in joined:
        return "state-space", inputs
    if "forcausallm" in joined or model_type in {"llama", "gpt2", "qwen2", "qwen3"}:
        return "dense decoder-only", inputs
    if (
        "whisper" in model_type
        or "encoderdecoder" in joined
        or "objectdetection" in joined
    ):
        return "encoder-decoder", inputs
    if "diffusion" in model_type or "diffusion" in joined:
        return "diffusion", inputs
    return None, inputs


def derive_modalities(
    card_data: dict[str, Any], config: dict[str, Any]
) -> tuple[dict[str, list[str]] | None, dict[str, Any]]:
    pipeline = str(card_data.get("pipeline_tag") or "").lower()
    architectures = " ".join(
        str(value) for value in config.get("architectures") or []
    ).lower()
    inputs: dict[str, Any] = {
        "pipeline_tag": pipeline,
        "architectures": architectures,
    }
    if pipeline == "text-generation":
        return {"input": ["text"], "output": ["text"]}, inputs
    if pipeline == "automatic-speech-recognition":
        return {"input": ["audio"], "output": ["text"]}, inputs
    if pipeline in {"image-to-text", "image-classification"}:
        output = "text" if pipeline == "image-to-text" else "labels"
        return {"input": ["image"], "output": [output]}, inputs
    if "objectdetection" in architectures:
        return {
            "input": ["image"],
            "output": ["bounding boxes", "labels"],
        }, inputs
    return None, inputs


__all__ = ["derive_architecture_type", "derive_modalities"]
