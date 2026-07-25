"""Composition root — the single place where ports are bound to adapters.

``ATLAS_ADAPTER_MODE`` selects the adapter set:

- ``mock`` (default): fully offline, deterministic adapters.
- ``real``: live market data via ``ATLAS_MARKET_DATA_SOURCE`` — ``kite`` (Zerodha
  Kite Connect, needs a key) or ``yahoo`` (public Yahoo Finance, no key).
  Fundamentals come from ``ATLAS_FUNDAMENTALS_SOURCE`` (``file`` or ``mock``),
  since neither feed provides fundamentals. The broker uses Zerodha Kite
  (``ATLAS_BROKER_SOURCE=kite``) when credentials are set, and falls back to the
  mock implementation otherwise — this is logged so the mixed state is never
  silent.

The LLM is selected independently of the adapter mode, via ``ATLAS_LLM_PROVIDER``
(``mock`` or ``anthropic``/Claude), so real narrative generation can be enabled
in either mode.
"""

from __future__ import annotations

import logging

from atlas_ai import __version__
from atlas_ai.adapters.broker.kite_broker import KiteBroker
from atlas_ai.adapters.broker.mock_broker import MockBroker
from atlas_ai.adapters.config import (
    AdapterMode,
    BrokerSource,
    FundamentalsSource,
    LLMProvider,
    MacroSource,
    MarketDataSource,
    NewsSource,
    OptionsSource,
    Settings,
    load_settings,
)
from atlas_ai.adapters.fundamentals.file_fundamentals import FileFundamentalsProvider
from atlas_ai.adapters.fundamentals.mock_fundamentals import MockFundamentals
from atlas_ai.adapters.fundamentals.yahoo_fundamentals import YahooFundamentals
from atlas_ai.adapters.llm.anthropic_llm import AnthropicLLM
from atlas_ai.adapters.llm.mock_llm import MockLLM
from atlas_ai.adapters.macro.mock_macro import MockMacro
from atlas_ai.adapters.macro.yahoo_macro import YahooMacro
from atlas_ai.adapters.market_data.kite_market_data import KiteMarketData
from atlas_ai.adapters.market_data.mock_market_data import MockMarketData
from atlas_ai.adapters.market_data.yahoo_market_data import YahooMarketData
from atlas_ai.adapters.news.google_news import GoogleNewsRSS
from atlas_ai.adapters.news.mock_news import MockNews
from atlas_ai.adapters.options.mock_options import MockOptions
from atlas_ai.adapters.options.nse_options import NseOptions
from atlas_ai.adapters.persistence.in_memory import (
    InMemoryAuditRepository,
    InMemoryRecommendationRepository,
)
from atlas_ai.application.agents.behavioral_agent import BehavioralAgent
from atlas_ai.application.agents.debate_agent import DebateAgent
from atlas_ai.application.agents.evidence_agent import EvidenceAgent
from atlas_ai.application.agents.fundamental_agent import FundamentalAgent
from atlas_ai.application.agents.learning_agent import LearningAgent
from atlas_ai.application.agents.macro_agent import MacroAgent
from atlas_ai.application.agents.memory_agent import MemoryAgent
from atlas_ai.application.agents.news_agent import NewsAgent
from atlas_ai.application.agents.options_agent import OptionsAgent
from atlas_ai.application.agents.portfolio_agent import PortfolioAgent
from atlas_ai.application.agents.quant_agent import QuantAgent
from atlas_ai.application.agents.risk_agent import RiskAgent
from atlas_ai.application.agents.technical_agent import TechnicalAgent
from atlas_ai.application.orchestration.orchestrator import Orchestrator
from atlas_ai.application.orchestration.pipeline import PIPELINE_VERSION, ResearchPipeline
from atlas_ai.application.ports.broker import BrokerPort
from atlas_ai.application.ports.fundamentals import FundamentalsPort
from atlas_ai.application.ports.llm import LLMPort
from atlas_ai.application.ports.macro import MacroPort
from atlas_ai.application.ports.market_data import MarketDataPort
from atlas_ai.application.ports.news import NewsPort
from atlas_ai.application.ports.options import OptionsPort
from atlas_ai.application.ports.repositories import (
    AuditRepository,
    RecommendationRepository,
)
from atlas_ai.application.prediction.engine import PredictionEngine
from atlas_ai.application.use_cases.generate_recommendation import GenerateRecommendation
from atlas_ai.application.use_cases.get_index_trends import GetIndexTrends
from atlas_ai.application.use_cases.get_weekly_trend import GetWeeklyTrend
from atlas_ai.domain.enums import AgentKind

logger = logging.getLogger("atlas_ai.container")


class Container:
    """Builds and holds application dependencies as singletons."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

        self.llm: LLMPort
        self.market_data: MarketDataPort
        self.fundamentals: FundamentalsPort
        self.broker: BrokerPort
        self.macro: MacroPort
        self.news: NewsPort
        self.options: OptionsPort

        # Whether the broker is the real Kite adapter (vs the mock fallback).
        self._broker_is_real = False

        if self.settings.adapter_mode is AdapterMode.MOCK:
            self.market_data = MockMarketData()
            self.fundamentals = MockFundamentals()
            self.broker = MockBroker()
            self.macro = MockMacro()
            self.news = MockNews()
            self.options = MockOptions()
        else:
            self.market_data = self._build_market_data()
            self.fundamentals = self._build_fundamentals()
            self.macro = self._build_macro()
            self.news = self._build_news()
            self.options = self._build_options()
            self.broker = self._build_broker()
            logger.warning(
                "ATLAS_ADAPTER_MODE=real: market data LIVE (%s), macro (%s), news (%s), "
                "options (%s), broker (%s).",
                self.settings.market_data_source.value,
                self.settings.macro_source.value,
                self.settings.news_source.value,
                self.settings.options_source.value,
                "kite" if self._broker_is_real else "mock (no Kite credentials)",
            )

        # The LLM is chosen independently of the market-data adapter mode.
        self.llm = self._build_llm()
        self._model_version = self.llm.model_version

        # Persistence singletons so GET-after-POST works within a process.
        self.repository: RecommendationRepository = InMemoryRecommendationRepository()
        self.audit: AuditRepository = InMemoryAuditRepository()

        self.pipeline = ResearchPipeline(
            fundamental=FundamentalAgent(),
            technical=TechnicalAgent(),
            quant=QuantAgent(),
            macro=MacroAgent(self.macro),
            news=NewsAgent(self.news),
            behavioral=BehavioralAgent(),
            options=OptionsAgent(self.options),
            portfolio=PortfolioAgent(self.broker),
            memory=MemoryAgent(self.repository),
            learning=LearningAgent(),
            risk=RiskAgent(),
            debate=DebateAgent(self.llm),
            evidence=EvidenceAgent(),
            prediction=PredictionEngine(
                simulations=self.settings.mc_simulations, seed=self.settings.mc_seed
            ),
        )

        self.orchestrator = self._build_orchestrator()

    def _build_orchestrator(self) -> Orchestrator:
        s = self.settings
        mock = s.adapter_mode is AdapterMode.MOCK

        market = (
            "Yahoo Finance prices (real)"
            if s.market_data_source is MarketDataSource.YAHOO
            else "Zerodha Kite prices (real)"
        )
        fundamentals = {
            FundamentalsSource.YAHOO: "Yahoo Finance fundamentals (real)",
            FundamentalsSource.FILE: "Researched JSON dataset (real)",
            FundamentalsSource.MOCK: "mock fundamentals",
        }[s.fundamentals_source]
        macro = (
            "Yahoo live vars + official RBI/MOSPI figures (real)"
            if s.macro_source is MacroSource.YAHOO
            else "mock macro snapshot"
        )
        news = (
            "Google News RSS + sentiment lexicon (real)"
            if s.news_source is NewsSource.GOOGLE
            else "mock headlines"
        )
        options = (
            "NSE option chain (real)"
            if s.options_source is OptionsSource.NSE
            else "mock option chain"
        )
        llm = (
            "Claude narrative (real)"
            if s.llm_provider is LLMProvider.ANTHROPIC
            else "deterministic mock narrative"
        )
        broker = (
            "Zerodha Kite holdings (real)"
            if self._broker_is_real
            else "Mock broker holdings (set Kite credentials for real)"
        )
        offline = "mock data (offline)"
        data_basis = {
            AgentKind.FUNDAMENTAL: offline if mock else fundamentals,
            AgentKind.TECHNICAL: offline if mock else market,
            AgentKind.QUANT: "Derived from price & fundamentals",
            AgentKind.MACRO: offline if mock else macro,
            AgentKind.NEWS: offline if mock else news,
            AgentKind.BEHAVIORAL: "Derived from price & volume",
            AgentKind.OPTIONS: offline if mock else options,
            AgentKind.PORTFOLIO: offline if mock else broker,
            AgentKind.MEMORY: "Recorded recommendation history",
            AgentKind.LEARNING: "Derived from price history (backtest)",
            AgentKind.RISK: "Derived from price & volatility",
            AgentKind.DEBATE: llm,
            AgentKind.EVIDENCE: "Synthesis of agent reports",
        }

        notes: list[str] = []
        if mock:
            notes.append(
                "ATLAS_ADAPTER_MODE=mock: market, fundamentals, macro, news, and "
                "options run on offline mock data."
            )
        else:
            if s.fundamentals_source is FundamentalsSource.MOCK:
                notes.append(
                    "Fundamentals are illustrative mock placeholders "
                    "(set ATLAS_FUNDAMENTALS_SOURCE=yahoo|file)."
                )
            if not self._broker_is_real:
                notes.append(
                    "Broker uses the mock adapter (set kite_api_key + "
                    "kite_access_token for real Zerodha holdings)."
                )
        if s.llm_provider is LLMProvider.MOCK:
            notes.append(
                "LLM narrative is deterministic mock "
                "(set ATLAS_LLM_PROVIDER=anthropic for Claude)."
            )

        return Orchestrator(
            app_name=s.app_name,
            version=__version__,
            adapter_mode=s.adapter_mode.value,
            pipeline_version=PIPELINE_VERSION,
            data_basis=data_basis,
            readiness_notes=tuple(notes),
        )

    def _build_llm(self) -> LLMPort:
        if self.settings.llm_provider is LLMProvider.ANTHROPIC:
            return AnthropicLLM(
                api_key=self.settings.anthropic_api_key,
                model=self.settings.anthropic_model,
                max_tokens=self.settings.anthropic_max_tokens,
            )
        return MockLLM()

    def _build_macro(self) -> MacroPort:
        if self.settings.macro_source is MacroSource.YAHOO:
            return YahooMacro(
                repo_rate_pct=self.settings.macro_repo_rate_pct,
                cpi_inflation_pct=self.settings.macro_cpi_inflation_pct,
                gdp_growth_pct=self.settings.macro_gdp_growth_pct,
                india_10y_yield_pct=self.settings.macro_india_10y_yield_pct,
                fii_flow_cr=self.settings.macro_fii_flow_cr,
            )
        return MockMacro()

    def _build_news(self) -> NewsPort:
        if self.settings.news_source is NewsSource.GOOGLE:
            return GoogleNewsRSS(query_suffix=self.settings.news_query_suffix)
        return MockNews()

    def _build_options(self) -> OptionsPort:
        if self.settings.options_source is OptionsSource.NSE:
            return NseOptions()
        return MockOptions()

    def _build_broker(self) -> BrokerPort:
        # There is no key-less broker feed; fall back to mock (loudly) when Kite
        # is selected but credentials are missing, so real mode never crashes.
        if self.settings.broker_source is BrokerSource.KITE:
            if self.settings.kite_api_key and self.settings.kite_access_token:
                self._broker_is_real = True
                return KiteBroker(
                    api_key=self.settings.kite_api_key,
                    access_token=self.settings.kite_access_token,
                )
            logger.warning(
                "ATLAS_BROKER_SOURCE=kite but kite_api_key/kite_access_token are "
                "unset: using the mock broker. Set both for real holdings."
            )
        return MockBroker()

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
        if self.settings.fundamentals_source is FundamentalsSource.YAHOO:
            return YahooFundamentals()
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

    def get_weekly_trend(self) -> GetWeeklyTrend:
        return GetWeeklyTrend(market_data=self.market_data)

    def get_index_trends(self) -> GetIndexTrends:
        return GetIndexTrends(weekly=self.get_weekly_trend())
