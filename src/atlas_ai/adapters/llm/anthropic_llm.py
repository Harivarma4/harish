"""Real Claude (Anthropic) LLM adapter implementing ``LLMPort``.

Uses the official ``anthropic`` Python SDK. It needs credentials (an
``ANTHROPIC_API_KEY``, or an ``ant auth login`` profile) and outbound access to
the Anthropic API — so it runs where you deploy it, not in an offline sandbox.

Design mirrors the Kite adapter: the SDK client is *injectable* behind a minimal
``AnthropicClient`` Protocol, so the request-building and response-parsing logic
is fully unit-testable offline with a fake client. A refusal (``stop_reason ==
"refusal"``) is handled gracefully rather than crashing the pipeline.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from atlas_ai.application.ports.llm import LLMResponse

# Default to the latest, most capable Claude model. Override via config.
DEFAULT_MODEL = "claude-opus-5"

_DEFAULT_SYSTEM = (
    "You are a disciplined equity-research analyst for Indian markets. Respond in "
    "one concise, evidence-oriented sentence. This is research, not investment "
    "advice, and never a guarantee."
)
# Returned when the model declines, so the debate pipeline stays intact and honest.
_REFUSAL_TEXT = "(The model declined to generate this narrative.)"


@runtime_checkable
class _Messages(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


@runtime_checkable
class AnthropicClient(Protocol):
    """The subset of ``anthropic.Anthropic`` this adapter uses."""

    @property
    def messages(self) -> _Messages: ...


class AnthropicError(RuntimeError):
    """Raised for adapter-level failures talking to the Anthropic API."""


def _build_client(api_key: str) -> AnthropicClient:
    """Construct a real Anthropic client. Import is lazy so the base package does
    not depend on ``anthropic`` unless the Claude adapter is actually used."""
    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise AnthropicError(
            "The 'anthropic' package is required for the Claude LLM adapter. "
            "Install it with: pip install 'atlas-ai[anthropic]'"
        ) from exc
    # With no explicit key the SDK resolves ANTHROPIC_API_KEY or an `ant auth
    # login` profile from the environment.
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


class AnthropicLLM:
    """Generates narrative via Claude, satisfying ``LLMPort``."""

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2048,
        client: AnthropicClient | None = None,
    ) -> None:
        self._client = client if client is not None else _build_client(api_key)
        self._model = model
        self._max_tokens = max_tokens

    @property
    def model_version(self) -> str:
        return self._model

    def complete(
        self, prompt: str, *, system: str | None = None, prompt_version: str = "v1"
    ) -> LLMResponse:
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system or _DEFAULT_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK/network error uniformly
            raise AnthropicError(f"Anthropic completion failed: {exc}") from exc

        model = str(getattr(message, "model", self._model))
        if getattr(message, "stop_reason", None) == "refusal":
            return LLMResponse(text=_REFUSAL_TEXT, model=model, prompt_version=prompt_version)
        return LLMResponse(
            text=_extract_text(message), model=model, prompt_version=prompt_version
        )


def _extract_text(message: Any) -> str:
    """Join the text blocks of a Messages API response, ignoring thinking blocks."""
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(str(getattr(block, "text", "")))
    return " ".join(p.strip() for p in parts if p.strip()).strip()
