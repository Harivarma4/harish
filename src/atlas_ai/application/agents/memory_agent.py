"""Memory agent — institutional memory of prior stances on this instrument.

Reads past recommendations for the candidate through the recommendation
repository and contributes a weak prior based on the *persistence* and
*consistency* of the house view:

- **PriorStance** — a recency-weighted mean of past directional calls. A book
  that has been steadily constructive on a name carries that conviction forward
  (weakly); a flip in stance is not reinforced.
- **PriorConsistency** — an informational read on how stable the past view was
  and how many times we have looked (it does not skew the directional blend).

Realized win/loss is deliberately *not* judged here — that needs outcome labels
and is the learning agent's job. With no prior coverage the agent is neutral.
"""

from __future__ import annotations

import statistics

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.ports.repositories import RecommendationRepository
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import Action, AgentKind, SignalStrength
from atlas_ai.domain.recommendation import Recommendation
from atlas_ai.domain.value_objects import Score

# Map a past action onto a directional stance in [-1, 1].
_STANCE = {
    Action.BUY: 1.0,
    Action.ACCUMULATE: 0.5,
    Action.HOLD: 0.0,
    Action.REDUCE: -0.5,
    Action.SELL: -1.0,
    Action.AVOID: -1.0,
}
_DECAY = 0.8  # recency weight decay per step back in time

_SCALE = (
    SignalStrength.STRONG_BEARISH,
    SignalStrength.BEARISH,
    SignalStrength.NEUTRAL,
    SignalStrength.BULLISH,
    SignalStrength.STRONG_BULLISH,
)


def _grade(value: float, thresholds: tuple[float, float, float, float]) -> SignalStrength:
    t0, t1, t2, t3 = thresholds
    rank = 0 if value < t0 else 1 if value < t1 else 2 if value < t2 else 3 if value < t3 else 4
    return _SCALE[rank]


class MemoryAgent:
    """Scores the persistence of the house view on this instrument."""

    kind = AgentKind.MEMORY

    def __init__(self, repository: RecommendationRepository, *, lookback: int = 200) -> None:
        self._repository = repository
        self._lookback = lookback

    def analyze(self, ctx: AgentContext) -> AgentReport:
        history = self._history(ctx)
        if not history:
            return self._no_memory_report()

        stances = [_STANCE[r.action] for r in history]  # most-recent first
        confidences = [r.confidence.value for r in history]
        prior = self._recency_weighted(stances)
        avg_conf = statistics.fmean(confidences)
        stance_sig = Signal(
            "PriorStance", _grade(prior, (-0.5, -0.15, 0.15, 0.5)),
            "Recency-weighted mean of prior directional calls", round(prior, 3),
        )
        consistency_sig = self._consistency(stances)

        signals = (stance_sig, consistency_sig)
        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))
        rationale = (
            f"{len(history)} prior look(s) on {ctx.instrument.symbol}: recency-weighted "
            f"stance {prior:+.2f}, avg prior confidence {avg_conf:.2f}. "
            f"Latest call was {history[0].action.value}."
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=signals,
            rationale=rationale,
            assumptions=(
                "Past stances are informative about the current setup (weak prior).",
                "Recency matters: older calls are discounted geometrically.",
            ),
            risks=(
                "Anchoring: prior views can bias fresh analysis (kept low-weight).",
                "No realized-outcome labels yet, so this is persistence, not skill.",
            ),
        )

    def _history(self, ctx: AgentContext) -> list[Recommendation]:
        key = ctx.instrument.key
        recent = self._repository.list_recent(limit=self._lookback)
        return [r for r in recent if r.instrument.key == key]

    @staticmethod
    def _recency_weighted(stances: list[float]) -> float:
        weights = [_DECAY**i for i in range(len(stances))]
        total = sum(weights)
        return sum(w * s for w, s in zip(weights, stances, strict=True)) / total

    def _consistency(self, stances: list[float]) -> Signal:
        if len(stances) < 2:
            return Signal("PriorConsistency", SignalStrength.NEUTRAL,
                          "Single prior look; view stability not yet meaningful", 1.0)
        stability = max(0.0, 1.0 - min(statistics.pstdev(stances), 1.0))
        detail = f"View stability across {len(stances)} looks (1 = unchanged)"
        return Signal("PriorConsistency", SignalStrength.NEUTRAL, detail, round(stability, 3))

    def _no_memory_report(self) -> AgentReport:
        return AgentReport(
            agent=self.kind,
            score=Score(50.0),
            signals=(
                Signal("PriorStance", SignalStrength.NEUTRAL,
                       "No prior coverage of this instrument", 0.0),
            ),
            rationale="No prior recommendations on record for this instrument; no memory prior.",
            assumptions=("This is the first recorded look at this instrument.",),
            risks=("Without history there is no house-view persistence to lean on.",),
        )
