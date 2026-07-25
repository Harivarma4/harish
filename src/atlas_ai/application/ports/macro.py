"""Macro port — supplies the macroeconomic snapshot used by the macro agent."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from atlas_ai.domain.macro import MacroIndicators


@runtime_checkable
class MacroPort(Protocol):
    """Read access to the current macroeconomic backdrop (market-wide)."""

    def get_snapshot(self) -> MacroIndicators: ...
