"""Regenerate cards/ from a pipeline run directory.

    python scripts/publish_cards.py --run ../model-card-system/runs/roster12-a --out cards

Takes the published projection each run already wrote, names it after the model rather
than the bundle slug, and writes the JSON with its Markdown companion. The Markdown
carries the SHA-256 of the exact JSON bytes beside it, so a reader can check that the two
files describe the same card.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_cards.public_export import assert_public_projection  # noqa: E402
from model_cards.public_markdown import render_public_markdown  # noqa: E402
from model_cards.publication_schema import validate_publication_card  # noqa: E402


def card_name(model_id: str) -> str:
    return model_id.rsplit("/", 1)[-1].lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="pipeline run directory")
    ap.add_argument("--out", default="cards")
    ap.add_argument("--limit", type=int, default=0, help="0 publishes every card in the run")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for path in sorted(Path(args.run).glob("*.public.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        validate_publication_card(card)
        assert_public_projection(card)
        name = card_name(card["identity"]["model_id"])
        payload = json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (out / f"{name}.json").write_text(payload, encoding="utf-8")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        (out / f"{name}.md").write_text(
            render_public_markdown(card, json_filename=f"{name}.json", json_sha256=digest),
            encoding="utf-8")
        written.append(name)
        if args.limit and len(written) >= args.limit:
            break
    print(json.dumps({"published": len(written), "out": str(out), "cards": written},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
