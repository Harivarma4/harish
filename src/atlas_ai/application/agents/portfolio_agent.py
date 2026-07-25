"""Portfolio-construction agent — fit of a candidate against the existing book.

Reads the current holdings and margins through the injected ``BrokerPort`` and
judges how a new position in the candidate would affect portfolio construction:

- **BookConcentration** — Herfindahl index of position weights; a top-heavy book
  is a standing risk.
- **SectorExposure** — how much of the book (including the candidate's sector) is
  already in that sector; piling into a crowded sector is a caution.
- **PositionFit** — whether the candidate diversifies the book (new/underweight
  name in an underweight sector) or doubles down on an already-large exposure.

An empty book is a clean slate: no concentration to flag. This agent tempers
conviction on portfolio grounds; it does not judge the security's own merit.
"""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.sectors import sector_of
from atlas_ai.application.ports.broker import BrokerPort, Holding
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.value_objects import Score

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


class PortfolioAgent:
    """Scores how a candidate fits the existing portfolio (construction risk)."""

    kind = AgentKind.PORTFOLIO

    def __init__(self, broker: BrokerPort) -> None:
        self._broker = broker

    def analyze(self, ctx: AgentContext) -> AgentReport:
        holdings = self._broker.get_holdings()
        if not holdings:
            return self._empty_book_report()

        weights = self._weights(holdings)
        cand_symbol = ctx.instrument.symbol.upper()
        cand_sector = sector_of(cand_symbol)

        hhi = sum(w * w for w in weights.values())
        cand_weight = weights.get(cand_symbol, 0.0)
        sector_weight = sum(
            w for sym, w in weights.items() if sector_of(sym) == cand_sector
        )

        signals = (
            self._concentration(hhi),
            self._sector_exposure(sector_weight, cand_sector),
            self._position_fit(cand_weight, sector_weight),
        )
        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))

        margins = self._broker.get_margins()
        cash_pct = (margins.available_cash / margins.net * 100.0) if margins.net else 0.0
        rationale = (
            f"Book of {len(holdings)} names, HHI {hhi:.2f}; {cand_symbol} is "
            f"{cand_weight * 100:.0f}% of the book, {cand_sector} sector "
            f"{sector_weight * 100:.0f}%. Cash headroom {cash_pct:.0f}% of net."
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=signals,
            rationale=rationale,
            assumptions=(
                "Holdings and last prices from the broker are current.",
                "Sector labels come from a static map; unmapped names are 'OTHER'.",
                "Equal-risk is proxied by market value, not volatility-adjusted weight.",
            ),
            risks=(
                "Naive market-value weights ignore correlation and factor overlap.",
                "A single-sector shock hits crowded exposures harder than HHI implies.",
            ),
        )

    def _empty_book_report(self) -> AgentReport:
        return AgentReport(
            agent=self.kind,
            score=Score(55.0),
            signals=(
                Signal("PositionFit", SignalStrength.BULLISH,
                       "No existing book; a new position adds no concentration", 0.0),
            ),
            rationale="No existing holdings; clean slate with no concentration to flag.",
            assumptions=("The broker returned an empty portfolio.",),
            risks=("A first position is undiversified by definition.",),
        )

    @staticmethod
    def _weights(holdings: list[Holding]) -> dict[str, float]:
        values = {
            h.instrument.symbol.upper(): abs(h.quantity) * h.last_price for h in holdings
        }
        total = sum(values.values())
        if total <= 0.0:
            return dict.fromkeys(values, 0.0)
        return {sym: mv / total for sym, mv in values.items()}

    def _concentration(self, hhi: float) -> Signal:
        # Low HHI = diversified (good); high HHI = concentrated (risk).
        strength = _grade(hhi, (0.25, 0.4, 0.6, 0.8), higher_is_better=False)
        return Signal("BookConcentration", strength,
                      "Herfindahl index of position weights (lower = diversified)",
                      round(hhi, 3))

    def _sector_exposure(self, sector_weight: float, sector: str) -> Signal:
        strength = _grade(sector_weight, (0.15, 0.3, 0.45, 0.6), higher_is_better=False)
        return Signal("SectorExposure", strength,
                      f"Book weight already in {sector} (higher = more crowded)",
                      round(sector_weight, 3))

    def _position_fit(self, cand_weight: float, sector_weight: float) -> Signal:
        # Adding to an already-large name or crowded sector concentrates the book;
        # a new/underweight name in an underweight sector diversifies it.
        if cand_weight >= 0.15 or sector_weight >= 0.5:
            strength = SignalStrength.BEARISH
        elif cand_weight == 0.0 and sector_weight < 0.2:
            strength = SignalStrength.BULLISH
        else:
            strength = SignalStrength.NEUTRAL
        return Signal("PositionFit", strength,
                      "Diversifying add vs doubling down on a large exposure",
                      round(cand_weight, 3))
