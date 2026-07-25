"""Options / derivatives domain model — an option chain and Greeks.

Pure, dependency-free value objects describing an equity/index option chain and
the sensitivities (Greeks) computed from it. The behaviour of a chain (PCR,
max-pain, IV skew, support/resistance) is derived by the options agent; the
Black-Scholes pricing math lives in the application layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from atlas_ai.domain.market import Instrument


class OptionRight(StrEnum):
    """The right conferred by an option contract."""

    CALL = "CALL"
    PUT = "PUT"


@dataclass(frozen=True, slots=True)
class OptionQuote:
    """A single option contract's market state at one strike."""

    strike: float
    right: OptionRight
    last_price: float
    open_interest: float
    implied_volatility: float  # annualised, as a fraction (0.25 = 25%)
    volume: float = 0.0
    change_in_oi: float = 0.0


@dataclass(frozen=True, slots=True)
class OptionChain:
    """One expiry's worth of calls and puts around a spot price."""

    instrument: Instrument
    spot: float
    expiry: date
    as_of: date
    calls: tuple[OptionQuote, ...]
    puts: tuple[OptionQuote, ...]

    def time_to_expiry_years(self) -> float:
        """Calendar time to expiry in years (floored just above zero)."""
        days = (self.expiry - self.as_of).days
        return max(days, 1) / 365.0

    def atm_strike(self) -> float:
        """The listed strike closest to spot."""
        strikes = {q.strike for q in (*self.calls, *self.puts)}
        return min(strikes, key=lambda k: abs(k - self.spot))


@dataclass(frozen=True, slots=True)
class Greeks:
    """First-order option sensitivities from Black-Scholes."""

    delta: float
    gamma: float
    vega: float   # per 1.00 (100%) change in volatility
    theta: float  # per calendar day
