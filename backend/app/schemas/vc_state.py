"""LangGraph state schema for the VC startup-evaluation pipeline."""

from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)

from app.schemas.startup import (
    FounderAnalysis,
    IntegratedAnalysis,
    MarketAnalysis,
    ProductAnalysis,
    StartupInfo,
)


class VCState(BaseModel):
    """State for the VC analysis graph.

    The pipeline fills these fields in order: ``scout_node`` populates
    ``startup_info`` from ``raw_input``; the three analyst nodes run in parallel
    to populate ``market_analysis``/``product_analysis``/``founder_analysis``;
    and ``chief_node`` integrates them into ``final``.

    ``provider``/``model``/``api_key`` carry the bring-your-own-key LLM
    configuration through every node so each call targets the user's chosen
    provider with the user's own credentials.
    """

    raw_input: str = Field(..., description="The raw company description supplied by the user")
    provider: str = Field(default="anthropic", description="LLM provider: 'anthropic', 'openai', or 'deepseek'")
    model: str = Field(default="claude-opus-4-8", description="The provider-specific model name")
    api_key: str = Field(default="", description="The user's API key for the chosen provider (bring-your-own-key)")
    startup_info: Optional[StartupInfo] = Field(default=None, description="Parsed structured startup profile")
    market_analysis: Optional[MarketAnalysis] = Field(default=None, description="Market analyst output")
    product_analysis: Optional[ProductAnalysis] = Field(default=None, description="Product analyst output")
    founder_analysis: Optional[FounderAnalysis] = Field(default=None, description="Founder analyst output")
    past_evaluations: str = Field(
        default="",
        description="Recalled summary of similar past analyses (from long-term memory), injected into the chief node",
    )
    final: Optional[IntegratedAnalysis] = Field(default=None, description="Chief analyst's integrated recommendation")
    agent_feedback: dict[str, str] = Field(
        default_factory=dict,
        description="Optional per-agent user feedback, keyed by node name",
    )
