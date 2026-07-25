"""Transparent, static sector classification for common NSE symbols.

Sector data is a data problem; a real deployment would source GICS/industry
classifications from a reference feed. This lookup is deliberately small and
explicit so the portfolio agent's exposure math is auditable. Unmapped symbols
fall back to ``OTHER`` (each treated as its own bucket by callers).
"""

from __future__ import annotations

_SECTORS: dict[str, str] = {
    # IT services
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT",
    "LTIM": "IT", "PERSISTENT": "IT",
    # Banks & financials
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "SBIN": "BANK", "KOTAKBANK": "BANK",
    "AXISBANK": "BANK", "INDUSINDBK": "BANK", "BAJFINANCE": "NBFC",
    "BAJAJFINSV": "NBFC", "SBILIFE": "INSURANCE", "HDFCLIFE": "INSURANCE",
    # Energy & materials
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "NTPC": "POWER", "POWERGRID": "POWER",
    "COALINDIA": "ENERGY", "TATASTEEL": "METALS", "JSWSTEEL": "METALS",
    "HINDALCO": "METALS", "ULTRACEMCO": "CEMENT", "GRASIM": "CEMENT",
    # Consumer
    "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG",
    "TATACONSUM": "FMCG", "TITAN": "CONSUMER", "ASIANPAINT": "CONSUMER",
    # Auto
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "BAJAJ-AUTO": "AUTO",
    "EICHERMOT": "AUTO", "HEROMOTOCO": "AUTO",
    # Pharma & healthcare
    "SUNPHARMA": "PHARMA", "CIPLA": "PHARMA", "DRREDDY": "PHARMA",
    "DIVISLAB": "PHARMA", "APOLLOHOSP": "HEALTHCARE",
    # Infra / telecom / other
    "LT": "INFRA", "ADANIPORTS": "INFRA", "BHARTIARTL": "TELECOM",
}


def sector_of(symbol: str) -> str:
    """Return the sector bucket for a symbol, or ``OTHER`` if unmapped."""
    return _SECTORS.get(symbol.upper(), "OTHER")
