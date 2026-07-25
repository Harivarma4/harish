"""Twelve-Factor configuration via environment variables."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdapterMode(StrEnum):
    MOCK = "mock"
    REAL = "real"


class MarketDataSource(StrEnum):
    KITE = "kite"      # Zerodha Kite Connect (needs API key + access token)
    YAHOO = "yahoo"    # public Yahoo Finance (no key)


class MacroSource(StrEnum):
    MOCK = "mock"
    YAHOO = "yahoo"    # live market vars from Yahoo + configured official figures


class NewsSource(StrEnum):
    MOCK = "mock"
    GOOGLE = "google"  # public Google News RSS + finance sentiment lexicon


class OptionsSource(StrEnum):
    MOCK = "mock"
    NSE = "nse"        # public NSE option-chain endpoint (no key; bot-protected)


class BrokerSource(StrEnum):
    MOCK = "mock"
    KITE = "kite"      # Zerodha Kite Connect holdings/margins (needs a key + token)


class PersistenceBackend(StrEnum):
    MEMORY = "memory"    # in-process, non-durable (used by the test suite)
    DUCKDB = "duckdb"    # durable, embedded, file-based (default; zero-infra)
    POSTGRES = "postgres"  # durable Postgres/JSONB (needs a reachable database_url)


class FundamentalsSource(StrEnum):
    MOCK = "mock"
    FILE = "file"      # user-supplied JSON (exact, researched)
    YAHOO = "yahoo"    # public Yahoo Finance quoteSummary (no key; some gaps)


class LLMProvider(StrEnum):
    MOCK = "mock"
    ANTHROPIC = "anthropic"  # Claude


class Settings(BaseSettings):
    """Application settings, read from the environment (prefix ``ATLAS_``)."""

    model_config = SettingsConfigDict(
        env_prefix="ATLAS_", env_file=".env", extra="ignore"
    )

    app_name: str = "Project Atlas AI"
    env: str = "local"
    log_level: str = "INFO"

    # REAL by default: the app runs on real data. Set ATLAS_ADAPTER_MODE=mock
    # only for fully-offline runs (this is what the test suite forces).
    adapter_mode: AdapterMode = AdapterMode.REAL

    # In real mode, which market-data feed to use: 'yahoo' (default; public, no
    # key) or 'kite' (Zerodha Kite Connect; needs a key).
    market_data_source: MarketDataSource = MarketDataSource.YAHOO

    # Fundamentals source (price feeds don't provide fundamentals): 'yahoo'
    # (default; public, no key), 'file' (researched JSON at `fundamentals_path`),
    # or 'mock' (illustrative placeholders; logs a warning).
    fundamentals_source: FundamentalsSource = FundamentalsSource.YAHOO
    fundamentals_path: str = ""

    # Macro source: 'yahoo' (default) fetches live rupee/crude/global vars and
    # combines them with the official policy figures below (update these from RBI
    # / MOSPI / NSE releases). 'mock' uses a fixed snapshot.
    macro_source: MacroSource = MacroSource.YAHOO
    macro_repo_rate_pct: float = 6.5
    macro_cpi_inflation_pct: float = 5.0
    macro_gdp_growth_pct: float = 6.5
    macro_india_10y_yield_pct: float = 7.0
    macro_fii_flow_cr: float = 0.0

    # News source: 'google' (default) uses the public Google News RSS feed with a
    # finance sentiment lexicon; 'mock' uses deterministic synthetic headlines.
    news_source: NewsSource = NewsSource.GOOGLE
    news_query_suffix: str = "share"

    # Options source: 'nse' (default) uses the public NSE option-chain endpoint
    # (no key; bot-protected, deploy-only); 'mock' uses a deterministic synthetic
    # chain. A fetch failure degrades to a neutral, no-signal options report.
    options_source: OptionsSource = OptionsSource.NSE

    # Broker source: 'kite' (default) reads real Zerodha holdings/margins (needs
    # kite_api_key + kite_access_token); 'mock' uses a small static portfolio.
    # There is no key-less broker feed, so real mode falls back to mock (with a
    # warning) when credentials are absent.
    broker_source: BrokerSource = BrokerSource.KITE

    # LLM provider for debate/evidence narrative. 'anthropic' (default) uses
    # Claude (needs anthropic_api_key or an `ant auth login` profile plus the
    # `anthropic` package); when those are unavailable the container falls back
    # to the deterministic offline mock (with a warning). 'mock' forces the mock.
    llm_provider: LLMProvider = LLMProvider.ANTHROPIC
    anthropic_model: str = "claude-opus-5"
    anthropic_max_tokens: int = Field(default=2048, ge=64)

    mc_simulations: int = Field(default=10_000, ge=100)
    mc_seed: int = 42

    # Persistence backend for recommendations + the audit trail. 'duckdb'
    # (default) is durable, embedded, and file-based (no server) — it just needs
    # the `duckdb` package and writes to `duckdb_path`. 'postgres' is durable but
    # needs a reachable `database_url` and the `psycopg` package. 'memory' forces
    # the in-process store. Any backend falls back to in-memory (with a warning)
    # when its dependency/target is unavailable, so nothing crashes.
    persistence_backend: PersistenceBackend = PersistenceBackend.DUCKDB
    duckdb_path: str = "atlas.duckdb"
    database_url: str = ""

    # Credentials (unused in mock mode); present so real adapters can read them.
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""


def load_settings() -> Settings:
    return Settings()
