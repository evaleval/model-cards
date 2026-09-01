"""Concrete, cache-free Hugging Face Hub transport for source bundles.

The adapter implements :class:`model_cards.source_bundle.HuggingFaceSourceAdapter`
using only the Python standard library.  Network access remains replaceable by
an injected transport, so tests and offline workflows never contact the Hub.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from .source_bundle import (
    FetchStatus,
    RemoteObject,
    SourceBundleError,
    TargetIdentity,
    parse_target_request,
)


HUGGING_FACE_HOST = "huggingface.co"
DETERMINISTIC_USER_AGENT = "evaleval-model-cards/0.1 hf-source-bundle/v1"
MAX_RESOLUTION_BYTES = 1_000_000

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class HuggingFaceAdapterError(SourceBundleError):
    """Base class for typed Hub failures during exact revision resolution."""


class RepositoryMissingError(HuggingFaceAdapterError):
    pass


class GatedRepositoryError(HuggingFaceAdapterError):
    pass


class AuthenticationRequiredError(HuggingFaceAdapterError):
    pass


class NetworkUnavailableError(HuggingFaceAdapterError):
    pass


class ResponseTooLargeError(HuggingFaceAdapterError):
    pass


class HubProtocolError(HuggingFaceAdapterError):
    pass


class RevisionDriftError(HuggingFaceAdapterError):
    pass


class UntrustedRedirectError(HuggingFaceAdapterError):
    pass


class TransportNetworkError(OSError):
    """Transport-level failure whose original message must not cross the adapter."""


@dataclass(frozen=True)
class TransportRequest:
    url: str
    headers: tuple[tuple[str, str], ...]
    max_bytes: int

    def __post_init__(self) -> None:
        _validate_https_url(self.url, {HUGGING_FACE_HOST})
        if not isinstance(self.max_bytes, int) or isinstance(self.max_bytes, bool):
            raise ValueError("transport max_bytes must be an integer")
        if self.max_bytes <= 0:
            raise ValueError("transport max_bytes must be positive")
        normalized: list[tuple[str, str]] = []
        seen: set[str] = set()
        for name, value in self.headers:
            if not isinstance(name, str) or not isinstance(value, str):
                raise ValueError("transport headers must be string pairs")
            lowered = name.strip().casefold()
            if not lowered or lowered in seen or "\n" in value or "\r" in value:
                raise ValueError("transport headers are invalid")
            seen.add(lowered)
            normalized.append((name, value))
        object.__setattr__(self, "headers", tuple(normalized))

    def header(self, name: str) -> str | None:
        wanted = name.casefold()
        for header_name, value in self.headers:
            if header_name.casefold() == wanted:
                return value
        return None

    def __repr__(self) -> str:
        names = tuple(name for name, _ in self.headers)
        return (
            f"TransportRequest(url={self.url!r}, header_names={names!r}, "
            f"max_bytes={self.max_bytes!r})"
        )


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    final_url: str
    headers: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    body: bytes = field(default=b"", repr=False)
    redirect_chain: tuple[str, ...] = ()
    too_large: bool = False

    def __post_init__(self) -> None:
        if (
            isinstance(self.status_code, bool)
            or not isinstance(self.status_code, int)
            or not 100 <= self.status_code <= 599
        ):
            raise ValueError("transport status_code is invalid")
        if not isinstance(self.final_url, str):
            raise ValueError("transport final_url must be a string")
        if not isinstance(self.body, bytes):
            raise ValueError("transport body must be bytes")
        if not isinstance(self.too_large, bool):
            raise ValueError("transport too_large must be boolean")
        if not all(isinstance(item, str) for item in self.redirect_chain):
            raise ValueError("transport redirect_chain must contain URLs")
        normalized_headers: list[tuple[str, str]] = []
        for header in self.headers:
            if (
                not isinstance(header, tuple)
                or len(header) != 2
                or not all(isinstance(item, str) for item in header)
            ):
                raise ValueError("transport response headers must be string pairs")
            normalized_headers.append(header)
        object.__setattr__(self, "headers", tuple(normalized_headers))
        object.__setattr__(self, "redirect_chain", tuple(self.redirect_chain))

    def header(self, name: str) -> str | None:
        wanted = name.casefold()
        for header_name, value in self.headers:
            if header_name.casefold() == wanted:
                return value
        return None


class OpenableTransport(Protocol):
    def open(self, request: TransportRequest) -> TransportResponse:
        """Open one bounded GET request without persisting request or response data."""


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, trusted_hosts: Sequence[str]) -> None:
        super().__init__()
        self.trusted_hosts = frozenset(item.casefold() for item in trusted_hosts)
        self.redirect_chain: list[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        _validate_https_url(newurl, self.trusted_hosts)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        redirected_headers = _redirect_headers(
            tuple(req.header_items()), req.full_url, newurl, self.trusted_hosts
        )
        for mapping in (redirected.headers, redirected.unredirected_hdrs):
            for name in list(mapping):
                del mapping[name]
        for name, value in redirected_headers:
            redirected.add_unredirected_header(name, value)
        self.redirect_chain.append(newurl)
        return redirected


class StdlibHuggingFaceTransport:
    """Minimal urllib transport with no proxy, cookie, or cache integration."""

    def __init__(self, *, timeout_seconds: float = 20.0, trusted_hosts: Sequence[str] = ()):
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = float(timeout_seconds)
        self.trusted_hosts = _normalize_trusted_hosts(trusted_hosts)

    def open(self, request: TransportRequest) -> TransportResponse:
        handler = _SafeRedirectHandler(self.trusted_hosts)
        opener = build_opener(ProxyHandler({}), handler, HTTPSHandler())
        urllib_request = Request(request.url, method="GET")
        for name, value in request.headers:
            urllib_request.add_unredirected_header(name, value)
        try:
            response = opener.open(urllib_request, timeout=self.timeout_seconds)
        except HTTPError as exc:
            response = exc
        except (URLError, OSError) as exc:
            raise TransportNetworkError("Hub transport is unavailable") from None
        try:
            content_length = _parse_content_length(response.headers.get("Content-Length"))
            too_large = content_length is not None and content_length > request.max_bytes
            body = b"" if too_large else response.read(request.max_bytes + 1)
            if len(body) > request.max_bytes:
                too_large = True
                body = body[: request.max_bytes]
            response_headers = tuple(
                sorted(
                    ((str(name), str(value)) for name, value in response.headers.items()),
                    key=lambda item: (item[0].casefold(), item[1]),
                )
            )
            return TransportResponse(
                status_code=int(getattr(response, "status", response.code)),
                final_url=str(response.geturl()),
                headers=response_headers,
                body=body,
                redirect_chain=tuple(handler.redirect_chain),
                too_large=too_large,
            )
        except (URLError, OSError):
            raise TransportNetworkError("Hub transport is unavailable") from None
        finally:
            response.close()


class HuggingFaceHubAdapter:
    """Official Hub adapter compatible with ``HuggingFaceSourceAdapter``."""

    def __init__(
        self,
        *,
        token: str | None = None,
        transport: OpenableTransport | None = None,
        trusted_redirect_hosts: Sequence[str] = (),
    ) -> None:
        self._token = _validate_token(token)
        self._trusted_hosts = _normalize_trusted_hosts(trusted_redirect_hosts)
        self._transport = transport or StdlibHuggingFaceTransport(
            trusted_hosts=tuple(self._trusted_hosts - {HUGGING_FACE_HOST})
        )

    def __repr__(self) -> str:
        return (
            f"HuggingFaceHubAdapter(token={'<redacted>' if self._token else None!r}, "
            f"transport={type(self._transport).__name__!r})"
        )

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        model_id, requested_revision = _validate_target_request(model_id, requested_revision)
        requested = requested_revision or "main"
        url = _metadata_url(model_id, requested)
        response = self._open(url, MAX_RESOLUTION_BYTES)
        self._raise_resolution_status(response)
        self._validate_response_route(
            response, initial_url=url, exact_revision=None, allow_file_redirect=False
        )
        data = _strict_json_object(response.body, malformed_reason="Hub metadata is malformed")
        resolved = data.get("sha")
        if not isinstance(resolved, str) or not _COMMIT_RE.fullmatch(resolved):
            raise HubProtocolError("Hub metadata did not provide an exact commit")
        _validate_metadata_identity(data, model_id, resolved)
        if _COMMIT_RE.fullmatch(requested) and requested != resolved:
            raise RevisionDriftError("resolved commit differs from the requested commit")
        return resolved

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        try:
            target = TargetIdentity(model_id, revision)
            limit = _validate_max_bytes(max_bytes)
            url = _metadata_url(target.model_id, target.revision)
            response = self._open(url, limit)
            failure = self._remote_failure(response)
            if failure is not None:
                return failure
            self._validate_response_route(
                response, initial_url=url, exact_revision=None, allow_file_redirect=False
            )
            data = _strict_json_object(
                response.body, malformed_reason="Hub metadata is malformed"
            )
            _validate_metadata_identity(data, target.model_id, target.revision)
            return RemoteObject(FetchStatus.OK, response.body)
        except AuthenticationRequiredError:
            return RemoteObject(FetchStatus.GATED, reason_code="authentication_required")
        except GatedRepositoryError:
            return RemoteObject(FetchStatus.GATED, reason_code="gated")
        except RepositoryMissingError:
            return RemoteObject(FetchStatus.MISSING, reason_code="not_found")
        except ResponseTooLargeError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="size_limit")
        except RevisionDriftError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="revision_drift")
        except UntrustedRedirectError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="untrusted_redirect")
        except NetworkUnavailableError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="network_unavailable")
        except HubProtocolError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="malformed_json")

    def fetch_file(
        self,
        model_id: str,
        revision: str,
        repo_path: str,
        *,
        max_bytes: int,
    ) -> RemoteObject:
        try:
            target = TargetIdentity(model_id, revision)
            _validate_repo_path(repo_path)
            limit = _validate_max_bytes(max_bytes)
            url = _file_url(target.model_id, target.revision, repo_path)
            response = self._open(url, limit)
            failure = self._remote_failure(response)
            if failure is not None:
                return failure
            self._validate_response_route(
                response,
                initial_url=url,
                exact_revision=target.revision,
                allow_file_redirect=True,
            )
            return RemoteObject(FetchStatus.OK, response.body)
        except AuthenticationRequiredError:
            return RemoteObject(FetchStatus.GATED, reason_code="authentication_required")
        except GatedRepositoryError:
            return RemoteObject(FetchStatus.GATED, reason_code="gated")
        except RepositoryMissingError:
            return RemoteObject(FetchStatus.MISSING, reason_code="not_found")
        except ResponseTooLargeError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="size_limit")
        except RevisionDriftError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="revision_drift")
        except UntrustedRedirectError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="untrusted_redirect")
        except NetworkUnavailableError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="network_unavailable")
        except HubProtocolError:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="protocol_error")

    def _open(self, url: str, max_bytes: int) -> TransportResponse:
        headers: list[tuple[str, str]] = [
            ("Accept", "application/json, text/plain;q=0.9, */*;q=0.1"),
            ("Cache-Control", "no-store"),
            ("Pragma", "no-cache"),
            ("User-Agent", DETERMINISTIC_USER_AGENT),
        ]
        if self._token is not None:
            headers.append(("Authorization", f"Bearer {self._token}"))
        request = TransportRequest(
            url=url,
            headers=tuple(sorted(headers, key=lambda item: item[0].casefold())),
            max_bytes=max_bytes,
        )
        try:
            response = self._transport.open(request)
        except (TransportNetworkError, URLError, OSError):
            raise NetworkUnavailableError("Hub network is unavailable") from None
        except HuggingFaceAdapterError:
            raise
        except Exception:
            raise NetworkUnavailableError("Hub transport failed") from None
        if not isinstance(response, TransportResponse):
            raise HubProtocolError("Hub transport returned an invalid response")
        if response.too_large or len(response.body) > max_bytes:
            raise ResponseTooLargeError("Hub response exceeded the byte limit")
        content_length = _parse_content_length(response.header("Content-Length"))
        if content_length is not None and content_length > max_bytes:
            raise ResponseTooLargeError("Hub response exceeded the byte limit")
        return response

    def _remote_failure(self, response: TransportResponse) -> RemoteObject | None:
        if response.status_code == 200:
            return None
        if response.status_code == 401:
            raise AuthenticationRequiredError("Hub authentication is required")
        if response.status_code == 403:
            raise GatedRepositoryError("Hub repository is gated")
        if response.status_code == 404:
            raise RepositoryMissingError("Hub resource was not found")
        if response.status_code == 413:
            raise ResponseTooLargeError("Hub response exceeded the byte limit")
        if response.status_code in {408, 409, 425, 429} or response.status_code >= 500:
            raise NetworkUnavailableError("Hub service is unavailable")
        raise HubProtocolError("Hub returned an unsupported status")

    def _raise_resolution_status(self, response: TransportResponse) -> None:
        self._remote_failure(response)

    def _validate_response_route(
        self,
        response: TransportResponse,
        *,
        initial_url: str,
        exact_revision: str | None,
        allow_file_redirect: bool,
    ) -> None:
        for redirected_url in (*response.redirect_chain, response.final_url):
            _validate_https_url(redirected_url, self._trusted_hosts)
        if not allow_file_redirect:
            if _route_identity(response.final_url) != _route_identity(initial_url):
                raise UntrustedRedirectError("Hub metadata redirect changed the endpoint")
            return
        if response.final_url != initial_url:
            assert exact_revision is not None
            decoded_route = unquote(response.final_url)
            if re.search(
                rf"(?<![0-9a-f]){re.escape(exact_revision)}(?![0-9a-f])",
                decoded_route,
            ) is None:
                raise RevisionDriftError("Hub file redirect lost the exact commit")


def _validate_target_request(
    model_id: str, requested_revision: str | None
) -> tuple[str, str | None]:
    parsed_model_id, parsed_revision = parse_target_request(model_id, requested_revision)
    if parsed_model_id != model_id:
        raise SourceBundleError("adapter model_id cannot contain an embedded revision")
    return parsed_model_id, parsed_revision


def _validate_metadata_identity(
    data: dict[str, Any], model_id: str, exact_revision: str
) -> None:
    sha = data.get("sha")
    if sha is not None and sha != exact_revision:
        raise RevisionDriftError("Hub metadata commit differs from the exact target")
    for key in ("id", "modelId"):
        declared_model = data.get(key)
        if declared_model is not None and declared_model != model_id:
            raise RevisionDriftError("Hub metadata repository differs from the exact target")


def _strict_json_object(body: bytes, *, malformed_reason: str) -> dict[str, Any]:
    try:
        value = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, HubProtocolError):
        raise HubProtocolError(malformed_reason) from None
    if not isinstance(value, dict):
        raise HubProtocolError(malformed_reason)
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise HubProtocolError("Hub JSON contains duplicate keys")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise HubProtocolError(f"Hub JSON contains invalid number type {value!r}")


def _validate_token(token: str | None) -> str | None:
    if token is None:
        return None
    if (
        not isinstance(token, str)
        or not token
        or len(token) > 4096
        or token.strip() != token
        or any(ord(character) < 33 or ord(character) == 127 for character in token)
    ):
        raise ValueError("token is invalid")
    return token


def _normalize_trusted_hosts(hosts: Sequence[str]) -> frozenset[str]:
    normalized = {HUGGING_FACE_HOST}
    for host in hosts:
        if (
            not isinstance(host, str)
            or not host
            or host.strip() != host
            or "/" in host
            or ":" in host
        ):
            raise ValueError("trusted redirect host is invalid")
        try:
            ascii_host = host.encode("idna").decode("ascii").casefold()
        except UnicodeError as exc:
            raise ValueError("trusted redirect host is invalid") from exc
        normalized.add(ascii_host)
    return frozenset(normalized)


def _validate_https_url(url: str, trusted_hosts: Sequence[str] | set[str]) -> None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
        host = (parsed.hostname or "").encode("idna").decode("ascii").casefold()
    except (TypeError, ValueError, UnicodeError) as exc:
        raise UntrustedRedirectError("Hub URL is malformed") from exc
    if (
        parsed.scheme.casefold() != "https"
        or not host
        or host not in {item.casefold() for item in trusted_hosts}
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise UntrustedRedirectError("Hub URL has an untrusted origin")


def _redirect_headers(
    headers: Sequence[tuple[str, str]],
    source_url: str,
    destination_url: str,
    trusted_hosts: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    _validate_https_url(destination_url, trusted_hosts)
    source_host = (urlsplit(source_url).hostname or "").casefold()
    destination_host = (urlsplit(destination_url).hostname or "").casefold()
    return tuple(
        (name, value)
        for name, value in headers
        if not (source_host != destination_host and name.casefold() == "authorization")
    )


def _validate_max_bytes(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("max_bytes must be a positive integer")
    return value


def _validate_repo_path(path: str) -> None:
    if (
        not isinstance(path, str)
        or not path
        or len(path) > 512
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    ):
        raise SourceBundleError("repository path is invalid or unsafe")


def _metadata_url(model_id: str, revision: str) -> str:
    return (
        f"https://{HUGGING_FACE_HOST}/api/models/{quote(model_id, safe='/')}/revision/"
        f"{quote(revision, safe='')}"
    )


def _file_url(model_id: str, revision: str, repo_path: str) -> str:
    return (
        f"https://{HUGGING_FACE_HOST}/{quote(model_id, safe='/')}/resolve/"
        f"{quote(revision, safe='')}/{quote(repo_path, safe='/')}"
    )


def _route_identity(url: str) -> tuple[str, str, int | None, str, str]:
    parsed = urlsplit(url)
    return (
        parsed.scheme.casefold(),
        (parsed.hostname or "").casefold(),
        parsed.port,
        parsed.path,
        parsed.query,
    )


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value, 10)
    except (TypeError, ValueError):
        raise HubProtocolError("Hub Content-Length is invalid") from None
    if parsed < 0:
        raise HubProtocolError("Hub Content-Length is invalid")
    return parsed


__all__ = [
    "AuthenticationRequiredError",
    "DETERMINISTIC_USER_AGENT",
    "GatedRepositoryError",
    "HubProtocolError",
    "HuggingFaceAdapterError",
    "HuggingFaceHubAdapter",
    "NetworkUnavailableError",
    "OpenableTransport",
    "RepositoryMissingError",
    "ResponseTooLargeError",
    "RevisionDriftError",
    "StdlibHuggingFaceTransport",
    "TransportNetworkError",
    "TransportRequest",
    "TransportResponse",
    "UntrustedRedirectError",
]
