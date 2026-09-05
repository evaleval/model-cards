"""A plain reading view of a markdown README for verbatim-quote extraction.

The verifier demands byte-exact quotes (after whitespace normalization). A model card
README is dense with links, emphasis markers and HTML, and the extractor drops those
when it quotes, so 4 of 13, 7 of 20 and 7 of 18 README quotes came back "not verbatim"
on the OLMo-2 Instruct smoke while the paper (docling text) verified 100%. This view
removes the markup deterministically and is recorded in the bundle as a derived file
next to the raw README, so every span still points at recorded bytes.

Rule markdown_plain_v1:
  - images ![alt](url) -> alt; links [text](url) -> text; autolinks <http://x> -> http://x
  - HTML tags removed, their inner text kept; common entities decoded
  - **bold**, __bold__, *italic* and `code` markers removed (underscore italics are left
    alone: they collide with identifiers such as olmo_2_mix)
  - tables, headings, list markers and line breaks are kept
"""

from __future__ import annotations

import html
import re

RULE = "markdown_plain_v1"

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_AUTOLINK_RE = re.compile(r"<(https?://[^>\s]+)>")
_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
_BOLD_US_RE = re.compile(r"__(.+?)__", re.S)
_ITALIC_RE = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
_CODE_RE = re.compile(r"`([^`\n]*)`")
_FENCE_RE = re.compile(r"^```[^\n]*$", re.M)


def markdown_plain(text: str) -> str:
    """The plain reading view of markdown text (see the module docstring)."""
    out = text or ""
    out = _COMMENT_RE.sub("", out)
    out = _IMAGE_RE.sub(r"\1", out)
    out = _LINK_RE.sub(r"\1", out)
    out = _AUTOLINK_RE.sub(r"\1", out)
    out = _TAG_RE.sub("", out)
    out = html.unescape(out)
    out = _FENCE_RE.sub("", out)
    out = _BOLD_RE.sub(r"\1", out)
    out = _BOLD_US_RE.sub(r"\1", out)
    out = _ITALIC_RE.sub(r"\1", out)
    out = _CODE_RE.sub(r"\1", out)
    return out
