"""Pydantic schemas for the VC startup-evaluation pipeline.

These models mirror the SSFF research codebase's agent outputs, adapted to the
template's conventions. All numeric scores use bounded integer/float fields so
the LLM's structured output is validated on the way in.
"""

from typing import (
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)


class StartupInfo(BaseModel):
    """Structured profile of a startup parsed from a raw text description.

    Only ``name`` and ``description`` are required; every other field is
    optional so the scout node can populate as much as the source text allows.
    """

    name: str = Field(..., description="The official name of the startup")
    description: str = Field(..., description="A brief overview of what the startup does")
    market_size: Optional[str] = Field(None, description="The size of the market the startup is targeting")
    growth_rate: Optional[str] = Field(None, description="The growth rate of the market")
    competition: Optional[str] = Field(None, description="Key competitors in the space")
    market_trends: Optional[str] = Field(None, description="Current trends within the market")
    go_to_market_strategy: Optional[str] = Field(None, description="The startup's plan for entering the market")
    product_details: Optional[str] = Field(None, description="Details about the startup's product or service")
    technology_stack: Optional[str] = Field(None, description="Technologies used in the product")
    scalability: Optional[str] = Field(None, description="How the product can scale")
    user_feedback: Optional[str] = Field(None, description="Any feedback received from users")
    product_fit: Optional[str] = Field(None, description="How well the product fits the target market")
    founder_backgrounds: Optional[str] = Field(None, description="Background information on the founders")
    track_records: Optional[str] = Field(None, description="The track records of the founders")
    leadership_skills: Optional[str] = Field(None, description="Leadership skills of the team")
    vision_alignment: Optional[str] = Field(None, description="How the team's vision aligns with the product")
    team_dynamics: Optional[str] = Field(None, description="The dynamics within the startup team")
    web_traffic_growth: Optional[str] = Field(None, description="Growth of web traffic to the startup's site")
    social_media_presence: Optional[str] = Field(None, description="The startup's presence on social media")
    investment_rounds: Optional[str] = Field(None, description="Details of any investment rounds")
    regulatory_approvals: Optional[str] = Field(None, description="Any regulatory approvals obtained")
    patents: Optional[str] = Field(None, description="Details of any patents held by the startup")


class MarketAnalysis(BaseModel):
    """Market analyst's assessment of the startup's market opportunity."""

    market_size: str = Field(..., description="Estimated market size")
    growth_potential: str = Field(..., description="Assessment of market growth potential")
    competition: str = Field(..., description="Overview of the competitive landscape")
    market_viability_score: int = Field(..., ge=1, le=10, description="Market viability score from 1 to 10")
    analysis: str = Field(..., description="Comprehensive market analysis narrative")


class ProductAnalysis(BaseModel):
    """Product expert's assessment of the startup's product."""

    innovation: str = Field(..., description="Assessment of the product's technical innovation")
    scalability: str = Field(..., description="Assessment of how well the product can scale")
    product_market_fit: str = Field(..., description="Assessment of the product-market fit")
    potential_score: int = Field(..., ge=1, le=10, description="Product potential score from 1 to 10")
    analysis: str = Field(..., description="Comprehensive product analysis narrative")


class FounderAnalysis(BaseModel):
    """Founder analyst's assessment of the founding team.

    ``segmentation`` is an LLM-only classification on the L1-L5 scale (1 = L1,
    5 = L5); the original ML idea-fit model has been dropped.
    """

    competency_score: int = Field(..., ge=1, le=10, description="Founder competency score from 1 to 10")
    segmentation: int = Field(..., ge=1, le=5, description="Founder segmentation level, 1 (L1) to 5 (L5)")
    analysis: str = Field(..., description="Detailed analysis of the founding team's strengths and challenges")


class IntegratedAnalysis(BaseModel):
    """Chief analyst's final, integrated investment recommendation."""

    overall_assessment: str = Field(..., description="Overall assessment of the startup")
    recommendation: Literal["Invest", "Hold", "Pass"] = Field(..., description="Final investment recommendation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the recommendation, 0 to 1")
    key_strengths: list[str] = Field(default_factory=list, description="Key strengths supporting the recommendation")
    key_risks: list[str] = Field(default_factory=list, description="Key risks against the recommendation")
    rationale: str = Field(..., description="Comprehensive rationale for the recommendation")
