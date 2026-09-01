"""Evidence-bound model cards for exact model revisions."""

from .artifact import CardArtifact, project_card
from .bindings import build_artifact, verify_artifact_sources
from .models import (
    Binding,
    Disposition,
    LifecycleStatus,
    RelationToTarget,
    ReviewAction,
    ReviewEvent,
    SourceDocument,
    SourceRole,
    TargetIdentity,
    ValidationCheck,
    ValidationCheckStatus,
)
from .orchestration import (
    OrchestrationError,
    ProviderOrchestrationResult,
    run_provider_assisted_pipeline,
)
from .pipeline import PipelineError, PipelineResult, run_offline_pipeline
from .quality_report import QualityReport, build_quality_report
from .run_summary import RunSummaryArtifacts, write_run_summaries
from .source_state import ImmutableSourceState, load_source_state

__all__ = [
    "Binding",
    "CardArtifact",
    "Disposition",
    "LifecycleStatus",
    "ImmutableSourceState",
    "OrchestrationError",
    "PipelineError",
    "PipelineResult",
    "ProviderOrchestrationResult",
    "QualityReport",
    "RelationToTarget",
    "ReviewAction",
    "ReviewEvent",
    "SourceDocument",
    "SourceRole",
    "TargetIdentity",
    "ValidationCheck",
    "ValidationCheckStatus",
    "build_artifact",
    "build_quality_report",
    "load_source_state",
    "project_card",
    "run_offline_pipeline",
    "run_provider_assisted_pipeline",
    "verify_artifact_sources",
    "RunSummaryArtifacts",
    "write_run_summaries",
]

__version__ = "0.1.0"
