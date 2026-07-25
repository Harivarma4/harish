"""Options port — supplies the option chain used by the options agent."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from atlas_ai.domain.market import Instrument
from atlas_ai.domain.options import OptionChain


@runtime_checkable
class OptionsPort(Protocol):
    """Read access to the nearest-expiry option chain for an instrument.

    Returns ``None`` when no chain is available (e.g. the symbol has no listed
    options, or the feed is unreachable); the options agent treats that as a
    neutral, no-signal report rather than failing the recommendation.
    """

    def get_chain(self, instrument: Instrument) -> OptionChain | None: ...
