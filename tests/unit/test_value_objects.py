"""Domain value-object invariants."""

from __future__ import annotations

import pytest

from atlas_ai.domain.value_objects import Confidence, Money, Score


@pytest.mark.parametrize("bad", [-0.01, 1.01, 5.0])
def test_confidence_rejects_out_of_range(bad: float) -> None:
    with pytest.raises(ValueError):
        Confidence(bad)


def test_confidence_as_percent() -> None:
    assert Confidence(0.734).as_percent() == 73.4


@pytest.mark.parametrize("bad", [-1.0, 100.1])
def test_score_rejects_out_of_range(bad: float) -> None:
    with pytest.raises(ValueError):
        Score(bad)


def test_score_as_unit() -> None:
    assert Score(75.0).as_unit() == 0.75


def test_money_rejects_negative() -> None:
    with pytest.raises(ValueError):
        Money(-1.0)
