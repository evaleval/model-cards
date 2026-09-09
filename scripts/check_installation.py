"""Offline installation smoke check; run from any working directory after installing."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", action="store_true", help="also import the full generator")
    args = parser.parse_args()

    from model_cards.core.bridge import load_composer_bridge

    bridge = load_composer_bridge()
    assert bridge.verify_span("a b", "a  b") == (0, 3)
    assert bridge.structural_anchor("# Results\na b", 10)["region"] == "results"

    from auto_benchmarkcard.tools.composer import field_spec

    assert Path(field_spec.__file__).resolve().is_relative_to(bridge.source_root)
    if args.generator:
        from model_cards.core import compose_llm

        assert Path(compose_llm.C.__file__).resolve().is_relative_to(bridge.source_root)
    # Recheck origins after normal package imports as well as dependency-light loading.
    assert load_composer_bridge().source_root == bridge.source_root
    print(f"Composer installation verified at {bridge.commit}")


if __name__ == "__main__":
    main()
