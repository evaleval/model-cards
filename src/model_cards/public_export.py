"""The public export boundary: what a local artifact may not carry across it.

A generated card is produced next to a binding ledger, a source bundle, a usage log and
a local filesystem. None of that belongs in a published card, and the ways it leaks are
mechanical: a key that names a private structure, a path out of somebody's home
directory, a credential pasted into a value. This guard rejects all three by shape,
before anything is written.

It is deliberately independent of the contract check. A card can carry exactly the
agreed fields and still have a home directory inside one of them.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


BLOCKED_KEYS = frozenset(
    {
        "authorization_sha256",
        "bindings",
        "context_after",
        "context_before",
        "contract_version",
        "cost_ledger",
        "evidence",
        "environmental_information",
        "exact_text",
        "lifecycle",
        "omission_review_events",
        "prompt",
        "provenance",
        "provider_trace",
        "request",
        "response",
        "reviews",
        "route",
        "snapshot_path",
        "source_bundle",
        "source_content",
        "source_text",
        "surrounding_context",
        "usage",
        "use_and_risk",
        "validation",
        "validation_checks",
    }
)
SENSITIVE_TEXT = re.compile(
    r"(?ix)(?:"
    r"/Users/|/home/|/private/|/tmp/|/var/tmp/|/var/folders/|"
    r"[A-Z]:[\\/]Users[\\/]|(?:^|\s)~[/\\]|file://|"
    r"\.cache(?:/|\\)|\.codex(?:/|\\)|\.claude(?:/|\\)|"
    r"\.pyenv(?:/|\\)|\.venv(?:/|\\)|"
    r"(?:^|[/\\])vault(?:[/\\]|$)|"
    r"attachments/|pasted-text|private-candidate-evidence|"
    r"source-freeze/|run-state|localhost|127\.0\.0\.1|openrouter|"
    r"https?://[^/@\s]+:[^/@\s]+@|"
    r"api[_-]?key|bearer\s+|sk-[A-Za-z0-9_-]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}"
    r")"
)


class PublicExportError(ValueError):
    """A local artifact cannot cross the public export boundary."""


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def assert_public_projection(value: Any) -> None:
    """Reject private artifact structure, local paths, credentials, and traces."""

    for path, item in _walk(value):
        if isinstance(item, dict):
            found = BLOCKED_KEYS.intersection(item)
            if found:
                raise PublicExportError(
                    f"blocked key at {path}: {', '.join(sorted(found))}"
                )
            for key in item:
                if isinstance(key, str) and SENSITIVE_TEXT.search(key):
                    raise PublicExportError(f"sensitive key at {path}")
        elif isinstance(item, str) and SENSITIVE_TEXT.search(item):
            raise PublicExportError(f"sensitive text at {path}")



__all__ = ["BLOCKED_KEYS", "PublicExportError", "SENSITIVE_TEXT",
           "assert_public_projection"]
