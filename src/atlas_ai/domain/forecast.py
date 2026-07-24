"""Probabilistic outlook — the output of the (non-deterministic) prediction engine."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.domain.value_objects import Confidence, Percent


@dataclass(frozen=True, slots=True)
class ProbabilisticOutlook:
    """A distributional, non-deterministic forecast.

    The platform never emits point predictions. This captures the probability of
    a favourable outcome over the horizon, an expected CAGR with a confidence
    interval, and the calibrated confidence in the estimate itself.
    """

    probability_favourable: float
    expected_cagr: Percent
    cagr_p05: Percent
    cagr_p95: Percent
    confidence: Confidence
    simulations: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability_favourable <= 1.0:
            raise ValueError("probability_favourable must be in [0, 1]")
        if self.simulations <= 0:
            raise ValueError("simulations must be positive")
        if self.cagr_p05.value > self.cagr_p95.value:
            raise ValueError("cagr_p05 cannot exceed cagr_p95")
