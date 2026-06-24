"""This file contains the VC analysis model for the application.

SECURITY: The user's LLM ``api_key`` arrives per-request but is NEVER persisted.
This table intentionally has NO ``api_key`` column. Only the analysis content,
the provider/model NAME, and derived metadata are stored — never any secret.
"""

from typing import Optional

from sqlalchemy import (
    JSON,
    Column,
)
from sqlmodel import Field

from app.models.base import BaseModel


class VCAnalysis(BaseModel, table=True):
    """VC analysis model for storing startup-evaluation pipeline results.

    SECURITY: There is intentionally NO ``api_key`` column. The user's LLM API
    key is supplied per-request and must never be written to the database. Only
    the analysis content, provider/model name, and derived scores are stored.

    Attributes:
        id: The primary key
        created_at: When the analysis was persisted (from BaseModel)
        company_name: The startup's name (indexed for lookup)
        raw_input: The raw company description that was analyzed
        provider: The LLM provider name (e.g. "anthropic")
        model: The LLM model NAME string (e.g. "claude-opus-4-8") — NOT a key
        recommendation: Final recommendation ("Invest" / "Hold" / "Pass")
        confidence: Confidence in the recommendation, 0 to 1
        founder_segmentation: Founder segmentation level, 1 (L1) to 5 (L5)
        market_score: Market viability score, 1 to 10
        product_score: Product potential score, 1 to 10
        founder_competency: Founder competency score, 1 to 10
        result: The full structured analysis serialized as JSON
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str = Field(index=True)
    raw_input: str
    provider: str
    model: str
    recommendation: Optional[str] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
    founder_segmentation: Optional[int] = Field(default=None)
    market_score: Optional[int] = Field(default=None)
    product_score: Optional[int] = Field(default=None)
    founder_competency: Optional[int] = Field(default=None)
    result: dict = Field(default_factory=dict, sa_column=Column(JSON))
