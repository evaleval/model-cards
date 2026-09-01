from __future__ import annotations

import unittest

from model_cards.official_http import (
    OfficialHttpError,
    OfficialHttpResponse,
    StdlibOfficialSourceAdapter,
)
from model_cards.official_sources import OfficialFetchStatus


class Transport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request):
        self.requests.append(request)
        if not self.responses:
            raise OSError("fixture unavailable")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class OfficialHttpTests(unittest.TestCase):
    def adapter(self, transport):
        return StdlibOfficialSourceAdapter(
            ("arxiv.org", "export.arxiv.org"), transport=transport
        )

    def test_manual_redirect_chain_is_validated_before_each_request(self) -> None:
        transport = Transport(
            OfficialHttpResponse(
                302, headers={"Location": "https://export.arxiv.org/pdf/2601.00001"}
            ),
            OfficialHttpResponse(
                200,
                headers={"Content-Type": "application/pdf"},
                body=b"%PDF synthetic fixture",
            ),
        )
        response = self.adapter(transport).fetch(
            "https://arxiv.org/abs/2601.00001", max_bytes=1000, max_redirects=2
        )
        self.assertEqual(OfficialFetchStatus.OK, response.status)
        self.assertEqual(
            (
                "https://arxiv.org/abs/2601.00001",
                "https://export.arxiv.org/pdf/2601.00001",
            ),
            response.redirect_chain,
        )
        self.assertEqual(2, len(transport.requests))
        self.assertEqual(1000, transport.requests[1].max_bytes)

    def test_unsafe_redirect_is_blocked_without_sending_second_request(self) -> None:
        for location in (
            "http://arxiv.org/file",
            "https://localhost/private",
            "https://127.0.0.1/private",
            "https://user:secret@arxiv.org/private",
            "https://example.com/unowned",
        ):
            with self.subTest(location=location):
                transport = Transport(OfficialHttpResponse(302, headers={"Location": location}))
                response = self.adapter(transport).fetch(
                    "https://arxiv.org/abs/2601.00001",
                    max_bytes=1000,
                    max_redirects=2,
                )
                self.assertEqual(OfficialFetchStatus.BLOCKED, response.status)
                self.assertEqual("unsafe_redirect", response.reason_code)
                self.assertEqual(1, len(transport.requests))

    def test_statuses_and_size_or_media_fail_closed(self) -> None:
        cases = (
            (OfficialHttpResponse(403), OfficialFetchStatus.GATED, "access_gated"),
            (OfficialHttpResponse(404), OfficialFetchStatus.MISSING, "source_missing"),
            (OfficialHttpResponse(429), OfficialFetchStatus.UNAVAILABLE, "remote_unavailable"),
            (OfficialHttpResponse(503), OfficialFetchStatus.UNAVAILABLE, "remote_unavailable"),
            (OfficialHttpResponse(418), OfficialFetchStatus.BLOCKED, "http_status_blocked"),
            (
                OfficialHttpResponse(200, headers={"Content-Type": "application/pdf"}, too_large=True),
                OfficialFetchStatus.BLOCKED,
                "size_limit",
            ),
            (
                OfficialHttpResponse(200, headers={"Content-Type": "application/octet-stream"}),
                OfficialFetchStatus.BLOCKED,
                "unsupported_media_type",
            ),
        )
        for raw, status, reason in cases:
            with self.subTest(status=status, reason=reason):
                result = self.adapter(Transport(raw)).fetch(
                    "https://arxiv.org/abs/2601.00001",
                    max_bytes=1000,
                    max_redirects=0,
                )
                self.assertEqual(status, result.status)
                self.assertEqual(reason, result.reason_code)

    def test_transport_failures_are_typed_without_exception_text(self) -> None:
        result = self.adapter(Transport(OSError("private host details"))).fetch(
            "https://arxiv.org/abs/2601.00001", max_bytes=1000, max_redirects=0
        )
        self.assertEqual(OfficialFetchStatus.UNAVAILABLE, result.status)
        self.assertEqual("network_unavailable", result.reason_code)
        self.assertNotIn("private", repr(result))

    def test_allowlist_and_request_url_reject_private_or_credentialed_hosts(self) -> None:
        for host in ("", "localhost", "127.0.0.1", "bad/path"):
            with self.subTest(host=host), self.assertRaises(OfficialHttpError):
                StdlibOfficialSourceAdapter((host,), transport=Transport())
        adapter = self.adapter(Transport())
        result = adapter.fetch(
            "https://user:password@arxiv.org/abs/x", max_bytes=100, max_redirects=0
        )
        self.assertEqual(OfficialFetchStatus.BLOCKED, result.status)
        self.assertEqual("unsafe_request_url", result.reason_code)
        self.assertEqual([], adapter.transport.requests)

    def test_header_normalization_rejects_ambiguous_values(self) -> None:
        with self.assertRaises(OfficialHttpError):
            OfficialHttpResponse(200, headers={"Location": "a", "location": "b"})
        with self.assertRaises(OfficialHttpError):
            OfficialHttpResponse(200, headers={"X": "value\nnext"})


if __name__ == "__main__":
    unittest.main()
