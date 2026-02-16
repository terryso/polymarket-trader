"""Prediction tracking and validation.

Story 6.1: 预测结果验证机制

This module provides functionality to validate LLM predictions against
resolved market outcomes and calculate accuracy statistics.
"""

from __future__ import annotations

__all__ = ["PredictionTracker", "ValidationResult", "AccuracyResult"]

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.models.prediction import Prediction, Recommendation
from src.utils.logger import OPERATION_EMOJIS, get_logger

if TYPE_CHECKING:
    from src.storage.repositories.market_repo import MarketRepository
    from src.storage.repositories.prediction_repo import PredictionRepository

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a single prediction validation.

    Attributes:
        prediction_id: ID of the validated prediction
        is_validated: Whether the prediction was validated
        is_correct: Whether the prediction was correct (None if not validated)
        actual_outcome: Actual market outcome
        reason: Optional reason if not validated
    """

    prediction_id: int
    is_validated: bool
    is_correct: bool | None
    actual_outcome: str | None
    reason: str | None = None


@dataclass
class AccuracyResult:
    """Accuracy calculation result.

    Attributes:
        total: Total validated predictions
        correct: Number of correct predictions
        accuracy: Accuracy ratio (0-1), None if no predictions
    """

    total: int
    correct: int
    accuracy: float | None


class PredictionTracker:
    """Tracker for prediction validation and accuracy.

    Validates predictions against resolved market outcomes and
    calculates accuracy statistics.

    Example:
        >>> tracker = PredictionTracker(market_repo, prediction_repo)
        >>> results = await tracker.check_resolved_markets()
        >>> print(f"Validated {len(results)} predictions")
    """

    def __init__(
        self,
        market_repo: MarketRepository,
        prediction_repo: PredictionRepository,
    ) -> None:
        """Initialize the PredictionTracker.

        Args:
            market_repo: Repository for market data
            prediction_repo: Repository for prediction data
        """
        self._market_repo = market_repo
        self._prediction_repo = prediction_repo
        self._logger = logger

    async def check_resolved_markets(self) -> list[ValidationResult]:
        """Check all resolved markets and validate pending predictions.

        This method:
        1. Gets all markets with resolution_status = 'RESOLVED'
        2. For each resolved market, gets its predictions
        3. Filters for predictions that haven't been validated yet
        4. Validates each prediction against the market outcome
        5. Updates the prediction with validation results

        Returns:
            List of validation results for all validated predictions

        Raises:
            DatabaseError: If database operations fail
        """
        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Starting prediction validation check"
        )

        # Get all resolved markets
        resolved_markets = await self._market_repo.get_resolved_markets()

        if not resolved_markets:
            self._logger.info(
                f"{OPERATION_EMOJIS['data']} No resolved markets found for validation"
            )
            return []

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Found {len(resolved_markets)} resolved markets"
        )

        results: list[ValidationResult] = []

        for market in resolved_markets:
            # Skip markets without resolution outcome
            if not market.resolution_outcome:
                self._logger.debug(
                    f"{OPERATION_EMOJIS['data']} Skipping market {market.id}: "
                    "no resolution outcome"
                )
                continue

            # Get predictions for this market
            predictions = await self._prediction_repo.get_predictions_by_market(
                market.id
            )

            # Filter for unvalidated predictions
            unvalidated = [p for p in predictions if p.validated_at is None]

            if not unvalidated:
                self._logger.debug(
                    f"{OPERATION_EMOJIS['data']} No unvalidated predictions for "
                    f"market {market.id}"
                )
                continue

            self._logger.debug(
                f"{OPERATION_EMOJIS['data']} Validating {len(unvalidated)} "
                f"predictions for market {market.id}"
            )

            # Validate each prediction
            for prediction in unvalidated:
                if prediction.id is None:
                    continue

                validation = self.validate_prediction(
                    prediction, market.resolution_outcome
                )

                # Only update database if validation was performed
                # (skip NO_TRADE recommendations)
                if validation.is_validated:
                    try:
                        await self._prediction_repo.update_prediction_result(
                            prediction_id=prediction.id,
                            actual_outcome=validation.actual_outcome or "",
                            is_correct=validation.is_correct or False,
                        )
                        results.append(validation)
                        self._logger.debug(
                            f"{OPERATION_EMOJIS['data']} Prediction {prediction.id} "
                            f"validated: correct={validation.is_correct}"
                        )
                    except Exception as e:
                        self._logger.error(
                            f"{OPERATION_EMOJIS['data']} Failed to update "
                            f"prediction {prediction.id}: {e}"
                        )
                        # Continue with other predictions

        self._logger.info(
            f"{OPERATION_EMOJIS['data']} Validated {len(results)} predictions"
        )

        return results

    def validate_prediction(
        self,
        prediction: Prediction,
        actual_outcome: str,
    ) -> ValidationResult:
        """Validate a single prediction against actual outcome.

        Uses the recommendation field to determine prediction direction:
        - BUY_YES: Prediction is YES
        - BUY_NO: Prediction is NO
        - NO_TRADE: Not counted (returns is_validated=False)

        If recommendation is not set, falls back to predicted_probability:
        - > 0.5: Prediction is YES
        - < 0.5: Prediction is NO
        - = 0.5: Neutral, not counted

        Args:
            prediction: Prediction to validate
            actual_outcome: Actual market outcome ("YES" or "NO")

        Returns:
            ValidationResult with validation details
        """
        # Normalize outcome to uppercase
        normalized_outcome = actual_outcome.upper()

        # Get prediction direction from recommendation or probability
        predicted_direction = self._get_prediction_direction(prediction)

        if predicted_direction is None:
            return ValidationResult(
                prediction_id=prediction.id or 0,
                is_validated=False,
                is_correct=None,
                actual_outcome=normalized_outcome,
                reason="NO_TRADE recommendation or neutral probability not counted",
            )

        is_correct = predicted_direction == normalized_outcome

        return ValidationResult(
            prediction_id=prediction.id or 0,
            is_validated=True,
            is_correct=is_correct,
            actual_outcome=normalized_outcome,
        )

    def calculate_accuracy(self, predictions: list[Prediction]) -> AccuracyResult:
        """Calculate accuracy for a list of predictions.

        Only counts validated predictions with is_correct set.
        Predictions with is_correct=None are excluded.

        Args:
            predictions: List of predictions to calculate accuracy for

        Returns:
            AccuracyResult with total, correct, and accuracy ratio
        """
        # Filter for validated predictions with is_correct not None
        validated = [p for p in predictions if p.is_correct is not None]

        if not validated:
            return AccuracyResult(
                total=0,
                correct=0,
                accuracy=None,
            )

        correct = sum(1 for p in validated if p.is_correct)
        total = len(validated)
        accuracy = correct / total

        return AccuracyResult(
            total=total,
            correct=correct,
            accuracy=accuracy,
        )

    def _get_prediction_direction(self, prediction: Prediction) -> str | None:
        """Get the prediction direction (YES/NO) from a prediction.

        Uses recommendation field if available, falls back to predicted_probability.

        Args:
            prediction: Prediction to analyze

        Returns:
            "YES", "NO", or None (for neutral/no-trade predictions)
        """
        # Prefer recommendation if available
        if prediction.recommendation is not None:
            if prediction.recommendation == Recommendation.BUY_YES:
                return "YES"
            elif prediction.recommendation == Recommendation.BUY_NO:
                return "NO"
            else:  # NO_TRADE
                return None

        # Fall back to predicted_probability
        if prediction.predicted_probability > 0.5:
            return "YES"
        elif prediction.predicted_probability < 0.5:
            return "NO"
        else:  # Exactly 0.5 - neutral
            return None
