from __future__ import annotations

import unittest

from model_cards.bindings import quote_binding
from model_cards.document_structure import (
    build_document_index,
    verify_document_index,
)
from model_cards.models import (
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from model_cards.quote import match_quote, normalize_ws


REVISION = "a" * 40
TARGET = TargetIdentity("acme/Instruct", REVISION)


MARKDOWN = """# Model Overview

This is the exact target model.

```text
# Not a real section
```

## Training Details

It was trained on publisher data.

## Evaluation Results

Table 1. Exact-target results

| Model | Score |
| --- | ---: |
| acme/Instruct | 73.5 |

## Limitations

The model may produce incorrect answers.
"""


class DocumentStructureTests(unittest.TestCase):
    def test_maps_normalized_quote_coordinates_to_nested_section_and_table(self) -> None:
        index = build_document_index(MARKDOWN)
        match = match_quote("acme/Instruct | 73.5", MARKDOWN)
        self.assertIsNotNone(match)
        assert match is not None
        context = index.context_at(match.char_start, match.char_end)
        self.assertEqual(("Model Overview", "Evaluation Results"), context.section_path)
        self.assertEqual("evaluation", context.region)
        self.assertEqual("t1", context.table_id)
        table = index.tables[0]
        self.assertEqual(("Model", "Score"), table.header_row)
        self.assertEqual(("acme/Instruct",), table.row_labels)
        self.assertEqual("Table 1. Exact-target results", table.caption)

    def test_code_fence_headings_are_not_indexed(self) -> None:
        index = build_document_index(MARKDOWN)
        self.assertNotIn("Not a real section", {item.title for item in index.sections})
        quote = match_quote("# Not a real section", MARKDOWN)
        self.assertIsNotNone(quote)
        assert quote is not None
        context = index.context_at(quote.char_start, quote.char_end)
        self.assertEqual(("Model Overview",), context.section_path)
        self.assertIsNone(context.table_id)

    def test_whitespace_and_typographic_normalization_share_one_coordinate_space(self) -> None:
        text = "# Overview\n\nThe model uses an 8–bit   precision mode.\n"
        index = build_document_index(text)
        match = match_quote("The model uses an 8-bit precision mode.", text)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(
            "The model uses an 8-bit precision mode.",
            normalize_ws(text)[match.char_start : match.char_end],
        )
        self.assertEqual(("Overview",), index.context_at(match.char_start).section_path)

    def test_index_replay_rejects_source_drift(self) -> None:
        index = build_document_index(MARKDOWN)
        verify_document_index(index, MARKDOWN)
        with self.assertRaisesRegex(ValueError, "does not replay"):
            verify_document_index(index, MARKDOWN.replace("73.5", "99.0"))

    def test_binding_carries_deterministic_context_into_immutable_evidence(self) -> None:
        source = SourceDocument(
            source_id="source-readme",
            source_uri=(
                "https://huggingface.co/acme/Instruct/resolve/" + REVISION + "/README.md"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=TARGET,
            text=MARKDOWN,
        )
        match = match_quote("The model may produce incorrect answers.", MARKDOWN)
        self.assertIsNotNone(match)
        assert match is not None
        context = build_document_index(MARKDOWN).context_at(
            match.char_start, match.char_end
        )
        binding = quote_binding(
            target=TARGET,
            source=source,
            field_path="use_and_risk.limitations[0]",
            value={
                "context_id": "context:placeholder",
                "description": "The model may produce incorrect answers.",
                "origin": "publisher_reported",
                "source_refs": ["source-readme"],
            },
            quote="The model may produce incorrect answers.",
            claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            section_path=context.section_path,
            table_id=context.table_id,
        )
        evidence = binding.evidence[0]
        self.assertEqual(("Model Overview", "Limitations"), evidence.section_path)
        self.assertIsNone(evidence.table_id)
        serialized = evidence.to_dict()
        self.assertEqual(["Model Overview", "Limitations"], serialized["section_path"])


if __name__ == "__main__":
    unittest.main()
