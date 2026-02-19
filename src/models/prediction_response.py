"""Prediction API response models.

This module defines Pydantic models for prediction API responses.

Story 7.4: 预测与统计 API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class PredictionListItem(BaseModel):
    """Prediction list item for API list responses.

    Contains prediction fields for list display.

    Attributes:
        id: Prediction unique identifier
        market_id: Reference to the market
        market_title: Title of the market
        market_slug: Slug for Polymarket URL
        predicted_probability: Predicted probability (0-1)
        confidence: LLM confidence (0-1)
        recommendation: Trade recommendation
        actual_outcome: Actual market outcome (if resolved)
        is_correct: Whether prediction was correct (if validated)
        created_at: Prediction creation timestamp
    """

    id: int = Field(..., description="Prediction ID")
    market_id: str = Field(..., description="Market reference")
    market_title: str | None = Field(None, description="Market title")
    market_slug: str | None = Field(None, description="Market slug for URL")
    predicted_probability: float = Field(..., description="Predicted probability (0-1)")
    confidence: float = Field(..., description="LLM confidence (0-1)")
    recommendation: str | None = Field(None, description="Trade recommendation")
    actual_outcome: str | None = Field(None, description="Actual outcome")
    is_correct: bool | None = Field(None, description="Prediction correctness")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format.

        Args:
            dt: The datetime value to serialize
            _info: Field serializer info (unused)

        Returns:
            ISO 8601 formatted string or None
        """
        if dt is None:
            return None
        return dt.isoformat()


class PredictionResponse(BaseModel):
    """Full prediction details for API detail responses.

    Contains all prediction fields for detailed view.

    Attributes:
        id: Prediction unique identifier
        market_id: Reference to the market
        predicted_probability: Predicted probability (0-1)
        confidence: LLM confidence (0-1)
        reasoning: LLM analysis reasoning
        key_assumptions: Key assumptions made
        model_used: LLM model used
        recommendation: Trade recommendation
        actual_outcome: Actual market outcome (if resolved)
        is_correct: Whether prediction was correct (if validated)
        validated_at: Validation timestamp
        created_at: Prediction creation timestamp
    """

    id: int = Field(..., description="Prediction ID")
    market_id: str = Field(..., description="Market reference")
    predicted_probability: float = Field(..., description="Predicted probability (0-1)")
    confidence: float = Field(..., description="LLM confidence (0-1)")
    reasoning: str | None = Field(None, description="Analysis reasoning")
    key_assumptions: list[str] | None = Field(None, description="Key assumptions")
    model_used: str | None = Field(None, description="LLM model")
    recommendation: str | None = Field(None, description="Trade recommendation")
    actual_outcome: str | None = Field(None, description="Actual outcome")
    is_correct: bool | None = Field(None, description="Prediction correctness")
    validated_at: datetime | None = Field(None, description="Validation timestamp")
    created_at: datetime | None = Field(None, description="Creation timestamp")

    @field_serializer("validated_at", "created_at")
    def serialize_datetime(self, dt: datetime | None, _info: Any) -> str | None:
        """Serialize datetime to ISO 8601 format.

        Args:
            dt: The datetime value to serialize
            _info: Field serializer info (unused)

        Returns:
            ISO 8601 formatted string or None
        """
        if dt is None:
            return None
        return dt.isoformat()


class CategoryAccuracy(BaseModel):
    """Accuracy statistics for a category.

    Attributes:
        total: Total predictions in category
        correct: Correct predictions
        accuracy: Accuracy rate (0-1)
    """

    total: int = Field(..., description="Total predictions")
    correct: int = Field(..., description="Correct predictions")
    accuracy: float = Field(..., description="Accuracy rate (0-1)")


class AccuracyStats(BaseModel):
    """Overall prediction accuracy statistics.

    Attributes:
        total_predictions: Total number of predictions
        validated_predictions: Number of validated predictions
        correct_predictions: Number of correct predictions
        accuracy: Overall accuracy rate (0-1)
        avg_confidence: Average confidence across all predictions
        by_category: Accuracy breakdown by category
    """

    total_predictions: int = Field(..., description="Total predictions")
    validated_predictions: int = Field(..., description="Validated predictions")
    correct_predictions: int = Field(..., description="Correct predictions")
    accuracy: float = Field(..., description="Overall accuracy (0-1)")
    avg_confidence: float = Field(..., description="Average confidence")
    by_category: dict[str, CategoryAccuracy] = Field(
        default_factory=dict, description="Accuracy by category"
    )


__all__ = [
    "PredictionListItem",
    "PredictionResponse",
    "CategoryAccuracy",
    "AccuracyStats",
]
