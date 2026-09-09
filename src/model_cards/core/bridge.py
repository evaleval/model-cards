"""Narrow, revision-pinned bridge to an installed or source Benchmark Card composer.

Only exact-span normalization/verification and deterministic document structure
are reused. Importing the benchmark-specific schema or orchestration here would
erase the project boundary this package is meant to establish.
"""

from __future__ import annotations

import json
import hashlib
import importlib.util
import importlib.metadata
import importlib.resources
import re
import threading
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
    repository: Path | None
    source_root: Path
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
    return Path(__file__).resolve().parents[3]


def _read_pin(package_root: Path) -> dict[str, Any]:
    # Source/editable installs read the tracked canonical file. Wheels contain a
    # build-time copy; setup.py also derives the VCS requirement from this file.
    pin_path = package_root / "composer-pin.json"
    if not (package_root / "src/model_cards/core/bridge.py").is_file():
        pin_path = importlib.resources.files("model_cards").joinpath("resources/composer-pin.json")
    try:
        data = json.loads(pin_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ComposerBridgeError(f"cannot read composer pin: {pin_path}") from exc
    if not isinstance(data, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(data.get("commit", ""))):
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


def _interface_digest(source_root: Path, paths: tuple[str, ...]) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in paths:
        target = source_root / path.removeprefix("src/")
        try:
            digests[path] = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError as exc:
            raise ComposerBridgeError(
                f"cannot read pinned composer interface: {target}"
            ) from exc
    return digests


def _require_pinned_interface_bytes(source_root: Path, pin: dict[str, Any],
                                    paths: tuple[str, ...]) -> None:
    """The imported interface files must be the bytes the pin recorded.

    This used to shell out to `git status` once per target. `git status` refreshes and
    rewrites .git/index, so under a concurrent batch the calls raced and six of the 247
    targets on 2026-09-05 died on a drift report for a tree that was clean before and
    after the run. Hashing the files is race-free, needs no subprocess, and pins the
    bytes rather than their agreement with whatever HEAD happens to be.
    """

    expected = pin.get("interface_sha256")
    if not isinstance(expected, dict) or not expected:
        raise ComposerBridgeError(
            "composer pin must record interface_sha256 for its declared interfaces"
        )
    found = _interface_digest(source_root, paths)
    drifted = sorted(path for path in paths if found.get(path) != expected.get(path))
    if drifted:
        raise ComposerBridgeError(
            "pinned composer interface files do not match the recorded bytes: "
            + ", ".join(drifted)
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


def _source_checkout(source_root: Path) -> Path | None:
    """Recognize the project's src layout without borrowing a parent repo's HEAD."""
    repository = source_root.parent
    if source_root.name == "src" and (repository / ".git").exists():
        return repository
    return None


def _installed_revision(source_root: Path, pin: dict[str, Any]) -> str:
    """Only pip's VCS provenance can identify a non-editable installed revision."""
    try:
        distribution = importlib.metadata.distribution("auto-benchmarkcard")
        installed_init = Path(distribution.locate_file("auto_benchmarkcard/__init__.py")).resolve()
        if installed_init != source_root / "auto_benchmarkcard/__init__.py":
            raise ComposerBridgeError("composer distribution does not own the importable package")
        data = json.loads(distribution.read_text("direct_url.json") or "null")
    except (importlib.metadata.PackageNotFoundError, OSError, ValueError) as exc:
        raise ComposerBridgeError("cannot read installed composer VCS provenance") from exc
    if not isinstance(data, dict):
        raise ComposerBridgeError("installed composer is missing direct_url.json VCS provenance")
    vcs = data.get("vcs_info", {})
    commit = vcs.get("commit_id") if isinstance(vcs, dict) else None
    if (not isinstance(vcs, dict) or vcs.get("vcs") != "git"
            or not re.fullmatch(r"[0-9a-f]{40}", str(commit or ""))):
        raise ComposerBridgeError("installed composer needs a full Git commit in VCS provenance")
    expected_url = pin.get("repository_url")
    actual_url = data.get("url")
    if (not isinstance(expected_url, str) or not isinstance(actual_url, str)
            or actual_url.removesuffix("/").removesuffix(".git")
            != expected_url.removesuffix("/").removesuffix(".git")):
        raise ComposerBridgeError("installed composer VCS repository does not match the pin")
    return commit


def _require_same_import_source(source_root: Path) -> None:
    """Do not validate one checkout while the generator executes another."""
    package = source_root / "auto_benchmarkcard"
    for name, module in tuple(sys.modules.items()):
        if name != "auto_benchmarkcard" and not name.startswith("auto_benchmarkcard."):
            continue
        if module is None:
            continue
        locations = list(getattr(module, "__path__", ()))
        origin = getattr(module, "__file__", None)
        if origin:
            locations.append(origin)
        if not locations or any(not Path(path).resolve().is_relative_to(package) for path in locations):
            raise ComposerBridgeError(f"loaded composer module uses a different source: {name}")


def _resolve_composer_source(package_root: Path, pin: dict[str, Any]) -> tuple[Path, Path | None, str]:
    try:
        spec = importlib.util.find_spec("auto_benchmarkcard")
    except (ImportError, ValueError) as exc:
        raise ComposerBridgeError("cannot resolve the importable composer package") from exc
    if spec is not None:
        if not spec.origin:
            raise ComposerBridgeError("composer must be a regular Python package")
        source_root = Path(spec.origin).resolve().parent.parent
        repository = _source_checkout(source_root)
        commit = _head(repository) if repository else _installed_revision(source_root, pin)
    else:
        # Keep the dependency-light bridge usable in a source checkout. Installed
        # wheels must get their composer through the documented generate extra.
        if not (package_root / "src/model_cards/core/bridge.py").is_file():
            raise ComposerBridgeError("composer is not installed; install evaleval-model-cards[generate]")
        repository = (package_root / pin["repository"]).resolve()
        source_root = repository / "src"
        if _source_checkout(source_root) != repository:
            raise ComposerBridgeError(f"composer source checkout is missing: {repository}")
        commit = _head(repository)
    if not (source_root / "auto_benchmarkcard/__init__.py").is_file():
        raise ComposerBridgeError(f"composer source directory is missing: {source_root}")
    _require_same_import_source(source_root)
    return source_root, repository, commit


_PRIMITIVE_IMPORT_LOCK = threading.RLock()


def load_composer_bridge(*, allow_unpinned: bool = False) -> ComposerBridge:
    """Verify the actual import source using Git or pip VCS provenance and hashes.

    An importable package takes precedence over the optional adjacent checkout.
    Missing or ambiguous provenance fails even in allow_unpinned mode: artifacts
    must still record a known revision. The override permits revision/byte drift.
    """
    with _PRIMITIVE_IMPORT_LOCK:
        return _load_composer_bridge(allow_unpinned=allow_unpinned)


def _load_composer_bridge(*, allow_unpinned: bool) -> ComposerBridge:
    package_root = _package_root()
    pin = _read_pin(package_root)
    source_root, repository, commit = _resolve_composer_source(package_root, pin)
    if commit != pin["commit"] and not allow_unpinned:
        raise ComposerBridgeError(
            f"composer revision drift: expected {pin['commit']}, found {commit}"
        )
    if not allow_unpinned:
        _require_pinned_interface_bytes(source_root, pin, _interface_source_paths(pin))

    try:
        normalize_ws, verify_quote, build_index = _load_pinned_primitives(source_root)
    except Exception as exc:  # import failures must not silently replace the shared logic
        raise ComposerBridgeError("cannot import pinned composer primitives") from exc

    return ComposerBridge(
        repository=repository,
        source_root=source_root,
        commit=commit,
        normalize_ws=normalize_ws,
        verify_quote=verify_quote,
        build_index=build_index,
    )
