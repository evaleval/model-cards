"""Deterministic, fail-closed text extraction from already-frozen PDF bytes.

This module is deliberately independent of source discovery and collection.  It
never accepts a URL or path, performs no network access or OCR, and does not
remove references or other document sections.  A short-lived child process
contains the parser so the caller can enforce wall-clock and operating-system
resource limits around untrusted, immutable bytes.

Only the extracted text is retained in memory.  :meth:`PdfExtractionResult.to_dict`
is body-free and records the source digest, parser identity, limits, outcome,
and (when successful) the digest of the normalized text.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from typing import Any, Mapping


PDF_EXTRACTOR_VERSION = "frozen-pdf-text/v1"
PDF_PARSER_NAME = "pypdf"
PDF_PARSER_VERSION = "6.4.0"

DEFAULT_MAX_SOURCE_BYTES = 8_000_000
DEFAULT_MAX_PAGES = 256
DEFAULT_MAX_TEXT_CHARACTERS = 2_000_000
DEFAULT_WALL_TIME_SECONDS = 15.0
DEFAULT_CPU_TIME_SECONDS = 10
DEFAULT_MAX_OPEN_FILES = 64

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_WORKER_FLAG = "--frozen-pdf-worker"


class PdfExtractionError(ValueError):
    """The PDF extraction request or worker result is structurally invalid."""


class PdfExtractionStatus(str, Enum):
    """Closed outcome of one bounded extraction attempt."""

    EXTRACTED = "extracted"
    ENCRYPTED = "encrypted"
    MALFORMED = "malformed"
    IMAGE_ONLY = "image_only"
    EMPTY = "empty"
    UNSAFE_TEXT = "unsafe_text"
    SOURCE_LIMIT = "source_limit"
    PAGE_LIMIT = "page_limit"
    TEXT_LIMIT = "text_limit"
    TIME_LIMIT = "time_limit"
    RESOURCE_LIMIT = "resource_limit"
    PARSER_UNAVAILABLE = "parser_unavailable"
    ISOLATION_UNAVAILABLE = "isolation_unavailable"
    FAILED = "failed"


_REASONS_BY_STATUS = {
    PdfExtractionStatus.EXTRACTED: frozenset({"extracted_text"}),
    PdfExtractionStatus.ENCRYPTED: frozenset({"encrypted_pdf"}),
    PdfExtractionStatus.MALFORMED: frozenset(
        {"malformed_pdf", "malformed_page_tree", "malformed_page_content"}
    ),
    PdfExtractionStatus.IMAGE_ONLY: frozenset({"image_only_pdf"}),
    PdfExtractionStatus.EMPTY: frozenset({"empty_pdf", "no_extractable_text"}),
    PdfExtractionStatus.UNSAFE_TEXT: frozenset({"unsafe_text_controls"}),
    PdfExtractionStatus.SOURCE_LIMIT: frozenset({"source_byte_limit"}),
    PdfExtractionStatus.PAGE_LIMIT: frozenset({"page_count_limit"}),
    PdfExtractionStatus.TEXT_LIMIT: frozenset({"text_character_limit"}),
    PdfExtractionStatus.TIME_LIMIT: frozenset({"wall_time_limit"}),
    PdfExtractionStatus.RESOURCE_LIMIT: frozenset(
        {"worker_resource_limit", "worker_memory_exhausted"}
    ),
    PdfExtractionStatus.PARSER_UNAVAILABLE: frozenset(
        {"parser_not_installed", "parser_version_mismatch"}
    ),
    PdfExtractionStatus.ISOLATION_UNAVAILABLE: frozenset(
        {
            "worker_launch_failed",
            "posix_resource_limits_unavailable",
            "posix_resource_limits_failed",
        }
    ),
    PdfExtractionStatus.FAILED: frozenset(
        {
            "worker_failed",
            "worker_protocol_limit",
            "worker_protocol_invalid",
            "unexpected_extraction_failure",
        }
    ),
}


@dataclass(frozen=True)
class PdfExtractionLimits:
    """Resource envelope for one frozen PDF.

    The byte, page, and text caps bound parser input and retained output.  The
    wall-clock cap is enforced by the parent process.  The child additionally
    receives a CPU-time limit, cannot create non-empty regular files, and has a
    bounded descriptor table.  These controls are intentionally independent of
    any limits used when the source bytes were originally collected.
    """

    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES
    max_pages: int = DEFAULT_MAX_PAGES
    max_text_characters: int = DEFAULT_MAX_TEXT_CHARACTERS
    wall_time_seconds: float = DEFAULT_WALL_TIME_SECONDS
    cpu_time_seconds: int = DEFAULT_CPU_TIME_SECONDS
    max_open_files: int = DEFAULT_MAX_OPEN_FILES

    def __post_init__(self) -> None:
        integer_bounds = {
            "max_source_bytes": (1, 64_000_000),
            "max_pages": (1, 2_048),
            "max_text_characters": (1, 16_000_000),
            "cpu_time_seconds": (1, 120),
            "max_open_files": (16, 256),
        }
        for name, (minimum, maximum) in integer_bounds.items():
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise PdfExtractionError(
                    f"{name} must be an integer between {minimum} and {maximum}"
                )
        wall_time = self.wall_time_seconds
        if (
            isinstance(wall_time, bool)
            or not isinstance(wall_time, (int, float))
            or not math.isfinite(float(wall_time))
            or not 0.1 <= float(wall_time) <= 180.0
        ):
            raise PdfExtractionError(
                "wall_time_seconds must be finite and between 0.1 and 180.0"
            )
        object.__setattr__(self, "wall_time_seconds", float(wall_time))

    def to_dict(self) -> dict[str, int | float]:
        return {
            "max_source_bytes": self.max_source_bytes,
            "max_pages": self.max_pages,
            "max_text_characters": self.max_text_characters,
            "wall_time_seconds": self.wall_time_seconds,
            "cpu_time_seconds": self.cpu_time_seconds,
            "max_open_files": self.max_open_files,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PdfExtractionLimits":
        item = _exact_mapping(
            value,
            {
                "max_source_bytes",
                "max_pages",
                "max_text_characters",
                "wall_time_seconds",
                "cpu_time_seconds",
                "max_open_files",
            },
            "PDF extraction limits",
        )
        return cls(
            max_source_bytes=item["max_source_bytes"],
            max_pages=item["max_pages"],
            max_text_characters=item["max_text_characters"],
            wall_time_seconds=item["wall_time_seconds"],
            cpu_time_seconds=item["cpu_time_seconds"],
            max_open_files=item["max_open_files"],
        )


@dataclass(frozen=True)
class PdfExtractionResult:
    """Typed result of extracting one immutable byte string.

    ``text`` is present only for ``EXTRACTED`` and is intentionally omitted
    from :meth:`to_dict`.  ``output_sha256`` binds that in-memory text without
    serializing source-derived content into an audit or publication artifact.
    """

    status: PdfExtractionStatus
    reason_code: str
    source_sha256: str
    source_byte_size: int
    limits: PdfExtractionLimits
    page_count: int | None = None
    text: str | None = None
    output_sha256: str | None = None
    extractor_version: str = PDF_EXTRACTOR_VERSION
    parser_name: str = PDF_PARSER_NAME
    parser_version: str = PDF_PARSER_VERSION

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", PdfExtractionStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise PdfExtractionError("PDF extraction status is invalid") from exc
        if self.extractor_version != PDF_EXTRACTOR_VERSION:
            raise PdfExtractionError("PDF extractor version is unsupported")
        if (
            self.parser_name != PDF_PARSER_NAME
            or self.parser_version != PDF_PARSER_VERSION
        ):
            raise PdfExtractionError("PDF parser identity is unsupported")
        if not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(
            self.reason_code
        ):
            raise PdfExtractionError("PDF extraction reason code is invalid")
        if self.reason_code not in _REASONS_BY_STATUS[self.status]:
            raise PdfExtractionError("PDF extraction status and reason disagree")
        if not isinstance(self.source_sha256, str) or not _DIGEST_RE.fullmatch(
            self.source_sha256
        ):
            raise PdfExtractionError("PDF source digest is invalid")
        if (
            isinstance(self.source_byte_size, bool)
            or not isinstance(self.source_byte_size, int)
            or self.source_byte_size < 0
        ):
            raise PdfExtractionError("PDF source byte size is invalid")
        if not isinstance(self.limits, PdfExtractionLimits):
            raise PdfExtractionError("PDF extraction limits are invalid")
        if self.page_count is not None and (
            isinstance(self.page_count, bool)
            or not isinstance(self.page_count, int)
            or self.page_count < 0
        ):
            raise PdfExtractionError("PDF page count is invalid")

        source_over_limit = self.source_byte_size > self.limits.max_source_bytes
        if source_over_limit != (self.status is PdfExtractionStatus.SOURCE_LIMIT):
            raise PdfExtractionError("PDF source-limit outcome is inconsistent")
        if self.status is PdfExtractionStatus.PAGE_LIMIT:
            if self.page_count is None or self.page_count <= self.limits.max_pages:
                raise PdfExtractionError("PDF page-limit outcome is inconsistent")
        elif self.page_count is not None and self.page_count > self.limits.max_pages:
            raise PdfExtractionError("PDF page count exceeds the admitted limit")

        if self.status is PdfExtractionStatus.EXTRACTED:
            if not isinstance(self.text, str) or not self.text:
                raise PdfExtractionError("successful PDF extraction requires text")
            expected = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
            if self.output_sha256 != expected:
                raise PdfExtractionError("PDF output digest does not match text")
            if self.page_count is None or self.page_count < 1:
                raise PdfExtractionError("successful PDF extraction requires pages")
            if len(self.text) > self.limits.max_text_characters:
                raise PdfExtractionError("PDF output exceeds the text limit")
        elif self.text is not None or self.output_sha256 is not None:
            raise PdfExtractionError(
                "unsuccessful PDF extraction cannot retain output text"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic body-free metadata for audit and replay."""

        return {
            "extractor_version": self.extractor_version,
            "parser": {
                "name": self.parser_name,
                "version": self.parser_version,
            },
            "status": self.status.value,
            "reason_code": self.reason_code,
            "source_sha256": self.source_sha256,
            "source_byte_size": self.source_byte_size,
            "limits": self.limits.to_dict(),
            "page_count": self.page_count,
            "output_sha256": self.output_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())


def extract_pdf_text(
    frozen_bytes: bytes,
    *,
    limits: PdfExtractionLimits | None = None,
) -> PdfExtractionResult:
    """Extract text from already-frozen PDF bytes in a bounded child process.

    No source location is accepted by this API.  This prevents the parser seam
    from fetching, reopening, or otherwise changing the immutable input.
    """

    if not isinstance(frozen_bytes, bytes):
        raise PdfExtractionError("frozen PDF input must be bytes")
    active_limits = PdfExtractionLimits() if limits is None else limits
    if not isinstance(active_limits, PdfExtractionLimits):
        raise PdfExtractionError("limits must be PdfExtractionLimits")
    source_digest = hashlib.sha256(frozen_bytes).hexdigest()
    source_size = len(frozen_bytes)
    if source_size > active_limits.max_source_bytes:
        return _result(
            PdfExtractionStatus.SOURCE_LIMIT,
            "source_byte_limit",
            source_digest,
            source_size,
            active_limits,
        )

    limits_payload = base64.urlsafe_b64encode(
        _canonical_json(active_limits.to_dict())
    ).decode("ascii")
    command = (
        sys.executable,
        str(Path(__file__).resolve()),
        _WORKER_FLAG,
        limits_payload,
    )
    try:
        completed = subprocess.run(
            command,
            input=frozen_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=active_limits.wall_time_seconds,
            check=False,
            env=_worker_environment(),
        )
    except subprocess.TimeoutExpired:
        return _result(
            PdfExtractionStatus.TIME_LIMIT,
            "wall_time_limit",
            source_digest,
            source_size,
            active_limits,
        )
    except OSError:
        return _result(
            PdfExtractionStatus.ISOLATION_UNAVAILABLE,
            "worker_launch_failed",
            source_digest,
            source_size,
            active_limits,
        )

    if completed.returncode != 0:
        resource_signals = {
            getattr(signal, "SIGKILL", -999),
            getattr(signal, "SIGXCPU", -998),
            getattr(signal, "SIGXFSZ", -997),
        }
        status = (
            PdfExtractionStatus.RESOURCE_LIMIT
            if completed.returncode < 0 and -completed.returncode in resource_signals
            else PdfExtractionStatus.FAILED
        )
        reason = (
            "worker_resource_limit"
            if status is PdfExtractionStatus.RESOURCE_LIMIT
            else "worker_failed"
        )
        return _result(
            status,
            reason,
            source_digest,
            source_size,
            active_limits,
        )

    maximum_protocol_bytes = active_limits.max_text_characters * 12 + 65_536
    if len(completed.stdout) > maximum_protocol_bytes:
        return _result(
            PdfExtractionStatus.FAILED,
            "worker_protocol_limit",
            source_digest,
            source_size,
            active_limits,
        )
    try:
        worker = _decode_worker_result(completed.stdout)
    except (PdfExtractionError, UnicodeDecodeError, json.JSONDecodeError):
        return _result(
            PdfExtractionStatus.FAILED,
            "worker_protocol_invalid",
            source_digest,
            source_size,
            active_limits,
        )

    text = worker["text"]
    output_digest = (
        hashlib.sha256(text.encode("utf-8")).hexdigest()
        if isinstance(text, str)
        else None
    )
    try:
        return PdfExtractionResult(
            status=worker["status"],
            reason_code=worker["reason_code"],
            source_sha256=source_digest,
            source_byte_size=source_size,
            limits=active_limits,
            page_count=worker["page_count"],
            text=text,
            output_sha256=output_digest,
        )
    except PdfExtractionError:
        return _result(
            PdfExtractionStatus.FAILED,
            "worker_protocol_invalid",
            source_digest,
            source_size,
            active_limits,
        )


def _worker_environment() -> dict[str, str]:
    """Return a small credential-free environment for the parser child."""

    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
    }
    # Windows needs SystemRoot to create a child process.  It is not a
    # credential and is ignored on other platforms.
    system_root = os.environ.get("SystemRoot")
    if system_root:
        environment["SystemRoot"] = system_root
    return environment


def _result(
    status: PdfExtractionStatus,
    reason_code: str,
    source_digest: str,
    source_size: int,
    limits: PdfExtractionLimits,
    *,
    page_count: int | None = None,
) -> PdfExtractionResult:
    return PdfExtractionResult(
        status=status,
        reason_code=reason_code,
        source_sha256=source_digest,
        source_byte_size=source_size,
        limits=limits,
        page_count=page_count,
    )


def _decode_worker_result(payload: bytes) -> dict[str, Any]:
    value = json.loads(payload.decode("utf-8"))
    item = _exact_mapping(
        value,
        {"status", "reason_code", "page_count", "text", "parser_version"},
        "PDF worker result",
    )
    try:
        status = PdfExtractionStatus(item["status"])
    except (TypeError, ValueError) as exc:
        raise PdfExtractionError("PDF worker status is invalid") from exc
    reason = item["reason_code"]
    if not isinstance(reason, str) or not _REASON_RE.fullmatch(reason):
        raise PdfExtractionError("PDF worker reason is invalid")
    page_count = item["page_count"]
    if page_count is not None and (
        isinstance(page_count, bool)
        or not isinstance(page_count, int)
        or page_count < 0
    ):
        raise PdfExtractionError("PDF worker page count is invalid")
    text = item["text"]
    if text is not None and not isinstance(text, str):
        raise PdfExtractionError("PDF worker text is invalid")
    if item["parser_version"] != PDF_PARSER_VERSION:
        raise PdfExtractionError("PDF worker parser version is not pinned")
    if status is PdfExtractionStatus.EXTRACTED:
        if not text or page_count is None or page_count < 1:
            raise PdfExtractionError("PDF worker success is incomplete")
    elif text is not None:
        raise PdfExtractionError("PDF worker failure retained text")
    return {
        "status": status,
        "reason_code": reason,
        "page_count": page_count,
        "text": text,
    }


def _worker_main(encoded_limits: str) -> int:
    try:
        limits = PdfExtractionLimits.from_dict(
            json.loads(base64.urlsafe_b64decode(encoded_limits).decode("utf-8"))
        )
    except Exception:
        return 64

    isolation_reason = _apply_worker_resource_limits(limits)
    if isolation_reason is not None:
        _write_worker_result(
            PdfExtractionStatus.ISOLATION_UNAVAILABLE,
            isolation_reason,
            parser_version=PDF_PARSER_VERSION,
        )
        return 0

    frozen_bytes = sys.stdin.buffer.read(limits.max_source_bytes + 1)
    if len(frozen_bytes) > limits.max_source_bytes:
        _write_worker_result(
            PdfExtractionStatus.SOURCE_LIMIT,
            "source_byte_limit",
            parser_version=PDF_PARSER_VERSION,
        )
        return 0

    try:
        import pypdf
    except (ImportError, ModuleNotFoundError):
        _write_worker_result(
            PdfExtractionStatus.PARSER_UNAVAILABLE,
            "parser_not_installed",
            parser_version=PDF_PARSER_VERSION,
        )
        return 0
    if getattr(pypdf, "__version__", None) != PDF_PARSER_VERSION:
        _write_worker_result(
            PdfExtractionStatus.PARSER_UNAVAILABLE,
            "parser_version_mismatch",
            parser_version=PDF_PARSER_VERSION,
        )
        return 0

    try:
        status, reason, page_count, text = _extract_with_pypdf(
            frozen_bytes,
            limits,
            pypdf,
        )
    except MemoryError:
        status = PdfExtractionStatus.RESOURCE_LIMIT
        reason = "worker_memory_exhausted"
        page_count = None
        text = None
    except Exception:
        status = PdfExtractionStatus.FAILED
        reason = "unexpected_extraction_failure"
        page_count = None
        text = None
    _write_worker_result(
        status,
        reason,
        page_count=page_count,
        text=text,
        parser_version=PDF_PARSER_VERSION,
    )
    return 0


def _apply_worker_resource_limits(limits: PdfExtractionLimits) -> str | None:
    """Apply hard POSIX controls before importing the PDF parser."""

    try:
        import resource
    except ImportError:
        return "posix_resource_limits_unavailable"

    required = ("RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_NOFILE")
    if any(not hasattr(resource, name) for name in required):
        return "posix_resource_limits_unavailable"
    try:
        _lower_resource_limit(resource, resource.RLIMIT_CPU, limits.cpu_time_seconds)
        _lower_resource_limit(resource, resource.RLIMIT_FSIZE, 0)
        _lower_resource_limit(resource, resource.RLIMIT_NOFILE, limits.max_open_files)
        if hasattr(resource, "RLIMIT_CORE"):
            _lower_resource_limit(resource, resource.RLIMIT_CORE, 0)
        sys.setrecursionlimit(2_000)
    except (OSError, ValueError):
        return "posix_resource_limits_failed"
    return None


def _lower_resource_limit(resource_module: Any, resource_id: int, requested: int) -> None:
    _soft, hard = resource_module.getrlimit(resource_id)
    infinity = resource_module.RLIM_INFINITY
    bounded = requested if hard == infinity else min(requested, hard)
    resource_module.setrlimit(resource_id, (bounded, bounded))


def _extract_with_pypdf(
    frozen_bytes: bytes,
    limits: PdfExtractionLimits,
    pypdf_module: Any,
) -> tuple[PdfExtractionStatus, str, int | None, str | None]:
    from io import BytesIO

    try:
        reader = pypdf_module.PdfReader(BytesIO(frozen_bytes), strict=True)
    except pypdf_module.errors.PdfReadError:
        return PdfExtractionStatus.MALFORMED, "malformed_pdf", None, None

    if reader.is_encrypted:
        return PdfExtractionStatus.ENCRYPTED, "encrypted_pdf", None, None
    try:
        page_count = len(reader.pages)
    except pypdf_module.errors.PdfReadError:
        return PdfExtractionStatus.MALFORMED, "malformed_page_tree", None, None
    if page_count > limits.max_pages:
        return PdfExtractionStatus.PAGE_LIMIT, "page_count_limit", page_count, None
    if page_count < 1:
        return PdfExtractionStatus.EMPTY, "empty_pdf", 0, None

    pages: list[str] = []
    has_image = False
    character_count = 0
    try:
        for page in reader.pages:
            has_image = has_image or _page_has_image(page)
            extracted = page.extract_text(extraction_mode="plain") or ""
            normalized = _normalize_page_text(extracted)
            if _unsafe_text(normalized):
                return (
                    PdfExtractionStatus.UNSAFE_TEXT,
                    "unsafe_text_controls",
                    page_count,
                    None,
                )
            character_count += len(normalized)
            if character_count > limits.max_text_characters:
                return (
                    PdfExtractionStatus.TEXT_LIMIT,
                    "text_character_limit",
                    page_count,
                    None,
                )
            if normalized:
                pages.append(normalized)
                # Account for the deterministic separator before retaining it.
                if len(pages) > 1:
                    character_count += 2
                    if character_count > limits.max_text_characters:
                        return (
                            PdfExtractionStatus.TEXT_LIMIT,
                            "text_character_limit",
                            page_count,
                            None,
                        )
    except pypdf_module.errors.PdfReadError:
        return PdfExtractionStatus.MALFORMED, "malformed_page_content", page_count, None

    if not pages:
        if has_image:
            return PdfExtractionStatus.IMAGE_ONLY, "image_only_pdf", page_count, None
        return PdfExtractionStatus.EMPTY, "no_extractable_text", page_count, None
    text = "\n\n".join(pages)
    return PdfExtractionStatus.EXTRACTED, "extracted_text", page_count, text


def _page_has_image(page: Any) -> bool:
    """Detect direct image XObjects without decoding image streams."""

    resources = page.get("/Resources")
    if resources is None:
        return False
    resources = resources.get_object()
    xobjects = resources.get("/XObject")
    if xobjects is None:
        return False
    xobjects = xobjects.get_object()
    for reference in xobjects.values():
        candidate = reference.get_object()
        if candidate.get("/Subtype") == "/Image":
            return True
    return False


def _normalize_page_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def _unsafe_text(value: str) -> bool:
    for character in value:
        codepoint = ord(character)
        if codepoint == 0 or codepoint == 127:
            return True
        if codepoint < 32 and character not in {"\t", "\n", "\f"}:
            return True
    return False


def _write_worker_result(
    status: PdfExtractionStatus,
    reason_code: str,
    *,
    parser_version: str,
    page_count: int | None = None,
    text: str | None = None,
) -> None:
    payload = {
        "status": status.value,
        "reason_code": reason_code,
        "page_count": page_count,
        "text": text,
        "parser_version": parser_version,
    }
    sys.stdout.buffer.write(_canonical_json(payload))
    sys.stdout.buffer.flush()


def _exact_mapping(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PdfExtractionError(f"{label} has invalid keys")
    if any(not isinstance(key, str) for key in value):
        raise PdfExtractionError(f"{label} keys must be strings")
    return value


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PdfExtractionError("PDF extraction metadata is not canonical JSON") from exc


__all__ = [
    "PDF_EXTRACTOR_VERSION",
    "PDF_PARSER_NAME",
    "PDF_PARSER_VERSION",
    "PdfExtractionError",
    "PdfExtractionLimits",
    "PdfExtractionResult",
    "PdfExtractionStatus",
    "extract_pdf_text",
]


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != _WORKER_FLAG:
        raise SystemExit(64)
    raise SystemExit(_worker_main(sys.argv[2]))
