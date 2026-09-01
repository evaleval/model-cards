"""Evidence-bound model cards for exact model revisions."""

from .artifact import CardArtifact, project_card
from .bindings import build_artifact, verify_artifact_sources
from .models import (
    Binding,
    Disposition,
    RelationToTarget,
    ReviewAction,
    ReviewEvent,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)

__all__ = [
    "Binding",
    "CardArtifact",
    "Disposition",
    "RelationToTarget",
    "ReviewAction",
    "ReviewEvent",
    "SourceDocument",
    "SourceRole",
    "TargetIdentity",
    "build_artifact",
    "project_card",
    "verify_artifact_sources",
]

__version__ = "0.1.0"
