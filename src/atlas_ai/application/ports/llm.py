"""LLM port — narrative generation for debate and evidence synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """A model completion plus the metadata needed for governance/audit."""

    text: str
    model: str
    prompt_version: str


@runtime_checkable
class LLMPort(Protocol):
    """Generates text from a prompt.

    Implementations must be deterministic given a fixed prompt in mock mode so
    that recommendations are reproducible and auditable.
    """

    @property
    def model_version(self) -> str:
        """Identifier of the underlying model, recorded in governance metadata."""
        ...

    def complete(
        self, prompt: str, *, system: str | None = None, prompt_version: str = "v1"
    ) -> LLMResponse: ...
