"""Prediction data model.

This module defines the Prediction, PredictionResult models and Recommendation
enum for representing LLM prediction data.

Usage:
    from src.models.prediction import Prediction, PredictionResult, Recommendation

    # LLM raw result
    result = PredictionResult(
        predicted_probability=0.72,
        confidence=0.85,
        reasoning="Strong technical indicators...",
        recommendation=Recommendation.BUY_YES,
    )

    # Stored prediction
    prediction = Prediction(
        id=1,
        market_id="market-123",
        predicted_probability=0.72,
        confidence=0.85,
        reasoning="Strong technical indicators...",
        recommendation=Recommendation.BUY_YES,
    )
"""

from __future__ import annotations

__all__ = ["Prediction", "PredictionResult", "Recommendation"]

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Recommendation(str, Enum):
    """LLM recommendation enumeration.

    Defines the possible trading recommendations from LLM analysis.

    Attributes:
        BUY_YES: LLM recommends buying YES outcome
        BUY_NO: LLM recommends buying NO outcome
        NO_TRADE: LLM recommends no trade (edge too low)
    """

    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_TRADE = "NO_TRADE"


class PredictionResult(BaseModel):
    """LLM raw prediction result model.

    Represents the structured output from LLM analysis.
    Used for parsing LLM JSON responses.

    Attributes:
        predicted_probability: LLM predicted probability (0-1)
        confidence: LLM confidence in prediction (0-1)
        reasoning: Explanation for the prediction
        key_assumptions: List of key assumptions made
        recommendation: Trading recommendation
        edge: Edge (price gap) between prediction and market price (0-1)

    Example:
        >>> result = PredictionResult(
        ...     predicted_probability=0.72,
        ...     confidence=0.85,
        ...     reasoning="Based on current market trends...",
        ...     key_assumptions=["Economic stability continues", "No major news events"],
        ...     recommendation=Recommendation.BUY_YES,
        ...     edge=0.15,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    predicted_probability: float = Field(
        ..., ge=0, le=1, description="Predicted probability (0-1)"
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence level (0-1)")
    reasoning: str = Field(..., min_length=1, description="Prediction reasoning")
    key_assumptions: list[str] = Field(
        default_factory=list, description="Key assumptions"
    )
    recommendation: Recommendation = Field(..., description="Trading recommendation")
    edge: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Edge (price gap) between prediction and market",
    )
    # Detailed analysis fields for PredictionResult (transient, not saved to DB directly)
    web_search_query: str | None = Field(
        default=None, description="Web search query used for analysis"
    )
    web_search_summary: str | None = Field(
        default=None, description="Web search results summary"
    )
    llm_prompt: str | None = Field(
        default=None, description="Full LLM prompt sent for analysis"
    )
    llm_response: str | None = Field(
        default=None, description="Full LLM response received"
    )


class Prediction(BaseModel):
    """Stored prediction data model.

    Represents a prediction record stored in the database.
    Includes all fields from PredictionResult plus metadata and validation status.

    Attributes:
        id: Unique prediction identifier (auto-generated)
        market_id: Reference to the market
        predicted_probability: LLM predicted probability (0-1)
        confidence: LLM confidence in prediction (0-1)
        reasoning: Explanation for the prediction
        key_assumptions: List of key assumptions made
        model_used: LLM model used for prediction
        recommendation: Trading recommendation
        edge: Edge (price gap) between prediction and market price (0-1)
        actual_outcome: Actual market outcome (for validation)
        is_correct: Whether prediction was correct
        validated_at: When prediction was validated
        created_at: Prediction creation timestamp

    Example:
        >>> prediction = Prediction(
        ...     id=1,
        ...     market_id="btc-100k-2026",
        ...     predicted_probability=0.72,
        ...     confidence=0.85,
        ...     reasoning="Strong technical indicators...",
        ...     recommendation=Recommendation.BUY_YES,
        ...     model_used="glm-4",
        ...     edge=0.15,
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: int | None = Field(default=None, description="Prediction unique identifier")
    market_id: str = Field(..., description="Market reference")
    predicted_probability: float = Field(
        ..., ge=0, le=1, description="Predicted probability (0-1)"
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence level (0-1)")
    reasoning: str | None = Field(default=None, description="Prediction reasoning")
    key_assumptions: list[str] | None = Field(
        default=None, description="Key assumptions"
    )
    model_used: str | None = Field(default=None, description="LLM model used")
    recommendation: Recommendation | None = Field(
        default=None, description="Trading recommendation"
    )
    edge: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Edge (price gap) between prediction and market",
    )
    actual_outcome: str | None = Field(default=None, description="Actual outcome")
    is_correct: bool | None = Field(default=None, description="Prediction correctness")
    validated_at: datetime | None = Field(
        default=None, description="Validation timestamp"
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    # Detailed analysis fields
    web_search_query: str | None = Field(default=None, description="Web search query used")
    web_search_summary: str | None = Field(default=None, description="Web search results summary")
    llm_prompt: str | None = Field(default=None, description="Full LLM prompt sent")
    llm_response: str | None = Field(default=None, description="Full LLM response received")
    trade_executed: bool | None = Field(default=None, description="Whether trade was executed")
    trade_result: str | None = Field(default=None, description="Trade execution result")
    trade_error: str | None = Field(default=None, description="Trade execution error if failed")

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
