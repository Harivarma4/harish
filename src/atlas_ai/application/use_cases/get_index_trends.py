"""Use case: read the last-week trend for many indices/sectors in one call.

Reuses ``GetWeeklyTrend`` per index. A failure on one index (e.g. Yahoo renamed a
ticker) is isolated — it lands in ``errors`` instead of failing the whole call.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.application.reference.indices import (
    IndexGroup,
    IndexRef,
    indices_for,
)
from atlas_ai.application.use_cases.get_weekly_trend import (
    TREND_DISCLAIMER,
    GetWeeklyTrend,
    GetWeeklyTrendCommand,
    TrendSummary,
)
from atlas_ai.domain.enums import Exchange


@dataclass(frozen=True, slots=True)
class IndexTrend:
    ref: IndexRef
    summary: TrendSummary


@dataclass(frozen=True, slots=True)
class IndexTrendError:
    ref: IndexRef
    message: str


@dataclass(frozen=True, slots=True)
class IndexTrendsResult:
    group: str
    sessions: int
    trends: tuple[IndexTrend, ...]
    errors: tuple[IndexTrendError, ...]
    disclaimer: str = TREND_DISCLAIMER


@dataclass(frozen=True, slots=True)
class GetIndexTrendsCommand:
    group: IndexGroup = IndexGroup.ALL
    sessions: int = 5


class GetIndexTrends:
    """Aggregates weekly trends across a set of indices."""

    def __init__(self, *, weekly: GetWeeklyTrend) -> None:
        self._weekly = weekly

    def execute(self, command: GetIndexTrendsCommand) -> IndexTrendsResult:
        trends: list[IndexTrend] = []
        errors: list[IndexTrendError] = []
        for ref in indices_for(command.group):
            try:
                summary = self._weekly.execute(
                    GetWeeklyTrendCommand(
                        symbol=ref.symbol, exchange=Exchange.NSE, sessions=command.sessions
                    )
                )
                trends.append(IndexTrend(ref, summary))
            except Exception as exc:  # noqa: BLE001 - isolate per-index failures
                errors.append(IndexTrendError(ref, str(exc)))
        return IndexTrendsResult(
            group=command.group.value,
            sessions=command.sessions,
            trends=tuple(trends),
            errors=tuple(errors),
        )
