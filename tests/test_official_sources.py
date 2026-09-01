from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.official_discovery import (
    DiscoveryStatus,
    OfficialSourceKind,
    OfficialSourcePolicy,
    discover_official_sources,
)
from model_cards.official_sources import (
    ContentPin,
    DiscoveryHint,
    EvalEvalAvailability,
    EvalEvalJoinTier,
    OfficialFetchStatus,
    OfficialRemoteObject,
    OfficialSourceIntegrityError,
    OfficialSourceStatus,
    RelationAssertion,
    RelationState,
    SourceAuthority,
    collect_official_sources,
    load_evaleval_join,
    replay_official_sources,
)
from model_cards.models import RelationToTarget
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)


COMMIT = "d" * 40


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class FrozenBundleAdapter:
    def __init__(self, readme: bytes) -> None:
        self.readme = readme

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        return COMMIT

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        return RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "id": model_id,
                    "sha": revision,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )

    def fetch_file(
        self, model_id: str, revision: str, repo_path: str, *, max_bytes: int
    ) -> RemoteObject:
        if repo_path == "README.md":
            return RemoteObject(FetchStatus.OK, self.readme)
        if repo_path == "config.json":
            return RemoteObject(FetchStatus.OK, b"{}\n")
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class PrimaryAdapter:
    def __init__(
        self,
        responses: dict[str, OfficialRemoteObject] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, int, int]] = []

    def fetch(
        self, url: str, *, max_bytes: int, max_redirects: int
    ) -> OfficialRemoteObject:
        self.calls.append((url, max_bytes, max_redirects))
        return self.responses.get(
            url,
            OfficialRemoteObject(
                OfficialFetchStatus.OK,
                content=("primary:" + url).encode(),
                final_url=url,
                redirect_chain=(url,),
                media_type="text/html",
            ),
        )


class OfficialSourceCollectionTests(unittest.TestCase):
    def discovery(
        self,
        readme: bytes,
        *,
        policy: OfficialSourcePolicy | None = None,
    ):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        bundle_path = Path(temporary.name) / "hf"
        collect_hf_source_bundle(
            "acme/Model", bundle_path, FrozenBundleAdapter(readme)
        )
        frozen = replay_source_bundle(bundle_path)
        return discover_official_sources(frozen, policy=policy)

    def destination(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name) / "official"

    def test_verified_declared_primary_is_content_addressed_and_replays_offline(self) -> None:
        url = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({url})\n".encode())
        body = b"<html>immutable official documentation</html>"
        adapter = PrimaryAdapter(
            {
                url: OfficialRemoteObject(
                    OfficialFetchStatus.OK,
                    content=body,
                    final_url=url,
                    redirect_chain=(url,),
                    media_type="text/html",
                )
            }
        )
        destination = self.destination()
        manifest = collect_official_sources(discovery, destination, adapter)
        source = next(
            item for item in manifest.sources
            if item.requested_url == url
        )
        digest = hashlib.sha256(body).hexdigest()
        self.assertEqual(OfficialSourceStatus.COLLECTED, source.status)
        self.assertEqual(digest, source.sha256)
        self.assertEqual(f"objects/sha256/{digest[:2]}/{digest}", source.object_path)
        self.assertTrue(source.evidence_eligible)
        relation = next(item for item in manifest.relations if item.source_id == source.source_id)
        self.assertEqual(RelationToTarget.EXACT_TARGET, relation.relation_to_target)
        self.assertEqual(RelationState.DECLARED, relation.state)

        serialized = json.dumps(manifest.to_dict(), sort_keys=True)
        self.assertNotIn(str(destination.parent), serialized)
        self.assertNotIn("immutable official documentation", serialized)
        replayed = replay_official_sources(
            destination,
            expected_target=discovery.target,
            expected_discovery_id=discovery.discovery_id,
        )
        self.assertEqual(body, replayed.contents[source.source_id])
        with self.assertRaises(FrozenInstanceError):
            source.reason_code = "tampered"

    def test_unverified_ownership_and_secondary_hints_are_never_fetched(self) -> None:
        hostile = "https://github.com/other/model"
        discovery = self.discovery(f"[Code]({hostile})\n".encode())
        adapter = PrimaryAdapter()
        manifest = collect_official_sources(
            discovery,
            self.destination(),
            adapter,
            discovery_hints=(
                DiscoveryHint(
                    OfficialSourceKind.PAPER,
                    "https://example.org/interesting-paper",
                    SourceAuthority.SCHOLARLY_DISCOVERY,
                    "scholarly_result_only",
                ),
                DiscoveryHint(
                    OfficialSourceKind.CODE,
                    "https://example.org/evaleval-link",
                    SourceAuthority.EVALEVAL_DISCOVERY,
                    "evaleval_link_only",
                ),
            ),
        )
        self.assertEqual([], adapter.calls)
        ownership = next(
            item for item in manifest.sources if item.requested_url == hostile
        )
        self.assertEqual(OfficialSourceStatus.BLOCKED, ownership.status)
        self.assertEqual("ownership_mismatch", ownership.reason_code)
        discovery_only = [
            item for item in manifest.sources
            if item.status is OfficialSourceStatus.DISCOVERY_ONLY
        ]
        self.assertGreaterEqual(len(discovery_only), 2)
        self.assertTrue(all(not item.evidence_eligible for item in discovery_only))

    def test_redirects_recheck_host_and_publisher_ownership(self) -> None:
        url = "https://github.com/acme/model"
        hostile = "https://github.com/other/model"
        discovery = self.discovery(f"[Code]({url})\n".encode())
        adapter = PrimaryAdapter(
            {
                url: OfficialRemoteObject(
                    OfficialFetchStatus.OK,
                    content=b"redirected bytes",
                    final_url=hostile,
                    redirect_chain=(url, hostile),
                    media_type="text/html",
                )
            }
        )
        manifest = collect_official_sources(discovery, self.destination(), adapter)
        source = next(item for item in manifest.sources if item.requested_url == url)
        self.assertEqual(OfficialSourceStatus.BLOCKED, source.status)
        self.assertEqual("redirect_policy_violation", source.reason_code)
        self.assertIsNone(source.object_path)
        self.assertFalse(source.evidence_eligible)

        signed = "https://github.com/acme/model?token=private"
        destination = self.destination()
        query_adapter = PrimaryAdapter(
            {
                url: OfficialRemoteObject(
                    OfficialFetchStatus.OK,
                    content=b"signed redirect",
                    final_url=signed,
                    redirect_chain=(url, signed),
                    media_type="text/html",
                )
            }
        )
        query_manifest = collect_official_sources(
            discovery, destination, query_adapter
        )
        query_source = next(
            item for item in query_manifest.sources if item.requested_url == url
        )
        self.assertEqual(OfficialSourceStatus.BLOCKED, query_source.status)
        self.assertNotIn("private", json.dumps(query_manifest.to_dict()))

    def test_missing_gated_blocked_and_unavailable_are_explicit(self) -> None:
        urls = {
            "missing": "https://github.com/acme/missing",
            "gated": "https://github.com/acme/gated",
            "blocked": "https://github.com/acme/blocked",
            "unavailable": "https://github.com/acme/unavailable",
        }
        readme = "\n".join(
            f"[Code {name}]({url})" for name, url in urls.items()
        ).encode()
        discovery = self.discovery(readme)
        responses = {
            urls["missing"]: OfficialRemoteObject(
                OfficialFetchStatus.MISSING, reason_code="not_found"
            ),
            urls["gated"]: OfficialRemoteObject(
                OfficialFetchStatus.GATED, reason_code="authentication_required"
            ),
            urls["blocked"]: OfficialRemoteObject(
                OfficialFetchStatus.BLOCKED, reason_code="robots_blocked"
            ),
            urls["unavailable"]: OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE, reason_code="network_unavailable"
            ),
        }
        manifest = collect_official_sources(
            discovery, self.destination(), PrimaryAdapter(responses)
        )
        observed = {
            name: next(item.status for item in manifest.sources if item.requested_url == url)
            for name, url in urls.items()
        }
        self.assertEqual(
            {
                "missing": OfficialSourceStatus.MISSING,
                "gated": OfficialSourceStatus.GATED,
                "blocked": OfficialSourceStatus.BLOCKED,
                "unavailable": OfficialSourceStatus.UNAVAILABLE,
            },
            observed,
        )
        availability_records = [
            item for item in manifest.sources
            if item.candidate_record_id is not None and item.requested_url is None
        ]
        self.assertTrue(
            any(item.status is OfficialSourceStatus.MISSING for item in availability_records)
        )

    def test_relation_graph_covers_all_relations_without_merging_sources(self) -> None:
        relations = list(RelationToTarget)
        urls = [f"https://github.com/acme/repository-{index}" for index in range(len(relations))]
        readme = "\n".join(
            f"[Code {index}]({url})" for index, url in enumerate(urls)
        ).encode()
        discovery = self.discovery(readme)
        candidates = {
            item.normalized_url: item for item in discovery.records
            if item.status is DiscoveryStatus.DISCOVERED
        }
        assertions = []
        for index, (url, relation) in enumerate(zip(urls, relations)):
            candidate = candidates[url]
            subject = "acme/Model" if relation is RelationToTarget.EXACT_TARGET \
                else f"acme/Related-{index}"
            assertions.append(
                RelationAssertion(
                    candidate.record_id,
                    subject,
                    relation,
                    candidate.declaring_source_id,
                    candidate.declaration_locator,
                )
            )
        manifest = collect_official_sources(
            discovery,
            self.destination(),
            PrimaryAdapter(),
            relation_assertions=assertions,
        )
        self.assertEqual(set(relations), {item.relation_to_target for item in manifest.relations})
        source_ids = {
            next(item.source_id for item in manifest.sources if item.requested_url == url)
            for url in urls
        }
        self.assertEqual(len(urls), len(source_ids))
        unknown_relation = next(
            item for item in manifest.relations
            if item.relation_to_target is RelationToTarget.UNKNOWN
        )
        unknown_source = next(
            item for item in manifest.sources if item.source_id == unknown_relation.source_id
        )
        self.assertEqual(RelationState.UNRESOLVED, unknown_relation.state)
        self.assertEqual(OfficialSourceStatus.CONFLICTING, unknown_source.status)
        self.assertFalse(unknown_source.evidence_eligible)

    def test_conflicting_official_relation_declarations_are_preserved(self) -> None:
        url = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({url})\n".encode())
        candidate = next(
            item for item in discovery.records
            if item.status is DiscoveryStatus.DISCOVERED
        )
        shared = (
            candidate.record_id,
            candidate.declaring_source_id,
            candidate.declaration_locator,
        )
        assertions = (
            RelationAssertion(shared[0], "acme/Model", RelationToTarget.EXACT_TARGET, shared[1], shared[2]),
            RelationAssertion(
                shared[0], "acme/Base", RelationToTarget.BASE_MODEL, shared[1], shared[2]
            ),
        )
        manifest = collect_official_sources(
            discovery,
            self.destination(),
            PrimaryAdapter(),
            relation_assertions=assertions,
        )
        source = next(item for item in manifest.sources if item.requested_url == url)
        self.assertEqual(OfficialSourceStatus.CONFLICTING, source.status)
        self.assertEqual("conflicting_official_declarations", source.reason_code)
        self.assertFalse(source.evidence_eligible)
        source_relations = [item for item in manifest.relations if item.source_id == source.source_id]
        self.assertEqual(2, len(source_relations))
        self.assertTrue(all(item.state is RelationState.CONFLICTING for item in source_relations))

    def test_content_pin_detects_source_drift_and_replay_detects_mutation(self) -> None:
        url = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({url})\n".encode())
        candidate = next(
            item for item in discovery.records
            if item.status is DiscoveryStatus.DISCOVERED
        )
        body = b"new bytes"
        destination = self.destination()
        manifest = collect_official_sources(
            discovery,
            destination,
            PrimaryAdapter(
                {
                    url: OfficialRemoteObject(
                        OfficialFetchStatus.OK, content=body, final_url=url,
                        redirect_chain=(url,), media_type="text/plain",
                    )
                }
            ),
            content_pins=(ContentPin(candidate.record_id, "0" * 64),),
        )
        source = next(item for item in manifest.sources if item.requested_url == url)
        self.assertEqual(OfficialSourceStatus.CONFLICTING, source.status)
        self.assertEqual("source_drift", source.reason_code)
        self.assertFalse(source.evidence_eligible)
        object_file = destination.joinpath(*Path(source.object_path).parts)
        object_file.write_bytes(b"mutated")
        with self.assertRaisesRegex(OfficialSourceIntegrityError, "address"):
            replay_official_sources(destination)

    def test_replay_rejects_symlinks_and_unexpected_files(self) -> None:
        url = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({url})\n".encode())
        destination = self.destination()
        collect_official_sources(discovery, destination, PrimaryAdapter())
        (destination / "unexpected.txt").write_text("stale")
        with self.assertRaisesRegex(OfficialSourceIntegrityError, "file set"):
            replay_official_sources(destination)

        second = self.destination()
        collect_official_sources(discovery, second, PrimaryAdapter())
        (second / "unsafe").symlink_to(second / "manifest.json")
        with self.assertRaisesRegex(OfficialSourceIntegrityError, "symbolic link"):
            replay_official_sources(second)

    def test_evaleval_join_uses_exact_shape_but_remains_discovery_only(self) -> None:
        record_path = "data/mmlu/acme/Model/result.json"
        raw_join = {
            "model_id": "acme/Model",
            "tier": "exact",
            "matched_id": "acme/Model",
            "benchmarks": {
                "mmlu": [
                    {
                        "evaluation_name": "MMLU",
                        "metric_name": "accuracy",
                        "metric_id": "acc",
                        "score": 0.735,
                        "hf_repo": "acme/Model",
                        "evaluation_result_id": "eval-1",
                        "source_file": record_path,
                    },
                    {
                        "evaluation_name": "MMLU comparison",
                        "metric_name": "accuracy",
                        "metric_id": "acc",
                        "score": 0.99,
                        "hf_repo": "other/Model",
                        "evaluation_result_id": "eval-2",
                        "source_file": record_path,
                    },
                ]
            },
            "record_files": [record_path],
        }
        join = load_evaleval_join(raw_join)
        self.assertEqual(raw_join, join.to_dict())
        discovery = self.discovery(b"# no declared links\n")
        manifest = collect_official_sources(
            discovery, self.destination(), PrimaryAdapter(), evaleval_join=join
        )
        self.assertEqual(EvalEvalAvailability.MATCHED, manifest.evaleval.availability)
        self.assertEqual(EvalEvalJoinTier.EXACT, manifest.evaleval.join.tier)
        self.assertEqual(2, len(manifest.evaluation_relations))
        exact = next(
            item for item in manifest.evaluation_relations
            if item.evaluation_result_id == "eval-1"
        )
        comparison = next(
            item for item in manifest.evaluation_relations
            if item.evaluation_result_id == "eval-2"
        )
        self.assertEqual(RelationToTarget.EXACT_TARGET, exact.relation_to_target)
        self.assertEqual(RelationToTarget.UNKNOWN, comparison.relation_to_target)
        self.assertTrue(all(not item.evidence_eligible for item in manifest.evaluation_relations))

        unavailable = collect_official_sources(
            discovery,
            self.destination(),
            PrimaryAdapter(),
            evaleval_unavailable_reason="network_unavailable",
        )
        self.assertEqual(EvalEvalAvailability.UNAVAILABLE, unavailable.evaleval.availability)
        self.assertIsNone(unavailable.evaleval.join)

    def test_evaleval_rejects_fuzzy_or_local_path_joins(self) -> None:
        with self.assertRaises(OfficialSourceIntegrityError):
            load_evaleval_join(
                {
                    "model_id": "acme/Model",
                    "tier": "fuzzy",
                    "matched_id": "acme/Model-v2",
                    "benchmarks": {},
                    "record_files": [],
                }
            )
        with self.assertRaisesRegex(OfficialSourceIntegrityError, "relative POSIX"):
            load_evaleval_join(
                {
                    "model_id": "acme/Model",
                    "tier": "exact",
                    "matched_id": "acme/Model",
                    "benchmarks": {},
                    "record_files": ["/private/cache/result.json"],
                }
            )


if __name__ == "__main__":
    unittest.main()
