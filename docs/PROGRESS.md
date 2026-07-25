# Project Atlas AI — Progress Log

An end-of-day record of shipped work. Each entry is a milestone; the detail
lives in the referenced PRs and in `CHANGELOG.md`.

## 2026-07-25 — Full agent fleet is live

Completed the multi-agent build. All specialist agents now run in the research
pipeline and contribute to the blended, probabilistic outlook. Every change went
out as its own PR and was squash-merged to `master` only after CI (ruff, mypy
strict, bandit, pytest) was green.

### Shipped today

| PR | Agent / layer | Contribution | Default data basis |
|----|---------------|--------------|--------------------|
| #13 | Behavioral | fear/greed, volatility regime, volume herding (contrarian) | derived from price/volume |
| #14 | Options | PCR, max-pain, IV skew + real Black-Scholes Greeks/IV solver | NSE option chain (real) |
| #15 | Portfolio | HHI concentration, sector exposure, position fit | broker holdings |
| #16 | Memory | recency-weighted prior stances on the instrument | recommendation history |
| #17 | Learning | walk-forward self-backtest of a trend rule (hit-rate/Sharpe) | derived from price history |
| #18 | Orchestration | CEO/COO/CTO coordination + `GET /api/v1/status` | reports the whole fleet |

### The fleet (13 agents / stages)

- **Scored specialists (11):** fundamental, technical, quant, macro, news,
  behavioral, options, portfolio, memory, learning, risk.
- **Synthesis stages (2):** debate (bull/bear/judge), evidence.
- Coordinated by the orchestration layer; `GET /api/v1/status` reports each
  agent's role, responsibilities, data basis (real vs mock), and blend weight.

### Data authenticity

Everything defaults to **real data**; `mock` is pinned only by the offline test
suite. Five agents run on genuine live feeds (fundamental, technical, macro,
news, options); the rest derive from those. Two surfaces remain on non-real
adapters and are reported as readiness notes rather than hidden:

- **Broker** — real Zerodha (Kite) holdings adapter pending.
- **LLM narrative** — mock until `ATLAS_LLM_PROVIDER=anthropic` (Claude) is set.

### Test suite

Grew from ~100 to 151 tests across the six PRs; the quality gate stayed green on
every merge.

### Next candidates

- Real broker (Zerodha Kite) holdings adapter.
- Real LLM (Claude) narrative behind the existing LLM port.
