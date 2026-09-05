import sys

from model_cards.core.bridge import load_composer_bridge


def test_pinned_bridge_verifies_and_indexes_exact_span():
    was_loaded = "auto_benchmarkcard" in sys.modules
    bridge = load_composer_bridge()
    assert ("auto_benchmarkcard" in sys.modules) is was_loaded
    source = """# Results

Table 1: Scores

| Model | MMLU |
|---|---:|
| target | 71.2 |
"""
    start, end = bridge.verify_span("target | 71.2", source)
    assert end > start
    anchor = bridge.structural_anchor(source, start)
    assert anchor["section_path"] == ["Results"]
    assert anchor["region"] == "results"
    assert anchor["table_caption"] == "Table 1: Scores"
    assert anchor["table_header"] == ["Model", "MMLU"]
    assert "target" in anchor["table_row_labels"]
