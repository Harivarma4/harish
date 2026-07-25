"""Portfolio-construction agent — concentration, sector exposure, position fit."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.portfolio_agent import PortfolioAgent
from atlas_ai.application.ports.broker import Holding, Margins
from atlas_ai.domain.enums import AgentKind, Exchange, SignalStrength
from atlas_ai.domain.market import Instrument, Quote
from tests.conftest import make_candles, make_fundamentals


def _ctx(symbol: str) -> AgentContext:
    instrument = Instrument(symbol, Exchange.NSE)
    candles = make_candles([100.0 + (i % 4) for i in range(40)])
    quote = Quote(instrument, 100.0, 101.0, 99.0, 1_000_000)
    return AgentContext(instrument, quote, candles, make_fundamentals(instrument), 100_000.0)


class _FakeBroker:
    def __init__(self, holdings: list[Holding], *, net: float = 1_000_000.0,
                 cash: float = 500_000.0) -> None:
        self._holdings = holdings
        self._margins = Margins(net=net, available_cash=cash)

    def get_holdings(self) -> list[Holding]:
        return list(self._holdings)

    def get_margins(self) -> Margins:
        return self._margins


def _hold(symbol: str, qty: int, price: float) -> Holding:
    return Holding(Instrument(symbol, Exchange.NSE), qty, price, price)


def _signal(signals: tuple, name: str) -> SignalStrength:
    return next(s for s in signals if s.name == name).strength


def test_empty_book_is_clean_slate() -> None:
    report = PortfolioAgent(_FakeBroker([])).analyze(_ctx("RELIANCE"))
    assert report.agent is AgentKind.PORTFOLIO
    assert report.score.value >= 50.0
    assert _signal(report.signals, "PositionFit") is SignalStrength.BULLISH


def test_diversified_book_low_concentration() -> None:
    holdings = [_hold(sym, 100, 100.0) for sym in
                ("TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "MARUTI", "ITC")]
    report = PortfolioAgent(_FakeBroker(holdings)).analyze(_ctx("BHARTIARTL"))
    conc = _signal(report.signals, "BookConcentration")
    assert conc in {SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH}


def test_top_heavy_book_flags_concentration() -> None:
    # One name dominates the book -> high HHI -> concentration risk.
    holdings = [_hold("TCS", 1000, 3800.0), _hold("ITC", 10, 400.0)]
    report = PortfolioAgent(_FakeBroker(holdings)).analyze(_ctx("BHARTIARTL"))
    conc = _signal(report.signals, "BookConcentration")
    assert conc in {SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH}


def test_crowded_sector_is_cautioned() -> None:
    # Book is almost entirely banks; adding another bank is crowded.
    holdings = [_hold("HDFCBANK", 100, 1600.0), _hold("ICICIBANK", 100, 1100.0),
                _hold("SBIN", 100, 800.0)]
    report = PortfolioAgent(_FakeBroker(holdings)).analyze(_ctx("AXISBANK"))
    sector = _signal(report.signals, "SectorExposure")
    assert sector in {SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH}
    assert _signal(report.signals, "PositionFit") is SignalStrength.BEARISH


def test_adding_to_large_existing_position_is_bearish_fit() -> None:
    holdings = [_hold("RELIANCE", 100, 2800.0), _hold("ITC", 100, 400.0),
                _hold("TCS", 5, 3800.0)]
    report = PortfolioAgent(_FakeBroker(holdings)).analyze(_ctx("RELIANCE"))
    assert _signal(report.signals, "PositionFit") is SignalStrength.BEARISH


def test_score_in_range_and_signals_present() -> None:
    holdings = [_hold("TCS", 10, 3800.0), _hold("HDFCBANK", 25, 1650.0)]
    report = PortfolioAgent(_FakeBroker(holdings)).analyze(_ctx("MARUTI"))
    names = {s.name for s in report.signals}
    assert names == {"BookConcentration", "SectorExposure", "PositionFit"}
    assert 0.0 <= report.score.value <= 100.0
