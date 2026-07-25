# Changelog

All notable changes to Project Atlas AI are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Quant / factor agent** — momentum, low-volatility, mean-reversion, quality,
  and value factors computed from the price + fundamentals already in context
  (no new data feed). The prediction engine now blends 6 agent scores.
- **News-sentiment agent** — reliability-weighted sentiment from recent coverage
  (weights a Reuters headline above a social post), contributing net sentiment,
  recent-tilt, and coverage signals to every recommendation (via the existing
  `NewsPort` + a mock adapter). The prediction engine now blends 5 agent scores.
- **Macro agent** — top-down analysis of rates, inflation, GDP growth, 10Y yield,
  rupee, crude, FII flows, and global markets, contributing a market-wide macro
  score/signals to every recommendation (via a new `MacroPort` + mock adapter).
- Multi-index trend endpoint `GET /api/v1/trend/indices?group=all|broad|sector` —
  last-week trend for Nifty 50, Bank Nifty, Sensex, and sector indices (IT, Auto,
  Pharma, FMCG, Metal, …) in one call, with per-index error isolation.
- Weekly-trend endpoint `GET /api/v1/trend/{symbol}` — a factual read of the last
  ~week of price action (change %, direction, high/low, SMA, per-session closes)
  from the configured market-data source. Not a prediction.
- Public **Yahoo Finance fundamentals** adapter (`ATLAS_FUNDAMENTALS_SOURCE=yahoo`,
  no API key) mapping quoteSummary onto the domain; shared `yahoo_common` module.
- Change-management strategy (CAB-aligned): `docs/CHANGE_MANAGEMENT.md`, a PR
  template, and `CODEOWNERS` for review routing.

## [0.1.0] — foundation

### Added
- Clean/Hexagonal + DDD foundation with an end-to-end multi-agent research
  pipeline (fundamental, technical, risk, debate, evidence) producing an
  explainable, evidence-backed `Recommendation` with governance metadata and a
  mandatory research-only disclaimer. Bayesian + Monte Carlo prediction engine
  (no deterministic predictions).
- FastAPI delivery, DI composition root, in-memory + append-only audit
  repositories, deterministic mock adapters, Docker/compose, CI, and tests.
- `FundamentalsPort` split out of `MarketDataPort`.
- Real **Zerodha Kite Connect** market-data adapter (quotes + candles), injectable
  client, offline tests.
- **File** fundamentals provider (user-supplied JSON) since broker/market feeds
  provide no fundamentals.
- Real **Claude (Anthropic)** LLM adapter for debate/evidence narrative
  (`ATLAS_LLM_PROVIDER`), injectable client, refusal handling, offline tests.
- Public **Yahoo Finance** market-data adapter (no API key) reading real Indian
  prices/candles (`ATLAS_MARKET_DATA_SOURCE`), injectable HTTP client, offline
  tests.

[Unreleased]: https://github.com/Harivarma4/harish/compare/master...HEAD
