"""Deterministic Hugging Face card frontmatter parsing."""

from __future__ import annotations

from typing import Any

import yaml


class _StringTimestampSafeLoader(yaml.SafeLoader):
    """SafeLoader variant that retains unquoted YAML timestamps as strings."""


_StringTimestampSafeLoader.yaml_implicit_resolvers = {
    leading: [
        (tag, expression)
        for tag, expression in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]
    for leading, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def parse_frontmatter(readme: str) -> dict[str, Any]:
    """Parse one YAML frontmatter block; malformed metadata fails closed to ``{}``."""

    if not readme.startswith("---"):
        return {}
    lines = readme.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
        value = yaml.load(
            "\n".join(lines[1:end]), Loader=_StringTimestampSafeLoader
        ) or {}
    except (StopIteration, yaml.YAMLError):
        return {}
    return value if isinstance(value, dict) else {}


__all__ = ["parse_frontmatter"]
