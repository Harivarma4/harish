"""Risk-assessment domain entities."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.domain.value_objects import Money, Percent


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Quantified position-level risk for a proposed trade.

    All prices are per-share in INR. ``value_at_risk_pct`` is a one-period,
    historical-simulation VaR at the stated confidence level.
    """

    entry_price: float
    stop_loss: float
    target_price: float
    quantity: int
    capital_at_risk: Money
    position_value: Money
    reward_to_risk: float
    value_at_risk_pct: Percent
    var_confidence: float

    def __post_init__(self) -> None:
        if self.entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")

    @property
    def risk_per_share(self) -> float:
        return abs(self.entry_price - self.stop_loss)

    @property
    def reward_per_share(self) -> float:
        return abs(self.target_price - self.entry_price)
