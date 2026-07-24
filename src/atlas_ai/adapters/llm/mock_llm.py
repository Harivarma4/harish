"""Deterministic mock LLM — templated narrative so the pipeline runs offline.

Given identical prompts it always returns identical text, which keeps
recommendations reproducible and auditable. Real OpenAI/Claude/Gemini adapters
implement the same ``LLMPort`` and slot in via configuration later.
"""

from __future__ import annotations

from atlas_ai.application.ports.llm import LLMResponse

MODEL_NAME = "atlas-mock-llm-v1"


class MockLLM:
    """Rule-based narrator satisfying ``LLMPort`` without any network call."""

    @property
    def model_version(self) -> str:
        return MODEL_NAME

    def complete(
        self, prompt: str, *, system: str | None = None, prompt_version: str = "v1"
    ) -> LLMResponse:
        text = self._narrate(prompt, system or "")
        return LLMResponse(text=text, model=MODEL_NAME, prompt_version=prompt_version)

    def _narrate(self, prompt: str, system: str) -> str:
        lowered = prompt.lower()
        # Check the judge branch first: its prompt mentions "bull and bear cases",
        # which would otherwise match the bear branch below.
        if "judge" in lowered or "reconcile" in lowered:
            leaning = self._extract_leaning(prompt)
            if leaning > 0.15:
                stance = "the bull case is better supported, but not decisively"
            elif leaning < -0.15:
                stance = "the bear case carries more weight on current evidence"
            else:
                stance = "the evidence is balanced and warrants patience"
            return (
                f"On balance {stance}; treat this as probabilistic research, size "
                "accordingly, and respect the stop."
            )
        if "bull case" in lowered:
            return (
                "The constructive case rests on the supportive signals above: "
                "quality and momentum align, and the risk plan offers favourable asymmetry."
            )
        if "bear case" in lowered:
            return (
                "The cautionary case flags the countervailing signals above: valuation, "
                "leverage, or momentum could reverse the thesis, so position sizing matters."
            )
        return "Analysis synthesized from the provided signals."

    @staticmethod
    def _extract_leaning(prompt: str) -> float:
        # Parse a token like "leaning is +0.42" if present; default neutral.
        for token in prompt.replace(",", " ").split():
            cleaned = token.strip(".")
            if cleaned.startswith(("+", "-")) and cleaned[1:].replace(".", "", 1).isdigit():
                try:
                    return float(cleaned)
                except ValueError:
                    continue
        return 0.0
