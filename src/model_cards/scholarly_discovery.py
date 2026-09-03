"""Bounded, credential-free scholarly discovery for primary paper locators.

The two public search APIs in this module are discovery aids only.  Their
responses can yield normalized arXiv and DOI URLs, but neither API response nor
the resulting URL is factual evidence.  Callers pass the returned
``DiscoveryHint`` objects through the official-source bundle, where they are
stored as ``discovery_only`` and are never fetched automatically.

Only content-free telemetry and normalized primary locators are serialized.
Search response bodies, titles, abstracts, authors, credentials, headers, and
local paths are never retained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from .official_discovery import OfficialSourceKind
from .official_sources import DiscoveryHint, SourceAuthority
from .source_bundle import TargetIdentity


SCHOLARLY_DISCOVERY_VERSION = "scholarly-source-discovery/v1"
SCHOLARLY_DISCOVERY_FILENAME = "scholarly-discovery.json"
DEFAULT_MAX_RESULTS_PER_SERVICE = 5
DEFAULT_MAX_HINTS = 8
DEFAULT_MAX_RESPONSE_BYTES = 512_000
DEFAULT_TIMEOUT_SECONDS = 15.0
DETERMINISTIC_USER_AGENT = "evaleval-model-cards/0.1 scholarly-discovery/v1"

_REPORT_ID_RE = re.compile(r"^scholarly_discovery_[0-9a-f]{32}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_MODERN_ARXIV_RE = re.compile(r"^(\d{4}\.\d{4,5})(?:v\d+)?$", re.I)
_LEGACY_ARXIV_RE = re.compile(
    r"^([a-z][a-z0-9.-]*/\d{7})(?:v\d+)?$", re.I
)
_DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s/?#][^\s?#]{0,511}$", re.I)


class ScholarlyDiscoveryError(ValueError):
    """A scholarly discovery record or configuration is invalid."""


class ScholarlyService(str, Enum):
    OPENALEX = "openalex"
    SEMANTIC_SCHOLAR = "semantic_scholar"


class ScholarlyServiceStatus(str, Enum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    GATED = "gated"
    BLOCKED = "blocked"
    MALFORMED = "malformed"


@dataclass(frozen=True)
class ScholarlyDiscoveryLimits:
    max_results_per_service: int = DEFAULT_MAX_RESULTS_PER_SERVICE
    max_hints: int = DEFAULT_MAX_HINTS
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        for name in (
            "max_results_per_service",
            "max_hints",
            "max_response_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ScholarlyDiscoveryError(f"{name} must be a positive integer")
        if self.max_results_per_service > 10:
            raise ScholarlyDiscoveryError("max_results_per_service cannot exceed 10")
        if self.max_hints > 16:
            raise ScholarlyDiscoveryError("max_hints cannot exceed 16")
        if self.max_response_bytes > 1_000_000:
            raise ScholarlyDiscoveryError("max_response_bytes cannot exceed 1000000")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_hints": self.max_hints,
            "max_response_bytes": self.max_response_bytes,
            "max_results_per_service": self.max_results_per_service,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ScholarlyDiscoveryLimits":
        item = _strict_object(
            value,
            {"max_hints", "max_response_bytes", "max_results_per_service"},
            "scholarly discovery limits",
        )
        return cls(**item)


@dataclass(frozen=True)
class ScholarlyRequest:
    service: ScholarlyService
    url: str
    max_bytes: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "service", ScholarlyService(self.service))
        except (TypeError, ValueError) as exc:
            raise ScholarlyDiscoveryError("scholarly request service is invalid") from exc
        if (
            isinstance(self.max_bytes, bool)
            or not isinstance(self.max_bytes, int)
            or not 1 <= self.max_bytes <= 1_000_000
        ):
            raise ScholarlyDiscoveryError("scholarly request byte bound is invalid")
        _validate_endpoint(self.service, self.url)


@dataclass(frozen=True)
class ScholarlyResponse:
    status_code: int
    body: bytes = field(default=b"", repr=False)
    too_large: bool = False

    def __post_init__(self) -> None:
        if (
            isinstance(self.status_code, bool)
            or not isinstance(self.status_code, int)
            or not 100 <= self.status_code <= 599
        ):
            raise ScholarlyDiscoveryError("scholarly response status is invalid")
        if not isinstance(self.body, bytes) or not isinstance(self.too_large, bool):
            raise ScholarlyDiscoveryError("scholarly response body metadata is invalid")


class ScholarlyDiscoveryTransport(Protocol):
    """Injected boundary performing one bounded GET for each fixed endpoint."""

    def open(self, request: ScholarlyRequest) -> ScholarlyResponse:
        """Perform one request without credentials, redirects, or retries."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class StdlibScholarlyDiscoveryTransport:
    """Minimal no-proxy HTTPS transport with no credentials or automatic retry."""

    def __init__(self, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
            or timeout_seconds > 60
        ):
            raise ScholarlyDiscoveryError("scholarly timeout must be in (0, 60]")
        self.timeout_seconds = float(timeout_seconds)

    def open(self, request: ScholarlyRequest) -> ScholarlyResponse:
        if not isinstance(request, ScholarlyRequest):
            raise ScholarlyDiscoveryError("scholarly transport request is invalid")
        urllib_request = Request(
            request.url,
            method="GET",
            headers={
                "Accept": "application/json",
                "User-Agent": DETERMINISTIC_USER_AGENT,
            },
        )
        opener = build_opener(ProxyHandler({}), _NoRedirect(), HTTPSHandler())
        try:
            response = opener.open(urllib_request, timeout=self.timeout_seconds)
        except HTTPError as exc:
            response = exc
        except (URLError, TimeoutError, OSError):
            raise OSError("scholarly discovery transport is unavailable") from None
        try:
            content_length = response.headers.get("Content-Length")
            too_large = False
            if content_length is not None:
                try:
                    too_large = int(content_length) > request.max_bytes
                except ValueError:
                    too_large = False
            body = b"" if too_large else response.read(request.max_bytes + 1)
            if len(body) > request.max_bytes:
                too_large = True
                body = body[: request.max_bytes]
            return ScholarlyResponse(
                status_code=int(getattr(response, "status", response.code)),
                body=body,
                too_large=too_large,
            )
        except (URLError, TimeoutError, OSError):
            raise OSError("scholarly discovery transport is unavailable") from None
        finally:
            response.close()


@dataclass(frozen=True)
class ScholarlyServiceRecord:
    service: ScholarlyService
    status: ScholarlyServiceStatus
    reason_code: str
    http_status: int | None
    results_seen: int
    normalized_urls_found: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "service", ScholarlyService(self.service))
            object.__setattr__(self, "status", ScholarlyServiceStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise ScholarlyDiscoveryError("scholarly service telemetry is invalid") from exc
        _validate_reason(self.reason_code)
        if self.http_status is not None and (
            isinstance(self.http_status, bool)
            or not isinstance(self.http_status, int)
            or not 100 <= self.http_status <= 599
        ):
            raise ScholarlyDiscoveryError("scholarly telemetry HTTP status is invalid")
        for name in ("results_seen", "normalized_urls_found"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ScholarlyDiscoveryError(f"scholarly telemetry {name} is invalid")
        if self.status is ScholarlyServiceStatus.COMPLETED:
            if self.http_status != 200 or self.reason_code != "ok":
                raise ScholarlyDiscoveryError("completed scholarly telemetry is inconsistent")
        elif self.results_seen != 0 or self.normalized_urls_found != 0:
            raise ScholarlyDiscoveryError("failed scholarly telemetry cannot report results")

    def to_dict(self) -> dict[str, Any]:
        return {
            "http_status": self.http_status,
            "normalized_urls_found": self.normalized_urls_found,
            "reason_code": self.reason_code,
            "results_seen": self.results_seen,
            "service": self.service.value,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ScholarlyServiceRecord":
        item = _strict_object(
            value,
            {
                "http_status",
                "normalized_urls_found",
                "reason_code",
                "results_seen",
                "service",
                "status",
            },
            "scholarly service telemetry",
        )
        return cls(**item)


@dataclass(frozen=True)
class ScholarlyDiscoveryReport:
    discovery_version: str
    report_id: str
    target: TargetIdentity
    query: str
    limits: ScholarlyDiscoveryLimits
    services: tuple[ScholarlyServiceRecord, ...]
    hints: tuple[DiscoveryHint, ...]
    truncated: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "services", tuple(self.services))
        object.__setattr__(self, "hints", tuple(self.hints))
        if self.discovery_version != SCHOLARLY_DISCOVERY_VERSION:
            raise ScholarlyDiscoveryError("scholarly discovery version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise ScholarlyDiscoveryError("scholarly discovery target is invalid")
        if self.query != _query_text(self.target.model_id):
            raise ScholarlyDiscoveryError("scholarly discovery query drifts from target")
        if not isinstance(self.limits, ScholarlyDiscoveryLimits):
            raise ScholarlyDiscoveryError("scholarly discovery limits are invalid")
        if not isinstance(self.truncated, bool):
            raise ScholarlyDiscoveryError("scholarly discovery truncated flag is invalid")
        expected_services = tuple(sorted(ScholarlyService, key=lambda item: item.value))
        if not all(isinstance(item, ScholarlyServiceRecord) for item in self.services):
            raise ScholarlyDiscoveryError("scholarly service telemetry is invalid")
        if tuple(item.service for item in self.services) != expected_services:
            raise ScholarlyDiscoveryError(
                "scholarly discovery must record each fixed service exactly once"
            )
        for record in self.services:
            if record.results_seen > self.limits.max_results_per_service:
                raise ScholarlyDiscoveryError("scholarly result telemetry exceeds its limit")
            if record.normalized_urls_found > record.results_seen * 6:
                raise ScholarlyDiscoveryError("scholarly URL telemetry is inconsistent")
        if len(self.hints) > self.limits.max_hints:
            raise ScholarlyDiscoveryError("scholarly discovery exceeds its hint limit")
        if not all(isinstance(item, DiscoveryHint) for item in self.hints):
            raise ScholarlyDiscoveryError("scholarly discovery hints are invalid")
        urls = tuple(item.url for item in self.hints)
        if urls != tuple(sorted(set(urls))):
            raise ScholarlyDiscoveryError("scholarly discovery hints must be sorted and unique")
        for hint in self.hints:
            if (
                hint.kind is not OfficialSourceKind.PAPER
                or hint.authority is not SourceAuthority.SCHOLARLY_DISCOVERY
                or hint.reason_code != "scholarly_result_only"
                or _normalize_primary_url(hint.url) != hint.url
            ):
                raise ScholarlyDiscoveryError("scholarly discovery hint is not admissible")
        if not isinstance(self.report_id, str) or not _REPORT_ID_RE.fullmatch(
            self.report_id
        ):
            raise ScholarlyDiscoveryError("scholarly discovery report id is invalid")
        if self.report_id != _report_id(
            target=self.target,
            query=self.query,
            limits=self.limits,
            services=self.services,
            hints=self.hints,
            truncated=self.truncated,
        ):
            raise ScholarlyDiscoveryError("scholarly discovery report id does not match content")

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovery_version": self.discovery_version,
            "hints": [_hint_dict(item) for item in self.hints],
            "limits": self.limits.to_dict(),
            "query": self.query,
            "report_id": self.report_id,
            "services": [item.to_dict() for item in self.services],
            "target": self.target.to_dict(),
            "truncated": self.truncated,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ScholarlyDiscoveryReport":
        item = _strict_object(
            value,
            {
                "discovery_version",
                "hints",
                "limits",
                "query",
                "report_id",
                "services",
                "target",
                "truncated",
            },
            "scholarly discovery report",
        )
        if not isinstance(item["services"], list) or not isinstance(item["hints"], list):
            raise ScholarlyDiscoveryError("scholarly discovery arrays are invalid")
        try:
            target = TargetIdentity.from_dict(item["target"])
            limits = ScholarlyDiscoveryLimits.from_dict(item["limits"])
            services = tuple(
                ScholarlyServiceRecord.from_dict(entry) for entry in item["services"]
            )
            hints = tuple(_hint_from_dict(entry) for entry in item["hints"])
        except ScholarlyDiscoveryError:
            raise
        except Exception as exc:
            raise ScholarlyDiscoveryError("scholarly discovery members are invalid") from exc
        return cls(
            discovery_version=item["discovery_version"],
            report_id=item["report_id"],
            target=target,
            query=item["query"],
            limits=limits,
            services=services,
            hints=hints,
            truncated=item["truncated"],
        )


def discover_scholarly_sources(
    target: TargetIdentity,
    transport: ScholarlyDiscoveryTransport,
    *,
    limits: ScholarlyDiscoveryLimits | None = None,
) -> ScholarlyDiscoveryReport:
    """Query both fixed services once and return non-authoritative paper hints."""

    if not isinstance(target, TargetIdentity):
        raise ScholarlyDiscoveryError("scholarly discovery requires a source target")
    effective_limits = limits or ScholarlyDiscoveryLimits()
    if not isinstance(effective_limits, ScholarlyDiscoveryLimits):
        raise ScholarlyDiscoveryError("scholarly discovery limits are invalid")
    query = _query_text(target.model_id)
    service_records: list[ScholarlyServiceRecord] = []
    discovered_urls: set[str] = set()
    service_truncated = False
    for service in sorted(ScholarlyService, key=lambda item: item.value):
        request = ScholarlyRequest(
            service=service,
            url=_service_url(service, query, effective_limits.max_results_per_service),
            max_bytes=effective_limits.max_response_bytes,
        )
        record, urls, response_truncated = _query_service(
            transport, request, effective_limits
        )
        service_records.append(record)
        discovered_urls.update(urls)
        service_truncated = service_truncated or response_truncated
    ordered_urls = sorted(discovered_urls)
    retained_urls = ordered_urls[: effective_limits.max_hints]
    hints = tuple(
        DiscoveryHint(
            kind=OfficialSourceKind.PAPER,
            url=url,
            authority=SourceAuthority.SCHOLARLY_DISCOVERY,
            reason_code="scholarly_result_only",
        )
        for url in retained_urls
    )
    truncated = service_truncated or len(ordered_urls) > len(retained_urls)
    services = tuple(service_records)
    report_id = _report_id(
        target=target,
        query=query,
        limits=effective_limits,
        services=services,
        hints=hints,
        truncated=truncated,
    )
    return ScholarlyDiscoveryReport(
        discovery_version=SCHOLARLY_DISCOVERY_VERSION,
        report_id=report_id,
        target=target,
        query=query,
        limits=effective_limits,
        services=services,
        hints=hints,
        truncated=truncated,
    )


def serialize_scholarly_discovery(report: ScholarlyDiscoveryReport) -> bytes:
    if not isinstance(report, ScholarlyDiscoveryReport):
        raise ScholarlyDiscoveryError("report must be a ScholarlyDiscoveryReport")
    return _canonical_json(report.to_dict())


def load_scholarly_discovery(
    payload: bytes | str,
    *,
    expected_target: TargetIdentity | None = None,
) -> ScholarlyDiscoveryReport:
    if isinstance(payload, str):
        encoded = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        encoded = payload
    else:
        raise ScholarlyDiscoveryError("scholarly discovery payload must be bytes or text")
    if encoded.endswith(b"\n"):
        encoded = encoded[:-1]
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ScholarlyDiscoveryError):
        raise ScholarlyDiscoveryError(
            "scholarly discovery payload is not strict JSON"
        ) from None
    if encoded != _canonical_json(value):
        raise ScholarlyDiscoveryError("scholarly discovery payload is non-canonical")
    report = ScholarlyDiscoveryReport.from_dict(value)
    if expected_target is not None and report.target != expected_target:
        raise ScholarlyDiscoveryError("scholarly discovery target differs from expected target")
    return report


def _query_service(
    transport: ScholarlyDiscoveryTransport,
    request: ScholarlyRequest,
    limits: ScholarlyDiscoveryLimits,
) -> tuple[ScholarlyServiceRecord, tuple[str, ...], bool]:
    try:
        response = transport.open(request)
    except Exception:
        return _service_failure(
            request.service,
            ScholarlyServiceStatus.UNAVAILABLE,
            "network_unavailable",
            None,
        ), (), False
    if not isinstance(response, ScholarlyResponse):
        return _service_failure(
            request.service,
            ScholarlyServiceStatus.MALFORMED,
            "invalid_transport_response",
            None,
        ), (), False
    if response.too_large:
        return _service_failure(
            request.service,
            ScholarlyServiceStatus.BLOCKED,
            "size_limit",
            response.status_code,
        ), (), False
    if response.status_code in {401, 403}:
        return _service_failure(
            request.service,
            ScholarlyServiceStatus.GATED,
            "access_gated",
            response.status_code,
        ), (), False
    if response.status_code == 429 or 500 <= response.status_code <= 599:
        return _service_failure(
            request.service,
            ScholarlyServiceStatus.UNAVAILABLE,
            "remote_unavailable",
            response.status_code,
        ), (), False
    if response.status_code != 200:
        return _service_failure(
            request.service,
            ScholarlyServiceStatus.BLOCKED,
            "unexpected_http_status",
            response.status_code,
        ), (), False
    try:
        value = json.loads(
            response.body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
        results, urls, truncated = _extract_service_urls(
            request.service, value, limits.max_results_per_service
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ScholarlyDiscoveryError):
        return _service_failure(
            request.service,
            ScholarlyServiceStatus.MALFORMED,
            "malformed_response",
            response.status_code,
        ), (), False
    return (
        ScholarlyServiceRecord(
            service=request.service,
            status=ScholarlyServiceStatus.COMPLETED,
            reason_code="ok",
            http_status=response.status_code,
            results_seen=results,
            normalized_urls_found=len(urls),
        ),
        urls,
        truncated,
    )


def _service_failure(
    service: ScholarlyService,
    status: ScholarlyServiceStatus,
    reason_code: str,
    http_status: int | None,
) -> ScholarlyServiceRecord:
    return ScholarlyServiceRecord(
        service=service,
        status=status,
        reason_code=reason_code,
        http_status=http_status,
        results_seen=0,
        normalized_urls_found=0,
    )


def _extract_service_urls(
    service: ScholarlyService,
    value: Any,
    max_results: int,
) -> tuple[int, tuple[str, ...], bool]:
    if not isinstance(value, dict):
        raise ScholarlyDiscoveryError("scholarly response root is not an object")
    key = "results" if service is ScholarlyService.OPENALEX else "data"
    results = value.get(key)
    if not isinstance(results, list):
        raise ScholarlyDiscoveryError("scholarly response results are absent")
    retained = results[:max_results]
    urls: set[str] = set()
    for entry in retained:
        if not isinstance(entry, dict):
            continue
        candidates: list[Any] = []
        if service is ScholarlyService.OPENALEX:
            candidates.append(entry.get("doi"))
            ids = entry.get("ids")
            if isinstance(ids, dict):
                candidates.extend((ids.get("doi"), ids.get("arxiv")))
            for location_key in ("primary_location", "best_oa_location"):
                location = entry.get(location_key)
                if isinstance(location, dict):
                    candidates.extend(
                        (location.get("landing_page_url"), location.get("pdf_url"))
                    )
        else:
            external = entry.get("externalIds")
            if isinstance(external, dict):
                candidates.extend((external.get("DOI"), external.get("ArXiv")))
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            normalized = _normalize_primary_url(candidate)
            if normalized is not None:
                urls.add(normalized)
    return len(retained), tuple(sorted(urls)), len(results) > len(retained)


def _normalize_primary_url(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or len(raw) > 1024 or not _portable_text(raw):
        return None
    arxiv_id = _arxiv_id(raw)
    if arxiv_id is not None:
        return f"https://arxiv.org/abs/{arxiv_id}"
    doi = _doi_id(raw)
    if doi is not None:
        return f"https://doi.org/{quote(doi, safe='/._-();:')}"
    return None


def _arxiv_id(value: str) -> str | None:
    raw = value.strip()
    lowered = raw.casefold()
    if lowered.startswith("arxiv:"):
        raw = raw[6:].strip()
    else:
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme.casefold() not in {"http", "https"}:
                return None
            if parsed.hostname is None or parsed.hostname.casefold() not in {
                "arxiv.org",
                "export.arxiv.org",
            }:
                return None
            if parsed.username is not None or parsed.password is not None:
                return None
            path = unquote(parsed.path).strip("/")
            for prefix in ("abs/", "pdf/"):
                if path.casefold().startswith(prefix):
                    path = path[len(prefix) :]
                    break
            if path.casefold().endswith(".pdf"):
                path = path[:-4]
            raw = path
    modern = _MODERN_ARXIV_RE.fullmatch(raw)
    if modern:
        return modern.group(1)
    legacy = _LEGACY_ARXIV_RE.fullmatch(raw)
    if legacy:
        return legacy.group(1).casefold()
    return None


def _doi_id(value: str) -> str | None:
    raw = value.strip()
    lowered = raw.casefold()
    if lowered.startswith("doi:"):
        raw = raw[4:].strip()
    else:
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme.casefold() not in {"http", "https"}:
                return None
            if parsed.hostname is None or parsed.hostname.casefold() not in {
                "doi.org",
                "dx.doi.org",
            }:
                return None
            if (
                parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
            ):
                return None
            raw = unquote(parsed.path).lstrip("/")
    raw = raw.rstrip(".,; ").casefold()
    return raw if _DOI_RE.fullmatch(raw) else None


def _query_text(model_id: str) -> str:
    namespace, name = model_id.split("/", 1)
    tokens = re.sub(r"[._/-]+", " ", f"{name} {namespace}")
    return " ".join(tokens.split())


def _service_url(service: ScholarlyService, query: str, limit: int) -> str:
    if service is ScholarlyService.OPENALEX:
        parameters = urlencode(
            {
                "per-page": str(limit),
                "search": query,
                "select": "doi,ids,primary_location,best_oa_location",
            }
        )
        return f"https://api.openalex.org/works?{parameters}"
    parameters = urlencode(
        {
            "fields": "externalIds",
            "limit": str(limit),
            "query": query,
        }
    )
    return f"https://api.semanticscholar.org/graph/v1/paper/search?{parameters}"


def _validate_endpoint(service: ScholarlyService, url: str) -> None:
    if not isinstance(url, str) or len(url) > 4096 or not _portable_text(url):
        raise ScholarlyDiscoveryError("scholarly request URL is invalid")
    parsed = urlsplit(url)
    expected_host, expected_path = {
        ScholarlyService.OPENALEX: ("api.openalex.org", "/works"),
        ScholarlyService.SEMANTIC_SCHOLAR: (
            "api.semanticscholar.org",
            "/graph/v1/paper/search",
        ),
    }[service]
    try:
        port = parsed.port
    except ValueError:
        raise ScholarlyDiscoveryError("scholarly request endpoint is not fixed") from None
    if (
        parsed.scheme != "https"
        or parsed.hostname != expected_host
        or parsed.path != expected_path
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.fragment
    ):
        raise ScholarlyDiscoveryError("scholarly request endpoint is not fixed")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if len(pairs) != len({key for key, _ in pairs}):
        raise ScholarlyDiscoveryError("scholarly request query is ambiguous")
    parameters = dict(pairs)
    expected_keys = {
        ScholarlyService.OPENALEX: {"per-page", "search", "select"},
        ScholarlyService.SEMANTIC_SCHOLAR: {"fields", "limit", "query"},
    }[service]
    if set(parameters) != expected_keys:
        raise ScholarlyDiscoveryError("scholarly request query shape is invalid")
    if service is ScholarlyService.OPENALEX:
        if parameters["select"] != "doi,ids,primary_location,best_oa_location":
            raise ScholarlyDiscoveryError("OpenAlex field selection is invalid")
        result_limit = parameters["per-page"]
        query = parameters["search"]
    else:
        if parameters["fields"] != "externalIds":
            raise ScholarlyDiscoveryError("Semantic Scholar field selection is invalid")
        result_limit = parameters["limit"]
        query = parameters["query"]
    try:
        parsed_limit = int(result_limit)
    except ValueError:
        raise ScholarlyDiscoveryError("scholarly request result limit is invalid") from None
    if not 1 <= parsed_limit <= 10 or not query or len(query) > 256:
        raise ScholarlyDiscoveryError("scholarly request parameters are invalid")


def _hint_dict(hint: DiscoveryHint) -> dict[str, str]:
    return {
        "authority": hint.authority.value,
        "kind": hint.kind.value,
        "reason_code": hint.reason_code,
        "url": hint.url,
    }


def _hint_from_dict(value: Any) -> DiscoveryHint:
    item = _strict_object(
        value,
        {"authority", "kind", "reason_code", "url"},
        "scholarly discovery hint",
    )
    return DiscoveryHint(**item)


def _report_id(
    *,
    target: TargetIdentity,
    query: str,
    limits: ScholarlyDiscoveryLimits,
    services: tuple[ScholarlyServiceRecord, ...],
    hints: tuple[DiscoveryHint, ...],
    truncated: bool,
) -> str:
    value = {
        "discovery_version": SCHOLARLY_DISCOVERY_VERSION,
        "hints": [_hint_dict(item) for item in hints],
        "limits": limits.to_dict(),
        "query": query,
        "services": [item.to_dict() for item in services],
        "target": target.to_dict(),
        "truncated": truncated,
    }
    digest = hashlib.sha256(_canonical_json(value)).hexdigest()[:32]
    return f"scholarly_discovery_{digest}"


def _validate_reason(value: Any) -> None:
    if not isinstance(value, str) or not _REASON_RE.fullmatch(value):
        raise ScholarlyDiscoveryError("scholarly reason code is invalid")


def _strict_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ScholarlyDiscoveryError(f"{label} has unexpected keys")
    return value


def _portable_text(value: str) -> bool:
    return all(character in "\t\n\r" or ord(character) >= 32 for character in value)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ScholarlyDiscoveryError("scholarly JSON contains duplicate keys")
        output[key] = value
    return output


def _reject_nonfinite(value: str) -> None:
    raise ScholarlyDiscoveryError(f"non-finite JSON number is not permitted: {value}")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
