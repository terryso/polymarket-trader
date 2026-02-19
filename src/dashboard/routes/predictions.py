"""Prediction data API routes.

This module provides REST API endpoints for prediction operations.

Story 7.4: 预测与统计 API
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.api_response import (
    ApiResponse,
    ErrorCode,
    PaginatedResponse,
    PaginationMeta,
)
from src.models.prediction_response import (
    AccuracyStats,
    CategoryAccuracy,
    PredictionListItem,
    PredictionResponse,
)
from src.storage.repositories.prediction_repo import (
    PaginationParams,
    PredictionOutcomeStatus,
    PredictionRepository,
    SortParams,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_prediction_repository() -> PredictionRepository:
    """Get PredictionRepository instance.

    Returns:
        PredictionRepository instance
    """
    return PredictionRepository()


@router.get("", response_model=PaginatedResponse[PredictionListItem])
async def list_predictions(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    validated: Annotated[
        bool | None, Query(description="Filter by validation status")
    ] = None,
    repo: PredictionRepository = Depends(get_prediction_repository),
) -> PaginatedResponse[PredictionListItem]:
    """Get prediction history with pagination and filtering.

    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        validated: Filter by validation status
        repo: PredictionRepository dependency

    Returns:
        Paginated list of predictions with market info
    """
    logger.info(
        f"📊 Listing predictions: page={page}, per_page={per_page}, validated={validated}"
    )

    # Determine status filter
    if validated is True:
        # Use get_validated_with_market for validated predictions
        validated_with_markets = await repo.get_validated_with_market()
        total = len(validated_with_markets)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = validated_with_markets[start:end]

        items = [
            PredictionListItem(
                id=p.id if p.id is not None else 0,
                market_id=p.market_id,
                market_title=m.title,
                market_slug=m.slug,
                market_yes_price=m.yes_price,
                predicted_probability=p.predicted_probability,
                confidence=p.confidence,
                edge=p.edge,
                recommendation=p.recommendation.value if p.recommendation else None,
                actual_outcome=p.actual_outcome,
                is_correct=p.is_correct,
                created_at=p.created_at,
            )
            for p, m in paginated
        ]
    else:
        # Use get_predictions_with_outcome for all predictions with market info
        status = PredictionOutcomeStatus.ALL
        if validated is False:
            status = PredictionOutcomeStatus.PENDING

        result = await repo.get_predictions_with_outcome(
            status=status,
            pagination=PaginationParams(page=page, per_page=per_page),
            sort=SortParams(),
        )
        total = result.total

        items = [
            PredictionListItem(
                id=p.id if p.id is not None else 0,
                market_id=p.market_id,
                market_title=m.title,
                market_slug=m.slug,
                market_yes_price=m.yes_price,
                predicted_probability=p.predicted_probability,
                confidence=p.confidence,
                edge=p.edge,
                recommendation=p.recommendation.value if p.recommendation else None,
                actual_outcome=p.actual_outcome,
                is_correct=p.is_correct,
                created_at=p.created_at,
            )
            for p, m in result.predictions
        ]

    return PaginatedResponse(
        success=True,
        data=items,
        meta=PaginationMeta(total=total, page=page, per_page=per_page),
    )


@router.get("/accuracy", response_model=ApiResponse[AccuracyStats])
async def get_accuracy(
    repo: PredictionRepository = Depends(get_prediction_repository),
) -> ApiResponse[AccuracyStats]:
    """Get prediction accuracy statistics.

    Args:
        repo: PredictionRepository dependency

    Returns:
        Accuracy statistics
    """
    logger.info("📊 Getting prediction accuracy statistics")

    # Get all predictions
    all_predictions = await repo.get_all(limit=10000)

    # Calculate statistics
    total = len(all_predictions)
    validated = [p for p in all_predictions if p.is_correct is not None]
    correct = [p for p in validated if p.is_correct is True]

    validated_count = len(validated)
    correct_count = len(correct)
    accuracy = correct_count / validated_count if validated_count > 0 else 0.0
    avg_confidence = (
        sum(p.confidence for p in all_predictions) / total if total > 0 else 0.0
    )

    # TODO: Calculate by_category when market categories are available
    by_category: dict[str, CategoryAccuracy] = {}

    stats = AccuracyStats(
        total_predictions=total,
        validated_predictions=validated_count,
        correct_predictions=correct_count,
        accuracy=accuracy,
        avg_confidence=avg_confidence,
        by_category=by_category,
    )

    return ApiResponse(success=True, data=stats, error=None)


@router.get("/{prediction_id}", response_model=ApiResponse[PredictionResponse])
async def get_prediction(
    prediction_id: int,
    repo: PredictionRepository = Depends(get_prediction_repository),
) -> ApiResponse[PredictionResponse]:
    """Get prediction details by ID.

    Args:
        prediction_id: Prediction ID
        repo: PredictionRepository dependency

    Returns:
        Prediction details

    Raises:
        HTTPException: If prediction not found
    """
    logger.info(f"📊 Getting prediction: {prediction_id}")

    prediction = await repo.get_by_id(prediction_id)

    if prediction is None:
        logger.warning(f"📊 Prediction not found: {prediction_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.NOT_FOUND,
                    "message": f"Prediction not found: {prediction_id}",
                },
            },
        )

    response = PredictionResponse(
        id=prediction.id if prediction.id is not None else 0,
        market_id=prediction.market_id,
        predicted_probability=prediction.predicted_probability,
        confidence=prediction.confidence,
        reasoning=prediction.reasoning,
        key_assumptions=prediction.key_assumptions,
        model_used=prediction.model_used,
        recommendation=(
            prediction.recommendation.value if prediction.recommendation else None
        ),
        actual_outcome=prediction.actual_outcome,
        is_correct=prediction.is_correct,
        validated_at=prediction.validated_at,
        created_at=prediction.created_at,
    )

    return ApiResponse(success=True, data=response, error=None)


__all__ = ["router"]
