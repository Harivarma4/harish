"""Options / derivatives agent — positioning and sentiment from the option chain.

Reads the nearest-expiry option chain through the injected ``OptionsPort`` and
derives well-known derivatives signals:

- **PCR** (put/call open-interest ratio) — a contrarian sentiment gauge:
  excessive put buying (high PCR) is over-bearish, low PCR is complacency.
- **Max pain** — the strike that inflicts the greatest loss on option buyers;
  price tends to gravitate toward it into expiry, so its distance from spot
  implies a pull.
- **IV skew** — put vs call implied volatility near the money; a rich put skew
  signals hedging demand / risk-off.

It also computes ATM Greeks with real Black-Scholes math for the rationale. When
no chain is available the agent emits a neutral, no-signal report rather than
failing the recommendation.
"""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.ports.options import OptionsPort
from atlas_ai.application.pricing import black_scholes as bs
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.options import OptionChain, OptionQuote, OptionRight
from atlas_ai.domain.value_objects import Score

# Risk-free rate used for Greeks (short-dated; ~India T-bill). Documented constant.
_RISK_FREE = 0.065

_SCALE = (
    SignalStrength.STRONG_BEARISH,
    SignalStrength.BEARISH,
    SignalStrength.NEUTRAL,
    SignalStrength.BULLISH,
    SignalStrength.STRONG_BULLISH,
)


def _grade(
    value: float, thresholds: tuple[float, float, float, float], *, higher_is_better: bool
) -> SignalStrength:
    t0, t1, t2, t3 = thresholds
    rank = 0 if value < t0 else 1 if value < t1 else 2 if value < t2 else 3 if value < t3 else 4
    scale = _SCALE if higher_is_better else _SCALE[::-1]
    return scale[rank]


class OptionsAgent:
    """Scores derivatives positioning; contrarian on sentiment extremes."""

    kind = AgentKind.OPTIONS

    def __init__(self, options: OptionsPort) -> None:
        self._options = options

    def analyze(self, ctx: AgentContext) -> AgentReport:
        chain = self._options.get_chain(ctx.instrument)
        if chain is None or not chain.calls or not chain.puts:
            return self._no_chain_report()

        pcr_sig, pcr = self._pcr(chain)
        pain_sig, max_pain = self._max_pain(chain)
        skew_sig, skew = self._iv_skew(chain)
        signals = (pcr_sig, pain_sig, skew_sig)

        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))
        rationale = (
            f"Derivatives ({chain.expiry}): PCR {pcr:.2f}, max-pain "
            f"{max_pain:.0f} vs spot {chain.spot:.0f}, put-call IV skew "
            f"{skew:+.1f} pts. {self._greeks_note(chain)} "
            f"{self._oi_walls(chain)}"
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=signals,
            rationale=rationale.strip(),
            assumptions=(
                "Open interest reflects real positioning, not stale/rolled contracts.",
                "Max-pain gravitation holds mainly into expiry, not far from it.",
                "Black-Scholes Greeks ignore dividends and assume European exercise.",
            ),
            risks=(
                "OI can be misread: hedges and spreads distort the naive PCR.",
                "A strong trend overrides max-pain and can crush short-vol positions.",
                "Illiquid strikes give noisy implied volatilities.",
            ),
        )

    def _no_chain_report(self) -> AgentReport:
        return AgentReport(
            agent=self.kind,
            score=Score(50.0),
            signals=(
                Signal(
                    "OptionChain", SignalStrength.NEUTRAL,
                    "No listed options / chain unavailable", None,
                ),
            ),
            rationale="No option chain available for this instrument; no derivatives signal.",
            assumptions=("The instrument may not have liquid listed options.",),
            risks=("Absence of a derivatives read removes a positioning cross-check.",),
        )

    def _pcr(self, chain: OptionChain) -> tuple[Signal, float]:
        call_oi = sum(c.open_interest for c in chain.calls)
        put_oi = sum(p.open_interest for p in chain.puts)
        pcr = put_oi / call_oi if call_oi else 1.0
        # Contrarian: high PCR (fear) -> bullish; low PCR (complacency) -> bearish.
        strength = _grade(pcr, (0.6, 0.8, 1.1, 1.4), higher_is_better=True)
        return (
            Signal("PutCallRatio", strength,
                   "OI put/call ratio (high = over-bearish, contrarian bullish)",
                   round(pcr, 2)),
            pcr,
        )

    def _max_pain(self, chain: OptionChain) -> tuple[Signal, float]:
        strikes = sorted({q.strike for q in (*chain.calls, *chain.puts)})
        max_pain = min(strikes, key=lambda s: self._pain_at(chain, s))
        pull_pct = (max_pain / chain.spot - 1.0) * 100.0 if chain.spot else 0.0
        # Max-pain above spot pulls price up (bullish); below pulls down (bearish).
        strength = _grade(pull_pct, (-3.0, -1.0, 1.0, 3.0), higher_is_better=True)
        return (
            Signal("MaxPain", strength,
                   "Max-pain strike vs spot, % (above spot = upward pull)",
                   round(pull_pct, 2)),
            max_pain,
        )

    @staticmethod
    def _pain_at(chain: OptionChain, settle: float) -> float:
        call_pain = sum(c.open_interest * max(settle - c.strike, 0.0) for c in chain.calls)
        put_pain = sum(p.open_interest * max(p.strike - settle, 0.0) for p in chain.puts)
        return call_pain + put_pain

    def _iv_skew(self, chain: OptionChain) -> tuple[Signal, float]:
        atm = chain.atm_strike()
        call_iv = self._nearest_iv(chain.calls, atm)
        put_iv = self._nearest_iv(chain.puts, atm)
        # Skew in volatility points; rich puts (positive) = hedging/risk-off (bearish).
        skew = (put_iv - call_iv) * 100.0
        strength = _grade(skew, (-4.0, -1.0, 1.0, 4.0), higher_is_better=False)
        return (
            Signal("IVSkew", strength,
                   "Put minus call IV near the money, vol pts (rich puts = risk-off)",
                   round(skew, 2)),
            skew,
        )

    @staticmethod
    def _nearest_iv(quotes: tuple[OptionQuote, ...], strike: float) -> float:
        candidates = [q for q in quotes if q.implied_volatility > 0.0]
        if not candidates:
            return 0.0
        return min(candidates, key=lambda q: abs(q.strike - strike)).implied_volatility

    def _greeks_note(self, chain: OptionChain) -> str:
        atm = chain.atm_strike()
        call = self._at_strike(chain.calls, atm)
        if call is None or call.implied_volatility <= 0.0:
            return "ATM Greeks unavailable."
        g = bs.greeks(
            chain.spot, atm, chain.time_to_expiry_years(), _RISK_FREE,
            call.implied_volatility, OptionRight.CALL,
        )
        return (
            f"ATM call delta {g.delta:.2f}, gamma {g.gamma:.4f}, "
            f"theta {g.theta:.2f}/day (IV {call.implied_volatility * 100:.0f}%)."
        )

    def _oi_walls(self, chain: OptionChain) -> str:
        resistance = max(chain.calls, key=lambda c: c.open_interest).strike
        support = max(chain.puts, key=lambda p: p.open_interest).strike
        return f"OI support ~{support:.0f}, resistance ~{resistance:.0f}."

    @staticmethod
    def _at_strike(quotes: tuple[OptionQuote, ...], strike: float) -> OptionQuote | None:
        for q in quotes:
            if q.strike == strike:
                return q
        return None
