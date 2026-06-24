"""Pydantic request/response schemas for the VC analysis API.

These models wrap the VC evaluation pipeline's inputs and outputs so the
``/api/v1/vc/analyze`` endpoint can validate the incoming request and serialize
the integrated analysis result back to the caller.
"""

from typing import (
    Literal,
    Optional,
    TypedDict,
)

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


class VCAnalyzeRequest(BaseModel):
    """Request body for a VC startup analysis run."""

    raw_input: str = Field(..., description="Raw text description of the startup to analyze")
    provider: str = Field("anthropic", description="The LLM provider to use for the analysis")
    model: str = Field("claude-opus-4-8", description="The model identifier to use for the analysis")
    api_key: str = Field(..., description="The user's bring-your-own-key credential for the LLM provider")
    agent_feedback: Optional[dict[str, str]] = Field(
        None,
        description="Optional per-agent feedback (node name -> feedback text) to steer a re-run analysis",
    )


class VCStreamEvent(TypedDict, total=False):
    """Documents the NDJSON events emitted by ``/analyze/stream``.

    Each streamed line is a JSON object with a ``type`` discriminator:

    - ``node_start``: an agent node began. Carries ``node``.
    - ``node_complete``: an agent node finished. Carries ``node`` and ``data``
      (the node's output object, or null).
    - ``done``: the run finished. Carries ``result`` (the full analysis payload:
      ``startup_info``, ``market_analysis``, ``product_analysis``,
      ``founder_analysis``, ``final``).
    - ``error``: the run failed. Carries ``detail`` (a human-readable message;
      never the api_key).
    """

    type: Literal["node_start", "node_complete", "done", "error"]
    node: str
    data: Optional[dict]
    result: dict
    detail: str


class VCAnalyzeResponse(BaseModel):
    """Response body mirroring the VC analysis pipeline output."""

    startup_info: Optional[StartupInfo] = Field(None, description="Structured startup profile parsed from the input")
    market_analysis: Optional[MarketAnalysis] = Field(None, description="Market analyst's assessment")
    product_analysis: Optional[ProductAnalysis] = Field(None, description="Product expert's assessment")
    founder_analysis: Optional[FounderAnalysis] = Field(None, description="Founder analyst's assessment")
    final: Optional[IntegratedAnalysis] = Field(None, description="Chief analyst's integrated recommendation")
