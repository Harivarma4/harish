"""AnthropicLLM adapter logic, exercised offline via a fake Anthropic client.

The real Anthropic API can't be reached in tests, so we inject a fake client
that mimics the ``messages.create`` response shape and assert the adapter builds
the request correctly and parses the response (including refusals).
"""

from __future__ import annotations

from typing import Any

import pytest

from atlas_ai.adapters.llm.anthropic_llm import (
    DEFAULT_MODEL,
    AnthropicError,
    AnthropicLLM,
)


class FakeBlock:
    def __init__(self, type_: str, text: str = "") -> None:
        self.type = type_
        self.text = text


class FakeMessage:
    def __init__(self, blocks: list[FakeBlock], *, model: str, stop_reason: str) -> None:
        self.content = blocks
        self.model = model
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, message: FakeMessage) -> None:
        self._message = message
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        return self._message


class FakeClient:
    def __init__(self, message: FakeMessage) -> None:
        self.messages = FakeMessages(message)


def _client(blocks: list[FakeBlock], *, stop_reason: str = "end_turn") -> FakeClient:
    return FakeClient(FakeMessage(blocks, model="claude-opus-5", stop_reason=stop_reason))


def test_extracts_text_and_ignores_thinking() -> None:
    client = _client(
        [FakeBlock("thinking", "internal"), FakeBlock("text", "The bull case is strong.")]
    )
    llm = AnthropicLLM(client=client)
    resp = llm.complete("Argue the bull case", system="You are an analyst.")
    assert resp.text == "The bull case is strong."
    assert resp.model == "claude-opus-5"


def test_request_is_well_formed() -> None:
    client = _client([FakeBlock("text", "ok")])
    llm = AnthropicLLM(client=client, model="claude-sonnet-5", max_tokens=1234)
    llm.complete("hello", system="sys", prompt_version="debate-v1")
    call = client.messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert call["max_tokens"] == 1234
    assert call["system"] == "sys"
    assert call["messages"] == [{"role": "user", "content": "hello"}]


def test_default_system_used_when_none() -> None:
    client = _client([FakeBlock("text", "ok")])
    AnthropicLLM(client=client).complete("hello")
    assert client.messages.calls[0]["system"]  # non-empty default


def test_refusal_returns_neutral_text_not_content() -> None:
    client = _client([FakeBlock("text", "should not surface")], stop_reason="refusal")
    resp = AnthropicLLM(client=client).complete("...")
    assert "declined" in resp.text.lower()
    assert "should not surface" not in resp.text


def test_sdk_error_is_wrapped() -> None:
    class Boom:
        @property
        def messages(self) -> Any:
            raise RuntimeError("boom")

    with pytest.raises(AnthropicError):
        AnthropicLLM(client=Boom()).complete("x")


def test_model_version_reports_configured_model() -> None:
    llm = AnthropicLLM(client=_client([FakeBlock("text", "ok")]), model="claude-opus-5")
    assert llm.model_version == "claude-opus-5"
    assert DEFAULT_MODEL == "claude-opus-5"


def test_construction_without_client_or_sdk_raises() -> None:
    # In this environment the `anthropic` package is not installed (it's an
    # optional extra), so building a real client fails with AnthropicError.
    with pytest.raises(AnthropicError):
        AnthropicLLM()
