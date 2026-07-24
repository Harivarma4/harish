"""Composition root — the single place where ports are bound to adapters.

``ATLAS_ADAPTER_MODE`` selects the adapter set:

- ``mock`` (default): fully offline, deterministic adapters.
- ``real``: live market data via ``ATLAS_MARKET_DATA_SOURCE`` — ``kite`` (Zerodha
  Kite Connect, needs a key) or ``yahoo`` (public Yahoo Finance, no key).
  Fundamentals come from ``ATLAS_FUNDAMENTALS_SOURCE`` (``file`` or ``mock``),
  since neither feed provides fundamentals. The broker still falls back to the
  mock implementation until its real adapter is built — this is logged so the
  mixed state is never silent.

The LLM is selected independently of the adapter mode, via ``ATLAS_LLM_PROVIDER``
(``mock`` or ``anthropic``/Claude), so real narrative generation can be enabled
in either mode.
"""

from __future__ import annotations

import logging

from atlas_ai.adapters.broker.mock_broker import MockBroker
from atlas_ai.adapters.config import (
    AdapterMode,
    FundamentalsSource,
    LLMProvider,
    MarketDataSource,
    Settings,
    load_settings,
)
from atlas_ai.adapters.fundamentals.file_fundamentals import FileFundamentalsProvider
from atlas_ai.adapters.fundamentals.mock_fundamentals import MockFundamentals
from atlas_ai.adapters.llm.anthropic_llm import AnthropicLLM
from atlas_ai.adapters.llm.mock_llm import MockLLM
from atlas_ai.adapters.market_data.kite_market_data import KiteMarketData
from atlas_ai.adapters.market_data.mock_market_data import MockMarketData
from atlas_ai.adapters.market_data.yahoo_market_data import YahooMarketData
from atlas_ai.adapters.persistence.in_memory import (
    InMemoryAuditRepository,
    InMemoryRecommendationRepository,
)
from atlas_ai.application.agents.debate_agent import DebateAgent
from atlas_ai.application.agents.evidence_agent import EvidenceAgent
from atlas_ai.application.agents.fundamental_agent import FundamentalAgent
from atlas_ai.application.agents.risk_agent import RiskAgent
from atlas_ai.application.agents.technical_agent import TechnicalAgent
from atlas_ai.application.orchestration.pipeline import ResearchPipeline
from atlas_ai.application.ports.broker import BrokerPort
from atlas_ai.application.ports.fundamentals import FundamentalsPort
from atlas_ai.application.ports.llm import LLMPort
from atlas_ai.application.ports.market_data import MarketDataPort
from atlas_ai.application.ports.repositories import (
    AuditRepository,
    RecommendationRepository,
)
from atlas_ai.application.prediction.engine import PredictionEngine
from atlas_ai.application.use_cases.generate_recommendation import GenerateRecommendation

logger = logging.getLogger("atlas_ai.container")


class Container:
    """Builds and holds application dependencies as singletons."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

        self.llm: LLMPort
        self.market_data: MarketDataPort
        self.fundamentals: FundamentalsPort
        self.broker: BrokerPort

        if self.settings.adapter_mode is AdapterMode.MOCK:
            self.market_data = MockMarketData()
            self.fundamentals = MockFundamentals()
            self.broker = MockBroker()
        else:
            self.market_data = self._build_market_data()
            self.fundamentals = self._build_fundamentals()
            # A real broker adapter is not built yet; use the mock and say so.
            logger.warning(
                "ATLAS_ADAPTER_MODE=real: market data is LIVE (%s); "
                "broker still uses the mock adapter (real one not built yet).",
                self.settings.market_data_source.value,
            )
            self.broker = MockBroker()

        # The LLM is chosen independently of the market-data adapter mode.
        self.llm = self._build_llm()
        self._model_version = self.llm.model_version

        # Persistence singletons so GET-after-POST works within a process.
        self.repository: RecommendationRepository = InMemoryRecommendationRepository()
        self.audit: AuditRepository = InMemoryAuditRepository()

        self.pipeline = ResearchPipeline(
            fundamental=FundamentalAgent(),
            technical=TechnicalAgent(),
            risk=RiskAgent(),
            debate=DebateAgent(self.llm),
            evidence=EvidenceAgent(),
            prediction=PredictionEngine(
                simulations=self.settings.mc_simulations, seed=self.settings.mc_seed
            ),
        )

    def _build_llm(self) -> LLMPort:
        if self.settings.llm_provider is LLMProvider.ANTHROPIC:
            return AnthropicLLM(
                api_key=self.settings.anthropic_api_key,
                model=self.settings.anthropic_model,
                max_tokens=self.settings.anthropic_max_tokens,
            )
        return MockLLM()

    def _build_market_data(self) -> MarketDataPort:
        if self.settings.market_data_source is MarketDataSource.YAHOO:
            return YahooMarketData()
        return KiteMarketData(
            api_key=self.settings.kite_api_key,
            access_token=self.settings.kite_access_token,
        )

    def _build_fundamentals(self) -> FundamentalsPort:
        if self.settings.fundamentals_source is FundamentalsSource.FILE:
            if not self.settings.fundamentals_path:
                raise ValueError(
                    "ATLAS_FUNDAMENTALS_SOURCE=file requires ATLAS_FUNDAMENTALS_PATH "
                    "to point at a JSON dataset of researched fundamentals."
                )
            return FileFundamentalsProvider(self.settings.fundamentals_path)
        logger.warning(
            "Fundamentals source is 'mock' in real mode: ROE/PE/etc. are "
            "ILLUSTRATIVE placeholders, not researched data. Set "
            "ATLAS_FUNDAMENTALS_SOURCE=file with ATLAS_FUNDAMENTALS_PATH for real data."
        )
        return MockFundamentals()

    def generate_recommendation(self) -> GenerateRecommendation:
        return GenerateRecommendation(
            market_data=self.market_data,
            fundamentals=self.fundamentals,
            pipeline=self.pipeline,
            repository=self.repository,
            audit=self.audit,
            model_version=self._model_version,
        )
