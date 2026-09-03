"""Concrete bounded HTTPS adapter for verified official-source collection.

Redirects are followed manually so every destination is validated before a
request is sent.  The adapter has no credentials, proxy, cookies, cache, or
automatic retry.  ``official_sources.collect_official_sources`` performs the
stricter per-kind publisher/ownership checks on the returned redirect trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
from typing import Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from .official_sources import (
    OfficialFetchStatus,
    OfficialRemoteObject,
    OfficialSourceAdapter,
    OfficialSourceError,
)


DETERMINISTIC_USER_AGENT = "evaleval-model-cards/0.1 official-source-bundle/v2"
DEFAULT_TIMEOUT_SECONDS = 30.0
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class OfficialHttpError(ValueError):
    """Concrete official-source HTTP configuration or response is unsafe."""


@dataclass(frozen=True)
class OfficialHttpRequest:
    url: str
    max_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.max_bytes, int) or isinstance(self.max_bytes, bool):
            raise OfficialHttpError("official request byte bound must be an integer")
        if self.max_bytes <= 0:
            raise OfficialHttpError("official request byte bound must be positive")


@dataclass(frozen=True)
class OfficialHttpResponse:
    status_code: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = field(default=b"", repr=False)
    too_large: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.status_code, int)
            or isinstance(self.status_code, bool)
            or not 100 <= self.status_code <= 599
        ):
            raise OfficialHttpError("official response status is invalid")
        if not isinstance(self.body, bytes) or not isinstance(self.too_large, bool):
            raise OfficialHttpError("official response body metadata is invalid")
        normalized = {}
        for key, value in self.headers.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise OfficialHttpError("official response headers are invalid")
            lowered = key.casefold()
            if lowered in normalized or "\r" in value or "\n" in value:
                raise OfficialHttpError("official response headers are ambiguous")
            normalized[lowered] = value
        object.__setattr__(self, "headers", normalized)

    def header(self, name: str) -> str | None:
        return self.headers.get(name.casefold())


class OfficialHttpTransport(Protocol):
    def open(self, request: OfficialHttpRequest) -> OfficialHttpResponse:
        """Perform exactly one HTTPS GET without following redirects."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class StdlibOfficialHttpTransport:
    def __init__(self, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise OfficialHttpError("official HTTP timeout must be positive")
        self.timeout_seconds = float(timeout_seconds)

    def open(self, request: OfficialHttpRequest) -> OfficialHttpResponse:
        urllib_request = Request(
            request.url,
            method="GET",
            headers={
                "Accept": (
                    "text/html,application/pdf,text/plain,text/markdown,"
                    "application/json;q=0.9,*/*;q=0.1"
                ),
                "User-Agent": DETERMINISTIC_USER_AGENT,
            },
        )
        opener = build_opener(ProxyHandler({}), _NoRedirect(), HTTPSHandler())
        try:
            response = opener.open(urllib_request, timeout=self.timeout_seconds)
        except HTTPError as exc:
            response = exc
        except (URLError, TimeoutError, OSError):
            raise OSError("official HTTPS transport is unavailable") from None
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
            headers = {
                str(key): str(value) for key, value in response.headers.items()
            }
            return OfficialHttpResponse(
                status_code=int(getattr(response, "status", response.code)),
                headers=headers,
                body=body,
                too_large=too_large,
            )
        except (URLError, TimeoutError, OSError):
            raise OSError("official HTTPS transport is unavailable") from None
        finally:
            response.close()


class StdlibOfficialSourceAdapter(OfficialSourceAdapter):
    """No-credential adapter restricted to an explicit public-host allowlist."""

    def __init__(
        self,
        allowed_hosts: Sequence[str],
        *,
        transport: OfficialHttpTransport | None = None,
    ) -> None:
        hosts = tuple(sorted({_host(item) for item in allowed_hosts}))
        if not hosts:
            raise OfficialHttpError("official adapter requires allowed hosts")
        self.allowed_hosts = hosts
        self.transport = transport or StdlibOfficialHttpTransport()

    def fetch(
        self, url: str, *, max_bytes: int, max_redirects: int
    ) -> OfficialRemoteObject:
        if (
            not isinstance(max_redirects, int)
            or isinstance(max_redirects, bool)
            or not 0 <= max_redirects <= 10
        ):
            raise OfficialHttpError("official redirect bound is invalid")
        try:
            current = _safe_url(url, self.allowed_hosts)
        except OfficialHttpError:
            return OfficialRemoteObject(
                OfficialFetchStatus.BLOCKED, reason_code="unsafe_request_url"
            )
        trace = [current]
        for redirect_index in range(max_redirects + 1):
            try:
                response = self.transport.open(OfficialHttpRequest(current, max_bytes))
            except Exception:
                return OfficialRemoteObject(
                    OfficialFetchStatus.UNAVAILABLE,
                    reason_code="network_unavailable",
                )
            if not isinstance(response, OfficialHttpResponse):
                raise OfficialSourceError("official HTTP transport returned an invalid response")
            if response.status_code in _REDIRECT_STATUSES:
                if redirect_index >= max_redirects:
                    return OfficialRemoteObject(
                        OfficialFetchStatus.BLOCKED,
                        reason_code="redirect_limit",
                    )
                location = response.header("location")
                if not location:
                    return OfficialRemoteObject(
                        OfficialFetchStatus.BLOCKED,
                        reason_code="redirect_missing_location",
                    )
                try:
                    current = _safe_url(urljoin(current, location), self.allowed_hosts)
                except OfficialHttpError:
                    return OfficialRemoteObject(
                        OfficialFetchStatus.BLOCKED,
                        reason_code="unsafe_redirect",
                    )
                trace.append(current)
                continue
            if response.status_code == 200:
                if response.too_large:
                    return OfficialRemoteObject(
                        OfficialFetchStatus.BLOCKED,
                        reason_code="size_limit",
                    )
                media_type = _media_type(response.header("content-type"))
                if media_type is None:
                    return OfficialRemoteObject(
                        OfficialFetchStatus.BLOCKED,
                        reason_code="unsupported_media_type",
                    )
                return OfficialRemoteObject(
                    OfficialFetchStatus.OK,
                    content=response.body,
                    final_url=current,
                    redirect_chain=tuple(trace),
                    media_type=media_type,
                )
            if response.status_code in {401, 403}:
                return OfficialRemoteObject(
                    OfficialFetchStatus.GATED,
                    reason_code="access_gated",
                )
            if response.status_code in {404, 410}:
                return OfficialRemoteObject(
                    OfficialFetchStatus.MISSING,
                    reason_code="source_missing",
                )
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                return OfficialRemoteObject(
                    OfficialFetchStatus.UNAVAILABLE,
                    reason_code="remote_unavailable",
                )
            return OfficialRemoteObject(
                OfficialFetchStatus.BLOCKED,
                reason_code="http_status_blocked",
            )
        raise AssertionError("unreachable official redirect state")


def _host(value: str) -> str:
    if not isinstance(value, str) or not value or "://" in value or "/" in value:
        raise OfficialHttpError("official allowed host is invalid")
    normalized = value.rstrip(".").casefold()
    if not normalized or normalized == "localhost" or "." not in normalized:
        raise OfficialHttpError("official allowed host is invalid")
    try:
        address = ipaddress.ip_address(normalized.strip("[]"))
    except ValueError:
        return normalized
    if not address.is_global:
        raise OfficialHttpError("official allowed host cannot be private")
    return normalized


def _safe_url(value: str, allowed_hosts: Sequence[str]) -> str:
    if not isinstance(value, str) or len(value) > 4096:
        raise OfficialHttpError("official URL is invalid")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.port not in (None, 443)
    ):
        raise OfficialHttpError("official URL must be credential-free HTTPS")
    host = _host(parsed.hostname or "")
    if host not in set(allowed_hosts):
        raise OfficialHttpError("official URL host is outside the allowlist")
    return value


def _media_type(value: str | None) -> str | None:
    if not value:
        return None
    media_type = value.split(";", 1)[0].strip().casefold()
    aliases = {
        "text/x-markdown": "text/markdown",
        "application/x-pdf": "application/pdf",
    }
    media_type = aliases.get(media_type, media_type)
    allowed = {
        "application/json",
        "application/pdf",
        "text/html",
        "text/markdown",
        "text/plain",
    }
    return media_type if media_type in allowed else None


__all__ = [
    "DETERMINISTIC_USER_AGENT",
    "OfficialHttpError",
    "OfficialHttpRequest",
    "OfficialHttpResponse",
    "OfficialHttpTransport",
    "StdlibOfficialHttpTransport",
    "StdlibOfficialSourceAdapter",
]
