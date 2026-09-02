from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from model_cards.artifact import CardArtifact, project_card
from model_cards.public_export import PublicExportError, export_public_card
from model_cards.publication import project_publication_card
from model_cards.publication_sources import (
    PUBLICATION_SOURCE_RULESET,
    PublicationFieldProvenance,
    SourcePointer,
)
from model_cards.review import save_artifact
from tests.helpers import synthetic_artifact


class PublicationSnapshotTests(unittest.TestCase):
    SOURCE_CATALOG_SHA256 = "a" * 64

    @staticmethod
    def _provenance(field_path: str) -> PublicationFieldProvenance:
        rule, pointer = {
            "identity.developed_by": (
                "developer_from_metadata_author",
                "/author",
            ),
            "identity.model_id": ("exact_target_model_id", "/id"),
            "links.code_repository": (
                "code_repository_from_explicit_readme_link",
                "text:0-1",
            ),
        }[field_path]
        return PublicationFieldProvenance(
            field_path=field_path,
            rule_name=f"{PUBLICATION_SOURCE_RULESET}/{rule}",
            sources=(
                SourcePointer(
                    source_id="synthetic-hf-metadata",
                    pointer=pointer,
                ),
            ),
        )

    def _snapshot_artifact(self) -> CardArtifact:
        artifact = synthetic_artifact()
        publication_card = project_publication_card(project_card(artifact))
        publication_card["identity"]["developed_by"] = "Example Lab"
        return replace(
            artifact,
            publication_card=publication_card,
            publication_provenance=(
                self._provenance("identity.developed_by"),
            ),
            publication_source_catalog_sha256=self.SOURCE_CATALOG_SHA256,
        )

    def test_publication_snapshot_roundtrips_exactly(self) -> None:
        artifact = self._snapshot_artifact()
        serialized = artifact.to_dict()

        restored = CardArtifact.from_dict(deepcopy(serialized))

        self.assertEqual(restored.to_dict(), serialized)
        self.assertEqual(restored.artifact_id, artifact.artifact_id)
        self.assertEqual(restored.publication_card, artifact.publication_card)
        self.assertEqual(
            restored.publication_provenance,
            artifact.publication_provenance,
        )
        self.assertEqual(
            restored.publication_source_catalog_sha256,
            self.SOURCE_CATALOG_SHA256,
        )

    def test_public_exporter_requires_frozen_source_replay(self) -> None:
        artifact = self._snapshot_artifact()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact_path = save_artifact(artifact, root / "artifact.json")
            output_path = root / "card.json"

            with self.assertRaises(PublicExportError):
                export_public_card(
                    artifact_path,
                    output_path,
                    source_bundle_directory=root / "missing-source-bundle",
                )
            self.assertFalse(output_path.exists())

    def test_publication_snapshot_target_mismatch_is_rejected(self) -> None:
        artifact = synthetic_artifact()
        publication_card = project_publication_card(project_card(artifact))
        publication_card["identity"]["model_id"] = "other-lab/other-model"

        with self.assertRaisesRegex(
            ValueError,
            "publication snapshot identity differs from artifact target",
        ):
            replace(
                artifact,
                publication_card=publication_card,
                publication_provenance=(
                    self._provenance("identity.model_id"),
                ),
                publication_source_catalog_sha256=self.SOURCE_CATALOG_SHA256,
            )

    def test_missing_or_extra_publication_provenance_path_is_rejected(self) -> None:
        artifact = synthetic_artifact()
        publication_card = project_publication_card(project_card(artifact))
        publication_card["identity"]["developed_by"] = "Example Lab"

        cases = {
            "missing": (),
            "extra": (
                self._provenance("identity.developed_by"),
                self._provenance("links.code_repository"),
            ),
        }
        for name, provenance in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError,
                "publication provenance and withholding do not cover changed public fields",
            ):
                replace(
                    artifact,
                    publication_card=publication_card,
                    publication_provenance=provenance,
                    publication_source_catalog_sha256=self.SOURCE_CATALOG_SHA256,
                )

    def test_serialized_publication_card_and_provenance_tampering_change_artifact_id(
        self,
    ) -> None:
        mutations = {
            "card": lambda value: value["publication"]["card"]["identity"].update(
                {"developed_by": "Tampered Lab"}
            ),
            "provenance": lambda value: value["publication"]["provenance"][0][
                "sources"
            ][0].update({"pointer": "/tampered-author"}),
        }
        for name, mutate in mutations.items():
            serialized = self._snapshot_artifact().to_dict()
            mutate(serialized)
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError,
                "serialized artifact_id does not match artifact content",
            ):
                CardArtifact.from_dict(serialized)

    def test_empty_serialized_publication_container_is_rejected(self) -> None:
        serialized = synthetic_artifact().to_dict()
        serialized["publication"] = {}

        with self.assertRaisesRegex(
            ValueError,
            "serialized publication snapshot has invalid keys",
        ):
            CardArtifact.from_dict(serialized)

    def test_extra_serialized_publication_container_key_is_rejected(self) -> None:
        serialized = self._snapshot_artifact().to_dict()
        serialized["publication"]["unexpected"] = "not artifact-bound"

        with self.assertRaisesRegex(
            ValueError,
            "serialized publication snapshot has invalid keys",
        ):
            CardArtifact.from_dict(serialized)

    def test_validate_integrity_catches_post_construction_nested_mutation(self) -> None:
        artifact = self._snapshot_artifact()
        assert artifact.publication_card is not None
        artifact.publication_card["identity"]["developed_by"] = "Tampered Lab"

        with self.assertRaisesRegex(
            ValueError,
            "artifact publication snapshot integrity failed",
        ):
            artifact.validate_integrity()

    def test_direct_publication_withholding_is_bound_and_roundtrips(self) -> None:
        artifact = synthetic_artifact()
        publication_card = project_publication_card(project_card(artifact))
        del publication_card["identity"]["name"]

        withheld = replace(
            artifact,
            publication_card=publication_card,
            publication_withheld_fields=("identity.name",),
            publication_source_catalog_sha256=self.SOURCE_CATALOG_SHA256,
        )
        restored = CardArtifact.from_dict(withheld.to_dict())

        self.assertEqual(("identity.name",), restored.publication_withheld_fields)
        self.assertNotIn("name", restored.publication_card["identity"])
        with self.assertRaisesRegex(ValueError, "cannot be withheld"):
            replace(
                artifact,
                publication_card=publication_card,
                publication_withheld_fields=("identity.model_id",),
                publication_source_catalog_sha256=self.SOURCE_CATALOG_SHA256,
            )


if __name__ == "__main__":
    unittest.main()
