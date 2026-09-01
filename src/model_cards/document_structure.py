"""Deterministic section and table coordinates over Markdown evidence.

This is a small adaptation of the document-structure seam in the MIT-licensed
EvalEval Auto-BenchmarkCards composer.  Quote offsets in this package index the
same whitespace-normalized view used by :mod:`model_cards.quote`; raw line
structure is scanned first and then mapped into that normalized coordinate
space.  Provider-supplied headings or table identifiers are never trusted.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from .quote import normalize_ws


STRUCTURE_VERSION = "markdown-document-structure/v1"
REGIONS = frozenset(
    {
        "introduction",
        "model_details",
        "training",
        "evaluation",
        "limitations",
        "risk",
        "environment",
        "appendix",
        "related_work",
        "other",
    }
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")
_CAPTION_RE = re.compile(r"^\s*Table\s+([A-Za-z0-9._-]+)\b", re.IGNORECASE)
_SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")


@dataclass(frozen=True)
class SectionAnchor:
    title: str
    path: tuple[str, ...]
    region: str
    char_start: int
    char_end: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", tuple(self.path))
        if not self.title or not self.path or self.path[-1] != self.title:
            raise ValueError("section anchor path is invalid")
        if self.region not in REGIONS:
            raise ValueError("section anchor region is invalid")
        if self.char_start < 0 or self.char_end <= self.char_start:
            raise ValueError("section anchor coordinates are invalid")


@dataclass(frozen=True)
class TableAnchor:
    table_id: str
    caption: str
    char_start: int
    char_end: int
    header_row: tuple[str, ...]
    row_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "header_row", tuple(self.header_row))
        object.__setattr__(self, "row_labels", tuple(self.row_labels))
        if not re.fullmatch(r"t[0-9]+", self.table_id):
            raise ValueError("table anchor id is invalid")
        if self.char_start < 0 or self.char_end <= self.char_start:
            raise ValueError("table anchor coordinates are invalid")


@dataclass(frozen=True)
class DocumentContext:
    section_path: tuple[str, ...] = ()
    region: str = "other"
    table_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_path", tuple(self.section_path))
        if self.region not in REGIONS:
            raise ValueError("document context region is invalid")
        if self.table_id is not None and not re.fullmatch(r"t[0-9]+", self.table_id):
            raise ValueError("document context table_id is invalid")


@dataclass(frozen=True)
class DocumentIndex:
    structure_version: str
    normalized_sha256: str
    normalized_length: int
    sections: tuple[SectionAnchor, ...]
    tables: tuple[TableAnchor, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "tables", tuple(self.tables))
        if self.structure_version != STRUCTURE_VERSION:
            raise ValueError("document structure version is unsupported")
        if not re.fullmatch(r"[0-9a-f]{64}", self.normalized_sha256):
            raise ValueError("document normalized digest is invalid")
        if self.normalized_length < 0:
            raise ValueError("document normalized length is invalid")
        previous = -1
        for section in self.sections:
            if section.char_start < previous or section.char_end > self.normalized_length:
                raise ValueError("document sections are out of bounds or order")
            previous = section.char_start
        previous = -1
        for table in self.tables:
            if table.char_start < previous or table.char_end > self.normalized_length:
                raise ValueError("document tables are out of bounds or order")
            previous = table.char_start
        if len({item.table_id for item in self.tables}) != len(self.tables):
            raise ValueError("document table identifiers are not unique")

    def context_at(self, char_start: int, char_end: int | None = None) -> DocumentContext:
        """Return the innermost deterministic context containing a quote span."""

        end = char_start + 1 if char_end is None else char_end
        if char_start < 0 or end <= char_start or end > self.normalized_length:
            raise ValueError("quote span is outside the normalized document")
        section = None
        for candidate in self.sections:
            if candidate.char_start <= char_start and end <= candidate.char_end:
                section = candidate
        table = None
        for candidate in self.tables:
            if candidate.char_start <= char_start and end <= candidate.char_end:
                table = candidate
                break
        return DocumentContext(
            section_path=section.path if section else (),
            region=section.region if section else "other",
            table_id=table.table_id if table else None,
        )


@dataclass
class _Heading:
    raw_start: int
    level: int
    title: str
    line: str
    norm_start: int = -1


@dataclass
class _Table:
    raw_start: int
    block: str
    rows: list[str]
    caption: str = ""
    norm_start: int = -1
    norm_end: int = -1


def build_document_index(markdown_text: str) -> DocumentIndex:
    """Build a closed normalized-coordinate index from untrusted Markdown text."""

    if not isinstance(markdown_text, str):
        raise TypeError("document text must be a string")
    normalized = normalize_ws(markdown_text)
    headings, raw_tables = _scan_raw(markdown_text)
    anchors = sorted(
        [(item.raw_start, "heading", item) for item in headings]
        + [(item.raw_start, "table", item) for item in raw_tables],
        key=lambda item: (item[0], item[1]),
    )
    cursor = 0
    for _, kind, item in anchors:
        chunk = item.line if kind == "heading" else item.block
        span = _map_anchor(markdown_text, normalized, item.raw_start, chunk, cursor)
        if span is None:
            continue
        item.norm_start = span[0]
        if kind == "table":
            item.norm_end = span[1]
        cursor = span[1]

    sections: list[SectionAnchor] = []
    # (level, title, path, region, start)
    stack: list[tuple[int, str, tuple[str, ...], str, int]] = []
    for heading in headings:
        if heading.norm_start < 0:
            continue
        while stack and heading.level <= stack[-1][0]:
            level, title, path, region, start = stack.pop()
            sections.append(SectionAnchor(title, path, region, start, heading.norm_start))
        path = tuple(item[1] for item in stack) + (heading.title,)
        region = _region_for(path)
        stack.append((heading.level, heading.title, path, region, heading.norm_start))
    while stack:
        level, title, path, region, start = stack.pop()
        sections.append(SectionAnchor(title, path, region, start, len(normalized)))
    sections.sort(key=lambda item: (item.char_start, -item.char_end))

    tables: list[TableAnchor] = []
    for sequence, raw_table in enumerate(raw_tables, start=1):
        if raw_table.norm_start < 0 or raw_table.norm_end <= raw_table.norm_start:
            continue
        parsed = [_parse_cells(row) for row in raw_table.rows]
        header = tuple(parsed[0]) if parsed else ()
        body = [cells for cells in parsed[1:] if not _separator_row(cells)]
        tables.append(
            TableAnchor(
                table_id=f"t{sequence}",
                caption=raw_table.caption,
                char_start=raw_table.norm_start,
                char_end=raw_table.norm_end,
                header_row=header,
                row_labels=tuple(cells[0] for cells in body if cells),
            )
        )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return DocumentIndex(
        structure_version=STRUCTURE_VERSION,
        normalized_sha256=digest,
        normalized_length=len(normalized),
        sections=tuple(sections),
        tables=tuple(tables),
    )


def verify_document_index(index: DocumentIndex, markdown_text: str) -> None:
    """Reject an index replayed against different or restructured source text."""

    replayed = build_document_index(markdown_text)
    if replayed != index:
        raise ValueError("document structure index does not replay exactly")


def _scan_raw(raw: str) -> tuple[list[_Heading], list[_Table]]:
    lines = raw.split("\n")
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line) + 1

    headings: list[_Heading] = []
    tables: list[_Table] = []
    in_fence = False
    table_start: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            if table_start is not None:
                _close_table(lines, offsets, table_start, index, tables)
                table_start = None
            in_fence = not in_fence
            continue
        is_pipe = not in_fence and stripped.startswith("|")
        if is_pipe:
            if table_start is None:
                table_start = index
            continue
        if table_start is not None:
            _close_table(lines, offsets, table_start, index, tables)
            table_start = None
        if in_fence:
            continue
        match = _HEADING_RE.fullmatch(stripped)
        if match:
            leading = len(line) - len(line.lstrip())
            headings.append(
                _Heading(
                    raw_start=offsets[index] + leading,
                    level=len(match.group(1)),
                    title=match.group(2).strip(),
                    line=stripped,
                )
            )
    if table_start is not None:
        _close_table(lines, offsets, table_start, len(lines), tables)
    return headings, tables


def _close_table(
    lines: list[str],
    offsets: list[int],
    start: int,
    end: int,
    tables: list[_Table],
) -> None:
    rows = lines[start:end]
    if len(rows) < 2:
        return
    parsed = [_parse_cells(row) for row in rows]
    if len(parsed) < 2 or not _separator_row(parsed[1]):
        return
    leading = len(lines[start]) - len(lines[start].lstrip())
    caption = ""
    for index in range(start - 1, max(-1, start - 6), -1):
        if not lines[index].strip():
            continue
        if _CAPTION_RE.match(lines[index]):
            caption = lines[index].strip()
        break
    tables.append(
        _Table(
            raw_start=offsets[start] + leading,
            block="\n".join(rows),
            rows=rows,
            caption=caption,
        )
    )


def _map_anchor(
    raw: str,
    normalized: str,
    raw_start: int,
    chunk: str,
    cursor: int,
) -> tuple[int, int] | None:
    normalized_chunk = normalize_ws(chunk)
    if not normalized_chunk:
        return None
    prefix = normalize_ws(raw[:raw_start])
    start = len(prefix) + (1 if prefix else 0)
    if normalized[start : start + len(normalized_chunk)] != normalized_chunk:
        start = normalized.find(normalized_chunk, cursor)
        if start < 0:
            return None
    return start, start + len(normalized_chunk)


def _parse_cells(row: str) -> list[str]:
    value = row.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [cell.strip() for cell in value.split("|")]


def _separator_row(cells: list[str]) -> bool:
    nonempty = [cell for cell in cells if cell]
    return bool(nonempty) and all(_SEPARATOR_CELL_RE.fullmatch(cell) for cell in nonempty)


def _region_for(path: tuple[str, ...]) -> str:
    text = " ".join(path).casefold()
    if "appendix" in text:
        return "appendix"
    if "related work" in text or "comparison" in text:
        return "related_work"
    if "limitation" in text or "bias" in text:
        return "limitations"
    if "risk" in text or "safety" in text or "misuse" in text:
        return "risk"
    if "environment" in text or "carbon" in text or "energy" in text:
        return "environment"
    if "evaluation" in text or "benchmark" in text or "result" in text:
        return "evaluation"
    if "training" in text or "data" in text or "adaptation" in text:
        return "training"
    if "model" in text or "architecture" in text:
        return "model_details"
    if "introduction" in text or "overview" in text:
        return "introduction"
    return "other"


__all__ = [
    "DocumentContext",
    "DocumentIndex",
    "REGIONS",
    "STRUCTURE_VERSION",
    "SectionAnchor",
    "TableAnchor",
    "build_document_index",
    "verify_document_index",
]
