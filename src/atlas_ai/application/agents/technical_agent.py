"""Technical analysis agent — trend, momentum, and volatility signals from candles."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.indicators import atr, ema, macd, rsi, sma
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.value_objects import Score


class TechnicalAgent:
    """Computes real indicators (SMA/EMA/RSI/MACD/ATR) and a 0..100 score."""

    kind = AgentKind.TECHNICAL

    def analyze(self, ctx: AgentContext) -> AgentReport:
        closes = [c.close for c in ctx.candles]
        last = closes[-1] if closes else ctx.quote.last_price
        signals: list[Signal] = []

        sma50 = sma(closes, 50)
        sma200 = sma(closes, 200)
        if sma50 is not None and sma200 is not None:
            if sma50 > sma200:
                trend = SignalStrength.STRONG_BULLISH
            elif last > sma50:
                trend = SignalStrength.BULLISH
            else:
                trend = SignalStrength.BEARISH
            signals.append(
                Signal("Trend", trend, "50-DMA vs 200-DMA (golden/death cross)", sma50)
            )

        ema20 = ema(closes, 20)
        if ema20 is not None:
            strength = SignalStrength.BULLISH if last > ema20 else SignalStrength.BEARISH
            signals.append(Signal("EMA20", strength, "Price vs 20-EMA", ema20))

        r = rsi(closes)
        if r is not None:
            if r >= 70:
                strength = SignalStrength.BEARISH        # overbought
            elif r >= 55:
                strength = SignalStrength.BULLISH
            elif r <= 30:
                strength = SignalStrength.BULLISH         # oversold bounce
            elif r <= 45:
                strength = SignalStrength.BEARISH
            else:
                strength = SignalStrength.NEUTRAL
            signals.append(Signal("RSI", strength, "14-period RSI", round(r, 2)))

        m = macd(closes)
        if m is not None:
            _, _, hist = m
            strength = SignalStrength.BULLISH if hist > 0 else SignalStrength.BEARISH
            signals.append(Signal("MACD", strength, "MACD histogram", round(hist, 3)))

        a = atr(ctx.candles)
        if a is not None:
            vol_pct = (a / last) * 100.0 if last else 0.0
            strength = (
                SignalStrength.NEUTRAL if vol_pct < 3 else SignalStrength.BEARISH
            )
            signals.append(Signal("ATR%", strength, "Volatility as % of price", round(vol_pct, 2)))

        if not signals:
            signals.append(
                Signal("Data", SignalStrength.NEUTRAL, "Insufficient history for indicators")
            )

        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))
        rationale = "; ".join(f"{s.name}={s.value}" for s in signals if s.value is not None)
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=tuple(signals),
            rationale=f"Technical read: {rationale}.",
            assumptions=("Price history is clean and split/dividend-adjusted.",),
            risks=("Technical signals can whipsaw; they describe price, not value.",),
        )
