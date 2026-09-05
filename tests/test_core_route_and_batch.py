"""Regression tests for the pinned route and the batch runner.

Failure classes:
  route_pin_drift                 the route silently serves a different model or provider
  route_env_override_ignored      an explicit environment pin is not honoured
  batch_failure_takes_down_run    one bad target aborts the whole batch
  batch_resume_recomposes         --resume recomposes a card that already exists (paid)
  batch_spend_runs_past_cap       the per-card or per-run tripwire does not stop the run
  cli_flag_drift                  the documented CLI flags stop parsing
"""

from __future__ import annotations

import json
import os

import pytest

from model_cards.core import batch as batch_mod
from model_cards.core import route as route_mod
from model_cards.core.cli import build_parser


def test_route_pin_is_the_recorded_binding():
    """route_pin_drift: the defaults are the pin recorded in vault/llm_config.md."""
    for key in ("MODELCARDS_OPENROUTER_MODEL", "MODELCARDS_PROVIDER_ORDER",
                "MODELCARDS_TEMPERATURE", "MODELCARDS_MAX_TOKENS"):
        os.environ.pop(key, None)
    cfg = route_mod.route()
    assert cfg["model"] == "deepseek/deepseek-v4-flash-0731"
    assert cfg["provider_order"] == ["Together"]
    assert cfg["allow_fallbacks"] is False
    assert cfg["temperature"] == 0.0
    assert cfg["credential"] == "OPENROUTER_API_KEY"


def test_route_honours_an_explicit_environment_pin(monkeypatch):
    """route_env_override_ignored."""
    monkeypatch.setenv("MODELCARDS_PROVIDER_ORDER", "Fireworks, Together")
    monkeypatch.setenv("MODELCARDS_TEMPERATURE", "0.2")
    cfg = route_mod.route()
    assert cfg["provider_order"] == ["Fireworks", "Together"]
    assert cfg["temperature"] == 0.2


def test_load_env_never_overwrites_an_existing_credential(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("OPENROUTER_API_KEY=from-file\nMODELCARDS_PROVIDER_ORDER=Nebius\n")
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-shell")
    monkeypatch.delenv("MODELCARDS_PROVIDER_ORDER", raising=False)
    assert route_mod.load_env(env) is True
    assert os.environ["OPENROUTER_API_KEY"] == "from-shell"
    assert os.environ["MODELCARDS_PROVIDER_ORDER"] == "Nebius"


def _targets(tmp_path, names):
    p = tmp_path / "targets.txt"
    p.write_text("\n".join(names) + "\n# a comment\n\n")
    return p


def test_read_targets_skips_blanks_comments_and_duplicates(tmp_path):
    p = _targets(tmp_path, ["a/b@" + "1" * 40, "a/b@" + "1" * 40, "c/d@" + "2" * 40])
    assert batch_mod.read_targets(p) == ["a/b@" + "1" * 40, "c/d@" + "2" * 40]


def test_one_failing_target_does_not_take_down_the_batch(tmp_path):
    """batch_failure_takes_down_run."""
    good, bad = "org/good@" + "a" * 40, "org/bad@" + "b" * 40

    def collect(target, out_dir, allow_network=True):
        if target == bad:
            raise RuntimeError("gated repo, no access")
        (out_dir / batch_mod.slug_for(target)).mkdir(parents=True, exist_ok=True)
        return {"slug": batch_mod.slug_for(target), "channels": {"hf": {"ok": True}}}

    manifest = batch_mod.run_batch([good, bad], phase="collect", bundle_dir=tmp_path / "b",
                                   out_dir=tmp_path / "run", concurrency=2, collect_fn=collect)
    assert manifest["status_counts"] == {"ok": 1, "failed": 1}
    failed = [r for r in manifest["results"] if r["status"] == "failed"][0]
    assert failed["target"] == bad and "gated repo" in failed["error"]
    assert json.loads((tmp_path / "run" / "run-manifest.json").read_text())["targets"] == 2


def _fake_artifact(cost, tmp_path):
    class _Artifact:
        bindings = ()
        card = {"provenance_and_quality": {"coverage_score": 0.5}}
        metadata = {"source_hashes": {"README.md": "a" * 64}}
        source_bundle = None

    return _Artifact()


def _compose_factory(cost_per_call, tmp_path):
    def compose(target, bundle_root, llm):
        from auto_benchmarkcard.llm_handler import _current_usage_log_path
        with open(_current_usage_log_path(), "a") as fh:
            fh.write(json.dumps({"cost": cost_per_call, "provider": "Together",
                                 "input_tokens": 10, "output_tokens": 5}) + "\n")
        return _fake_artifact(cost_per_call, tmp_path)
    return compose


def test_per_card_tripwire_stops_the_run(tmp_path, monkeypatch):
    """batch_spend_runs_past_cap (per card)."""
    targets = [f"org/m{i}@" + str(i) * 40 for i in range(4)]
    monkeypatch.setattr(batch_mod, "slug_for", lambda t: t.split("@")[0].replace("/", "-"))
    saved = []
    monkeypatch.setattr("model_cards.core.review.save_artifact",
                        lambda a, p: saved.append(p) or p.write_text("{}"))
    manifest = batch_mod.run_batch(
        targets, phase="compose", bundle_dir=tmp_path / "b", out_dir=tmp_path / "run",
        concurrency=1, per_card_cap=0.01, run_cap=100.0, export_html=False,
        compose_fn=_compose_factory(0.5, tmp_path), llm_factory=lambda: object())
    assert manifest["stopped_early"] and "per-card cap" in manifest["stopped_early"]
    assert manifest["status_counts"].get("ok") == 4  # the run stops, targets stay isolated
    skipped = [r for r in manifest["results"] if r["compose"]["status"] == "skipped_budget"]
    assert skipped, "later targets must be skipped once the tripwire fires"


def test_per_run_tripwire_stops_the_run(tmp_path, monkeypatch):
    """batch_spend_runs_past_cap (per run)."""
    targets = [f"org/m{i}@" + str(i) * 40 for i in range(5)]
    monkeypatch.setattr(batch_mod, "slug_for", lambda t: t.split("@")[0].replace("/", "-"))
    monkeypatch.setattr("model_cards.core.review.save_artifact",
                        lambda a, p: p.write_text("{}"))
    manifest = batch_mod.run_batch(
        targets, phase="compose", bundle_dir=tmp_path / "b", out_dir=tmp_path / "run",
        concurrency=1, per_card_cap=10.0, run_cap=0.6, export_html=False,
        compose_fn=_compose_factory(0.25, tmp_path), llm_factory=lambda: object())
    assert manifest["stopped_early"] and "run cap" in manifest["stopped_early"]
    composed = [r for r in manifest["results"] if r["compose"]["status"] == "ok"]
    assert len(composed) == 3


def test_resume_skips_a_card_that_already_exists(tmp_path, monkeypatch):
    """batch_resume_recomposes."""
    target = "org/m@" + "a" * 40
    monkeypatch.setattr(batch_mod, "slug_for", lambda t: "org-m")
    run = tmp_path / "run"
    run.mkdir()
    calls = []
    monkeypatch.setattr("model_cards.core.review.load_artifact", lambda p: object())
    (run / "org-m.json").write_text("{}")

    def compose(*a, **k):
        calls.append(a)
        raise AssertionError("resume must not recompose an existing card")

    manifest = batch_mod.run_batch([target], phase="compose", bundle_dir=tmp_path / "b",
                                   out_dir=run, resume=True, export_html=False,
                                   compose_fn=compose, llm_factory=lambda: object())
    assert calls == []
    assert manifest["results"][0]["compose"]["status"] == "skipped_existing"


def test_cli_exposes_the_documented_flags():
    """cli_flag_drift."""
    parser = build_parser()
    args = parser.parse_args(["compose", "a/b@c", "--bundle-dir", "bd", "--out", "o.json",
                              "--llm-usage-log", "u.jsonl"])
    assert args.handler.__name__ == "_cmd_compose_llm"
    assert (args.bundle_dir, args.output, args.usage_log) == ("bd", "o.json", "u.jsonl")
    args = parser.parse_args(["batch", "t.txt", "--out", "run", "--resume",
                              "--phase", "compose", "--concurrency", "5",
                              "--per-target-timeout", "600", "--collect-timeout", "300"])
    assert args.handler.__name__ == "_cmd_batch"
    assert (args.out_dir, args.resume, args.phase, args.concurrency) == ("run", True, "compose", 5)
    assert (args.per_target_timeout, args.collect_timeout) == (600, 300)
    args = parser.parse_args(["collect", "a/b@c"])
    assert args.bundle_dir is None  # resolved from the environment default at run time
    assert parser.parse_args(["compose-llm", "a/b@c", "-o", "x"]).handler.__name__ == "_cmd_compose_llm"


def test_batch_concurrency_is_bounded():
    with pytest.raises(ValueError):
        batch_mod.run_batch([], phase="nonsense", bundle_dir=".", out_dir=".")


def test_usage_log_parent_directory_is_created(tmp_path, monkeypatch):
    """usage_ledger_silently_dropped: the handler appends fail-soft, so composing with
    --llm-usage-log into a directory that does not exist yet lost the entire spend record
    of the run (observed 2026-09-04 on the first OLMo composition)."""
    from model_cards.core import cli

    log = tmp_path / "fresh" / "nested" / "llm_usage.jsonl"
    recorded = {}
    monkeypatch.setattr("auto_benchmarkcard.llm_handler.set_usage_log_path",
                        lambda p: recorded.setdefault("path", p))
    monkeypatch.setattr("model_cards.core.compose_llm.compose_model_card_llm",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stop after wiring")))
    monkeypatch.setattr(cli, "_pinned_llm", lambda: object())
    args = cli.build_parser().parse_args(
        ["compose", "a/b@" + "c" * 40, "--llm-usage-log", str(log), "--out", str(tmp_path / "o.json")])
    with pytest.raises(RuntimeError):
        args.handler(args)
    assert log.parent.is_dir()
    assert recorded["path"] == str(log)


def test_resume_recomposes_a_card_that_does_not_load(tmp_path, monkeypatch):
    """batch_resume_accepts_a_broken_card: an artifact that saved cleanly and then failed
    downstream left a file behind, and a bare existence check skipped it on every retry."""
    target = "org/m@" + "a" * 40
    monkeypatch.setattr(batch_mod, "slug_for", lambda t: "org-m")
    run = tmp_path / "run"
    run.mkdir()
    (run / "org-m.json").write_text('{"not": "an artifact"}')
    calls = []
    monkeypatch.setattr("model_cards.core.review.save_artifact",
                        lambda a, p: p.write_text("{}"))

    def compose(*a, **k):
        calls.append(a)
        return _fake_artifact(0.0, tmp_path)

    manifest = batch_mod.run_batch([target], phase="compose", bundle_dir=tmp_path / "b",
                                   out_dir=run, resume=True, export_html=False,
                                   compose_fn=compose, llm_factory=lambda: object())
    assert len(calls) == 1
    assert manifest["results"][0]["compose"]["status"] == "ok"


def test_a_target_that_hangs_is_killed_and_the_run_continues(tmp_path, monkeypatch):
    """batch_hangs_forever: a twelve-target run stopped dead for six and a half hours with
    eight sockets to the provider still ESTABLISHED and every worker blocked inside a raw
    SSL read, past the HTTP client's own 420-second read timeout, which never fired. A
    thread in that state cannot be interrupted from inside the process, so the deadline
    has to belong to a supervisor that can kill."""
    import pathlib
    import subprocess

    targets = ["org/hangs@" + "a" * 40, "org/fine@" + "b" * 40]
    monkeypatch.setattr(batch_mod, "slug_for", lambda t: t.split("/")[1].split("@")[0])
    calls = []

    real_run = subprocess.run

    def fake_run(command, **kwargs):
        if "model_cards.core" not in command:
            return real_run(command, **kwargs)      # the manifest still reads git HEAD
        target = next(part for part in command if "@" in part)
        calls.append((target, kwargs.get("timeout")))
        if "hangs" in target:
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))
        pathlib.Path(command[command.index("--out") + 1]).write_text("{}")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(batch_mod.subprocess, "run", fake_run)
    monkeypatch.setattr("model_cards.core.review.load_artifact",
                        lambda p: _fake_artifact(0.0, tmp_path))
    manifest = batch_mod.run_batch(targets, phase="compose", bundle_dir=tmp_path / "b",
                                   out_dir=tmp_path / "run", concurrency=1,
                                   per_target_timeout=7, export_html=False)
    assert [t for t, _ in calls] == targets
    assert {timeout for _, timeout in calls} == {7}
    statuses = {r["target"]: r["status"] for r in manifest["results"]}
    assert statuses[targets[0]] == "failed"
    assert statuses[targets[1]] == "ok"
    failed = next(r for r in manifest["results"] if r["status"] == "failed")
    assert "exceeded 7s" in failed["error"]
    assert manifest["caps"]["per_target_timeout_s"] == 7


def test_a_target_whose_process_exits_nonzero_reports_its_error(tmp_path, monkeypatch):
    """batch_failure_takes_down_run, out of process."""
    import subprocess

    monkeypatch.setattr(batch_mod, "slug_for", lambda t: "only")
    real_run = subprocess.run
    monkeypatch.setattr(
        batch_mod.subprocess, "run",
        lambda command, **kw: (
            real_run(command, **kw) if "model_cards.core" not in command
            else subprocess.CompletedProcess(
                command, 2, "", "modelcards: error: no bundle for org/x under bundles\n")))
    manifest = batch_mod.run_batch(["org/x@" + "a" * 40], phase="compose",
                                   bundle_dir=tmp_path / "b", out_dir=tmp_path / "run",
                                   export_html=False)
    assert manifest["status_counts"] == {"failed": 1}
    assert "no bundle for org/x" in manifest["results"][0]["error"]


def test_collection_is_isolated_and_deadlined_like_composition(tmp_path, monkeypatch):
    """batch_hangs_forever, collection side. Document extraction is a native dependency
    reading an arbitrary PDF from the internet; it gets one chance at a wall clock."""
    import subprocess

    real_run = subprocess.run
    targets = ["org/slow@" + "a" * 40, "org/fine@" + "b" * 40]
    monkeypatch.setattr(batch_mod, "slug_for", lambda t: t.split("/")[1].split("@")[0])
    seen = []

    def fake_run(command, **kwargs):
        if "model_cards.core" not in command:
            return real_run(command, **kwargs)
        target = next(part for part in command if "@" in part)
        seen.append((command[command.index("model_cards.core") + 1], kwargs.get("timeout")))
        if "slow" in target:
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))
        bundle = tmp_path / "b" / target.split("/")[1].split("@")[0]
        bundle.mkdir(parents=True, exist_ok=True)
        (bundle / "bundle-manifest.json").write_text(
            '{"channels": {"hf": {}}, "absent_channels": ["paper"]}')
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(batch_mod.subprocess, "run", fake_run)
    manifest = batch_mod.run_batch(targets, phase="collect", bundle_dir=tmp_path / "b",
                                   out_dir=tmp_path / "run", concurrency=1,
                                   collect_timeout=11)
    assert [name for name, _ in seen] == ["collect", "collect"]
    assert {timeout for _, timeout in seen} == {11}
    statuses = {r["target"]: r["status"] for r in manifest["results"]}
    assert statuses[targets[0]] == "failed" and statuses[targets[1]] == "ok"
    assert "exceeded 11s" in next(r for r in manifest["results"]
                                  if r["status"] == "failed")["error"]
    ok = next(r for r in manifest["results"] if r["status"] == "ok")
    assert ok["collect"]["absent_channels"] == ["paper"]
    assert manifest["caps"]["collect_timeout_s"] == 11
