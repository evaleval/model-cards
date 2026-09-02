"""Write deterministic public and private-audit JSON Schema resources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contract import build_contract_schema
from .publication_contract import build_publication_schema


def schema_text() -> str:
    """Return the canonical seven-section public Model Card schema."""

    return json.dumps(build_publication_schema(), ensure_ascii=False, indent=2) + "\n"


def audit_schema_text() -> str:
    """Return the richer local evidence-pipeline audit schema."""

    return json.dumps(build_contract_schema(), ensure_ascii=False, indent=2) + "\n"


def sync_schema(repository_root: str | Path) -> tuple[Path, Path, Path]:
    root = Path(repository_root)
    public_path = root / "schema" / "model-card.schema.json"
    package_public_path = (
        root / "src" / "model_cards" / "resources" / "model-card.schema.json"
    )
    package_audit_path = (
        root / "src" / "model_cards" / "resources" / "audit-card.schema.json"
    )
    public_text = schema_text()
    for path in (public_path, package_public_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(public_text, encoding="utf-8")
    package_audit_path.write_text(audit_schema_text(), encoding="utf-8")
    return public_path, package_public_path, package_audit_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository_root", nargs="?", default=Path(__file__).resolve().parents[3])
    args = parser.parse_args(argv)
    for path in sync_schema(args.repository_root):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
