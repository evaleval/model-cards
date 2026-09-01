from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.official_discovery import (
    DiscoveryProvenance,
    DiscoveryStatus,
    OfficialDiscoveryError,
    OfficialSourceKind,
    OfficialSourcePolicy,
    discover_official_sources,
    load_official_discovery,
    replay_official_discovery,
    serialize_official_discovery,
)
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)


COMMIT = "c" * 40


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FrozenBundleAdapter:
    def __init__(
        self,
        *,
        metadata: RemoteObject | None = None,
        readme: RemoteObject | None = None,
        extra_files: dict[str, RemoteObject] | None = None,
    ) -> None:
        self.metadata = metadata or RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "id": "acme/Model",
                    "sha": COMMIT,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )
        self.readme = readme or RemoteObject(FetchStatus.OK, b"# Exact model\n")
        self.files = {
            "config.json": RemoteObject(FetchStatus.OK, b"{}\n"),
        }
        if extra_files:
            self.files.update(extra_files)

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        return COMMIT

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        return self.metadata

    def fetch_file(
        self, model_id: str, revision: str, repo_path: str, *, max_bytes: int
    ) -> RemoteObject:
        if repo_path == "README.md":
            return self.readme
        return self.files.get(
            repo_path,
            RemoteObject(FetchStatus.MISSING, reason_code="not_found"),
        )


class OfficialDiscoveryTests(unittest.TestCase):
    def frozen_bundle(self, adapter: FrozenBundleAdapter):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "bundle"
        collect_hf_source_bundle("acme/Model", path, adapter)
        return replay_source_bundle(path)

    def test_publisher_links_are_verified_normalized_deduplicated_and_not_evidence(self) -> None:
        metadata = RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "id": "acme/Model",
                    "sha": COMMIT,
                    "cardData": {
                        "paper_url": "https://arxiv.org/abs/2401.12345#abstract",
                        "code_url": "https://github.com/acme/model?utm_source=card#readme",
                    },
                    "code_url": "https://github.com/acme/metadata-hint",
                    "tags": ["arxiv:2501.00001"],
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )
        readme = RemoteObject(
            FetchStatus.OK,
            b"""# Exact model

[Paper](https://arxiv.org/abs/2401.12345?tracking=yes#page)
[Code](https://github.com/acme/model#files)
[Duplicate code](https://github.com/acme/model?download=1)
[System Card](docs/system-card.md#scope)
""",
        )
        result = discover_official_sources(
            self.frozen_bundle(FrozenBundleAdapter(metadata=metadata, readme=readme))
        )
        discovered = [
            item for item in result.records if item.status is DiscoveryStatus.DISCOVERED
        ]
        self.assertEqual(
            {OfficialSourceKind.PAPER, OfficialSourceKind.CODE, OfficialSourceKind.SYSTEM_CARD},
            {item.kind for item in discovered},
        )
        self.assertEqual(
            1,
            len(
                [
                    item
                    for item in discovered
                    if item.normalized_url == "https://github.com/acme/model"
                ]
            ),
        )
        paper = next(item for item in discovered if item.kind is OfficialSourceKind.PAPER)
        self.assertEqual("https://arxiv.org/abs/2401.12345", paper.normalized_url)
        system_card = next(
            item for item in discovered if item.kind is OfficialSourceKind.SYSTEM_CARD
        )
        self.assertEqual(
            f"https://huggingface.co/acme/Model/resolve/{COMMIT}/docs/system-card.md",
            system_card.normalized_url,
        )
        secondary = [
            item
            for item in result.records
            if item.provenance is DiscoveryProvenance.SECONDARY_HINT
        ]
        self.assertEqual(2, len(secondary))
        self.assertTrue(all(item.status is DiscoveryStatus.REJECTED for item in secondary))
        self.assertTrue(all(item.reason_code == "secondary_hint_only" for item in secondary))
        self.assertTrue(all(item.evidence_eligible is False for item in result.records))

    def test_untrusted_hosts_wrong_owners_and_unsupported_schemes_are_rejected(self) -> None:
        readme = RemoteObject(
            FetchStatus.OK,
            b"""# Exact model

[Code](https://github.com/other/repository)
[Code owner only](https://github.com/acme)
[System Card](https://untrusted.example/system-card.pdf)
[Paper](ftp://arxiv.org/paper.pdf?token=removed#fragment)
[Paper root](https://arxiv.org/)
""",
        )
        result = discover_official_sources(
            self.frozen_bundle(FrozenBundleAdapter(readme=readme))
        )
        rejected = [item for item in result.records if item.status is DiscoveryStatus.REJECTED]
        self.assertEqual(
            {
                "ownership_mismatch",
                "ownership_unverified",
                "resource_unverified",
                "untrusted_host",
                "unsupported_scheme",
            },
            {item.reason_code for item in rejected},
        )
        unsupported = next(item for item in rejected if item.reason_code == "unsupported_scheme")
        self.assertEqual("ftp://arxiv.org/paper.pdf", unsupported.declared_url)
        self.assertIsNone(unsupported.normalized_url)
        for kind in OfficialSourceKind:
            self.assertTrue(
                any(
                    item.kind is kind and item.status is DiscoveryStatus.UNAVAILABLE
                    for item in result.records
                )
            )

    def test_custom_verified_owned_host_can_be_declared_by_policy(self) -> None:
        readme = RemoteObject(
            FetchStatus.OK,
            b"[System Card](https://research.acme.example/cards/model)\n",
        )
        bundle = self.frozen_bundle(FrozenBundleAdapter(readme=readme))
        default = discover_official_sources(bundle)
        self.assertTrue(
            any(item.reason_code == "untrusted_host" for item in default.records)
        )
        policy = OfficialSourcePolicy.for_target(
            bundle.manifest.target,
            owned_hosts=("research.acme.example",),
        )
        trusted = discover_official_sources(bundle, policy=policy)
        self.assertTrue(
            any(
                item.kind is OfficialSourceKind.SYSTEM_CARD
                and item.status is DiscoveryStatus.DISCOVERED
                for item in trusted.records
            )
        )

    def test_missing_publisher_sources_produce_explicit_unavailable_records(self) -> None:
        adapter = FrozenBundleAdapter(
            metadata=RemoteObject(
                FetchStatus.UNAVAILABLE, reason_code="network_unavailable"
            ),
            readme=RemoteObject(FetchStatus.MISSING, reason_code="not_found"),
        )
        result = discover_official_sources(self.frozen_bundle(adapter))
        self.assertEqual(3, len(result.records))
        self.assertTrue(
            all(item.status is DiscoveryStatus.UNAVAILABLE for item in result.records)
        )
        self.assertTrue(
            all(item.reason_code == "publisher_source_unavailable" for item in result.records)
        )

    def test_serialization_and_replay_are_canonical_and_bound_to_frozen_bundle(self) -> None:
        bundle = self.frozen_bundle(
            FrozenBundleAdapter(
                readme=RemoteObject(
                    FetchStatus.OK,
                    b"[Paper](https://arxiv.org/abs/2401.12345)\n",
                )
            )
        )
        discovered = discover_official_sources(bundle)
        payload = serialize_official_discovery(discovered)
        self.assertEqual(discovered, load_official_discovery(payload))
        self.assertEqual(discovered, replay_official_discovery(bundle, payload))
        with self.assertRaises(FrozenInstanceError):
            discovered.truncated = True

        raw = json.loads(payload)
        raw["records"][0]["reason_code"] = "tampered"
        tampered = (
            json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        )
        with self.assertRaises(OfficialDiscoveryError):
            replay_official_discovery(bundle, tampered)

        noncanonical = json.dumps(discovered.to_dict(), indent=2).encode("utf-8")
        with self.assertRaisesRegex(OfficialDiscoveryError, "non-canonical"):
            load_official_discovery(noncanonical)

    def test_closed_records_and_duplicate_json_keys_fail_strict_loading(self) -> None:
        bundle = self.frozen_bundle(FrozenBundleAdapter())
        payload = serialize_official_discovery(discover_official_sources(bundle))
        raw = json.loads(payload)
        raw["unexpected"] = True
        opened = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        with self.assertRaisesRegex(OfficialDiscoveryError, "closed object"):
            load_official_discovery(opened)

        duplicate = payload[:-2] + b',"records":[]}\n'
        with self.assertRaises(OfficialDiscoveryError):
            load_official_discovery(duplicate)

    def test_candidate_limit_is_deterministic_and_preserves_kind_coverage(self) -> None:
        links = [
            f"[Code {index}](https://github.com/acme/repository-{index})"
            for index in range(12)
        ]
        links.append("[Paper](https://arxiv.org/abs/2401.12345)")
        readme = RemoteObject(FetchStatus.OK, ("\n".join(links) + "\n").encode())
        bundle = self.frozen_bundle(FrozenBundleAdapter(readme=readme))
        first = discover_official_sources(bundle, max_candidates=4)
        second = discover_official_sources(bundle, max_candidates=4)
        self.assertEqual(first, second)
        self.assertTrue(first.truncated)
        self.assertEqual(4, len(first.records))
        self.assertEqual(set(OfficialSourceKind), {item.kind for item in first.records})
        self.assertTrue(all(item.evidence_eligible is False for item in first.records))


if __name__ == "__main__":
    unittest.main()
