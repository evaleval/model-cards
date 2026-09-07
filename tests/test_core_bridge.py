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


def test_the_pin_check_is_race_free_under_concurrency():
    """Failure class: pin_check_races_under_concurrency. The check shelled out to
    `git status` once per target. git status rewrites .git/index, so a concurrent batch
    raced on it and six of the 247 targets on 2026-09-05 died reporting drift in a tree
    that was clean before and after the run. Hashing the declared interface files needs
    no subprocess and no index."""
    import json
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path

    from model_cards.core import bridge as B

    pin = json.loads((Path(B.__file__).resolve().parents[3] / "composer-pin.json").read_text())
    assert isinstance(pin.get("interface_sha256"), dict) and pin["interface_sha256"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        loaded = list(pool.map(lambda _: B.load_composer_bridge(), range(16)))
    assert len({b.commit for b in loaded}) == 1
    assert all(b.normalize_ws("a  b") == "a b" for b in loaded)

    # and no git subprocess is involved in the byte check itself
    repository = Path(B._package_root() / pin["repository"]).resolve()
    paths = B._interface_source_paths(pin)
    B._require_pinned_interface_bytes(repository, pin, paths)
    tampered = {**pin, "interface_sha256": {**pin["interface_sha256"], paths[0]: "0" * 64}}
    try:
        B._require_pinned_interface_bytes(repository, tampered, paths)
    except B.ComposerBridgeError as exc:
        assert paths[0] in str(exc)
    else:
        raise AssertionError("a changed interface file must be refused")
