"""Options / derivatives agent — PCR, max-pain, IV skew, and no-chain handling."""

from __future__ import annotations

from datetime import date

from atlas_ai.adapters.options.mock_options import MockOptions
from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.options_agent import OptionsAgent
from atlas_ai.domain.enums import AgentKind, Exchange, SignalStrength
from atlas_ai.domain.market import Instrument, Quote
from atlas_ai.domain.options import OptionChain, OptionQuote, OptionRight
from tests.conftest import make_candles, make_fundamentals

_INSTRUMENT = Instrument("RELIANCE", Exchange.NSE)


def _ctx() -> AgentContext:
    candles = make_candles([100.0 + (i % 5) for i in range(60)])
    quote = Quote(_INSTRUMENT, 100.0, 101.0, 99.0, 1_000_000)
    return AgentContext(_INSTRUMENT, quote, candles, make_fundamentals(_INSTRUMENT), 100_000.0)


def _chain(rows: list[tuple[float, float, float, float, float]], spot: float) -> OptionChain:
    """rows: (strike, call_oi, put_oi, call_iv, put_iv)."""
    calls = tuple(
        OptionQuote(strike=s, right=OptionRight.CALL, last_price=1.0,
                    open_interest=c_oi, implied_volatility=c_iv)
        for s, c_oi, _p_oi, c_iv, _p_iv in rows
    )
    puts = tuple(
        OptionQuote(strike=s, right=OptionRight.PUT, last_price=1.0,
                    open_interest=p_oi, implied_volatility=p_iv)
        for s, _c_oi, p_oi, _c_iv, p_iv in rows
    )
    return OptionChain(
        instrument=_INSTRUMENT, spot=spot, expiry=date(2026, 2, 1),
        as_of=date(2026, 1, 4), calls=calls, puts=puts,
    )


class _FixedOptions:
    def __init__(self, chain: OptionChain | None) -> None:
        self._chain = chain

    def get_chain(self, instrument: Instrument) -> OptionChain | None:
        return self._chain


def _signal(report_signals: tuple, name: str) -> SignalStrength:
    return next(s for s in report_signals if s.name == name).strength


def test_no_chain_is_neutral() -> None:
    report = OptionsAgent(_FixedOptions(None)).analyze(_ctx())
    assert report.agent is AgentKind.OPTIONS
    assert report.score.value == 50.0
    assert _signal(report.signals, "OptionChain") is SignalStrength.NEUTRAL


def test_high_pcr_is_contrarian_bullish() -> None:
    rows = [(90 + i * 5, 100_000.0, 400_000.0, 0.25, 0.25) for i in range(5)]
    report = OptionsAgent(_FixedOptions(_chain(rows, 100.0))).analyze(_ctx())
    assert _signal(report.signals, "PutCallRatio") in {
        SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH
    }


def test_low_pcr_is_contrarian_bearish() -> None:
    rows = [(90 + i * 5, 400_000.0, 100_000.0, 0.25, 0.25) for i in range(5)]
    report = OptionsAgent(_FixedOptions(_chain(rows, 100.0))).analyze(_ctx())
    assert _signal(report.signals, "PutCallRatio") in {
        SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH
    }


def test_max_pain_above_spot_is_bullish() -> None:
    # OI concentrated at 108 (above spot 100) pulls max-pain up.
    rows = [(s, oi, oi, 0.25, 0.25) for s, oi in
            [(96, 0.0), (100, 0.0), (104, 0.0), (108, 500_000.0)]]
    report = OptionsAgent(_FixedOptions(_chain(rows, 100.0))).analyze(_ctx())
    assert _signal(report.signals, "MaxPain") in {
        SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH
    }


def test_max_pain_below_spot_is_bearish() -> None:
    rows = [(s, oi, oi, 0.25, 0.25) for s, oi in
            [(92, 500_000.0), (96, 0.0), (100, 0.0), (104, 0.0)]]
    report = OptionsAgent(_FixedOptions(_chain(rows, 100.0))).analyze(_ctx())
    assert _signal(report.signals, "MaxPain") in {
        SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH
    }


def test_rich_put_skew_is_risk_off() -> None:
    # Puts markedly more expensive than calls near the money -> bearish.
    rows = [(90 + i * 5, 200_000.0, 200_000.0, 0.22, 0.30) for i in range(5)]
    report = OptionsAgent(_FixedOptions(_chain(rows, 100.0))).analyze(_ctx())
    assert _signal(report.signals, "IVSkew") in {
        SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH
    }


def test_mock_adapter_produces_a_scoreable_report() -> None:
    report = OptionsAgent(MockOptions(today=date(2026, 1, 4))).analyze(_ctx())
    assert report.agent is AgentKind.OPTIONS
    assert 0.0 <= report.score.value <= 100.0
    names = {s.name for s in report.signals}
    assert names == {"PutCallRatio", "MaxPain", "IVSkew"}


def test_mock_adapter_is_deterministic() -> None:
    a = MockOptions().get_chain(_INSTRUMENT)
    b = MockOptions().get_chain(_INSTRUMENT)
    assert a is not None and b is not None
    assert a.spot == b.spot
    assert [c.open_interest for c in a.calls] == [c.open_interest for c in b.calls]
