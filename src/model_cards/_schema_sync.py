"""Write deterministic JSON Schema copies from the canonical contract source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contract import build_contract_schema


def schema_text() -> str:
    return json.dumps(build_contract_schema(), ensure_ascii=False, indent=2) + "\n"


def sync_schema(repository_root: str | Path) -> tuple[Path, Path]:
    root = Path(repository_root)
    public_path = root / "schema" / "model-card.schema.json"
    package_path = root / "src" / "model_cards" / "resources" / "model-card.schema.json"
    text = schema_text()
    for path in (public_path, package_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return public_path, package_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository_root", nargs="?", default=Path(__file__).resolve().parents[3])
    args = parser.parse_args(argv)
    for path in sync_schema(args.repository_root):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
