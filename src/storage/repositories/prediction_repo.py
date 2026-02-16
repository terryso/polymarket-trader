"""Prediction repository for database operations.

This module provides the PredictionRepository class for persisting
and querying LLM prediction records.

Usage:
    from src.storage.repositories import PredictionRepository

    repo = PredictionRepository()
    prediction_id = await repo.save_prediction(prediction)
    predictions = await repo.get_predictions_by_market(market_id)
"""

from __future__ import annotations

__all__ = ["PredictionRepository"]

import json
from datetime import datetime, timezone

import aiosqlite

from src.exceptions import DatabaseError
from src.models.prediction import Prediction, Recommendation
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

logger = get_logger(__name__)


class PredictionRepository:
    """Repository for prediction data operations.

    Provides methods to save, retrieve, and manage LLM prediction records
    in the SQLite database.

    Example:
        >>> repo = PredictionRepository()
        >>> prediction = Prediction(
        ...     market_id="market-123",
        ...     predicted_probability=0.75,
        ...     confidence=0.85,
        ... )
        >>> prediction_id = await repo.save_prediction(prediction)
        >>> predictions = await repo.get_predictions_by_market("market-123")
    """

    def __init__(self) -> None:
        """Initialize the PredictionRepository."""
        pass

    async def save_prediction(self, prediction: Prediction, upsert: bool = True) -> int:
        """Save a prediction record to the database.

        Uses UPSERT logic by default: if a prediction for the same market
        already exists, it will be replaced with the new one.

        Args:
            prediction: Prediction model to save
            upsert: If True, replace existing prediction for same market.
                   If False, always insert new record.

        Returns:
            The ID of the inserted/updated prediction record

        Raises:
            DatabaseError: If database operation fails

        Example:
            >>> prediction = Prediction(
            ...     market_id="market-123",
            ...     predicted_probability=0.75,
            ...     confidence=0.85,
            ...     reasoning="Strong indicators...",
            ... )
            >>> prediction_id = await repo.save_prediction(prediction)
        """
        logger.info(
            f"{OPERATION_EMOJIS['data']} Saving prediction for market: "
            f"{prediction.market_id}"
        )

        # Serialize key_assumptions to JSON
        assumptions_json = (
            json.dumps(prediction.key_assumptions)
            if prediction.key_assumptions
            else None
        )

        # Serialize recommendation to string
        recommendation_str = (
            prediction.recommendation.value if prediction.recommendation else None
        )

        try:
            async with get_connection() as conn:
                if upsert:
                    # UPSERT: Delete existing predictions for this market first,
                    # then insert new one. This avoids duplicate records.
                    await conn.execute(
                        "DELETE FROM predictions WHERE market_id = ?",
                        (prediction.market_id,),
                    )

                cursor = await conn.execute(
                    """
                    INSERT INTO predictions (
                        market_id, predicted_probability, confidence,
                        reasoning, key_assumptions, model_used, recommendation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prediction.market_id,
                        prediction.predicted_probability,
                        prediction.confidence,
                        prediction.reasoning,
                        assumptions_json,
                        prediction.model_used,
                        recommendation_str,
                    ),
                )
                await conn.commit()
                prediction_id = cursor.lastrowid or 0

            logger.info(
                f"{OPERATION_EMOJIS['data']} Prediction saved with ID: "
                f"{prediction_id}"
            )

            return prediction_id
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to save prediction for market "
                f"{prediction.market_id}: {e}"
            )
            raise DatabaseError(
                message=f"Failed to save prediction for market: "
                f"{prediction.market_id}",
                operation="save_prediction",
                original_exception=e,
            ) from e

    async def get_predictions_by_market(self, market_id: str) -> list[Prediction]:
        """Get all predictions for a specific market.

        Args:
            market_id: The market ID to query

        Returns:
            List of Prediction models, ordered by created_at descending

        Example:
            >>> predictions = await repo.get_predictions_by_market("market-123")
            >>> len(predictions)
            5
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM predictions
                    WHERE market_id = ?
                    ORDER BY created_at DESC
                    """,
                    (market_id,),
                )
                rows = await cursor.fetchall()

            predictions = [self._row_to_prediction(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} predictions "
                f"for market: {market_id}"
            )
            return predictions
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get predictions for market "
                f"{market_id}: {e}"
            )
            raise

    async def get_pending_predictions(self) -> list[Prediction]:
        """Get all pending predictions (for unresolved markets).

        Returns predictions for markets that have not been resolved yet.
        Used for prediction validation tracking.

        Returns:
            List of pending Prediction models

        Example:
            >>> pending = await repo.get_pending_predictions()
            >>> len(pending)
            10
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT p.* FROM predictions p
                    JOIN markets m ON p.market_id = m.id
                    WHERE m.resolution_status IS NULL
                    ORDER BY p.created_at DESC
                    """)
                rows = await cursor.fetchall()

            predictions = [self._row_to_prediction(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} "
                f"pending predictions"
            )
            return predictions
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get pending predictions: {e}"
            )
            raise

    async def get_latest_prediction(self, market_id: str) -> Prediction | None:
        """Get the most recent prediction for a specific market.

        Args:
            market_id: The market ID to query

        Returns:
            The most recent Prediction model, or None if not found

        Example:
            >>> latest = await repo.get_latest_prediction("market-123")
            >>> latest.predicted_probability
            0.75
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM predictions
                    WHERE market_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (market_id,),
                )
                row = await cursor.fetchone()

            if row is None:
                return None

            return self._row_to_prediction(row)
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get latest prediction for "
                f"market {market_id}: {e}"
            )
            raise

    async def update_prediction_result(
        self,
        prediction_id: int,
        actual_outcome: str,
        is_correct: bool,
    ) -> bool:
        """Update prediction with validation result.

        Used after market resolution to record whether the prediction
        was correct.

        Args:
            prediction_id: The prediction ID to update
            actual_outcome: The actual market outcome (e.g., "YES", "NO")
            is_correct: Whether the prediction was correct

        Returns:
            True if update succeeded, False if prediction not found

        Example:
            >>> success = await repo.update_prediction_result(1, "YES", True)
            >>> assert success is True
        """
        logger.info(
            f"{OPERATION_EMOJIS['data']} Updating prediction {prediction_id}: "
            f"outcome={actual_outcome}, correct={is_correct}"
        )

        try:
            async with get_connection() as conn:
                cursor = await conn.execute(
                    """
                    UPDATE predictions
                    SET actual_outcome = ?,
                        is_correct = ?,
                        validated_at = ?
                    WHERE id = ?
                    """,
                    (
                        actual_outcome,
                        is_correct,
                        datetime.now(timezone.utc).isoformat(),
                        prediction_id,
                    ),
                )
                await conn.commit()

                if cursor.rowcount == 0:
                    logger.warning(
                        f"{OPERATION_EMOJIS['data']} Prediction not found: "
                        f"{prediction_id}"
                    )
                    return False

            logger.info(
                f"{OPERATION_EMOJIS['data']} Updated prediction {prediction_id} result"
            )
            return True
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to update prediction "
                f"{prediction_id}: {e}"
            )
            raise DatabaseError(
                message=f"Failed to update prediction: {prediction_id}",
                operation="update_prediction_result",
                original_exception=e,
            ) from e

    def _row_to_prediction(self, row: aiosqlite.Row) -> Prediction:
        """Convert a database row to a Prediction model.

        Args:
            row: Database row from predictions table

        Returns:
            Prediction model instance
        """
        # Deserialize key_assumptions from JSON
        key_assumptions: list[str] | None = None
        if row["key_assumptions"]:
            key_assumptions = json.loads(row["key_assumptions"])

        # Parse recommendation
        recommendation: Recommendation | None = None
        if row["recommendation"]:
            try:
                recommendation = Recommendation(row["recommendation"])
            except ValueError:
                recommendation = None

        # Parse created_at
        created_at: datetime | None = None
        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except ValueError:
                created_at = None

        # Parse validated_at
        validated_at: datetime | None = None
        if "validated_at" in row.keys() and row["validated_at"]:
            try:
                validated_at = datetime.fromisoformat(row["validated_at"])
            except ValueError:
                validated_at = None

        # Parse is_correct
        is_correct: bool | None = None
        if "is_correct" in row.keys() and row["is_correct"] is not None:
            is_correct = bool(row["is_correct"])

        # Parse actual_outcome
        actual_outcome: str | None = None
        if "actual_outcome" in row.keys():
            actual_outcome = row["actual_outcome"]

        return Prediction(
            id=row["id"],
            market_id=row["market_id"],
            predicted_probability=row["predicted_probability"],
            confidence=row["confidence"],
            reasoning=row["reasoning"],
            key_assumptions=key_assumptions,
            model_used=row["model_used"],
            recommendation=recommendation,
            actual_outcome=actual_outcome,
            is_correct=is_correct,
            validated_at=validated_at,
            created_at=created_at,
        )
