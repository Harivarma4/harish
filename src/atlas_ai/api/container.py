"""Composition root — the single place where ports are bound to adapters.

``ATLAS_ADAPTER_MODE`` selects the adapter set. Only ``mock`` is implemented in
this foundation build; ``real`` raises a clear, actionable error so the seam is
obvious when real adapters are added.
"""

from __future__ import annotations

from atlas_ai.adapters.broker.mock_broker import MockBroker
from atlas_ai.adapters.config import AdapterMode, Settings, load_settings
from atlas_ai.adapters.llm.mock_llm import MODEL_NAME, MockLLM
from atlas_ai.adapters.market_data.mock_market_data import MockMarketData
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
from atlas_ai.application.ports.llm import LLMPort
from atlas_ai.application.ports.market_data import MarketDataPort
from atlas_ai.application.ports.repositories import (
    AuditRepository,
    RecommendationRepository,
)
from atlas_ai.application.prediction.engine import PredictionEngine
from atlas_ai.application.use_cases.generate_recommendation import GenerateRecommendation


class Container:
    """Builds and holds application dependencies as singletons."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

        self.llm: LLMPort
        self.market_data: MarketDataPort
        self.broker: BrokerPort

        if self.settings.adapter_mode is AdapterMode.MOCK:
            self.llm = MockLLM()
            self.market_data = MockMarketData()
            self.broker = MockBroker()
            self._model_version = MODEL_NAME
        else:  # pragma: no cover - real adapters are a later phase
            raise NotImplementedError(
                "ATLAS_ADAPTER_MODE=real is not available yet. Real Zerodha/LLM "
                "adapters land in a later phase; set ATLAS_ADAPTER_MODE=mock."
            )

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

    def generate_recommendation(self) -> GenerateRecommendation:
        return GenerateRecommendation(
            market_data=self.market_data,
            pipeline=self.pipeline,
            repository=self.repository,
            audit=self.audit,
            model_version=self._model_version,
        )
