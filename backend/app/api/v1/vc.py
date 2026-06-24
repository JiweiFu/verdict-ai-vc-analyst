"""VC analysis API endpoints.

This module exposes the bring-your-own-key VC startup-evaluation pipeline. The
``/analyze`` endpoint runs the multi-agent analysis and returns the integrated
investment recommendation; ``/health`` is a lightweight liveness probe.
"""

import json
from collections.abc import AsyncIterator

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import StreamingResponse

from app.core.langgraph.vc_graph import (
    run_vc_analysis,
    stream_vc_analysis,
)
from app.core.limiter import limiter
from app.core.logging import logger
from app.schemas.startup import (
    FounderAnalysis,
    IntegratedAnalysis,
    MarketAnalysis,
    ProductAnalysis,
    StartupInfo,
)
from app.schemas.vc_api import (
    VCAnalyzeRequest,
    VCAnalyzeResponse,
)
from app.schemas.vc_history import (
    VCAnalysisDetail,
    VCAnalysisListItem,
)
from app.services.vc_memory import vc_memory
from app.services.vc_repository import vc_repository

# Maps each key in an analysis result to the Pydantic model used to reconstruct
# it when the value arrives as a plain dict (e.g. from the streaming endpoint,
# whose events are already ``model_dump()``'d).
_RESULT_MODELS: dict[str, type] = {
    "startup_info": StartupInfo,
    "market_analysis": MarketAnalysis,
    "product_analysis": ProductAnalysis,
    "founder_analysis": FounderAnalysis,
    "final": IntegratedAnalysis,
}

router = APIRouter()


def _build_memory_summary(result: dict) -> str:
    """Build a compact, key-free memory string from an analysis result.

    Only analysis content (company, scores, recommendation) is included — never
    the user's API key.
    """
    startup = result.get("startup_info")
    market = result.get("market_analysis")
    product = result.get("product_analysis")
    founder = result.get("founder_analysis")
    final = result.get("final")

    name = startup.name if startup is not None else "Unknown company"
    parts = [f"Company: {name}."]
    if startup is not None and startup.description:
        parts.append(startup.description)
    if market is not None:
        parts.append(f"Market score {market.market_viability_score}/10.")
    if product is not None:
        parts.append(f"Product score {product.potential_score}/10.")
    if founder is not None:
        parts.append(f"Founder competency {founder.competency_score}/10 (L{founder.segmentation}).")
    if final is not None:
        parts.append(f"Recommendation: {final.recommendation} (confidence {final.confidence:.0%}).")
    return " ".join(parts)


def _normalize_result(result: dict) -> dict:
    """Coerce an analysis result into one whose values are Pydantic models.

    ``run_vc_analysis`` returns Pydantic models, but the streaming endpoint's
    ``done`` event carries a ``model_dump()``'d result (plain dicts / None). The
    downstream consumers (``vc_repository.save_analysis`` and
    ``_build_memory_summary``) both expect model objects, so this rebuilds any
    dict values back into their models. Already-model and None values pass
    through unchanged, and a value that fails validation is dropped to None so
    persistence can never crash the request/stream.

    Args:
        result: The analysis result; values may be Pydantic models, dicts, or None.

    Returns:
        dict: A result whose known keys hold Pydantic models or None.
    """
    normalized: dict = dict(result)
    for key, model_cls in _RESULT_MODELS.items():
        value = normalized.get(key)
        if isinstance(value, dict):
            try:
                normalized[key] = model_cls(**value)
            except Exception:
                logger.warning("vc_result_normalize_failed", field=key)
                normalized[key] = None
    return normalized


async def _persist_analysis(result: dict, body: VCAnalyzeRequest) -> None:
    """Persist an analysis and store a compact, key-free long-term memory of it.

    Shared by the non-streaming ``/analyze`` and streaming ``/analyze/stream``
    endpoints. Tolerant of both shapes of ``result``: model-valued (from
    ``run_vc_analysis``) and dict-valued (from a streamed ``done`` event) — the
    latter is normalized back to models first. The whole body is guarded so it
    never raises and never breaks the response/stream the user already received.

    SECURITY: the api_key is never passed to, logged by, or persisted in either
    the repository or the memory store.

    Args:
        result: The analysis result (model- or dict-valued).
        body: The originating request, used only for raw_input/provider/model.
    """
    try:
        normalized = _normalize_result(result)
        final = normalized.get("final")
        analysis_id = await vc_repository.save_analysis(
            normalized, raw_input=body.raw_input, provider=body.provider, model=body.model
        )
        startup = normalized.get("startup_info")
        if startup is not None:
            await vc_memory.store_analysis(
                company_name=startup.name,
                summary=_build_memory_summary(normalized),
                recommendation=final.recommendation if final else None,
                metadata={"analysis_id": analysis_id, "provider": body.provider, "model": body.model},
            )
    except Exception as e:  # defence-in-depth; the callees already swallow errors
        logger.exception("vc_analyze_postprocess_failed", error=str(e))


@router.post("/analyze", response_model=VCAnalyzeResponse)
@limiter.limit("10 per minute")
async def analyze_startup(request: Request, body: VCAnalyzeRequest) -> VCAnalyzeResponse:
    """Run the VC analysis pipeline on a raw startup description.

    Args:
        request: The FastAPI request object, required by the rate limiter.
        body: The analysis request containing the raw input and BYO credentials.

    Returns:
        VCAnalyzeResponse: The integrated VC analysis result.

    Raises:
        HTTPException: 400 if the request is invalid (missing/unknown provider or
            api_key); 502 if the LLM provider call itself fails.
    """
    logger.info("vc_analyze_requested", provider=body.provider, model=body.model)
    try:
        result = await run_vc_analysis(
            raw_input=body.raw_input,
            provider=body.provider,
            model=body.model,
            api_key=body.api_key,
        )
    except ValueError as e:
        logger.warning("vc_analyze_bad_request", provider=body.provider, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("vc_analyze_llm_failed", provider=body.provider, error=str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="llm provider call failed")

    final = result.get("final")
    logger.info(
        "vc_analyze_completed",
        provider=body.provider,
        model=body.model,
        recommendation=final.recommendation if final else None,
    )

    # Persist the analysis + store a compact long-term memory of it. The helper
    # is internally guarded (never raises) and must NOT break the response — the
    # user already has their answer. The api_key is never passed to it.
    await _persist_analysis(result, body)

    return VCAnalyzeResponse(**result)


@router.post("/analyze/stream")
@limiter.limit("10 per minute")
async def analyze_startup_stream(request: Request, body: VCAnalyzeRequest) -> StreamingResponse:
    """Stream the VC analysis pipeline as newline-delimited JSON (NDJSON) events.

    Mirrors ``/analyze`` but emits incremental progress so the dashboard can
    render per-agent status. Each line is one JSON event (``node_start``,
    ``node_complete``, ``done`` or ``error``). After a successful ``done`` event,
    the same persistence + memory post-processing as ``/analyze`` runs.

    Args:
        request: The FastAPI request object, required by the rate limiter.
        body: The analysis request containing the raw input and BYO credentials.

    Returns:
        StreamingResponse: An ``application/x-ndjson`` stream of analysis events.
    """
    logger.info("vc_analyze_stream_requested", provider=body.provider, model=body.model)

    async def event_stream() -> AsyncIterator[str]:
        result: dict | None = None
        try:
            async for event in stream_vc_analysis(
                raw_input=body.raw_input,
                provider=body.provider,
                model=body.model,
                api_key=body.api_key,
                agent_feedback=body.agent_feedback,
            ):
                if event.get("type") == "done":
                    result = event.get("result")
                yield json.dumps(event) + "\n"
        except Exception as e:
            # SECURITY: only the error message is surfaced — never the api_key.
            logger.exception("vc_analyze_stream_failed", provider=body.provider, error=str(e))
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"
            return

        # Stream finished cleanly; run the same key-free post-processing as
        # /analyze using the streamed (dict-valued) result.
        if result is not None:
            logger.info("vc_analyze_stream_completed", provider=body.provider, model=body.model)
            await _persist_analysis(result, body)

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/analyses", response_model=list[VCAnalysisListItem])
@limiter.limit("60 per minute")
async def list_analyses(request: Request, limit: int = 50, offset: int = 0) -> list[VCAnalysisListItem]:
    """List persisted VC analyses (most recent first) for the dashboard.

    Args:
        request: The FastAPI request object, required by the rate limiter.
        limit: Maximum number of records to return (default 50).
        offset: Number of records to skip for pagination (default 0).

    Returns:
        list[VCAnalysisListItem]: Lightweight rows (no full result payload).
    """
    logger.info("vc_analyses_listed", limit=limit, offset=offset)
    return await vc_repository.list_analyses(limit=limit, offset=offset)


@router.get("/analyses/{analysis_id}", response_model=VCAnalysisDetail)
@limiter.limit("60 per minute")
async def get_analysis(request: Request, analysis_id: int) -> VCAnalysisDetail:
    """Fetch a single persisted VC analysis, including its full result payload.

    Args:
        request: The FastAPI request object, required by the rate limiter.
        analysis_id: The primary key of the analysis to retrieve.

    Returns:
        VCAnalysisDetail: The full record.

    Raises:
        HTTPException: 404 when no analysis with that id exists.
    """
    record = await vc_repository.get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="analysis not found")
    logger.info("vc_analysis_fetched", analysis_id=analysis_id)
    return record


@router.get("/health")
async def vc_health() -> dict:
    """Report liveness for the VC analysis router.

    Returns:
        dict: A simple status payload.
    """
    logger.info("vc_health_called")
    return {"status": "ok"}
