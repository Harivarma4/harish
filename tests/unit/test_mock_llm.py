"""Mock LLM narration routing (deterministic, offline)."""

from __future__ import annotations

from atlas_ai.adapters.llm.mock_llm import MockLLM


def test_bull_bear_judge_are_distinct() -> None:
    llm = MockLLM()
    bull = llm.complete("Argue the BULL case for RELIANCE in one sentence given: X").text
    bear = llm.complete("Argue the BEAR case for RELIANCE in one sentence given: Y").text
    # The judge prompt mentions "bull and bear cases" — it must not be mistaken
    # for the bear branch (regression guard).
    verdict = llm.complete(
        "As an impartial judge, reconcile the bull and bear cases for RELIANCE. "
        "Net analytical leaning is +0.40 on [-1,1]. Give a one-sentence verdict."
    ).text
    assert bull != bear != verdict
    assert verdict != bull
    assert "on balance" in verdict.lower()


def test_judge_reflects_leaning_direction() -> None:
    llm = MockLLM()
    bullish = llm.complete("judge: reconcile; leaning is +0.50").text
    bearish = llm.complete("judge: reconcile; leaning is -0.50").text
    assert "bull case" in bullish.lower()
    assert "bear case" in bearish.lower()


def test_deterministic() -> None:
    llm = MockLLM()
    p = "Argue the BULL case for TCS in one sentence given: Z"
    assert llm.complete(p).text == llm.complete(p).text
