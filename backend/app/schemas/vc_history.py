"""Pydantic response schemas for the VC analysis history API.

These shape the stored ``VCAnalysis`` rows for read endpoints. Note that no
schema here exposes an API key — the model never stores one.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VCAnalysisListItem(BaseModel):
    """Summary view of a stored VC analysis for list endpoints."""

    id: int
    created_at: datetime
    company_name: str
    recommendation: Optional[str]
    confidence: Optional[float]
    market_score: Optional[int]
    product_score: Optional[int]
    founder_competency: Optional[int]
    founder_segmentation: Optional[int]


class VCAnalysisDetail(BaseModel):
    """Full view of a stored VC analysis, including the raw input and result."""

    id: int
    created_at: datetime
    company_name: str
    recommendation: Optional[str]
    confidence: Optional[float]
    market_score: Optional[int]
    product_score: Optional[int]
    founder_competency: Optional[int]
    founder_segmentation: Optional[int]
    raw_input: str
    provider: str
    model: str
    result: dict
