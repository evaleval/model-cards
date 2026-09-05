"""Deterministic benchmark scores from the markdown table cell that IS the target's.

Results tables come in two orientations and both have to be read, because the developer
picks one and the paper often picks the other:

  model-major   one row per model, one column per benchmark. The row whose first cell
                names the target is this model's score row.
  benchmark-major (transposed)  one row per benchmark, one column per model. The column
                whose header names the target is this model's score column. Every Qwen3
                and DeepSeek-V3 results table in their technical reports is this shape,
                and reading only the first orientation returned no scores at all for
                three of the six 2026-09-04 acceptance targets.

Either way the cell is selected by an exact label match against the target's own aliases,
so a comparison model's number is never picked up and the referent question never reaches
the language model. The anchor recorded with each score is the table line the number came
from, which is what the ledger's row-anchor rule requires.

A score is only comparable when its metric and its evaluation setting travel with it.
Both are read from the table itself, never guessed: the header cell first ("MMLU
(5-shot)", "HumanEval pass@1"), then the table's caption ("Table 4: Accuracy (%) in the
zero-shot setting"), then the corner cell. What cannot be read stays "Not specified".

The same benchmark is often reported twice, once in the README and once in the paper.
reconcile_rows keeps one row when they agree, keeps both when they were measured under
different settings, and withholds both with a conflict flag when they disagree under the
same setting, because there is no evidence in the sources for choosing one.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from auto_benchmarkcard.tools.composer import evidence as evidence_mod

_SEP_ROW_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_NUM_RE = re.compile(r"^[<>~≈]?\s*-?\d+(?:[.,]\d+)?\s*%?(?:\s*[±\+/-]\s*\d+(?:\.\d+)?)?$")
_SETTING_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<setting>[^()]{1,40})\)\s*$")
_MARKUP_RE = re.compile(r"[*_`]+")

# An evaluation setting is a stated measurement condition, not a metric.
_SHOT_RE = re.compile(r"\b(\d{1,2})[- ]?shot\b", re.IGNORECASE)
_SETTING_WORD_RE = re.compile(
    r"\b(zero[- ]shot|few[- ]shot|one[- ]shot|chain[- ]of[- ]thought|cot|greedy|"
    r"non[- ]thinking|thinking|reasoning mode|maj@\d+|self[- ]consistency|pass@\d+ sampling|"
    r"temperature\s*=?\s*[\d.]+)\b", re.IGNORECASE)
# A metric names what was measured.
_METRIC_PATTERNS = (
    (re.compile(r"\bpass@(\d+)\b", re.IGNORECASE), lambda m: f"pass@{m.group(1)}"),
    (re.compile(r"\bacc(?:uracy)?\b", re.IGNORECASE), lambda m: "accuracy"),
    (re.compile(r"\bexact[- ]match\b", re.IGNORECASE), lambda m: "exact match"),
    (re.compile(r"\bEM\b"), lambda m: "exact match"),
    (re.compile(r"\bF1\b", re.IGNORECASE), lambda m: "F1"),
    (re.compile(r"\bwin[- ]rate\b|\bLC win\b", re.IGNORECASE), lambda m: "win rate"),
    (re.compile(r"\belo\b", re.IGNORECASE), lambda m: "Elo"),
    (re.compile(r"\bBLEU\b", re.IGNORECASE), lambda m: "BLEU"),
    (re.compile(r"\bROUGE(?:-[12L])?\b", re.IGNORECASE), lambda m: "ROUGE"),
    (re.compile(r"\bWER\b"), lambda m: "WER"),
    (re.compile(r"\bperplexity\b|\bPPL\b", re.IGNORECASE), lambda m: "perplexity"),
    (re.compile(r"\bnDCG(?:@\d+)?\b", re.IGNORECASE), lambda m: "nDCG"),
    (re.compile(r"\bMRR\b"), lambda m: "MRR"),
    (re.compile(r"\bscore\b", re.IGNORECASE), lambda m: "score"),
)
_CAPTION_RE = re.compile(r"^\s*(?:\*\*)?\s*Table\s*\d*[.:]?\s*(.+?)\s*(?:\*\*)?\s*$",
                         re.IGNORECASE)
NOT_SPECIFIED = "Not specified"


def read_metric(*texts: str) -> str:
    """The metric named in the first text that names one, else Not specified."""
    for text in texts:
        for pattern, render in _METRIC_PATTERNS:
            m = pattern.search(text or "")
            if m:
                return render(m)
    return NOT_SPECIFIED


def read_setting(*texts: str) -> str:
    """The evaluation setting stated in the first text that states one."""
    for text in texts:
        text = text or ""
        m = _SHOT_RE.search(text)
        if m:
            shots = f"{m.group(1)}-shot"
            cot = re.search(r"\b(cot|chain[- ]of[- ]thought)\b", text, re.IGNORECASE)
            return f"{shots} CoT" if cot else shots
        m = _SETTING_WORD_RE.search(text)
        if m:
            return m.group(0).strip()
    return NOT_SPECIFIED


def _cells(line: str) -> List[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [_MARKUP_RE.sub("", c).strip() for c in s.split("|")]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


_LABEL_DECORATIONS = ("ours", "this work", "this model")

# A results table names benchmarks or scores in its header. A training-cost table
# (GPU hours, MWh, tCO2eq, FLOPs, tokens, parameters, price, latency) never does; the
# OLMo 2 paper's "| OLMo 2 7B | 131 | 1.2 | 0.332 |" row is such a table and its cells
# are not scores. Header words decide, the row label alone does not.
_BENCHMARK_WORDS = {
    "average", "avg", "score", "scores", "accuracy", "acc", "pass", "em", "f1", "win", "elo",
    "mmlu", "mmlupro", "gsm8k", "gsm", "math", "arc", "hellaswag", "hswag", "winogrande", "winog",
    "truthfulqa", "humaneval", "mbpp", "bbh", "drop", "nq", "triviaqa", "agieval", "gpqa", "ifeval",
    "alpacaeval", "ae2", "arenahard", "mtbench", "mt", "bench", "safety", "popqa", "squad", "boolq",
    "piqa", "siqa", "openbookqa", "obqa", "csqa", "commonsenseqa", "coqa", "mgsm", "livecodebench",
    "swe", "aime", "codeforces", "livebench", "mmmu", "mathvista", "docvqa", "chartqa", "ai2d",
    "textvqa", "vqav2", "lambada", "wikitext", "ppl", "perplexity", "rouge", "bleu", "chrf", "wer",
    "cer", "ndcg", "mrr", "recall", "precision", "auc", "hits", "toxigen", "bias", "xstest",
    "hallucination", "helm", "leaderboard", "benchmark", "benchmarks", "task", "tasks", "eval",
    "evaluation", "results", "%", "@",
}
_COST_WORDS = {
    "flops", "flop", "mwh", "kwh", "tco2eq", "tco2", "co2", "carbon", "power", "energy", "pue",
    "hours", "gpu", "gpus", "tokens", "params", "parameters", "price", "cost", "latency",
    "throughput", "memory", "vram", "tps", "steps", "batch", "lr", "epochs", "checkpoints",
    "size", "context", "length", "date", "release", "license", "downloads",
    # a report's architecture table has one column per model too, and its rows are
    # configuration, not results
    "layers", "layer", "heads", "head", "dim", "dims", "dimension", "hidden", "vocab",
    "vocabulary", "experts", "expert", "kv", "rope", "seq", "window", "quantization",
    "precision", "dtype", "activated", "embedding", "embeddings", "ffn", "mlp", "groups",
    "tokenizer", "optimizer", "warmup", "schedule", "stage", "stages", "budget",
}


def header_is_results_table(header: List[str]) -> bool:
    words = set()
    for cell in header:
        for w in re.split(r"[^a-z0-9%@]+", (cell or "").lower()):
            if w:
                words.add(w)
    if not words & _BENCHMARK_WORDS:
        return False
    return not (words & _COST_WORDS and not (words & _BENCHMARK_WORDS - {"task", "tasks", "results"}))


def _label_matches(label: str, aliases: List[str]) -> bool:
    """The label IS the target: equal to an alias after normalization, optionally
    followed by a decoration such as "(ours)". A containment match would hand a base
    model its derivative's row ("OLMo-2-1124-7B" inside "OLMo-2-1124-7B-Instruct")."""
    lab = _norm(label)
    if not lab:
        return False
    for alias in aliases:
        a = _norm(alias)
        if not a:
            continue
        if lab == a:
            return True
        if lab.startswith(a + " ") and lab[len(a) + 1:] in _LABEL_DECORATIONS:
            return True
    return False


def _caption_above(lines: List[str], table_start: int) -> str:
    """The caption line just above a table, if the source writes one."""
    for k in range(table_start - 1, max(-1, table_start - 4), -1):
        line = (lines[k] or "").strip()
        if not line:
            continue
        m = _CAPTION_RE.match(line)
        return m.group(1) if m else ""
    return ""


def _row_label_is_a_benchmark(label: str) -> bool:
    """A transposed table's rows are benchmarks, except the ones that are not: a report's
    headline table mixes "# Total Params", "Architecture" and "# Training Tokens" in with
    the benchmarks, and none of those is a score."""
    words = {w for w in re.split(r"[^a-z0-9%@]+", (label or "").lower()) if w}
    if not words:
        return False
    return not (words & _COST_WORDS) or bool(words & _BENCHMARK_WORDS)


def _transposed_rows(block: List[str], header: List[str], aliases: List[str], caption: str,
                     source_doc: str) -> List[Dict[str, Any]]:
    """Scores from the column whose header names the target, one per benchmark row."""
    columns = [j for j, cell in enumerate(header) if j and _label_matches(cell, aliases)]
    if not columns:
        return []
    rows: List[Dict[str, Any]] = []
    for line in block[1:]:
        if _SEP_ROW_RE.match(line):
            continue
        cells = _cells(line)
        if not cells or not cells[0]:
            continue
        name, parenthetical = cells[0], ""
        m = _SETTING_RE.match(name)
        if m:
            name, parenthetical = m.group("name").strip(), m.group("setting").strip()
        if not _row_label_is_a_benchmark(name):
            continue
        for j in columns:
            if j >= len(cells) or not _NUM_RE.match(cells[j]):
                continue
            rows.append({
                "benchmark": name, "score": cells[j],
                "metric": read_metric(parenthetical, cells[0], caption),
                "setting": read_setting(parenthetical, cells[0], caption),
                "row_text": evidence_mod.normalize_ws(line),
                "header": [h for h in header if h], "caption": caption,
                "source_doc": source_doc, "orientation": "benchmark_major",
            })
    return rows


def target_score_rows(text: str, aliases: List[str], source_doc: str) -> List[Dict[str, Any]]:
    """Score rows for the target from every markdown table in text.

    Returns [{"benchmark", "score", "metric", "setting", "row_text", "header", "caption",
    "source_doc"}], row_text being the raw table row (whitespace-normalized by the
    caller's verifier) and header the cleaned header cells.
    """
    rows: List[Dict[str, Any]] = []
    lines = (text or "").split("\n")
    i = 0
    while i < len(lines):
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        table_start = i
        block = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            block.append(lines[i])
            i += 1
        if len(block) < 2:
            continue
        header = _cells(block[0])
        caption = _caption_above(lines, table_start)
        corner = header[0] if header else ""
        # a header cell naming the target means the table is benchmark-major, whatever
        # its header words look like
        transposed = _transposed_rows(block, header, aliases, caption, source_doc)
        if transposed:
            rows.extend(transposed)
            continue
        if not header_is_results_table(header):
            continue
        for line in block[1:]:
            if _SEP_ROW_RE.match(line):
                continue
            cells = _cells(line)
            if not cells or not _label_matches(cells[0], aliases):
                continue
            for j, cell in enumerate(cells[1:], start=1):
                if j >= len(header) or not header[j] or not _NUM_RE.match(cell):
                    continue
                name, parenthetical = header[j], ""
                m = _SETTING_RE.match(name)
                if m:
                    name, parenthetical = m.group("name").strip(), m.group("setting").strip()
                # the parenthetical of a column header is the setting when it reads like
                # one ("5-shot") and the metric when it reads like one ("acc")
                setting = read_setting(parenthetical, header[j], caption, corner)
                metric = read_metric(parenthetical, header[j], caption, corner)
                rows.append({
                    "benchmark": name, "score": cell, "metric": metric,
                    "setting": setting, "row_text": evidence_mod.normalize_ws(line),
                    "header": [h for h in header if h], "caption": caption,
                    "source_doc": source_doc, "orientation": "model_major",
                })
    return rows


def _scope(row: Dict[str, Any]) -> tuple:
    return (_norm(row["benchmark"]), (row.get("setting") or NOT_SPECIFIED).lower())


def _same_score(a: str, b: str) -> bool:
    """70 and 70.0 are the same number; 70 and 70.5 are not. A score that does not parse
    as a number is compared as text."""
    a, b = str(a).strip(), str(b).strip()
    if a == b:
        return True
    try:
        return float(a.replace(",", "").rstrip("%")) == float(b.replace(",", "").rstrip("%"))
    except ValueError:
        return False


def reconcile_rows(rows: List[Dict[str, Any]]) -> tuple:
    """Reconcile score rows that more than one SOURCE reports for the same claim.

    Returns (accepted, withheld). Two sources reporting one benchmark under one setting
    make one claim: identical scores collapse to a single row recording both sources, and
    different scores are a contradiction the sources do not resolve, so both are withheld
    with a conflict flag.

    Rows from the SAME source are never a conflict. A README often carries several results
    tables (thinking and non-thinking mode, per-language breakdowns, a headline table and
    a detailed one) whose rows share a benchmark name and state no setting. Treating those
    as one claim withheld 279 real score rows across the 2026-09-05 batch, including
    twenty-three per-language CER rows collapsed into a single contradiction.
    """
    by_scope: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        by_scope.setdefault(_scope(row), []).append(row)
    accepted: List[Dict[str, Any]] = []
    withheld: List[Dict[str, Any]] = []
    for group in by_scope.values():
        docs: List[str] = []
        for row in group:
            if row["source_doc"] not in docs:
                docs.append(row["source_doc"])
        if len(docs) == 1:
            # one source: these are distinct rows of distinct tables, kept once each
            seen_scores = set()
            for row in group:
                key = str(row["score"]).strip()
                if key in seen_scores:
                    continue
                seen_scores.add(key)
                accepted.append({**row, "source_docs": docs})
            continue
        values = sorted({str(r["score"]).strip() for r in group})
        if all(_same_score(values[0], v) for v in values):
            accepted.append({**group[0], "source_docs": docs})
            continue
        for row in group:
            withheld.append({**row, "withhold_reason": "score_conflict_between_sources",
                             "conflict": values,
                             "conflict_scope": {"benchmark": group[0]["benchmark"],
                                                "setting": group[0].get("setting"),
                                                "sources": docs}})
    return accepted, withheld
