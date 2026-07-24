"""File-backed fundamentals provider."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas_ai.adapters.fundamentals.file_fundamentals import (
    FileFundamentalsProvider,
    FundamentalsNotFound,
)
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

INSTRUMENT = Instrument("RELIANCE", Exchange.NSE)


def _entry() -> dict[str, float]:
    return dict(
        market_cap_cr=1_900_000, pe=24.0, pb=2.3, roe_pct=9.0, roce_pct=11.0,
        debt_to_equity=0.42, operating_margin_pct=17.0, net_margin_pct=8.0,
        revenue_growth_pct=10.0, earnings_growth_pct=11.0, dividend_yield_pct=0.4,
        promoter_holding_pct=50.3, promoter_pledge_pct=0.0,
    )


def _write(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "fundamentals.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_reads_by_full_key(tmp_path: Path) -> None:
    path = _write(tmp_path, {"NSE:RELIANCE": _entry()})
    f = FileFundamentalsProvider(path).get_fundamentals(INSTRUMENT)
    assert f.roe_pct == 9.0
    assert f.pe == 24.0


def test_reads_by_bare_symbol(tmp_path: Path) -> None:
    path = _write(tmp_path, {"reliance": _entry()})
    f = FileFundamentalsProvider(path).get_fundamentals(INSTRUMENT)
    assert f.debt_to_equity == 0.42


def test_missing_symbol_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, {"NSE:TCS": _entry()})
    with pytest.raises(FundamentalsNotFound):
        FileFundamentalsProvider(path).get_fundamentals(INSTRUMENT)


def test_missing_field_raises(tmp_path: Path) -> None:
    incomplete = _entry()
    del incomplete["roe_pct"]
    path = _write(tmp_path, {"NSE:RELIANCE": incomplete})
    with pytest.raises(ValueError, match="roe_pct"):
        FileFundamentalsProvider(path).get_fundamentals(INSTRUMENT)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        FileFundamentalsProvider(tmp_path / "nope.json")
