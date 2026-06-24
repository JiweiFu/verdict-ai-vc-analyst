"""This file contains the VC analysis repository for the application.

SECURITY: This repository NEVER receives or stores the user's LLM API key. The
``save_analysis`` method only persists analysis content, the provider/model name,
and derived metadata — there is no code path that writes a secret.
"""

from typing import Optional

from sqlmodel import (
    Session,
    col,
    select,
)

from app.core.logging import logger
from app.models.vc_analysis import VCAnalysis
from app.schemas.vc_history import (
    VCAnalysisDetail,
    VCAnalysisListItem,
)
from app.services.database import database_service


class VCRepository:
    """Repository for persisting and reading VC analysis results.

    Mirrors the template's ``DatabaseService`` pattern: methods are ``async def``
    but use a synchronous ``with Session(...)`` block inside. Persistence failures
    must never break the calling request, so every method swallows exceptions and
    returns a safe fallback.
    """

    async def save_analysis(
        self,
        result: dict,
        *,
        raw_input: str,
        provider: str,
        model: str,
    ) -> Optional[int]:
        """Persist a VC analysis result and return the new row id.

        SECURITY: ``result`` contains no API key and none is added here. Only the
        analysis content, provider/model name, and derived scores are stored.

        Args:
            result: The ``run_vc_analysis`` dict; values are Pydantic models or None.
            raw_input: The raw company description that was analyzed.
            provider: The LLM provider name.
            model: The LLM model NAME string (never a key).

        Returns:
            Optional[int]: The new row id, or None if persistence failed.
        """
        try:
            startup_info = result.get("startup_info")
            market_analysis = result.get("market_analysis")
            product_analysis = result.get("product_analysis")
            founder_analysis = result.get("founder_analysis")
            final = result.get("final")

            company_name = startup_info.name if startup_info is not None else "Unknown"
            market_score = market_analysis.market_viability_score if market_analysis is not None else None
            product_score = product_analysis.potential_score if product_analysis is not None else None
            founder_competency = founder_analysis.competency_score if founder_analysis is not None else None
            founder_segmentation = founder_analysis.segmentation if founder_analysis is not None else None
            recommendation = final.recommendation if final is not None else None
            confidence = final.confidence if final is not None else None

            serialized = {k: (v.model_dump() if v is not None else None) for k, v in result.items()}

            row = VCAnalysis(
                company_name=company_name,
                raw_input=raw_input,
                provider=provider,
                model=model,
                recommendation=recommendation,
                confidence=confidence,
                founder_segmentation=founder_segmentation,
                market_score=market_score,
                product_score=product_score,
                founder_competency=founder_competency,
                result=serialized,
            )

            with Session(database_service.engine) as session:
                session.add(row)
                session.commit()
                session.refresh(row)
                logger.info(
                    "vc_analysis_persisted",
                    analysis_id=row.id,
                    company_name=company_name,
                    recommendation=recommendation,
                )
                return row.id
        except Exception:
            logger.exception("vc_analysis_persist_failed", provider=provider, model=model)
            return None

    async def list_analyses(self, limit: int = 50, offset: int = 0) -> list[VCAnalysisListItem]:
        """List stored VC analyses, most recent first.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip.

        Returns:
            list[VCAnalysisListItem]: Summary items, or an empty list on failure.
        """
        try:
            with Session(database_service.engine) as session:
                statement = (
                    select(VCAnalysis)
                    .order_by(col(VCAnalysis.created_at).desc())
                    .offset(offset)
                    .limit(limit)
                )
                rows = session.exec(statement).all()
                return [
                    VCAnalysisListItem(
                        id=row.id if row.id is not None else 0,
                        created_at=row.created_at,
                        company_name=row.company_name,
                        recommendation=row.recommendation,
                        confidence=row.confidence,
                        market_score=row.market_score,
                        product_score=row.product_score,
                        founder_competency=row.founder_competency,
                        founder_segmentation=row.founder_segmentation,
                    )
                    for row in rows
                ]
        except Exception:
            logger.exception("vc_analysis_list_failed")
            return []

    async def get_analysis(self, analysis_id: int) -> Optional[VCAnalysisDetail]:
        """Fetch a single stored VC analysis by id.

        Args:
            analysis_id: The id of the analysis to retrieve.

        Returns:
            Optional[VCAnalysisDetail]: The detail view, or None if not found / on failure.
        """
        try:
            with Session(database_service.engine) as session:
                row = session.get(VCAnalysis, analysis_id)
                if row is None:
                    return None
                return VCAnalysisDetail(
                    id=row.id if row.id is not None else 0,
                    created_at=row.created_at,
                    company_name=row.company_name,
                    recommendation=row.recommendation,
                    confidence=row.confidence,
                    market_score=row.market_score,
                    product_score=row.product_score,
                    founder_competency=row.founder_competency,
                    founder_segmentation=row.founder_segmentation,
                    raw_input=row.raw_input,
                    provider=row.provider,
                    model=row.model,
                    result=row.result,
                )
        except Exception:
            logger.exception("vc_analysis_get_failed", analysis_id=analysis_id)
            return None


# Create a singleton instance
vc_repository = VCRepository()
