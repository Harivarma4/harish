"""Governance metadata attached to every model output for auditability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class GovernanceMetadata:
    """Reproducibility and audit envelope for a recommendation.

    Records exactly which models/prompts produced the output and when, plus a
    human-readable summary of the reasoning path.
    """

    model_version: str
    prompt_version: str
    pipeline_version: str
    reasoning_summary: str
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.reasoning_summary.strip():
            raise ValueError("reasoning_summary must not be empty")
