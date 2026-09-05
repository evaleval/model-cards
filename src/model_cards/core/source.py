"""Exact, offline-first Hugging Face model snapshot adapter."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download

from .frontmatter import parse_frontmatter
from .records import SourceBundle, SourceFile, TargetIdentity


_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_MODEL_ID_RE = re.compile(r"^[^/@\s]+(?:/[^@\s]+)?$")


class ModelSourceError(RuntimeError):
    """A model snapshot could not be resolved without weakening its identity."""


def _is_gated_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return "gated" in text or "403" in text or "401" in text


def split_target(target: str) -> tuple[str, str]:
    """Split `model_id@revision`, retaining slashes inside the model id."""
    if not isinstance(target, str) or "@" not in target:
        raise ModelSourceError("target must be model_id@revision")
    model_id, revision = target.rsplit("@", 1)
    model_id, revision = model_id.strip(), revision.strip()
    if not _MODEL_ID_RE.fullmatch(model_id) or not revision:
        raise ModelSourceError("target must contain a canonical model id and revision")
    return model_id, revision


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_text_file(snapshot: Path, model_id: str, revision: str, name: str) -> SourceFile | None:
    path = snapshot / name
    if not path.is_file():
        return None
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ModelSourceError(f"source file is not UTF-8 text: {name}") from exc
    media_type = "text/markdown" if name.lower().endswith(".md") else "application/json"
    return SourceFile(
        name=name,
        source_uri=f"https://huggingface.co/{model_id}/blob/{revision}/{name}",
        sha256=_sha256(raw),
        size_bytes=len(raw),
        media_type=media_type,
        content=content,
    )


class HfModelSourceAdapter:
    """Resolve README/config from one exact Hugging Face model snapshot.

    Network fallback is deliberately opt-in. `snapshot_download` always receives
    `repo_type="model"` and the caller's revision; the returned directory name is
    the resolved commit recorded in the artifact.
    """

    def __init__(self, *, cache_dir: str | Path | None = None, allow_network: bool = False):
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self.allow_network = allow_network

    def _snapshot(self, model_id: str, revision: str, patterns: list[str]) -> str:
        return snapshot_download(
            repo_id=model_id,
            repo_type="model",
            revision=revision,
            allow_patterns=patterns,
            local_files_only=not self.allow_network,
            cache_dir=str(self.cache_dir) if self.cache_dir else None,
        )

    def collect(self, target: str, model_info: dict[str, Any] | None = None) -> SourceBundle:
        """Freeze README/config for the exact snapshot; model_info (the Hub's model_info
        fields, base_model tags, model-index, fetched by the caller through the composer's
        hf_model_metadata tool) is recorded verbatim in the bundle metadata when given."""
        model_id, requested_revision = split_target(target)
        gated_unavailable: list[str] = []
        try:
            snapshot_value = self._snapshot(model_id, requested_revision, ["README.md", "config.json"])
        except Exception as exc:
            # a gated repo serves its model card to an authenticated user but not its
            # weights or config.json; the bundle is then the README alone, recorded
            if not _is_gated_error(exc):
                mode = "local cache" if not self.allow_network else "Hugging Face Hub"
                raise ModelSourceError(f"cannot resolve {target} from {mode}: {exc}") from exc
            try:
                snapshot_value = self._snapshot(model_id, requested_revision, ["README.md"])
            except Exception as exc2:
                raise ModelSourceError(f"cannot resolve {target}: gated repo, README unavailable: "
                                       f"{exc2}") from exc2
            gated_unavailable = ["config.json"]

        snapshot = Path(snapshot_value).resolve()
        resolved_revision = snapshot.name
        if not _REVISION_RE.fullmatch(resolved_revision):
            raise ModelSourceError(
                f"snapshot did not resolve to a 40-character commit: {snapshot}"
            )
        if _REVISION_RE.fullmatch(requested_revision) and requested_revision != resolved_revision:
            raise ModelSourceError(
                f"resolved snapshot {resolved_revision} differs from requested commit "
                f"{requested_revision}"
            )

        identity = TargetIdentity(
            model_id=model_id,
            requested_revision=requested_revision,
            resolved_revision=resolved_revision,
        )
        files = tuple(
            item
            for name in ("README.md", "config.json")
            if (item := _read_text_file(snapshot, model_id, resolved_revision, name)) is not None
        )
        if not files:
            raise ModelSourceError(
                f"exact snapshot has neither README.md nor config.json: {target}")

        # A repository with weights and a config but no model card is still a model, and
        # its card is the config and the Hub manifest. Requiring a README refused
        # ontocord/wide_3b_sft_stage1.2-ss1-expert_fictional_lyrical outright, which has
        # a config.json and four safetensors shards.
        readme_file = next((item for item in files if item.name == "README.md"), None)
        readme = (readme_file.content if readme_file is not None else "") or ""
        config: dict[str, Any] = {}
        config_file = next((item for item in files if item.name == "config.json"), None)
        if config_file is not None and config_file.content:
            try:
                parsed = json.loads(config_file.content)
            except ValueError as exc:
                raise ModelSourceError("config.json is not valid JSON") from exc
            if not isinstance(parsed, dict):
                raise ModelSourceError("config.json must contain an object")
            config = parsed

        metadata = {
            "model_id": model_id,
            "requested_revision": requested_revision,
            "resolved_revision": resolved_revision,
            "repo_type": "model",
            "card_data": parse_frontmatter(readme),
            "config": config,
            "available_files": [item.name for item in files],
            "metadata_scope": ("frozen snapshot files plus the caller's Hub model_info"
                               if model_info is not None
                               else "frozen snapshot files; live Hub counters were not queried"),
        }
        if model_info is not None:
            metadata["model_info"] = model_info
        if gated_unavailable:
            metadata["gated_files_unavailable"] = gated_unavailable
        return SourceBundle(
            target=identity,
            repo_type="model",
            snapshot_path=str(snapshot),
            metadata=metadata,
            files=files,
            retrieved_at=datetime.now(timezone.utc),
            offline=not self.allow_network,
        )

    def freeze(self, target: str, destination: str | Path) -> SourceBundle:
        """Collect and materialize an auditable local source bundle."""
        bundle = self.collect(target)
        out = Path(destination)
        out.mkdir(parents=True, exist_ok=True)
        for item in bundle.files:
            if item.content is not None:
                (out / item.name).write_text(item.content, encoding="utf-8")
        (out / "source-bundle.json").write_text(
            bundle.model_dump_json(indent=2), encoding="utf-8"
        )
        return bundle


def load_source_bundle(path: str | Path) -> SourceBundle:
    """Load and revalidate a frozen source-bundle manifest."""
    manifest = Path(path)
    if manifest.is_dir():
        manifest = manifest / "source-bundle.json"
    return SourceBundle.model_validate_json(manifest.read_text(encoding="utf-8"))
