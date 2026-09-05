"""The pinned serving route and the process configuration read from the environment.

One place decides which model answers, on which provider, with which decoding
parameters, so the CLI, the batch runner and the probe cannot drift apart. The pin is
recorded in vault/llm_config.md; a provider change is a user decision, not a default.

Environment overrides (all optional, the defaults below are the recorded pin):
  MODELCARDS_OPENROUTER_MODEL   OpenRouter checkpoint slug
  MODELCARDS_PROVIDER_ORDER     comma separated provider order, fallbacks stay off
  MODELCARDS_TEMPERATURE        decoding temperature
  MODELCARDS_MAX_TOKENS         max completion tokens
  MODELCARDS_BUNDLE_DIR         default bundle root for the CLI
  MODELCARDS_OUT_DIR            default output root for the CLI
  MODELCARDS_ENV_FILE           dotenv file to load the credentials from
  MODELCARDS_FACTCHECK           "1" to run the final-claim pass, off by default
The credential is OPENROUTER_API_KEY, read from the environment and never printed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

MODEL_SLUG = "deepseek/deepseek-v4-flash-0731"
PROVIDER_ORDER = "Together"
TEMPERATURE = 0.0
MAX_COMPLETION_TOKENS = 16384

DEFAULT_BUNDLE_DIR = "bundles"
DEFAULT_OUT_DIR = "runs"

ROUTE: Dict[str, Any] = {
    "serving": "openrouter",
    "model": MODEL_SLUG,
    "provider_order": [PROVIDER_ORDER],
    "allow_fallbacks": False,
    "structured_outputs": "json_schema on every extraction and writer call",
    "temperature": TEMPERATURE,
    "max_completion_tokens": MAX_COMPLETION_TOKENS,
    "credential": "OPENROUTER_API_KEY",
}


def _composer_repo() -> Path:
    """The adjacent auto-benchmarkcard checkout, from the composer pin (no absolute paths)."""
    import json

    root = Path(__file__).resolve().parents[2]
    try:
        rel = json.loads((root / "composer-pin.json").read_text(encoding="utf-8"))["repository"]
    except (OSError, ValueError, KeyError):
        rel = "../auto-benchmarkcard"
    return (root / rel).resolve()


def load_env(path: Optional[str | Path] = None) -> bool:
    """Load credentials from a dotenv file into os.environ without overwriting what is
    already set. Returns whether a file was read. Nothing is printed."""
    candidate = Path(path or os.environ.get("MODELCARDS_ENV_FILE") or (_composer_repo() / ".env"))
    if not candidate.is_file():
        return False
    for line in candidate.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)
    return True


def route() -> Dict[str, Any]:
    """The effective route after environment overrides."""
    out = dict(ROUTE)
    out["model"] = os.environ.get("MODELCARDS_OPENROUTER_MODEL", MODEL_SLUG)
    out["provider_order"] = [p.strip() for p in
                             os.environ.get("MODELCARDS_PROVIDER_ORDER", PROVIDER_ORDER).split(",")
                             if p.strip()]
    out["temperature"] = float(os.environ.get("MODELCARDS_TEMPERATURE", TEMPERATURE))
    out["max_completion_tokens"] = int(os.environ.get("MODELCARDS_MAX_TOKENS", MAX_COMPLETION_TOKENS))
    return out


def build_llm():
    """An LLMHandler bound to the effective route. Requires OPENROUTER_API_KEY."""
    cfg = route()
    os.environ["OPENROUTER_MODEL_ID"] = cfg["model"]
    os.environ["OPENROUTER_PROVIDER_ORDER"] = ",".join(cfg["provider_order"])
    os.environ.pop("OPENROUTER_QUANTIZATION", None)
    from auto_benchmarkcard.llm_handler import LLMHandler

    return LLMHandler(engine_type="openrouter", model_name=cfg["model"],
                      parameters={"temperature": cfg["temperature"],
                                  "max_completion_tokens": cfg["max_completion_tokens"]})


def factcheck_enabled() -> bool:
    """Whether the final-claim pass runs. Off by default: the pinned route returns no
    token logprobs (probed 2026-09-04), so FactReasoner's probabilistic layer would leave
    every atom at 0.5 and report nothing. Turning it on needs a route that has them,
    which is a provider decision."""
    return os.environ.get("MODELCARDS_FACTCHECK", "").strip() in ("1", "true", "yes")


def factcheck_route_defaults() -> None:
    """Point FactReasoner's generic OpenAI-compatible route at the pinned serving route
    unless the environment already names another one."""
    cfg = route()
    os.environ.setdefault("FACTREASONER_MODEL", cfg["model"])
    os.environ.setdefault("FACTREASONER_API_BASE",
                          os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        os.environ.setdefault("FACTREASONER_API_KEY", key)


def bundle_dir_default() -> str:
    return os.environ.get("MODELCARDS_BUNDLE_DIR", DEFAULT_BUNDLE_DIR)


def out_dir_default() -> str:
    return os.environ.get("MODELCARDS_OUT_DIR", DEFAULT_OUT_DIR)
