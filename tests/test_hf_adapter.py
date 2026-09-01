from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from model_cards.hf_adapter import (
    DETERMINISTIC_USER_AGENT,
    AuthenticationRequiredError,
    GatedRepositoryError,
    HuggingFaceHubAdapter,
    NetworkUnavailableError,
    RepositoryMissingError,
    RevisionDriftError,
    TransportNetworkError,
    TransportRequest,
    TransportResponse,
    UntrustedRedirectError,
    _redirect_headers,
)
from model_cards.source_bundle import (
    FetchStatus,
    SourceBundleError,
    collect_hf_source_bundle,
    replay_source_bundle,
)


COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40
TOKEN = "synthetic_token_value_for_test"


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FixtureTransport:
    def __init__(self, handler):
        self.handler = handler
        self.requests: list[TransportRequest] = []

    def open(self, request: TransportRequest) -> TransportResponse:
        self.requests.append(request)
        return self.handler(request)


def response_for(
    request: TransportRequest,
    *,
    status: int = 200,
    body: bytes = b"",
    final_url: str | None = None,
    redirects: tuple[str, ...] = (),
    headers: tuple[tuple[str, str], ...] = (),
    too_large: bool = False,
) -> TransportResponse:
    return TransportResponse(
        status_code=status,
        final_url=final_url or request.url,
        headers=headers,
        body=body,
        redirect_chain=redirects,
        too_large=too_large,
    )


class HuggingFaceAdapterTests(unittest.TestCase):
    def test_concrete_adapter_drives_exact_bundle_collection_without_live_network(self) -> None:
        def hub_fixture(request: TransportRequest) -> TransportResponse:
            if request.url.endswith("/revision/main"):
                payload = {"id": "acme/Model", "sha": COMMIT}
            elif "/api/models/" in request.url:
                payload = {
                    "id": "acme/Model",
                    "sha": COMMIT,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            elif request.url.endswith("/README.md"):
                return response_for(request, body=b"# Exact model\n")
            elif request.url.endswith("/config.json"):
                return response_for(request, body=b"{}\n")
            else:
                return response_for(request, status=404)
            return response_for(request, body=encoded(payload))

        transport = FixtureTransport(hub_fixture)
        adapter = HuggingFaceHubAdapter(transport=transport)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        destination = Path(temporary.name) / "bundle"
        manifest = collect_hf_source_bundle("acme/Model", destination, adapter)
        replayed = replay_source_bundle(
            destination,
            expected_model_id="acme/Model",
            expected_revision=COMMIT,
        )
        self.assertEqual(manifest.bundle_id, replayed.manifest.bundle_id)
        self.assertEqual(4, len(transport.requests))

    def test_resolution_uses_official_endpoint_and_deterministic_no_cache_headers(self) -> None:
        transport = FixtureTransport(
            lambda request: response_for(
                request,
                body=encoded({"id": "acme/Model", "sha": COMMIT}),
            )
        )
        adapter = HuggingFaceHubAdapter(token=TOKEN, transport=transport)
        self.assertEqual(COMMIT, adapter.resolve_revision("acme/Model", "release-1"))
        self.assertEqual(1, len(transport.requests))
        request = transport.requests[0]
        self.assertEqual(
            "https://huggingface.co/api/models/acme/Model/revision/release-1",
            request.url,
        )
        self.assertEqual(DETERMINISTIC_USER_AGENT, request.header("User-Agent"))
        self.assertEqual("no-store", request.header("Cache-Control"))
        self.assertEqual("no-cache", request.header("Pragma"))
        self.assertEqual(f"Bearer {TOKEN}", request.header("Authorization"))
        self.assertNotIn(TOKEN, repr(request))
        self.assertNotIn(TOKEN, repr(adapter))

    def test_exact_requested_revision_cannot_resolve_to_a_different_commit(self) -> None:
        transport = FixtureTransport(
            lambda request: response_for(
                request,
                body=encoded({"id": "acme/Model", "sha": OTHER_COMMIT}),
            )
        )
        adapter = HuggingFaceHubAdapter(transport=transport)
        with self.assertRaises(RevisionDriftError):
            adapter.resolve_revision("acme/Model", COMMIT)

    def test_resolution_has_explicit_missing_auth_gated_and_network_errors(self) -> None:
        cases = (
            (401, AuthenticationRequiredError),
            (403, GatedRepositoryError),
            (404, RepositoryMissingError),
            (503, NetworkUnavailableError),
        )
        for status, error_type in cases:
            with self.subTest(status=status):
                transport = FixtureTransport(
                    lambda request, status=status: response_for(request, status=status)
                )
                with self.assertRaises(error_type):
                    HuggingFaceHubAdapter(transport=transport).resolve_revision(
                        "acme/Model", None
                    )

        def unavailable(_request):
            raise TransportNetworkError(f"network failed with {TOKEN}")

        with self.assertRaises(NetworkUnavailableError) as caught:
            HuggingFaceHubAdapter(
                token=TOKEN,
                transport=FixtureTransport(unavailable),
            ).resolve_revision("acme/Model", None)
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_file_fetch_maps_remote_outcomes_to_typed_status_records(self) -> None:
        cases = (
            (401, FetchStatus.GATED, "authentication_required"),
            (403, FetchStatus.GATED, "gated"),
            (404, FetchStatus.MISSING, "not_found"),
            (413, FetchStatus.UNAVAILABLE, "size_limit"),
            (429, FetchStatus.UNAVAILABLE, "network_unavailable"),
        )
        for status, expected_status, expected_reason in cases:
            with self.subTest(status=status):
                transport = FixtureTransport(
                    lambda request, status=status: response_for(request, status=status)
                )
                outcome = HuggingFaceHubAdapter(transport=transport).fetch_file(
                    "acme/Model", COMMIT, "README.md", max_bytes=100
                )
                self.assertIs(expected_status, outcome.status)
                self.assertEqual(expected_reason, outcome.reason_code)

    def test_malformed_metadata_and_revision_drift_fail_closed(self) -> None:
        malformed = FixtureTransport(
            lambda request: response_for(request, body=b"{not-json")
        )
        outcome = HuggingFaceHubAdapter(transport=malformed).fetch_model_metadata(
            "acme/Model", COMMIT, max_bytes=1_000
        )
        self.assertIs(FetchStatus.UNAVAILABLE, outcome.status)
        self.assertEqual("malformed_json", outcome.reason_code)

        duplicate = FixtureTransport(
            lambda request: response_for(
                request, body=b'{"sha":"' + COMMIT.encode() + b'","sha":"x"}'
            )
        )
        outcome = HuggingFaceHubAdapter(transport=duplicate).fetch_model_metadata(
            "acme/Model", COMMIT, max_bytes=1_000
        )
        self.assertEqual("malformed_json", outcome.reason_code)

        drifting = FixtureTransport(
            lambda request: response_for(
                request,
                body=encoded({"id": "other/Model", "sha": COMMIT}),
            )
        )
        outcome = HuggingFaceHubAdapter(transport=drifting).fetch_model_metadata(
            "acme/Model", COMMIT, max_bytes=1_000
        )
        self.assertEqual("revision_drift", outcome.reason_code)

    def test_oversized_body_or_content_length_is_never_returned(self) -> None:
        oversized = FixtureTransport(
            lambda request: response_for(request, body=b"x" * 11)
        )
        outcome = HuggingFaceHubAdapter(transport=oversized).fetch_file(
            "acme/Model", COMMIT, "README.md", max_bytes=10
        )
        self.assertIs(FetchStatus.UNAVAILABLE, outcome.status)
        self.assertEqual("size_limit", outcome.reason_code)

        declared_oversized = FixtureTransport(
            lambda request: response_for(
                request,
                body=b"x",
                headers=(("Content-Length", "100"),),
            )
        )
        outcome = HuggingFaceHubAdapter(transport=declared_oversized).fetch_file(
            "acme/Model", COMMIT, "README.md", max_bytes=10
        )
        self.assertEqual("size_limit", outcome.reason_code)

    def test_untrusted_redirect_and_exact_commit_loss_are_rejected(self) -> None:
        evil_url = "https://evil.example/collect"
        untrusted = FixtureTransport(
            lambda request: response_for(
                request,
                body=b"safe-looking",
                final_url=evil_url,
                redirects=(evil_url,),
            )
        )
        outcome = HuggingFaceHubAdapter(token=TOKEN, transport=untrusted).fetch_file(
            "acme/Model", COMMIT, "README.md", max_bytes=100
        )
        self.assertEqual("untrusted_redirect", outcome.reason_code)

        with self.assertRaises(UntrustedRedirectError):
            HuggingFaceHubAdapter(token=TOKEN, transport=untrusted).resolve_revision(
                "acme/Model", "main"
            )

        trusted_but_drifting = "https://cdn.huggingface.co/blob/README.md"
        drifting = FixtureTransport(
            lambda request: response_for(
                request,
                body=b"content",
                final_url=trusted_but_drifting,
                redirects=(trusted_but_drifting,),
            )
        )
        outcome = HuggingFaceHubAdapter(
            transport=drifting,
            trusted_redirect_hosts=("cdn.huggingface.co",),
        ).fetch_file("acme/Model", COMMIT, "README.md", max_bytes=100)
        self.assertEqual("revision_drift", outcome.reason_code)

    def test_authorization_is_stripped_before_a_trusted_cross_host_redirect(self) -> None:
        headers = (
            ("Authorization", f"Bearer {TOKEN}"),
            ("User-Agent", DETERMINISTIC_USER_AGENT),
        )
        redirected = _redirect_headers(
            headers,
            "https://huggingface.co/acme/Model/resolve/main/README.md",
            "https://cdn.huggingface.co/acme/README.md",
            ("huggingface.co", "cdn.huggingface.co"),
        )
        self.assertNotIn("Authorization", {name for name, _ in redirected})
        self.assertIn("User-Agent", {name for name, _ in redirected})
        retained = _redirect_headers(
            headers,
            "https://huggingface.co/first",
            "https://huggingface.co/second",
            ("huggingface.co",),
        )
        self.assertEqual(f"Bearer {TOKEN}", dict(retained)["Authorization"])
        with self.assertRaises(UntrustedRedirectError):
            _redirect_headers(
                headers,
                "https://huggingface.co/first",
                "http://huggingface.co/second",
                ("huggingface.co",),
            )

    def test_invalid_input_never_reaches_transport(self) -> None:
        transport = FixtureTransport(
            lambda request: response_for(request, body=b"unused")
        )
        adapter = HuggingFaceHubAdapter(transport=transport)
        with self.assertRaises(SourceBundleError):
            adapter.fetch_file("acme/Model", COMMIT, "../secret", max_bytes=100)
        with self.assertRaises(SourceBundleError):
            adapter.resolve_revision("acme/Model@main", None)
        with self.assertRaises(ValueError):
            HuggingFaceHubAdapter(token="bad\nheader", transport=transport)
        self.assertEqual([], transport.requests)


if __name__ == "__main__":
    unittest.main()
