# Project Atlas AI

**Institutional AI investment-research platform for Indian markets — a research
tool, not investment advice.**

Project Atlas AI is an evidence-first, multi-agent research platform. Specialized
agents gather and analyze data, debate a thesis (bull vs. bear vs. judge),
quantify risk and uncertainty, and synthesize a fully-explained recommendation.
Every output carries a confidence level, stated assumptions, known risks,
supporting evidence, and a clear disclaimer. **It makes no deterministic
predictions and guarantees no returns.** See [docs/DISCLAIMER.md](docs/DISCLAIMER.md).

> This repository is the **foundation build**: a correctly-architected skeleton
> plus one end-to-end working pipeline. The broader vision (real broker/LLM
> integrations, streaming, knowledge graph, the full agent roster, backtesting,
> and a frontend) is tracked as a roadmap in
> [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What works today

A single API call runs the full research pipeline **offline** on deterministic
mock data:

- **Fundamental agent** — ROE, ROCE, debt/equity, margins, P/E, PEG → a score.
- **Technical agent** — SMA, EMA, RSI, MACD, ATR on a candle series → a score.
- **Risk agent** — position sizing, Value-at-Risk, ATR-based stop, reward:risk.
- **Debate agent** — bull and bear arguments reconciled by a judge (via the LLM port).
- **Prediction engine** — Bayesian score blend + Monte Carlo → probability,
  expected-CAGR distribution, confidence interval (no point predictions).
- **Evidence agent** — assembles evidence, counter-arguments, and unknowns.
- **Recommendation synthesis** — a complete recommendation with governance
  metadata, persisted with an immutable audit record.

## Architecture

Clean / Hexagonal + DDD. Dependencies point inward; infrastructure is hidden
behind `typing.Protocol` ports so mock adapters (today) and real adapters
(later) are interchangeable via the `ATLAS_ADAPTER_MODE` setting. Full details in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
src/atlas_ai/
  domain/        pure business model (Recommendation, Evidence, Risk, Market…)
  application/   use cases · agents · prediction · orchestration · ports
  adapters/      config · mock llm/market-data/broker · in-memory persistence
  api/           FastAPI app · DI container · routes · DTOs
```

## Quickstart

```bash
make setup                 # pip install -e ".[dev]"
make check                 # ruff + mypy + bandit + pytest
make run                   # uvicorn on http://localhost:8000
```

Generate a recommendation:

```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H 'content-type: application/json' \
  -d '{"symbol":"RELIANCE","exchange":"NSE","capital":100000}' | jq
```

Interactive API docs: <http://localhost:8000/docs>.

### Docker

```bash
make docker-up             # docker compose up --build
```

## Configuration

Copy `.env.example` to `.env`. Key setting: `ATLAS_ADAPTER_MODE` (`mock` by
default — fully offline). Real integration keys (Kite, OpenAI, Anthropic, Gemini)
are read from the environment and used only when real adapters land.

## Development

- **Conventional Commits** for every change.
- Quality gate (`make check`) runs ruff, mypy, bandit, and pytest — the same
  gate enforced in CI (`.github/workflows/ci.yml`).
