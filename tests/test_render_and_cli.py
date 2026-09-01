from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from model_cards.cli import main
from model_cards.bindings import build_artifact
from model_cards.render import render_html, render_json
from model_cards.review import load_artifact, save_artifact
from tests.helpers import SYNTHETIC_INPUT, synthetic_artifact, synthetic_specification


class RenderAndCliTests(unittest.TestCase):
    def test_json_and_static_html_render_offline(self) -> None:
        artifact = synthetic_artifact()
        payload = json.loads(render_json(artifact))
        self.assertEqual(payload["contract_version"], "1")
        self.assertEqual(payload["target"]["model_id"], "example-lab/synthetic-model-1b")

        html = render_html(artifact)
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn("Evidence bindings", html)
        self.assertIn("family_scope_not_target", html)
        self.assertIn("generated_unreviewed", html)
        self.assertNotIn("Schema v", html)
        self.assertNotIn("<script", html.lower())

    def test_rendering_is_byte_stable(self) -> None:
        first = synthetic_artifact()
        second = synthetic_artifact()
        self.assertEqual(render_json(first), render_json(second))
        self.assertEqual(render_html(first), render_html(second))

    def test_semantic_object_key_order_does_not_change_rendered_bytes(self) -> None:
        first_specification = synthetic_specification()
        second_specification = synthetic_specification()
        source = next(
            item
            for item in second_specification["sources"]
            if item["source_id"] == "synthetic-comparison-record"
        )
        record = source["data"]["record"]
        source["data"]["record"] = {
            "link": record["link"],
            "model_id": record["model_id"],
        }
        first = build_artifact(first_specification)
        second = build_artifact(second_specification)

        unsorted_first = json.dumps(first.to_dict(), ensure_ascii=False, indent=2)
        unsorted_second = json.dumps(second.to_dict(), ensure_ascii=False, indent=2)
        self.assertNotEqual(unsorted_first, unsorted_second)
        self.assertEqual(render_json(first), render_json(second))
        self.assertEqual(render_html(first), render_html(second))

        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            save_artifact(first, first_path)
            save_artifact(second, second_path)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

    def test_synthetic_end_to_end_cli_writes_valid_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            json_path = destination / "synthetic-card.json"
            html_path = destination / "synthetic-card.html"
            result = main(
                [
                    "build",
                    str(SYNTHETIC_INPUT),
                    "--json",
                    str(json_path),
                    "--html",
                    str(html_path),
                ]
            )
            self.assertEqual(result, 0)
            self.assertTrue(json_path.is_file())
            self.assertTrue(html_path.is_file())
            self.assertEqual(load_artifact(json_path).contract_version, "1")
            self.assertIn("<!doctype html>", html_path.read_text(encoding="utf-8"))

            self.assertEqual(main(["validate", str(json_path)]), 0)
            public_path = destination / "public.json"
            self.assertEqual(
                main(["export", str(json_path), "--output", str(public_path)]),
                0,
            )
            self.assertEqual(main(["validate", str(public_path)]), 0)
            public = json.loads(public_path.read_text(encoding="utf-8"))
            self.assertEqual(public["contract_version"], "1")
            self.assertEqual(public["lifecycle"]["status"], "generated_unreviewed")

    def test_loader_rejects_a_tampered_projection(self) -> None:
        payload = synthetic_artifact().to_dict()
        payload["card"]["identity"]["name"] = "Changed after projection"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_artifact(path)

    def test_loader_rejects_structured_binding_tampering(self) -> None:
        for change_fragment in (False, True):
            with self.subTest(change_fragment=change_fragment):
                payload = synthetic_artifact().to_dict()
                binding = next(
                    item
                    for item in payload["bindings"]
                    if item["field_path"] == "model_details.context_length"
                )
                binding["value"] = "999999 tokens"
                if change_fragment:
                    binding["evidence"][0]["fragment"] = "999999 tokens"
                payload["card"]["model_details"]["context_length"] = "999999 tokens"
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "changed.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_artifact(path)


if __name__ == "__main__":
    unittest.main()
