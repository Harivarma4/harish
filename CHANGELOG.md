# Changelog

All notable changes to Project Atlas AI are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
