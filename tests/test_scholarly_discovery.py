from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from urllib.parse import parse_qs, urlsplit
import unittest

from model_cards.official_discovery import OfficialSourceKind
from model_cards.official_sources import SourceAuthority
from model_cards.scholarly_discovery import (
    DEFAULT_MAX_HINTS,
    DEFAULT_MAX_RESPONSE_BYTES,
    DEFAULT_MAX_RESULTS_PER_SERVICE,
    ScholarlyDiscoveryError,
    ScholarlyDiscoveryLimits,
    ScholarlyRequest,
    ScholarlyResponse,
    ScholarlyService,
    ScholarlyServiceStatus,
    discover_scholarly_sources,
    load_scholarly_discovery,
    serialize_scholarly_discovery,
)
from model_cards.source_bundle import TargetIdentity


COMMIT = "e" * 40


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class FixtureTransport:
    def __init__(self, responses: dict[ScholarlyService, object]) -> None:
        self.responses = responses
        self.requests: list[ScholarlyRequest] = []

    def open(self, request: ScholarlyRequest) -> ScholarlyResponse:
        self.requests.append(request)
        response = self.responses[request.service]
        if isinstance(response, Exception):
            raise response
        return response  # type: ignore[return-value]


class ScholarlyDiscoveryTests(unittest.TestCase):
    def target(self) -> TargetIdentity:
        return TargetIdentity("acme/Model-7B-Instruct", COMMIT)

    def test_two_fixed_queries_normalize_deduplicate_and_remain_hint_only(self) -> None:
        transport = FixtureTransport(
            {
                ScholarlyService.OPENALEX: ScholarlyResponse(
                    200,
                    json_bytes(
                        {
                            "results": [
                                {
                                    "doi": "https://doi.org/10.1234/ABC.7",
                                    "ids": {
                                        "doi": "doi:10.1234/abc.7",
                                        "arxiv": "arXiv:2401.01234v2",
                                    },
                                    "primary_location": {
                                        "landing_page_url": (
                                            "https://export.arxiv.org/pdf/2401.01234v1.pdf"
                                        )
                                    },
                                },
                                {
                                    "best_oa_location": {
                                        "landing_page_url": "https://example.org/not-primary"
                                    }
                                },
                            ]
                        }
                    ),
                ),
                ScholarlyService.SEMANTIC_SCHOLAR: ScholarlyResponse(
                    200,
                    json_bytes(
                        {
                            "data": [
                                {
                                    "externalIds": {
                                        "ArXiv": "2401.01234",
                                        "DOI": "10.5555/Second",
                                    }
                                },
                                {"externalIds": {"CorpusId": 123}},
                            ]
                        }
                    ),
                ),
            }
        )
        report = discover_scholarly_sources(self.target(), transport)

        self.assertEqual(2, len(transport.requests))
        self.assertEqual(
            [ScholarlyService.OPENALEX, ScholarlyService.SEMANTIC_SCHOLAR],
            [item.service for item in transport.requests],
        )
        for request in transport.requests:
            parsed = urlsplit(request.url)
            self.assertEqual("https", parsed.scheme)
            self.assertNotIn("key", parse_qs(parsed.query))
            self.assertEqual(DEFAULT_MAX_RESPONSE_BYTES, request.max_bytes)
            values = parse_qs(parsed.query)
            queries = values.get("search", []) + values.get("query", [])
            self.assertIn("Model 7B Instruct acme", queries)
            self.assertIn(
                str(DEFAULT_MAX_RESULTS_PER_SERVICE),
                values.get("per-page", []) + values.get("limit", []),
            )

        self.assertEqual(
            (
                "https://arxiv.org/abs/2401.01234",
                "https://doi.org/10.1234/abc.7",
                "https://doi.org/10.5555/second",
            ),
            tuple(item.url for item in report.hints),
        )
        self.assertFalse(report.truncated)
        self.assertTrue(
            all(item.kind is OfficialSourceKind.PAPER for item in report.hints)
        )
        self.assertTrue(
            all(
                item.authority is SourceAuthority.SCHOLARLY_DISCOVERY
                and item.reason_code == "scholarly_result_only"
                for item in report.hints
            )
        )
        self.assertTrue(
            all(
                item.status is ScholarlyServiceStatus.COMPLETED
                for item in report.services
            )
        )
        self.assertEqual([2, 2], [item.results_seen for item in report.services])

        payload = serialize_scholarly_discovery(report)
        self.assertNotIn(b"example.org", payload)
        self.assertNotIn(b"title", payload)
        self.assertEqual(report, load_scholarly_discovery(payload))
        self.assertEqual(
            report,
            load_scholarly_discovery(payload + b"\n", expected_target=self.target()),
        )
        with self.assertRaises(FrozenInstanceError):
            report.truncated = False

    def test_every_failure_is_explicit_and_does_not_abort_other_service(self) -> None:
        cases = (
            (
                RuntimeError("network response body secret"),
                ScholarlyServiceStatus.UNAVAILABLE,
                "network_unavailable",
                None,
            ),
            (
                ScholarlyResponse(429),
                ScholarlyServiceStatus.UNAVAILABLE,
                "remote_unavailable",
                429,
            ),
            (
                ScholarlyResponse(403),
                ScholarlyServiceStatus.GATED,
                "access_gated",
                403,
            ),
            (
                ScholarlyResponse(302),
                ScholarlyServiceStatus.BLOCKED,
                "unexpected_http_status",
                302,
            ),
            (
                ScholarlyResponse(200, b"{}", too_large=True),
                ScholarlyServiceStatus.BLOCKED,
                "size_limit",
                200,
            ),
            (
                ScholarlyResponse(200, b'{"results":'),
                ScholarlyServiceStatus.MALFORMED,
                "malformed_response",
                200,
            ),
        )
        semantic_ok = ScholarlyResponse(200, json_bytes({"data": []}))
        for response, expected_status, expected_reason, expected_http in cases:
            with self.subTest(expected_reason=expected_reason, expected_http=expected_http):
                transport = FixtureTransport(
                    {
                        ScholarlyService.OPENALEX: response,
                        ScholarlyService.SEMANTIC_SCHOLAR: semantic_ok,
                    }
                )
                report = discover_scholarly_sources(self.target(), transport)
                openalex = report.services[0]
                semantic = report.services[1]
                self.assertEqual(expected_status, openalex.status)
                self.assertEqual(expected_reason, openalex.reason_code)
                self.assertEqual(expected_http, openalex.http_status)
                self.assertEqual(ScholarlyServiceStatus.COMPLETED, semantic.status)
                self.assertEqual((), report.hints)
                self.assertNotIn("response body secret", str(report.to_dict()))

    def test_hint_and_response_caps_are_strict_and_reported(self) -> None:
        openalex_results = [
            {"doi": f"10.1234/result.{index}"} for index in range(12)
        ]
        semantic_results = [
            {"externalIds": {"ArXiv": f"2401.{index:05d}"}}
            for index in range(12)
        ]
        transport = FixtureTransport(
            {
                ScholarlyService.OPENALEX: ScholarlyResponse(
                    200, json_bytes({"results": openalex_results})
                ),
                ScholarlyService.SEMANTIC_SCHOLAR: ScholarlyResponse(
                    200, json_bytes({"data": semantic_results})
                ),
            }
        )
        report = discover_scholarly_sources(self.target(), transport)
        self.assertEqual(DEFAULT_MAX_HINTS, len(report.hints))
        self.assertEqual(
            [DEFAULT_MAX_RESULTS_PER_SERVICE, DEFAULT_MAX_RESULTS_PER_SERVICE],
            [item.results_seen for item in report.services],
        )
        self.assertTrue(report.truncated)

        with self.assertRaises(ScholarlyDiscoveryError):
            ScholarlyDiscoveryLimits(max_results_per_service=11)
        with self.assertRaises(ScholarlyDiscoveryError):
            ScholarlyDiscoveryLimits(max_hints=17)
        with self.assertRaises(ScholarlyDiscoveryError):
            ScholarlyDiscoveryLimits(max_response_bytes=1_000_001)

    def test_replay_rejects_drift_duplicates_and_noncanonical_json(self) -> None:
        transport = FixtureTransport(
            {
                ScholarlyService.OPENALEX: ScholarlyResponse(
                    200, json_bytes({"results": []})
                ),
                ScholarlyService.SEMANTIC_SCHOLAR: ScholarlyResponse(
                    200, json_bytes({"data": []})
                ),
            }
        )
        report = discover_scholarly_sources(self.target(), transport)
        payload = serialize_scholarly_discovery(report)
        with self.assertRaises(ScholarlyDiscoveryError):
            load_scholarly_discovery(b" " + payload)
        with self.assertRaises(ScholarlyDiscoveryError):
            load_scholarly_discovery(
                payload,
                expected_target=TargetIdentity("acme/Other", COMMIT),
            )
        duplicate = payload.replace(b'{"discovery_version":', b'{"query":"x","discovery_version":')
        with self.assertRaises(ScholarlyDiscoveryError):
            load_scholarly_discovery(duplicate)


if __name__ == "__main__":
    unittest.main()
