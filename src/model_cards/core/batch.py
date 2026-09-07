"""Batch collection and composition over a target list.

One run directory holds the cards, the per-card usage logs and one run manifest.
Targets are independent: a target that raises is recorded as failed and the rest of
the run continues. Composition is paid, so the runner carries two spend tripwires
(per card and per run) computed from the handler's own usage records, and it stops the
run when either is crossed. Resume skips targets whose output already exists.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from .model_sources import slug_for

logger = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 4
PER_CARD_USD_CAP = 2.00
PER_RUN_USD_CAP = 40.00
# Generous against the observed distribution: a card is 70 to 420 seconds of wall time on
# the pinned route, and the longest legitimate one is a large paper with a full gap pass.
PER_TARGET_TIMEOUT_S = 900
# Collection is free but not fast: extracting a ninety-page report is minutes of CPU.
COLLECT_TIMEOUT_S = 900


class BudgetExceeded(RuntimeError):
    """A spend tripwire fired; the run stops and keeps everything already written."""


def read_targets(path: str | Path) -> List[str]:
    """Non-empty, non-comment lines of a targets file, in order, deduplicated."""
    out: List[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in out:
            out.append(line)
    return out


def _git_head(repo: Path) -> Optional[str]:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def usage_totals(path: str | Path) -> Dict[str, Any]:
    """calls, tokens, cost and the providers seen in one usage jsonl."""
    p = Path(path)
    if not p.is_file():
        return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "providers": []}
    calls = inp = outp = 0
    cost = 0.0
    providers: List[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        calls += 1
        inp += row.get("input_tokens") or 0
        outp += row.get("output_tokens") or 0
        cost += row.get("cost") or 0.0
        prov = row.get("provider")
        if prov and prov not in providers:
            providers.append(prov)
    return {"calls": calls, "input_tokens": inp, "output_tokens": outp,
            "cost_usd": round(cost, 8), "providers": providers}


def _bundle_digest(source_hashes: Dict[str, Any]) -> Optional[str]:
    """One digest over the frozen source file hashes, so a replay can be checked."""
    if not source_hashes:
        return None
    blob = json.dumps(source_hashes, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _write_public(artifact, out_root: Path, slug: str) -> Dict[str, Any]:
    """The published projection and its Markdown companion, or why they were refused."""
    from .public import export_public
    from .public_markdown import render_public_markdown

    try:
        projection = export_public(artifact, reviewed=False)
    except Exception as exc:
        # the public export never takes down a card that composed: the artifact and the
        # inspector are written either way, and the manifest says why nothing published
        logger.warning("public export refused for %s: %s", slug, str(exc)[:200])
        return {"public": {"error": f"{type(exc).__name__}: {exc}"[:300]}}
    payload = json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    json_name = f"{slug}.public.json"
    (out_root / json_name).write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    (out_root / f"{slug}.public.md").write_text(
        render_public_markdown(projection, json_filename=json_name, json_sha256=digest),
        encoding="utf-8")
    return {"public": {"json": json_name, "markdown": f"{slug}.public.md",
                       "sha256": digest}}


class _Ledger:
    """Run-wide spend, guarded by an ordinary lock."""

    def __init__(self, run_cap: float) -> None:
        self._lock = threading.Lock()
        self._cost = 0.0
        self._calls = 0
        self._run_cap = run_cap
        self.stop = threading.Event()
        self.stop_reason: Optional[str] = None

    def add(self, totals: Dict[str, Any]) -> float:
        with self._lock:
            self._cost += totals.get("cost_usd") or 0.0
            self._calls += totals.get("calls") or 0
            if self._cost > self._run_cap and not self.stop.is_set():
                self.stop_reason = (f"run spend USD {self._cost:.4f} crossed the "
                                    f"USD {self._run_cap:.2f} run cap")
                self.stop.set()
            return self._cost

    @property
    def cost(self) -> float:
        with self._lock:
            return round(self._cost, 8)

    @property
    def calls(self) -> int:
        with self._lock:
            return self._calls


def run_batch(targets: Iterable[str], *, phase: str, bundle_dir: str | Path,
              out_dir: str | Path, concurrency: int = DEFAULT_CONCURRENCY,
              resume: bool = False, per_card_cap: float = PER_CARD_USD_CAP,
              run_cap: float = PER_RUN_USD_CAP,
              per_target_timeout: int = PER_TARGET_TIMEOUT_S,
              collect_timeout: int = COLLECT_TIMEOUT_S,
              collect_fn: Optional[Callable[..., Any]] = None,
              compose_fn: Optional[Callable[..., Any]] = None,
              llm_factory: Optional[Callable[[], Any]] = None,
              export_html: bool = True) -> Dict[str, Any]:
    """Run `phase` ("collect", "compose" or "both") over the targets.

    collect is free and network-bound; compose is paid and spends against the caps.
    Returns the run manifest, which is also written to out_dir/run-manifest.json.
    """
    if phase not in ("collect", "compose", "both"):
        raise ValueError(f"unknown phase: {phase}")
    targets = list(targets)
    bundle_root = Path(bundle_dir)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    package_root = Path(__file__).resolve().parents[2]

    ledger = _Ledger(run_cap)
    results: Dict[str, Dict[str, Any]] = {}
    results_lock = threading.Lock()
    started = time.monotonic()

    def do_collect(target: str) -> Dict[str, Any]:
        slug = slug_for(target)
        manifest_path = bundle_root / slug / "bundle-manifest.json"
        if resume and manifest_path.is_file():
            return {"status": "skipped_existing",
                    "channels": json.loads(manifest_path.read_text(encoding="utf-8")).get("channels")}
        if collect_fn is None:
            # same deadline discipline as composition: document extraction is a native
            # dependency reading an arbitrary PDF, and it gets one chance at a wall clock
            run_subprocess(["collect", target, "--bundle-dir", str(bundle_root.resolve())],
                           timeout=collect_timeout)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            manifest = collect_fn(target, bundle_root, allow_network=True)
        return {"status": "ok", "channels": manifest.get("channels"),
                "absent_channels": manifest.get("absent_channels")}

    def run_subprocess(args: List[str], *, timeout: int) -> None:
        """One target, one process, one deadline. Raises on failure or timeout."""
        command = [sys.executable, "-m", "model_cards.core", *args]
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(package_root / "src"), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        try:
            done = subprocess.run(command, env=env, capture_output=True, text=True,
                                  timeout=timeout, cwd=str(package_root))
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"{args[0]} exceeded {timeout}s and was killed") from exc
        if done.returncode != 0:
            tail = [line for line in (done.stderr or done.stdout or "").strip().splitlines()
                    if line.strip()]
            raise RuntimeError("; ".join(tail[-3:])[:400]
                               or f"{args[0]} exited {done.returncode}")

    def compose_out_of_process(target: str, card_path: Path, usage_path: Path) -> None:
        run_subprocess(["compose", target, "--bundle-dir", str(bundle_root.resolve()),
                        "--llm-usage-log", str(usage_path.resolve()),
                        "--out", str(card_path.resolve()), "--force"],
                       timeout=per_target_timeout)

    def do_compose(target: str) -> Dict[str, Any]:
        from .review import load_artifact, save_artifact
        from .records import VerifierAction

        slug = slug_for(target)
        card_path = out_root / f"{slug}.json"
        usage_path = out_root / f"llm_usage_{slug}.jsonl"
        if resume and card_path.is_file():
            # a file that exists is not a card. An artifact that saved cleanly and then
            # failed to render satisfied a bare existence check and was skipped forever
            # (seen 2026-09-04 on the two targets a duplicated lineage rule broke).
            from .review import load_artifact

            try:
                load_artifact(card_path)
            except Exception as exc:
                logger.warning("recomposing %s: existing card does not load: %s",
                               target, str(exc)[:160])
            else:
                return {"status": "skipped_existing", "card": card_path.name,
                        "usage": usage_totals(usage_path)}
        if ledger.stop.is_set():
            return {"status": "skipped_budget", "reason": ledger.stop_reason}
        if compose_fn is None:
            compose_out_of_process(target, card_path, usage_path)
            artifact = load_artifact(card_path)
        else:
            # an injected composer runs in process; the usage sink is this thread's
            from auto_benchmarkcard.llm_handler import set_usage_log_path

            set_usage_log_path(str(usage_path), this_thread_only=True)
            artifact = compose_fn(target, bundle_root, llm_factory())
            save_artifact(artifact, card_path)
        totals = usage_totals(usage_path)
        run_cost = ledger.add(totals)
        source_hashes = (artifact.metadata or {}).get("source_hashes") or {}
        accepted = sum(1 for b in artifact.bindings if b.verifier_action is VerifierAction.ACCEPT)
        withheld = sum(1 for b in artifact.bindings if b.verifier_action is VerifierAction.WITHHOLD)
        out = {"status": "ok", "card": card_path.name, "usage": totals,
               "bindings": {"accepted": accepted, "withheld": withheld},
               "coverage": artifact.card["provenance_and_quality"]["coverage_score"],
               "bundle_sha256": _bundle_digest(source_hashes),
               "source_files": sorted(source_hashes),
               "run_cost_usd_after": round(run_cost, 8)}
        out.update(_write_public(artifact, out_root, slug))
        if totals["cost_usd"] > per_card_cap:
            ledger.stop_reason = (f"{target} cost USD {totals['cost_usd']:.4f}, over the "
                                 f"USD {per_card_cap:.2f} per-card cap")
            ledger.stop.set()
            out["budget"] = ledger.stop_reason
        if export_html:
            from .render import save_html
            save_html(artifact, out_root / f"{slug}.html", reviewed=False)
            out["inspector"] = f"{slug}.html"
        return out

    def work(target: str) -> None:
        entry: Dict[str, Any] = {"target": target, "slug": slug_for(target)}
        t0 = time.monotonic()
        try:
            if phase in ("collect", "both"):
                entry["collect"] = do_collect(target)
            if phase in ("compose", "both"):
                if ledger.stop.is_set():
                    entry["compose"] = {"status": "skipped_budget", "reason": ledger.stop_reason}
                else:
                    entry["compose"] = do_compose(target)
            entry["status"] = "ok"
        except Exception as exc:  # one target never takes the run down
            logger.warning("%s failed: %s", target, exc)
            entry["status"] = "failed"
            entry["error"] = f"{type(exc).__name__}: {exc}"[:400]
        entry["wall_s"] = round(time.monotonic() - t0, 2)
        with results_lock:
            results[target] = entry

    workers = max(1, min(int(concurrency), 6))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, t) for t in targets]
        for fut in as_completed(futures):
            fut.result()

    from .composer_schema import prompts_fingerprint
    from .route import route as effective_route

    tokens_in = sum((r.get("compose", {}).get("usage") or {}).get("input_tokens", 0)
                    for r in results.values())
    tokens_out = sum((r.get("compose", {}).get("usage") or {}).get("output_tokens", 0)
                     for r in results.values())
    providers = sorted({p for r in results.values()
                        for p in ((r.get("compose", {}).get("usage") or {}).get("providers") or [])})
    manifest = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "phase": phase, "targets": len(targets), "concurrency": workers, "resume": resume,
        "bundle_dir": str(bundle_root), "out_dir": str(out_root),
        "pipeline_commit": _git_head(package_root),
        "composer_commit": _git_head((package_root / "../auto-benchmarkcard").resolve()),
        "route": effective_route(), "observed_providers": providers,
        "prompts_sha256": prompts_fingerprint(),
        "caps": {"per_card_usd": per_card_cap, "per_run_usd": run_cap,
                 "per_target_timeout_s": per_target_timeout,
                 "collect_timeout_s": collect_timeout},
        "totals": {"calls": ledger.calls, "cost_usd": ledger.cost,
                   "input_tokens": tokens_in, "output_tokens": tokens_out,
                   "wall_s": round(time.monotonic() - started, 2)},
        "stopped_early": ledger.stop_reason,
        "results": [results[t] for t in targets if t in results],
    }
    counts: Dict[str, int] = {}
    for entry in manifest["results"]:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    manifest["status_counts"] = counts
    (out_root / "run-manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    return manifest
