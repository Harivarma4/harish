# Architecture

Project Atlas AI is built with **Clean / Hexagonal Architecture** and
**Domain-Driven Design**. Dependencies point inward: the domain knows nothing
about the outside world; the application layer defines *ports* (interfaces); and
infrastructure *adapters* implement those ports and are wired together at a
single composition root.

```
            ┌─────────────────────────────────────────────┐
            │                    api/                       │  driving adapter
            │        FastAPI · DI container · DTOs           │  (HTTP)
            └───────────────────────┬───────────────────────┘
                                    │ calls use cases
            ┌───────────────────────▼───────────────────────┐
            │                application/                    │
            │  use_cases · agents · prediction · orchestration│
            │            ports (Protocols) ◄─────────────────┼── implemented by adapters
            └───────────────────────┬───────────────────────┘
                                    │ depends only on
            ┌───────────────────────▼───────────────────────┐
            │                   domain/                      │  pure, no I/O
            │  Recommendation · Evidence · Risk · Market …    │
            └────────────────────────────────────────────────┘
                                    ▲
            ┌───────────────────────┴───────────────────────┐
            │                  adapters/                     │  driven adapters
            │  mock LLM · mock market data · mock broker ·    │
            │  in-memory repositories · config                │
            └────────────────────────────────────────────────┘
```

## Layers

| Layer | Package | Responsibility | May import |
|-------|---------|----------------|------------|
| Domain | `atlas_ai.domain` | Entities, value objects, business invariants. No I/O. | stdlib only |
| Application | `atlas_ai.application` | Use cases, agents, orchestration, prediction, ports. | domain |
| Adapters | `atlas_ai.adapters` | Concrete implementations of ports (mock now, real later). | domain, application ports |
| API | `atlas_ai.api` | HTTP delivery, DTOs, dependency wiring. | all of the above |

The **domain must never import** from application, adapters, or api. The
**application depends only on domain** and on its own port abstractions — never
on a concrete adapter.

## Agent pipeline (the working slice)

```
MarketDataPort ──▶ FundamentalAgent ─┐
                   TechnicalAgent ───┼─▶ DebateAgent (Bull/Bear/Judge) ─┐
                   RiskAgent ────────┘        via LLMPort               │
                                                                        ▼
                              PredictionEngine (Bayesian blend + Monte Carlo)
                                                                        │
                                                                        ▼
                              EvidenceAgent ──▶ Recommendation synthesis
                                                                        │
                                                                        ▼
                              RecommendationRepository + AuditRepository
```

Fundamental and technical agents compute **real numbers** (financial ratios,
SMA/EMA/RSI/MACD/ATR) from the data supplied through the port — the *data* is
mock, the *analysis* is genuine. The debate and evidence narratives are produced
through the `LLMPort`, which in mock mode returns deterministic, templated text
so the whole pipeline runs offline and reproducibly.

## Prediction engine

No point predictions. The engine blends agent scores into a prior (Bayesian
update) and runs a Monte Carlo simulation (fixed seed → reproducible) over a
return distribution to produce a probability of a favourable outcome, an
expected-CAGR distribution with confidence intervals, and a calibrated
confidence score.

## Governance & compliance

Every `Recommendation` carries `GovernanceMetadata` (timestamps, model version,
prompt version, reasoning summary) and a mandatory disclaimer, and cannot be
constructed without confidence, assumptions, risks, and evidence (enforced in
`domain/recommendation.py`). See [DISCLAIMER.md](./DISCLAIMER.md).

## Mapping the master-prompt vision to this code

The master prompt describes loose top-level folders. They map into the package:

| Vision folder | This codebase |
|---------------|---------------|
| `agents/` | `application/agents/` |
| `llm/` | `application/ports/llm.py` + `adapters/llm/` |
| `core/` | `domain/` + `application/` |
| `api/` | `api/` |
| `broker-agent` | `application/ports/broker.py` + `adapters/broker/` |

## Real market data (Zerodha Kite Connect)

`ATLAS_ADAPTER_MODE=real` swaps the mock price feed for a live one:

- `adapters/market_data/kite_market_data.py` implements `MarketDataPort`
  (quotes + candles) against the Kite Connect v3 API. The `kiteconnect` client is
  injectable (a `KiteClient` Protocol), so the mapping logic is unit-tested
  offline with a fake client; live calls happen only where you deploy it with an
  API key + daily access token and outbound access to Kite.
- Kite provides **no fundamentals**, so those are a separate port
  (`FundamentalsPort`). In real mode choose the source via
  `ATLAS_FUNDAMENTALS_SOURCE`: `file` reads a researched JSON dataset
  (`FileFundamentalsProvider`, see `docs/sample_fundamentals.json`), or `mock`
  falls back to illustrative placeholders with a logged warning.
- The LLM and broker still use mock adapters in real mode until their real
  adapters are built; the container logs this so the mixed state is never silent.

Install the integration with the optional extra: `pip install -e ".[kite]"`.

## Roadmap (out of scope for this foundation build)

- Real adapters: OpenAI / Claude / Gemini / local models; a fundamentals vendor
  feed; a live Kite broker adapter (holdings/margins/execution).
- Remaining agents: news, macro, quant, options, behavioral, portfolio, memory,
  learning; a CEO/COO/CTO orchestration layer.
- Streaming & storage: Kafka, TimescaleDB, ClickHouse, DuckDB, Elasticsearch,
  Qdrant/Weaviate, S3/MinIO lakehouse.
- Knowledge graph (Neo4j) of companies/people/funds/events.
- Backtesting & learning loop; evaluation metrics (Sharpe, drawdown, alpha…).
- Next.js/Tailwind/shadcn frontend with TradingView charts.
- AuthN/AuthZ (OAuth, JWT, RBAC, MFA, audit), secrets vault, prompt-injection
  detection, rate limiting.
- Kubernetes, Terraform, Grafana/Prometheus/OpenTelemetry/ELK observability.

The current architecture is designed so each of these slots in behind an existing
port or as a new agent node without reworking the core.
