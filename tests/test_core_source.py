import json
from pathlib import Path

import pytest

from model_cards.core.source import (
    HfModelSourceAdapter,
    ModelSourceError,
    parse_frontmatter,
    split_target,
)


REV = "a" * 40


def _snapshot(tmp_path: Path) -> Path:
    snap = tmp_path / REV
    snap.mkdir()
    (snap / "README.md").write_text(
        "---\nlicense: apache-2.0\npipeline_tag: text-generation\n---\n# Target\n",
        encoding="utf-8",
    )
    (snap / "config.json").write_text(
        json.dumps({"model_type": "llama", "torch_dtype": "bfloat16"}),
        encoding="utf-8",
    )
    return snap


def test_model_repo_revision_is_pinned_and_local_first(monkeypatch, tmp_path):
    snap = _snapshot(tmp_path)
    seen = {}

    def fake_snapshot_download(**kwargs):
        seen.update(kwargs)
        return str(snap)

    monkeypatch.setattr("model_cards.core.source.snapshot_download", fake_snapshot_download)
    bundle = HfModelSourceAdapter().collect(f"owner/model@{REV}")
    assert seen["repo_type"] == "model"
    assert seen["revision"] == REV
    assert seen["local_files_only"] is True
    assert bundle.target.resolved_revision == REV
    assert bundle.metadata["card_data"]["license"] == "apache-2.0"
    assert {item.name for item in bundle.files} == {"README.md", "config.json"}


def test_network_fallback_is_explicit(monkeypatch, tmp_path):
    snap = _snapshot(tmp_path)
    seen = {}

    def fake_snapshot_download(**kwargs):
        seen.update(kwargs)
        return str(snap)

    monkeypatch.setattr("model_cards.core.source.snapshot_download", fake_snapshot_download)
    HfModelSourceAdapter(allow_network=True).collect(f"owner/model@{REV}")
    assert seen["local_files_only"] is False


def test_gated_repo_yields_a_readme_only_bundle(monkeypatch, tmp_path):
    # meta-llama/Llama-3.1-8B: the Hub serves README.md to an authenticated user but
    # answers 403 for config.json; the bundle must be the README alone, recorded, not
    # an aborted collect (seen live on the roster 2026-08-27)
    snap = tmp_path / REV
    snap.mkdir()
    (snap / "README.md").write_text("---\nlicense: llama3.1\n---\n# Llama 3.1\n", encoding="utf-8")
    calls = []

    def fake_snapshot_download(**kwargs):
        calls.append(list(kwargs["allow_patterns"]))
        if "config.json" in kwargs["allow_patterns"]:
            raise RuntimeError("GatedRepoError: 403 Client Error. Cannot access gated repo for url .../config.json")
        return str(snap)

    monkeypatch.setattr("model_cards.core.source.snapshot_download", fake_snapshot_download)
    bundle = HfModelSourceAdapter(allow_network=True).collect(f"meta-llama/Llama-3.1-8B@{REV}")
    assert calls == [["README.md", "config.json"], ["README.md"]]
    assert [f.name for f in bundle.files] == ["README.md"]
    assert bundle.metadata["available_files"] == ["README.md"]
    assert bundle.metadata["gated_files_unavailable"] == ["config.json"]
    assert bundle.metadata["config"] == {}


def test_non_gated_snapshot_failure_still_raises(monkeypatch):
    def fake_snapshot_download(**kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setattr("model_cards.core.source.snapshot_download", fake_snapshot_download)
    with pytest.raises(ModelSourceError, match="cannot resolve"):
        HfModelSourceAdapter(allow_network=True).collect(f"owner/model@{REV}")


def test_requested_commit_must_match_snapshot(monkeypatch, tmp_path):
    snap = tmp_path / ("b" * 40)
    snap.mkdir()
    (snap / "README.md").write_text("# x", encoding="utf-8")
    monkeypatch.setattr("model_cards.core.source.snapshot_download", lambda **_: str(snap))
    with pytest.raises(ModelSourceError, match="differs from requested"):
        HfModelSourceAdapter().collect(f"owner/model@{REV}")


def test_frontmatter_malformed_fails_closed():
    assert parse_frontmatter("---\nnot: [valid\n---\ntext") == {}


def test_frontmatter_retains_unquoted_dates_as_json_strings():
    parsed = parse_frontmatter("---\nrelease_date: 2024-01-02\n---\n# Model\n")
    assert parsed["release_date"] == "2024-01-02"


def test_root_namespace_model_ids_are_valid_targets():
    assert split_target(f"gpt2@{REV}") == ("gpt2", REV)
