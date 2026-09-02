from __future__ import annotations

from collections import OrderedDict
import unittest

from model_cards.public_export import PublicExportError
from model_cards.public_markdown import render_public_markdown
from model_cards.publication_contract import SECTION_FIELDS
from model_cards.publication_schema import blank_publication_card


JSON_SHA256 = "a" * 64


def populated_card() -> dict[str, dict[str, object]]:
    card = blank_publication_card()
    card["identity"].update(
        {
            "model_id": "example/model-7b",
            "name": "Example Model 7B",
            "developed_by": "Example Lab",
            "license": "Apache-2.0",
            "version": "abc123",
        }
    )
    card["lineage"]["base_models"] = [
        {
            "model_id": "example/base-7b",
            "relation": "base_model",
            "kind": "continued pretraining",
            "version": "v1",
        }
    ]
    card["specifications"].update(
        {
            "architecture_type": "dense decoder-only Transformer",
            "num_parameters": "7 billion",
            "input_output": ["input: text", "output: text"],
        }
    )
    card["training_context"]["training_data"] = "A documented public corpus."
    card["access_and_adoption"].update(
        {"access_type": "weights available", "downloads": "1234"}
    )
    card["evaluation"].update(
        {
            "results_summary": "Reported evaluation results.",
            "benchmark_scores": [
                {
                    "benchmark": "MMLU",
                    "metric": "accuracy",
                    "score": 0.71,
                    "setting": "5-shot; test split",
                    "split": "test",
                },
                {
                    "benchmark": "GSM8K",
                    "metric": "exact match",
                    "score": "68.2%",
                    "setting": "8-shot, chain-of-thought",
                },
            ],
        }
    )
    card["links"].update(
        {
            "model_card": "https://example.test/model/card",
            "code_repository": "https://example.test/code",
            "citation": "Example Lab (2026). Example Model 7B.",
        }
    )
    return card


class PublicMarkdownTests(unittest.TestCase):
    def render(self, card=None, **kwargs) -> str:
        return render_public_markdown(
            populated_card() if card is None else card,
            json_filename=kwargs.get("json_filename", "example-model-7b.json"),
            json_sha256=kwargs.get("json_sha256", JSON_SHA256),
        )

    def test_renders_all_agreed_sections_in_contract_order(self) -> None:
        rendered = self.render()
        headings = [
            "## Identity",
            "## Lineage",
            "## Specifications",
            "## Training Context",
            "## Access and Adoption",
            "## Evaluation",
            "## Links",
        ]
        offsets = [rendered.index(heading) for heading in headings]
        self.assertEqual(offsets, sorted(offsets))
        self.assertEqual(rendered.count("\n## "), len(SECTION_FIELDS))

        self.assertIn(
            "> This is an automated candidate generated from public sources. "
            "It has not been human-reviewed or released as an official model card.",
            rendered,
        )
        self.assertIn(
            r"Paired JSON: [example\-model\-7b\.json](<./example-model-7b.json>)",
            rendered,
        )
        self.assertIn(f"SHA-256: `{JSON_SHA256}`", rendered)
        self.assertNotIn("environmental_information", rendered)
        self.assertNotIn("use_and_risk", rendered)
        self.assertNotIn("provenance", rendered)
        self.assertNotIn("lifecycle", rendered)

    def test_omits_unknown_values_and_lists_unavailable_fields(self) -> None:
        card = blank_publication_card()
        card["identity"]["model_id"] = "example/model"
        card["identity"]["summary"] = "Not specified"
        card["lineage"]["derivatives"] = "Not applicable"
        rendered = self.render(card)

        self.assertNotIn("| Summary |", rendered)
        self.assertIn("| Derivatives | Not applicable |", rendered)
        unavailable_line = next(
            line
            for line in rendered.splitlines()
            if line.startswith("Unavailable agreed fields")
        )
        self.assertIn("`identity.name`", unavailable_line)
        self.assertIn("`identity.summary`", unavailable_line)
        self.assertNotIn("`identity.model_id`", unavailable_line)
        self.assertNotIn("`lineage.derivatives`", unavailable_line)
        expected_unknowns = sum(
            1
            for section, fields in SECTION_FIELDS.items()
            for field in fields
            if field not in card[section] or card[section][field] == "Not specified"
        )
        self.assertEqual(unavailable_line.count("`"), expected_unknowns * 2)

    def test_benchmark_scores_have_stable_table_and_setting(self) -> None:
        rendered = self.render()
        self.assertIn(
            "| Benchmark | Metric | Score | Setting | Split |\n"
            "| --- | --- | ---: | --- | --- |",
            rendered,
        )
        self.assertIn(
            r"| MMLU | accuracy | 0\.71 | 5\-shot; test split | test |",
            rendered,
        )
        self.assertIn(
            "| GSM8K | exact match | 68\\.2% | "
            "8\\-shot, chain\\-of\\-thought | Not reported |",
            rendered,
        )

    def test_mapping_reordering_does_not_change_output(self) -> None:
        card = populated_card()
        reordered = OrderedDict()
        for section in reversed(tuple(card)):
            values = card[section]
            reordered[section] = OrderedDict(reversed(tuple(values.items())))
        reordered_scores = []
        for row in reordered["evaluation"]["benchmark_scores"]:
            reordered_scores.append(OrderedDict(reversed(tuple(row.items()))))
        reordered["evaluation"]["benchmark_scores"] = reordered_scores

        self.assertEqual(self.render(card), self.render(reordered))

    def test_escapes_untrusted_markdown_html_table_cells_and_links(self) -> None:
        card = populated_card()
        card["identity"]["name"] = "<script>x</script> | *bold*\n# heading"
        card["identity"]["summary"] = "[click](javascript:alert(1))"
        card["links"]["system_card"] = "javascript:alert(1)"
        card["links"]["model_card"] = "https://example.test/a_(b)?q=%3Ctag%3E"
        rendered = self.render(card)

        self.assertNotIn("<script>", rendered)
        self.assertNotIn("| *bold*", rendered)
        self.assertNotIn("\n# heading", rendered)
        self.assertNotIn("[click](javascript:alert(1))", rendered)
        self.assertNotIn("](<javascript:", rendered)
        self.assertIn(
            "&lt;script&gt;x&lt;/script&gt; \\| \\*bold\\*<br>\\# heading",
            rendered,
        )
        self.assertIn(
            "(<https://example.test/a_%28b%29?q=%3Ctag%3E>)",
            rendered,
        )

    def test_rejects_non_public_cards_and_sensitive_projection_text(self) -> None:
        card = populated_card()
        card["environmental_information"] = {"carbon_emissions": "unknown"}
        with self.assertRaises(ValueError):
            self.render(card)

        card = populated_card()
        card["identity"]["summary"] = "Read /Users/example/private.txt"
        with self.assertRaises(PublicExportError):
            self.render(card)

    def test_rejects_unsafe_json_metadata(self) -> None:
        for filename in ("../card.json", "/card.json", "nested/card.json", "card.md"):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                self.render(json_filename=filename)
        for digest in ("a" * 63, "A" * 64, "not-a-digest"):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                self.render(json_sha256=digest)


if __name__ == "__main__":
    unittest.main()
