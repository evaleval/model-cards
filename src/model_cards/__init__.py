"""Evidence-bound model cards for exact Hugging Face model revisions.

The package has two halves that stay apart on purpose.

The publication surface is what a reader of a card touches: the seven-section, 33-field
contract, its JSON Schema, the deterministic Markdown renderer, the export guard that
refuses to let a local path or a credential cross the boundary, and the Hugging Face
source adapter that freezes a snapshot at an exact commit.

`model_cards.core` is the generator: it collects the sources for one model_id@revision,
extracts verbatim quotes, resolves what each quote is about, gates what may reach which
field, writes the card from the accepted evidence only, and keeps one binding record per
value it accepted AND per value it refused. It imports the contract from this package, so
there is one definition of what a card is.
"""

from .hf_adapter import HuggingFaceAdapterError, HuggingFaceHubAdapter
from .public_export import PublicExportError, assert_public_projection
from .public_markdown import render_public_markdown
from .publication_contract import (
    FIELD_PATHS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    PUBLICATION_SECTIONS,
    SECTION_FIELDS,
    build_publication_schema,
)
from .publication_schema import blank_publication_card, validate_publication_card

__all__ = [
    "FIELD_PATHS",
    "HuggingFaceAdapterError",
    "HuggingFaceHubAdapter",
    "NOT_APPLICABLE",
    "NOT_SPECIFIED",
    "PUBLICATION_SECTIONS",
    "PublicExportError",
    "SECTION_FIELDS",
    "assert_public_projection",
    "blank_publication_card",
    "build_publication_schema",
    "render_public_markdown",
    "validate_publication_card",
]

__version__ = "0.2.0"
