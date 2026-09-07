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
    (re.compile(r"\bEM\b", re.IGNORECASE), lambda m: "exact match"),
    (re.compile(r"\bF1\b", re.IGNORECASE), lambda m: "F1"),
    (re.compile(r"\bwin[- ]rate\b|\bLC win\b", re.IGNORECASE), lambda m: "win rate"),
    (re.compile(r"\belo\b", re.IGNORECASE), lambda m: "Elo"),
    (re.compile(r"\bBLEU\b", re.IGNORECASE), lambda m: "BLEU"),
    (re.compile(r"\bROUGE(?:-[12L])?\b", re.IGNORECASE), lambda m: "ROUGE"),
    (re.compile(r"\bWER\b"), lambda m: "WER"),
    (re.compile(r"\bperplexity\b|\bPPL\b", re.IGNORECASE), lambda m: "perplexity"),
    (re.compile(r"\bnDCG(?:@\d+)?\b", re.IGNORECASE), lambda m: "nDCG"),
    (re.compile(r"\bMRR\b"), lambda m: "MRR"),
    (re.compile(r"\btop[- ]?(\d)\b", re.IGNORECASE), lambda m: f"top-{m.group(1)}"),
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


# A table sits under headings that say whose numbers it holds. The DeepSeek-V3 report puts
# its pre-training table under "4. Evaluation Results / Base Model" and its chat table
# under "Chat Model", and both tables have a column labelled "DeepSeek-V3". Reading the
# column label alone published five base-model rows on the chat card (seen 2026-09-05).
_HEADING_RE = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")
_BASE_SCOPE_RE = re.compile(
    r"\b(base model|base models|pre-?training|pretrained model|foundation model)\b", re.IGNORECASE)
_POST_SCOPE_RE = re.compile(
    r"\b(post-?training|chat model|chat models|instruct(?:ion)?[- ]tuned|instruction "
    r"following|aligned model|thinking mode|non-?thinking|reasoning model)\b", re.IGNORECASE)
_BASE_NAME_TOKENS = {"base", "pt", "pretrain", "pretrained"}
_POST_NAME_TOKENS = {"instruct", "chat", "it", "sft", "dpo", "rl", "rlhf", "rlvr",
                     "think", "thinking", "reasoning", "distill", "tulu"}


def target_stage(model_id: str, sources: str = "",
                 base_model_tags: Optional[list] = None) -> str | None:
    """"base", "post" or None: which member of a base/post-trained pair the target is.

    The repo name usually says it. DeepSeek-V3 does not, and carries no base_model tag
    either, yet its report has a "Base Model" section and a "Chat Model" section with a
    DeepSeek-V3 column in both. The tie-breaker is literal: when a repo named
    "<this name>-Base" occurs in the target's own frozen sources, this checkpoint is the
    post-trained member of that pair. Same discipline as the frame, no inference.
    """

    name = (model_id or "").rsplit("/", 1)[-1]
    tokens = {t for t in re.split(r"[^a-z0-9.]+", name.lower()) if t}
    if tokens & _BASE_NAME_TOKENS:
        return "base"
    if tokens & _POST_NAME_TOKENS:
        return "post"
    low = (sources or "").lower()
    if low and any(f"{name.lower()}-{token}" in low for token in ("base", "pt")):
        return "post"
    # and the mirror: a repo named "<this name>-Instruct" in the target's own sources
    # makes this checkpoint the pre-trained member. google/gemma-2-9b carries no stage
    # token, its README names gemma-2-9b-it on every other line, and without a stage the
    # section-scope rule let the instruction-tuned tables onto the base card (2026-09-07).
    if low and any(f"{name.lower()}-{token}" in low
                   for token in ("instruct", "it", "chat", "sft", "dpo", "rlhf")):
        return "base"
    # and the structural fallback: a repo whose name declares no post-training stage and
    # which declares no base model is the pre-trained member of its own release. Llama 3.2
    # 3B says neither in its name nor in its README that Llama-3.2-3B-Instruct exists, and
    # without a stage its README's "Instruction Tuned Models" tables were read as this
    # checkpoint's own: thirteen instruct scores on the base card (2026-09-07).
    if base_model_tags is not None and not base_model_tags:
        from .model_frame import is_derivative_name

        if not is_derivative_name(model_id):
            return "base"
    return None


def _headings_above(lines: List[str], table_start: int) -> str:
    """The markdown headings in force at a table, deepest last, as one string."""
    path: Dict[int, str] = {}
    for line in lines[:table_start]:
        m = _HEADING_RE.match(line or "")
        if not m:
            continue
        level = len(m.group(1))
        path[level] = m.group(2)
        for deeper in [k for k in path if k > level]:
            path.pop(deeper)
    return " / ".join(path[k] for k in sorted(path))


def _lead_in(lines: List[str], table_start: int, max_lines: int = 3) -> str:
    """The prose immediately above a table, which is where a README says what the table
    is for: "Evaluation results marked in the table are for instruction-tuned models."
    sat two lines above the Gemma 4 26B A4B table with no "Table N" caption, and the base
    card took all 15 rows (2026-09-06)."""
    out: List[str] = []
    for k in range(table_start - 1, -1, -1):
        line = (lines[k] or "").strip()
        if not line:
            if out:
                break
            continue
        if line.startswith("|") or _HEADING_RE.match(line):
            break
        out.append(line)
        if len(out) >= max_lines:
            break
    return " ".join(reversed(out))


def row_quote_for_target(quote: str, header: Optional[List[str]], aliases: List[str], *,
                        stage: str | None = None, own_readme: bool = False) -> str:
    """A table-row quote reduced to what supports a claim about the target.

    A row such as "Safety (6 task avg.) | 94.4 | 89.0 | 88.3 | ..." under a header that
    names seven models supports exactly one number for the target: the one in its
    column. The writer of the Tulu 3 70B DPO card of 2026-09-06 took 94.4, the SFT
    sibling's column, and the leaf-support check passed it because the number was in
    the quote. With no target column the row supports no number at all.
    """
    if not header or "|" not in (quote or ""):
        return quote
    cells = [c.strip() for c in quote.strip().strip("|").split("|")]
    if len(cells) < 2:
        return quote
    head = [h.strip() for h in header]
    target_cols = [i for i, h in enumerate(head)
                   if _label_matches(h, aliases, stage=stage, own_readme=own_readme)]
    if not target_cols:
        return cells[0]
    keep = [cells[0]] + [cells[i] for i in target_cols if i < len(cells)]
    return " | ".join(keep)


_BASE_NAME_SUFFIX_RE = re.compile(r"[-_ ]+(?:base|pt)$", re.IGNORECASE)
_POST_NAME_SUFFIX_RE = re.compile(r"[-_ ]+(?:instruct|it|chat|sft|dpo|rlhf|rlvr)$", re.IGNORECASE)


def bare_base_names(aliases: List[str]) -> List[str]:
    """The aliases with a trailing base-stage token removed ("DeepSeek-V3-Base" ->
    "DeepSeek-V3"), for tables whose own heading already says they hold base models."""
    out: List[str] = []
    for alias in aliases:
        bare = _BASE_NAME_SUFFIX_RE.sub("", alias or "")
        if bare and bare != alias and bare not in out:
            out.append(bare)
    return out


def bare_post_names(aliases: List[str]) -> List[str]:
    """The mirror of bare_base_names: the aliases with a trailing post-training token
    removed ("Llama-3.2-3B-Instruct" -> "Llama-3.2-3B"), for tables whose own heading
    already says they hold instruction-tuned models. The Llama 3.2 README labels the
    instruct table's unquantized column "Llama 3.2 3B bf16" under the heading
    "Instruction Tuned Models", and the instruct card read none of it (2026-09-07)."""
    out: List[str] = []
    for alias in aliases:
        bare = _POST_NAME_SUFFIX_RE.sub("", alias or "")
        if bare and bare != alias and bare not in out:
            out.append(bare)
    return out


def _scope_conflict(stage: str | None, context: str) -> bool:
    """Whether the section a table sits in contradicts the target's own stage."""
    if not stage or not context:
        return False
    if stage == "base":
        return bool(_POST_SCOPE_RE.search(context)) and not _BASE_SCOPE_RE.search(context)
    return bool(_BASE_SCOPE_RE.search(context)) and not _POST_SCOPE_RE.search(context)


# A column label is written in the developer's own shorthand, not in the repo name's
# order: the Gemma 2 README labels its columns "Gemma PT 9B" and "Gemma 2 IT 9B" for
# google/gemma-2-9b and google/gemma-2-9b-it. String equality read zero score rows off
# both cards (2026-09-07), so the comparison is by token role: sizes must be the same
# set, the stage must agree, and the family words must agree.
# Failure class: stage_token_order_and_omitted_version_in_column_labels.
# Spellings of one training stage, kept apart where the developer keeps them apart: an
# SFT column and a DPO column are two different checkpoints, and collapsing both to
# "post-trained" handed the DPO card the SFT model's row (caught by the Tulu 3 test).
_LABEL_STAGE_TOKENS = {
    "pt": "base", "base": "base", "pretrain": "base", "pretrained": "base",
    "it": "instruct", "instruct": "instruct", "instruction": "instruct",
    "instructed": "instruct", "tuned": "instruct",
    "chat": "chat", "aligned": "aligned", "sft": "sft", "dpo": "dpo", "rlhf": "rlhf",
    "rlvr": "rlvr", "think": "thinking", "thinking": "thinking", "reasoning": "reasoning",
}


def _coarse_stage(token: str) -> str:
    """Which member of the base/post-trained pair a stage token names."""
    return "base" if token == "base" else "post"
_SIZE_LABEL_RE = re.compile(r"^\d+(?:\.\d+)?[bmk]$|^\d+x\d+(?:\.\d+)?[bm]$")
_VERSION_LABEL_RE = re.compile(r"^v?\d+(?:\.\d+)*$")
# The dtype a table names beside the model is the released checkpoint's own serving
# precision, not another checkpoint: "Llama 3.2 3B bf16" is this model. A quantized
# re-upload (int4, fp8, awq, gptq) is NOT, and stays a different label.
# Failure class: precision_decoration_in_column_label.
_PRECISION_LABEL_TOKENS = {"bf16", "fp16", "f16", "fp32", "float16", "bfloat16", "ours"}


def _label_parts(text: str):
    """(family words, size tokens, stages) of a column label or an alias.

    Dots stay inside a token so "3.2" and "1.5b" survive as one version or size token,
    which _norm cannot do because it splits on every non-alphanumeric.
    """
    rest: List[str] = []
    sizes, stages = set(), set()
    for tok in re.split(r"[^a-z0-9.]+", (text or "").lower()):
        tok = tok.strip(".")
        if not tok:
            continue
        if _SIZE_LABEL_RE.match(tok):
            sizes.add(tok)
        elif tok in _LABEL_STAGE_TOKENS:
            stages.add(_LABEL_STAGE_TOKENS[tok])
        elif tok in _PRECISION_LABEL_TOKENS:
            continue
        else:
            rest.append(tok)
    return rest, sizes, stages


def _label_matches(label: str, aliases: List[str], *, stage: str | None = None,
                   own_readme: bool = False) -> bool:
    """The label IS the target: equal to an alias after normalization, optionally
    followed by a decoration such as "(ours)", or the same tokens in the developer's own
    order. A containment match would hand a base model its derivative's row
    ("OLMo-2-1124-7B" inside "OLMo-2-1124-7B-Instruct"), so nothing here is containment.

    stage is the target's own stage when the sources state it, and it is what admits a
    label that declares a stage the repo name leaves out ("Gemma PT 9B"). own_readme
    admits a label that leaves the family version out ("Gemma PT 9B" for gemma-2-9b),
    which is only safe in the checkpoint's own README.
    """
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
    lab_rest, lab_sizes, lab_stages = _label_parts(label)
    if not lab_rest or len({_coarse_stage(t) for t in lab_stages}) > 1:
        return False
    for alias in aliases:
        a_rest, a_sizes, a_stages = _label_parts(alias)
        if not a_rest or a_sizes != lab_sizes:
            continue
        if a_stages and lab_stages:
            if a_stages != lab_stages:
                continue
        elif a_stages:
            continue
        elif lab_stages and (stage is None
                             or {_coarse_stage(t) for t in lab_stages} != {stage}):
            # the label declares a stage the repo name does not: it is this checkpoint's
            # only when the sources say which member of the pair this checkpoint is
            continue
        if set(lab_rest) == set(a_rest):
            return True
        missing = set(a_rest) - set(lab_rest)
        if (own_readme and missing and not set(lab_rest) - set(a_rest)
                and all(_VERSION_LABEL_RE.match(t) for t in missing)):
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


_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:[^)]*)\)|\[([^\]]+)\]\[[^\]]*\]|\[([^\]]+)\]")


def clean_label(label: str) -> str:
    """A cell's own words, with markdown link syntax removed: the Gemma 2 README writes
    its benchmark column as "[MMLU][mmlu]" and the card published that verbatim."""
    text = _MD_LINK_RE.sub(lambda m: m.group(1) or m.group(2) or m.group(3) or "", label or "")
    return re.sub(r"\s+", " ", text).strip()


def _row_label_is_a_benchmark(label: str) -> bool:
    """A transposed table's rows are benchmarks, except the ones that are not: a report's
    headline table mixes "# Total Params", "Architecture" and "# Training Tokens" in with
    the benchmarks, and none of those is a score."""
    words = {w for w in re.split(r"[^a-z0-9%@]+", (label or "").lower()) if w}
    if not words:
        return False
    return not (words & _COST_WORDS) or bool(words & _BENCHMARK_WORDS)


# The columns a transposed table puts before the models. Reading the first cell as the
# benchmark name made "General" a benchmark on the Llama 3.2 cards and "English", "Code",
# "Math" and "Chinese" benchmarks on the DeepSeek-V3 card, each carrying the first real
# benchmark's number, and it dropped every row whose category cell was left empty.
# Failure class: category_column_read_as_benchmark.
_NAME_COLUMN_RE = re.compile(
    r"^(?:benchmark|benchmarks|task|tasks|dataset|datasets|eval|evals|evaluation)\b")
_METRIC_COLUMN_RE = re.compile(r"^metric")
_SHOTS_COLUMN_RE = re.compile(r"^(?:n\s+)?shots?\b")


def _shots_setting(cell: str) -> str:
    """The evaluation setting a "# Shots" column states, in the setting's own words."""
    text = (cell or "").strip()
    if not text:
        return NOT_SPECIFIED
    if re.fullmatch(r"\d{1,2}", text):
        return f"{text}-shot"
    m = re.fullmatch(r"(\d{1,2})\s*-\s*(\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)} shot"
    return read_setting(text)


def _leading_columns(header: List[str], first_model: int):
    """(name, metric, shots) column indexes among the columns before the first model."""
    name_col, metric_col, shots_col = 0, None, None
    for j, cell in enumerate(header[:first_model]):
        norm = _norm(cell)
        if not norm:
            continue
        if name_col == 0 and _NAME_COLUMN_RE.match(norm):
            name_col = j
        elif metric_col is None and _METRIC_COLUMN_RE.match(norm):
            metric_col = j
        elif shots_col is None and _SHOTS_COLUMN_RE.match(norm):
            shots_col = j
    return name_col, metric_col, shots_col


def _transposed_rows(block: List[str], header: List[str], aliases: List[str], caption: str,
                     source_doc: str, stage: str | None = None,
                     own_readme: bool = False) -> List[Dict[str, Any]]:
    """Scores from the column whose header names the target, one per benchmark row."""
    columns = [j for j, cell in enumerate(header)
               if j and _label_matches(cell, aliases, stage=stage, own_readme=own_readme)]
    if not columns:
        return []
    name_col, metric_col, shots_col = _leading_columns(header, min(columns))
    rows: List[Dict[str, Any]] = []
    for line in block[1:]:
        if _SEP_ROW_RE.match(line):
            continue
        cells = _cells(line)
        if len(cells) <= name_col or not cells[name_col]:
            continue
        name, parenthetical = clean_label(cells[name_col]), ""
        m = _SETTING_RE.match(name)
        if m:
            name, parenthetical = m.group("name").strip(), m.group("setting").strip()
        if not _row_label_is_a_benchmark(name):
            continue
        metric_cell = cells[metric_col] if metric_col is not None and metric_col < len(cells) else ""
        shots_cell = cells[shots_col] if shots_col is not None and shots_col < len(cells) else ""
        shots = _shots_setting(shots_cell)
        for j in columns:
            if j >= len(cells) or not _NUM_RE.match(cells[j]):
                continue
            rows.append({
                "benchmark": name, "score": cells[j],
                "metric": read_metric(metric_cell, parenthetical, cells[name_col], caption),
                # a "Metric" column often states the shots as well ("5-shot, top-1")
                "setting": (shots if shots != NOT_SPECIFIED
                            else read_setting(metric_cell, parenthetical, cells[name_col],
                                              caption)),
                "row_text": evidence_mod.normalize_ws(line),
                "header": [h for h in header if h], "caption": caption,
                "source_doc": source_doc, "orientation": "benchmark_major",
            })
    return rows


def target_score_rows(text: str, aliases: List[str], source_doc: str,
                      stage: str | None = None, own_readme: bool = False) -> List[Dict[str, Any]]:
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
        section = _headings_above(lines, table_start)
        scope_text = f"{section} {caption} {_lead_in(lines, table_start)}"
        if _scope_conflict(stage, scope_text):
            continue
        # Under a heading that says "Base Model", a column labelled with the bare family
        # name is the base checkpoint: the DeepSeek-V3 report labels the base model's
        # column "DeepSeek-V3" in its base-model tables, and DeepSeek-V3-Base matched
        # nothing at all (0 rows, 2026-09-06). The bare name is admitted only there.
        row_aliases = aliases
        if stage == "base" and _BASE_SCOPE_RE.search(scope_text) and not _POST_SCOPE_RE.search(scope_text):
            row_aliases = list(aliases) + bare_base_names(aliases)
        elif stage == "post" and _POST_SCOPE_RE.search(scope_text) and not _BASE_SCOPE_RE.search(scope_text):
            row_aliases = list(aliases) + bare_post_names(aliases)
        corner = header[0] if header else ""
        # a header cell naming the target means the table is benchmark-major, whatever
        # its header words look like
        transposed = _transposed_rows(block, header, row_aliases, caption, source_doc,
                                      stage=stage, own_readme=own_readme)
        if transposed:
            rows.extend(transposed)
            continue
        if not header_is_results_table(header):
            continue
        for line in block[1:]:
            if _SEP_ROW_RE.match(line):
                continue
            cells = _cells(line)
            if not cells or not _label_matches(cells[0], row_aliases, stage=stage,
                                               own_readme=own_readme):
                continue
            for j, cell in enumerate(cells[1:], start=1):
                if j >= len(header) or not header[j] or not _NUM_RE.match(cell):
                    continue
                name, parenthetical = clean_label(header[j]), ""
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
