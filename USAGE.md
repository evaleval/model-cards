# Usage

Run these commands from a checkout of this repository, with a Python environment
activated and credentials configured for the model provider you intend to use.
Source collection can require credentials for gated repositories, and composition
uses hosted models that may incur charges.

```sh
pip install -e .               # contract, validator and Markdown export
pip install -e '.[generate]'   # installs the generator's composer at the pinned Git commit
pip install -e '.[eval]'       # plus the Anthropic client for the paid judge and screen

# Freeze the sources for an exact revision
modelcards collect 'allenai/OLMo-2-1124-7B@7df9a82518afdecae4e8c026b27adccc8c1f0032' \
    --bundle-dir bundles

# Compose the card using a paid model endpoint
modelcards compose 'allenai/OLMo-2-1124-7B@7df9a82518afdecae4e8c026b27adccc8c1f0032' \
    --bundle-dir bundles --llm-usage-log runs/olmo/llm_usage.jsonl \
    --out runs/olmo/olmo.json

# the published projection, the Markdown companion, and the inspector
modelcards export runs/olmo/olmo.json --kind public --format json --out cards/olmo.json
modelcards export runs/olmo/olmo.json --kind public --format markdown --out cards/olmo.md
modelcards inspect runs/olmo/olmo.json --format html --out olmo.html

# a list of targets, four to six at a time, each in its own process under a deadline
modelcards batch targets.txt --phase both --bundle-dir bundles --out runs/batch \
    --concurrency 5 --resume
```

The generation extra installs the composer directly from GitHub, so a sibling checkout
is optional. Non-editable installs (`pip install '.[generate]'`) work the same way. The
wheel carries the pin, and both its dependency requirement and that packaged copy are
built from the root `composer-pin.json` included in the source distribution. To update
the composer, update that one file (commit and interface hashes), then rebuild.

For composer development, install the intended Git checkout with
`pip install -e /path/to/auto-benchmarkcard` and keep it at the recorded commit. An importable composer
always takes precedence over an adjacent checkout. The dependency-light bridge can also
read a sibling `../auto-benchmarkcard` checkout when no composer is installed. Copying
package files or installing an untracked archive loses revision provenance and is refused.

Set credentials in the environment, a `.env` in the current working directory, or a file
selected by `MODELCARDS_ENV_FILE`. After installing, `python scripts/check_installation.py`
checks the pin and interface imports offline; add `--generator` to check all generator
imports without making model calls.

`modelcards inspect --format html` writes a self-contained, script-free page where every
field links to the exact span it came from, with the relation and the reason beside it,
and a section listing what was withheld and why. The inspection page stays local with the evidence ledger and source bundle.

Serving is configured from the environment (`src/model_cards/core/route.py`) and probed
before spending with `scripts/probe_route.py`. Every call runs with a server-enforced JSON
schema, a temperature of 0 and a per-stage token cap, and every composer call is written
to a usage log for each card, which records the reported token usage and cost. FactReasoner,
when enabled, calls its own route through its own client and is accounted for separately.
