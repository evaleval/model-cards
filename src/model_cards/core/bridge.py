"""Narrow, revision-pinned bridge to the adjacent Benchmark Card composer.

Only exact-span normalization/verification and deterministic document structure
are reused. Importing the benchmark-specific schema or orchestration here would
erase the project boundary this package is meant to establish.
"""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class ComposerBridgeError(RuntimeError):
    """The declared local composer interface cannot be loaded safely."""


@dataclass(frozen=True)
class ComposerBridge:
    repository: Path
    commit: str
    normalize_ws: Callable[[str], str]
    verify_quote: Callable[[str, str], int | None]
    build_index: Callable[[str], Any]

    def verify_span(self, exact_span: str, source_text: str) -> tuple[int, int]:
        """Return normalized coordinates for an exact evidence span."""
        quote = self.normalize_ws(exact_span or "")
        source = self.normalize_ws(source_text or "")
        start = self.verify_quote(quote, source)
        if start is None:
            raise ComposerBridgeError("evidence span is not an exact normalized substring")
        return start, start + len(quote)

    def structural_anchor(self, source_text: str, char_start: int) -> dict[str, Any]:
        """Map a verified normalized offset to deterministic section/table context."""
        index = self.build_index(source_text or "")
        section = index.locate(char_start)
        table = index.table_at(char_start)
        return {
            "section_path": list(section.path) if section is not None else [],
            "region": section.region if section is not None else None,
            "table_id": table.table_id if table is not None else None,
            "table_caption": table.caption if table is not None else None,
            "table_header": list(table.header_row) if table is not None else [],
            "table_row_labels": list(table.row_labels) if table is not None else [],
        }

    def verify_table_row_span(
        self,
        exact_row: str,
        source_text: str,
        *,
        table_block: str,
        table_occurrence_index: int = 0,
        row_occurrence_index: int = 0,
    ) -> tuple[int, int]:
        """Verify a row inside the exact local table block, without index coupling."""

        if table_occurrence_index < 0 or row_occurrence_index < 0:
            raise ComposerBridgeError("table and row occurrence indices cannot be negative")
        source = self.normalize_ws(source_text or "")
        block = self.normalize_ws(table_block or "")
        quote = self.normalize_ws(exact_row or "")
        cursor = 0
        table_start = -1
        for _ in range(table_occurrence_index + 1):
            table_start = source.find(block, cursor)
            if table_start < 0:
                raise ComposerBridgeError("exact table block is absent from source")
            cursor = table_start + len(block)
        table_end = table_start + len(block)
        cursor = table_start
        start = -1
        for _ in range(row_occurrence_index + 1):
            start = source.find(quote, cursor, table_end)
            if start < 0:
                raise ComposerBridgeError("table row is absent from the selected table")
            cursor = start + len(quote)
        return start, start + len(quote)


def _package_root() -> Path:
    """The repository root, which is where composer-pin.json lives."""
    return Path(__file__).resolve().parents[3]


def _read_pin(package_root: Path) -> dict[str, Any]:
    pin_path = package_root / "composer-pin.json"
    try:
        data = json.loads(pin_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ComposerBridgeError(f"cannot read composer pin: {pin_path}") from exc
    if not isinstance(data.get("commit"), str) or len(data["commit"]) != 40:
        raise ComposerBridgeError("composer pin must contain a 40-character commit")
    return data


def _head(repository: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ComposerBridgeError(f"cannot resolve composer revision: {repository}") from exc


def _interface_source_paths(pin: dict[str, Any]) -> tuple[str, ...]:
    paths = {
        "src/" + interface.rsplit(".", 1)[0].replace(".", "/") + ".py"
        for interface in pin.get("interfaces", [])
        if isinstance(interface, str) and "." in interface
    }
    if not paths:
        raise ComposerBridgeError("composer pin must declare imported interfaces")
    return tuple(sorted(paths))


def _require_clean_interfaces(repository: Path, paths: tuple[str, ...]) -> None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                *paths,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ComposerBridgeError(
            f"cannot verify pinned composer interface bytes: {repository}"
        ) from exc
    if result.stdout.strip():
        raise ComposerBridgeError(
            "pinned composer interface files have staged, unstaged, or untracked drift: "
            + ", ".join(paths)
        )


def _load_source_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ComposerBridgeError(f"cannot create module spec for pinned interface: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _load_pinned_primitives(source_root: Path) -> tuple[Any, Any, Any]:
    """Load the two dependency-light files without executing package ``__init__``."""

    evidence_path = source_root / "auto_benchmarkcard/tools/composer/evidence.py"
    docstructure_path = source_root / "auto_benchmarkcard/tools/composer/docstructure.py"
    evidence_private = "model_cards.core._pinned_composer_evidence"
    docstructure_private = "model_cards.core._pinned_composer_docstructure"
    try:
        evidence = _load_source_module(evidence_private, evidence_path)
    except Exception as exc:
        raise ComposerBridgeError("cannot load pinned composer evidence primitives") from exc

    temporary_names = (
        "auto_benchmarkcard",
        "auto_benchmarkcard.tools",
        "auto_benchmarkcard.tools.composer",
        "auto_benchmarkcard.tools.composer.evidence",
    )
    missing = object()
    prior = {name: sys.modules.get(name, missing) for name in temporary_names}
    try:
        for name, path in (
            ("auto_benchmarkcard", source_root / "auto_benchmarkcard"),
            ("auto_benchmarkcard.tools", source_root / "auto_benchmarkcard/tools"),
            (
                "auto_benchmarkcard.tools.composer",
                source_root / "auto_benchmarkcard/tools/composer",
            ),
        ):
            namespace = types.ModuleType(name)
            namespace.__path__ = [str(path)]  # type: ignore[attr-defined]
            sys.modules[name] = namespace
        sys.modules["auto_benchmarkcard.tools.composer.evidence"] = evidence
        docstructure = _load_source_module(docstructure_private, docstructure_path)
    except Exception as exc:
        sys.modules.pop(docstructure_private, None)
        raise ComposerBridgeError("cannot load pinned document-structure primitive") from exc
    finally:
        for name, previous in prior.items():
            if previous is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous

    return evidence.normalize_ws, evidence.verify_quote, docstructure.build_index


def load_composer_bridge(*, allow_unpinned: bool = False) -> ComposerBridge:
    """Load the three declared primitives after checking the adjacent Git pin."""
    package_root = _package_root()
    pin = _read_pin(package_root)
    repository = (package_root / pin["repository"]).resolve()
    commit = _head(repository)
    if commit != pin["commit"] and not allow_unpinned:
        raise ComposerBridgeError(
            f"composer revision drift: expected {pin['commit']}, found {commit}"
        )
    if not allow_unpinned:
        _require_clean_interfaces(repository, _interface_source_paths(pin))

    source_root = repository / "src"
    if not source_root.is_dir():
        raise ComposerBridgeError(f"composer source directory is missing: {source_root}")
    try:
        normalize_ws, verify_quote, build_index = _load_pinned_primitives(source_root)
    except Exception as exc:  # import failures must not silently replace the shared logic
        raise ComposerBridgeError("cannot import pinned composer primitives") from exc

    return ComposerBridge(
        repository=repository,
        commit=commit,
        normalize_ws=normalize_ws,
        verify_quote=verify_quote,
        build_index=build_index,
    )
