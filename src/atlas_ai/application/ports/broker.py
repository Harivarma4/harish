"""Broker port — portfolio access and (future, user-authorized) execution.

Starts with Zerodha Kite Connect in mind. Order placement is intentionally
excluded from this foundation build; only read access is exposed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from atlas_ai.domain.market import Instrument


@dataclass(frozen=True, slots=True)
class Holding:
    """A single portfolio holding."""

    instrument: Instrument
    quantity: int
    average_price: float
    last_price: float

    @property
    def pnl(self) -> float:
        return (self.last_price - self.average_price) * self.quantity


@dataclass(frozen=True, slots=True)
class Margins:
    """Available trading capital."""

    net: float
    available_cash: float


@runtime_checkable
class BrokerPort(Protocol):
    """Read-only broker access for portfolio-aware research."""

    def get_holdings(self) -> list[Holding]: ...

    def get_margins(self) -> Margins: ...
