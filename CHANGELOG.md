# Changelog

All notable changes to Project Atlas AI are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Real broker adapter** (`ATLAS_BROKER_SOURCE=kite`, default) — reads live
  Zerodha Kite Connect equity holdings and margins for the portfolio agent
  (settled + T1 quantity; non-equity legs skipped). Needs `kite_api_key` +
  `kite_access_token`; since there is no key-less broker feed, real mode falls
  back to the mock broker (with a warning) when credentials are absent. The
  injected client keeps parsing unit-tested offline, and `GET /api/v1/status`
  now reports the portfolio agent as real vs mock accordingly.

### Added
- **Orchestration layer** — a thin coordination tier over the agent pipeline,
  framed as CEO (research-not-advice mandate), COO (operations), and CTO
  (readiness). New `GET /api/v1/status` reports every agent's role,
  responsibilities, data basis (real vs mock, per source), and blend weight, so
  the authenticity of each contribution is explicit and it's clear which agents
  are live.
- **Learning agent** — instrument-specific calibration from a transparent
  walk-forward self-backtest of a long-only trend rule (close above its SMA held
  a fixed horizon) over the candles in context: historical hit-rate, per-trade
  Sharpe (reliability), and a live rule reading that is only actionable when the
  backtest shows edge. The prediction engine now blends 11 agent scores.
- **Memory agent** — an institutional-memory prior from past recommendations on
  the same instrument (read through the recommendation repository): a
  recency-weighted mean of prior directional calls plus a view-stability read.
  Realized win/loss is left to the learning agent; with no prior coverage it is
  neutral. The prediction engine now blends 10 agent scores.
- **Portfolio-construction agent** — judges how a candidate fits the existing
  book (read through the broker port): Herfindahl concentration, sector exposure
  (via a transparent static NSE sector map), and position fit (diversifying add
  vs doubling down). An empty book is treated as a clean slate. The prediction
  engine now blends 9 agent scores.
- **Options / derivatives agent** — positioning and sentiment from the nearest
  option chain: put/call OI ratio (contrarian), max-pain gravitation vs spot,
  and near-money IV skew, plus ATM Greeks from real Black-Scholes math
  (`application/pricing/black_scholes.py`: prices, first-order Greeks, and a
  bisection implied-vol solver). The prediction engine now blends 8 agent scores.
- **Real options adapter** (`ATLAS_OPTIONS_SOURCE=nse`, default) — the public,
  key-less NSE option-chain endpoint (bot-protected, so deploy-only; a fetch
  failure degrades to a neutral, no-signal options report). A deterministic
  `MockOptions` chain backs the offline test suite.
- **Behavioral-finance agent** — contrarian market psychology read from the
  candles already in context (no new data feed): a fear/greed index (RSI +
  extension vs the 50-SMA), a volatility regime (short vs baseline ATR), and
  volume herding (a volume surge into a rally is herding/caution; into a
  sell-off is capitulation/opportunity). The prediction engine now blends 7
  agent scores.

### Changed
- **Real data is now the default.** `ATLAS_ADAPTER_MODE` defaults to `real` with
  `ATLAS_MARKET_DATA_SOURCE=yahoo` and `ATLAS_FUNDAMENTALS_SOURCE=yahoo` (public,
  no API key). `mock` is now opt-in and used only by the offline test suite.

### Added
- **Real news adapter** (`ATLAS_NEWS_SOURCE=google`, default) — public Google
  News RSS search feed (no key) with a transparent finance sentiment lexicon and
  per-source reliability weighting. News is now real by default; a fetch failure
  degrades to "no news" (neutral) rather than failing the recommendation. **All
  data feeds now default to real** (news, macro, prices, fundamentals); only the
  LLM narrative stays mock until an Anthropic key is set.
- **Real macro adapter** (`ATLAS_MACRO_SOURCE=yahoo`, default) — live rupee
  (`INR=X`), Brent crude (`BZ=F`), and a global-equity proxy (`^GSPC`) from Yahoo,
  combined with official RBI/MOSPI/NSE figures from config (repo, CPI, GDP, 10Y,
  FII).

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
