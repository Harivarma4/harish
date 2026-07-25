"""Deterministic, offline mock option chain.

Builds a plausible, internally-consistent chain around a symbol-seeded spot so
the options agent runs reproducibly offline. Illustrative only — the real NSE
adapter implements the same ``OptionsPort`` for live data.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

import numpy as np

from atlas_ai.domain.market import Instrument
from atlas_ai.domain.options import OptionChain, OptionQuote, OptionRight

_STEP = 50.0  # strike spacing


def _seed(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16)


class MockOptions:
    """Satisfies ``OptionsPort`` with a deterministic synthetic chain."""

    def __init__(self, *, today: date | None = None, strikes: int = 11) -> None:
        self._today = today or date(2026, 1, 1)
        self._strikes = strikes

    def get_chain(self, instrument: Instrument) -> OptionChain | None:
        rng = np.random.default_rng(_seed(instrument.symbol))
        spot = float(round(500.0 + rng.uniform(0.0, 2000.0), 0))
        atm = round(spot / _STEP) * _STEP
        half = self._strikes // 2
        strikes = [atm + (i - half) * _STEP for i in range(self._strikes)]
        base_iv = float(rng.uniform(0.18, 0.35))

        calls: list[OptionQuote] = []
        puts: list[OptionQuote] = []
        for k in strikes:
            moneyness = (k - spot) / spot
            # OI peaks near the money; puts a touch heavier (typical hedging).
            call_oi = float(round(max(0.0, 1e6 * np.exp(-((moneyness + 0.02) ** 2) / 0.004))))
            put_oi = float(round(max(0.0, 1.1e6 * np.exp(-((moneyness - 0.02) ** 2) / 0.004))))
            # Volatility smile: wings richer; puts carry a small extra skew.
            call_iv = round(base_iv + 0.6 * moneyness**2, 4)
            put_iv = round(base_iv + 0.6 * moneyness**2 + 0.01, 4)
            calls.append(
                OptionQuote(
                    strike=k, right=OptionRight.CALL,
                    last_price=round(max(spot - k, 0.0) + base_iv * spot * 0.04, 2),
                    open_interest=call_oi, implied_volatility=call_iv,
                    volume=call_oi * 0.2,
                )
            )
            puts.append(
                OptionQuote(
                    strike=k, right=OptionRight.PUT,
                    last_price=round(max(k - spot, 0.0) + base_iv * spot * 0.04, 2),
                    open_interest=put_oi, implied_volatility=put_iv,
                    volume=put_oi * 0.2,
                )
            )
        return OptionChain(
            instrument=instrument,
            spot=spot,
            expiry=self._today + timedelta(days=28),
            as_of=self._today,
            calls=tuple(calls),
            puts=tuple(puts),
        )
