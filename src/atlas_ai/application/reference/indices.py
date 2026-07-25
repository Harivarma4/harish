"""Curated registry of Indian broad-market and sector indices.

Symbols are Yahoo Finance index tickers (leading ``^``); the Yahoo adapter passes
them through unchanged. If Yahoo renames a ticker, the multi-index endpoint
degrades gracefully — that index shows up under ``errors`` rather than failing the
whole call.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IndexGroup(StrEnum):
    ALL = "all"
    BROAD = "broad"
    SECTOR = "sector"


@dataclass(frozen=True, slots=True)
class IndexRef:
    key: str      # stable slug, e.g. "banknifty"
    name: str     # display name, e.g. "Nifty Bank"
    symbol: str   # Yahoo index ticker, e.g. "^NSEBANK"
    group: str    # "broad" | "sector"


INDIAN_INDICES: tuple[IndexRef, ...] = (
    # Broad market
    IndexRef("nifty50", "Nifty 50", "^NSEI", "broad"),
    IndexRef("banknifty", "Nifty Bank", "^NSEBANK", "broad"),
    IndexRef("sensex", "BSE Sensex", "^BSESN", "broad"),
    # Sectors
    IndexRef("niftyit", "Nifty IT", "^CNXIT", "sector"),
    IndexRef("niftyauto", "Nifty Auto", "^CNXAUTO", "sector"),
    IndexRef("niftypharma", "Nifty Pharma", "^CNXPHARMA", "sector"),
    IndexRef("niftyfmcg", "Nifty FMCG", "^CNXFMCG", "sector"),
    IndexRef("niftymetal", "Nifty Metal", "^CNXMETAL", "sector"),
    IndexRef("niftyrealty", "Nifty Realty", "^CNXREALTY", "sector"),
    IndexRef("niftyenergy", "Nifty Energy", "^CNXENERGY", "sector"),
    IndexRef("niftypsubank", "Nifty PSU Bank", "^CNXPSUBANK", "sector"),
    IndexRef("niftyinfra", "Nifty Infrastructure", "^CNXINFRA", "sector"),
    IndexRef("niftymedia", "Nifty Media", "^CNXMEDIA", "sector"),
)


def indices_for(group: IndexGroup) -> tuple[IndexRef, ...]:
    if group is IndexGroup.ALL:
        return INDIAN_INDICES
    return tuple(i for i in INDIAN_INDICES if i.group == group.value)
