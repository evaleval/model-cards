"""Offline regressions for VCS provenance and the built distribution boundary."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import types
import zipfile

import pytest

from model_cards.core import bridge as B

ROOT = Path(__file__).resolve().parents[1]


def _composer_source() -> Path:
    spec = importlib.util.find_spec("auto_benchmarkcard")
    if spec is not None and spec.origin:
        return Path(spec.origin).resolve().parent.parent
    pin = B._read_pin(ROOT)
    return (ROOT / pin["repository"] / "src").resolve()


@pytest.fixture
def isolated_composer(tmp_path, monkeypatch):
    pin = B._read_pin(ROOT)
    source = _composer_source()
    installed = tmp_path / "site-packages"
    for path in B._interface_source_paths(pin):
        relative = path.removeprefix("src/")
        target = installed / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    (installed / "auto_benchmarkcard/__init__.py").write_text("")
    for name in tuple(sys.modules):
        if name == "auto_benchmarkcard" or name.startswith("auto_benchmarkcard."):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(B.importlib.util, "find_spec", lambda name: types.SimpleNamespace(
        origin=str(installed / "auto_benchmarkcard/__init__.py")))
    direct_url = {"url": pin["repository_url"], "vcs_info": {
        "vcs": "git", "commit_id": pin["commit"]}}

    class Distribution:
        def locate_file(self, name):
            return installed / name

        def read_text(self, name):
            assert name == "direct_url.json"
            return json.dumps(direct_url)

    monkeypatch.setattr(B.importlib.metadata, "distribution", lambda name: Distribution())
    monkeypatch.setattr(B, "_read_pin", lambda root: pin)
    return installed, pin, direct_url


def test_installed_vcs_package_uses_its_own_source(isolated_composer):
    installed, pin, _ = isolated_composer
    bridge = B.load_composer_bridge()
    assert bridge.repository is None
    assert bridge.source_root == installed
    assert bridge.commit == pin["commit"]
    assert bridge.verify_span("a b", "a  b") == (0, 3)
    assert Path(bridge.normalize_ws.__code__.co_filename).is_relative_to(installed)


@pytest.mark.parametrize("provenance", [None, {}, {"vcs_info": []},
    {"vcs_info": {"vcs": "git", "commit_id": "branch-name"}},
    {"vcs_info": {"vcs": "hg", "commit_id": "a" * 40}}])
def test_missing_or_non_git_provenance_is_refused(isolated_composer, monkeypatch, provenance):
    installed, _, _ = isolated_composer
    distribution = types.SimpleNamespace(locate_file=lambda name: installed / name,
                                        read_text=lambda name: json.dumps(provenance))
    monkeypatch.setattr(B.importlib.metadata, "distribution", lambda name: distribution)
    with pytest.raises(B.ComposerBridgeError, match="provenance"):
        B.load_composer_bridge(allow_unpinned=True)


def test_wrong_vcs_repository_is_refused(isolated_composer):
    _, _, provenance = isolated_composer
    provenance["url"] = "https://example.test/unrelated.git"
    with pytest.raises(B.ComposerBridgeError, match="repository does not match"):
        B.load_composer_bridge()


def test_distribution_for_a_different_import_source_is_refused(isolated_composer, monkeypatch):
    installed, _, provenance = isolated_composer
    distribution = types.SimpleNamespace(
        locate_file=lambda name: installed.parent / "other" / name,
        read_text=lambda name: json.dumps(provenance))
    monkeypatch.setattr(B.importlib.metadata, "distribution", lambda name: distribution)
    with pytest.raises(B.ComposerBridgeError, match="does not own"):
        B.load_composer_bridge()


def test_revision_drift_requires_explicit_override(isolated_composer):
    _, _, provenance = isolated_composer
    provenance["vcs_info"]["commit_id"] = "a" * 40
    with pytest.raises(B.ComposerBridgeError, match="revision drift"):
        B.load_composer_bridge()
    assert B.load_composer_bridge(allow_unpinned=True).commit == "a" * 40


def test_installed_interface_tampering_is_refused(isolated_composer):
    installed, _, _ = isolated_composer
    path = installed / "auto_benchmarkcard/tools/composer/evidence.py"
    path.write_text(path.read_text() + "\n# changed after installation\n")
    with pytest.raises(B.ComposerBridgeError, match="recorded bytes"):
        B.load_composer_bridge()
    assert B.load_composer_bridge(allow_unpinned=True).verify_span("a", "a") == (0, 1)


def test_preloaded_generator_cannot_use_a_different_composer(isolated_composer, monkeypatch):
    installed, _, _ = isolated_composer
    module = types.ModuleType("auto_benchmarkcard.tools.composer.composer_tool")
    module.__file__ = str(installed.parent / "other/composer_tool.py")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    with pytest.raises(B.ComposerBridgeError, match="different source"):
        B.load_composer_bridge(allow_unpinned=True)


def test_source_and_editable_checkouts_use_git_head(isolated_composer, tmp_path, monkeypatch):
    installed, pin, _ = isolated_composer
    repo = tmp_path / "composer"
    shutil.copytree(installed, repo / "src")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "src"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.test", "-c", "commit.gpgsign=false",
                    "commit", "-qm", "Fixture"], check=True)
    pin["commit"] = B._head(repo)
    monkeypatch.setattr(B.importlib.util, "find_spec", lambda name: types.SimpleNamespace(
        origin=str(repo / "src/auto_benchmarkcard/__init__.py")))
    monkeypatch.setattr(B.importlib.metadata, "distribution", lambda name: pytest.fail(
        "a source checkout must get its revision from Git, not another distribution"))
    assert B.load_composer_bridge().repository == repo
    # No installed composer: the canonical source pin's adjacent fallback still works.
    source_package = tmp_path / "model-cards"
    marker = source_package / "src/model_cards/core/bridge.py"
    marker.parent.mkdir(parents=True)
    marker.touch()
    pin["repository"] = "../composer"
    monkeypatch.setattr(B, "_package_root", lambda: source_package)
    monkeypatch.setattr(B.importlib.util, "find_spec", lambda name: None)
    assert B.load_composer_bridge().source_root == repo / "src"


def test_wheel_and_sdist_keep_the_canonical_pin_and_work_away_from_checkout(tmp_path):
    """Build a wheel from the sdist, install it elsewhere, and check installed imports."""
    source = tmp_path / "build-source"
    source.mkdir()
    for name in ("setup.py", "setup.cfg", "pyproject.toml", "MANIFEST.in", "composer-pin.json",
                 "README.md", "LICENSE", "NOTICE.md"):
        shutil.copyfile(ROOT / name, source / name)
    shutil.copytree(ROOT / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    env = dict(os.environ)
    # This test requires the standard build tools in the test environment, never a download.
    subprocess.run([sys.executable, "setup.py", "sdist", "--dist-dir", str(tmp_path / "dist")],
                   cwd=source, env=env, capture_output=True, text=True, check=True)
    archive = next((tmp_path / "dist").glob("*.tar.gz"))
    with tarfile.open(archive) as package:
        pin_member = next(name for name in package.getnames() if name.endswith("/composer-pin.json"))
        assert package.extractfile(pin_member).read() == (ROOT / "composer-pin.json").read_bytes()
        package.extractall(tmp_path / "sdist")
    unpacked = next((tmp_path / "sdist").iterdir())
    subprocess.run([sys.executable, "setup.py", "bdist_wheel", "--dist-dir", str(tmp_path / "dist")],
                   cwd=unpacked, env=env, capture_output=True, text=True, check=True)
    wheel = next((tmp_path / "dist").glob("*.whl"))
    pin = B._read_pin(ROOT)
    with zipfile.ZipFile(wheel) as package:
        assert package.read("model_cards/resources/composer-pin.json") == (ROOT / "composer-pin.json").read_bytes()
        metadata_path = next(name for name in package.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = package.read(metadata_path).decode()
        assert f"git+{pin['repository_url']}@{pin['commit']}" in metadata
    installed = tmp_path / "installed"
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--no-index",
                    "--target", str(installed), str(wheel)], capture_output=True, text=True, check=True)
    # An installed composer fixture uses the real composer bytes and pip's VCS metadata
    # format. The installation smoke script can also be run manually with a VCS install.
    shutil.copytree(_composer_source() / "auto_benchmarkcard", installed / "auto_benchmarkcard",
                    ignore=shutil.ignore_patterns("__pycache__"))
    dist_info = installed / "auto_benchmarkcard-0.0.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Metadata-Version: 2.1\nName: auto-benchmarkcard\nVersion: 0.0.0\n")
    (dist_info / "direct_url.json").write_text(json.dumps({"url": pin["repository_url"],
        "vcs_info": {"vcs": "git", "commit_id": pin["commit"]}}))
    elsewhere = tmp_path / "unrelated-cwd"
    elsewhere.mkdir()
    probe = """
import pathlib, sys
sys.path.insert(0, sys.argv[1])
from model_cards.core import bridge as B
loaded = B.load_composer_bridge()
assert loaded.source_root == pathlib.Path(sys.argv[1])
assert loaded.repository is None
assert loaded.verify_span('a b', 'a  b') == (0, 3)
from auto_benchmarkcard.tools.composer import evidence, field_spec
assert pathlib.Path(evidence.__file__).is_relative_to(loaded.source_root)
assert pathlib.Path(field_spec.__file__).is_relative_to(loaded.source_root)
assert B.load_composer_bridge().source_root == loaded.source_root
assert B._read_pin(B._package_root())['commit'] == loaded.commit
print(loaded.commit)
"""
    result = subprocess.run([sys.executable, "-I", "-c", probe, str(installed)], cwd=elsewhere,
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == pin["commit"]
