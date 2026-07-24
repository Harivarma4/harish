"""Twelve-Factor configuration via environment variables."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdapterMode(StrEnum):
    MOCK = "mock"
    REAL = "real"


class FundamentalsSource(StrEnum):
    MOCK = "mock"
    FILE = "file"


class Settings(BaseSettings):
    """Application settings, read from the environment (prefix ``ATLAS_``)."""

    model_config = SettingsConfigDict(
        env_prefix="ATLAS_", env_file=".env", extra="ignore"
    )

    app_name: str = "Project Atlas AI"
    env: str = "local"
    log_level: str = "INFO"

    adapter_mode: AdapterMode = AdapterMode.MOCK

    # Fundamentals source in real mode (Kite does not provide fundamentals).
    # 'file' reads researched data from `fundamentals_path`; 'mock' uses
    # illustrative placeholders (a loud warning is logged).
    fundamentals_source: FundamentalsSource = FundamentalsSource.MOCK
    fundamentals_path: str = ""

    mc_simulations: int = Field(default=10_000, ge=100)
    mc_seed: int = 42

    # Credentials (unused in mock mode); present so real adapters can read them.
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""


def load_settings() -> Settings:
    return Settings()
