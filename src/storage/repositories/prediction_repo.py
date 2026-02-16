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

__all__ = [
    "PredictionRepository",
    "PredictionOutcomeStatus",
    "PredictionSortBy",
    "SortOrder",
    "PaginationParams",
    "SortParams",
    "PredictionQueryResult",
]

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

import aiosqlite

from src.exceptions import DatabaseError
from src.models.prediction import Prediction, Recommendation
from src.storage.database import get_connection
from src.utils.logger import OPERATION_EMOJIS, get_logger

if TYPE_CHECKING:
    from src.models.market import Market

logger = get_logger(__name__)


# ==================== Story 6.4: 预测历史查询 API 数据模型 ====================


class PredictionOutcomeStatus(str, Enum):
    """Status filter for prediction queries.

    Attributes:
        ALL: Return all predictions (no filter)
        CORRECT: Return only correct predictions (is_correct = TRUE)
        INCORRECT: Return only incorrect predictions (is_correct = FALSE)
        PENDING: Return only pending predictions (validated_at IS NULL)
    """

    ALL = "all"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PENDING = "pending"


class PredictionSortBy(str, Enum):
    """Sort field for prediction queries.

    Attributes:
        DATE: Sort by prediction creation date (created_at)
        CONFIDENCE: Sort by confidence level
        ACCURACY: Sort by correctness (is_correct)
    """

    DATE = "date"
    CONFIDENCE = "confidence"
    ACCURACY = "accuracy"


class SortOrder(str, Enum):
    """Sort order for queries.

    Attributes:
        ASC: Ascending order
        DESC: Descending order
    """

    ASC = "asc"
    DESC = "desc"


@dataclass
class PaginationParams:
    """Pagination parameters for queries.

    Attributes:
        page: Page number (1-indexed, must be >= 1)
        per_page: Items per page (must be >= 1 and <= 1000)

    Raises:
        ValueError: If page < 1, per_page < 1, or per_page > 1000
    """

    page: int = 1
    per_page: int = 20

    def __post_init__(self) -> None:
        """Validate pagination parameters after initialization."""
        if self.page < 1:
            raise ValueError(f"page must be >= 1, got {self.page}")
        if self.per_page < 1:
            raise ValueError(f"per_page must be >= 1, got {self.per_page}")
        if self.per_page > 1000:
            raise ValueError(f"per_page must be <= 1000, got {self.per_page}")


@dataclass
class SortParams:
    """Sort parameters for queries.

    Attributes:
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
    """

    sort_by: PredictionSortBy = PredictionSortBy.DATE
    sort_order: SortOrder = SortOrder.DESC


@dataclass
class PredictionQueryResult:
    """Result of a prediction query with pagination.

    Attributes:
        predictions: List of (Prediction, Market) tuples
        total: Total number of matching records
        page: Current page number
        per_page: Items per page
        has_next: Whether there's a next page
        has_prev: Whether there's a previous page
    """

    predictions: list[tuple[Prediction, Market]]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


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
                        reasoning, key_assumptions, model_used, recommendation,
                        edge
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prediction.market_id,
                        prediction.predicted_probability,
                        prediction.confidence,
                        prediction.reasoning,
                        assumptions_json,
                        prediction.model_used,
                        recommendation_str,
                        prediction.edge,
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

    # ==================== Story 7.4: 预测与统计 API ====================

    async def get_by_id(self, prediction_id: int) -> Prediction | None:
        """Get a prediction by its ID.

        Story 7.4: 预测与统计 API

        Args:
            prediction_id: The prediction ID to query

        Returns:
            Prediction if found, None otherwise

        Example:
            >>> prediction = await repo.get_by_id(1)
            >>> if prediction:
            ...     print(f"Market: {prediction.market_id}")
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM predictions WHERE id = ?",
                    (prediction_id,),
                )
                row = await cursor.fetchone()

            if row is None:
                return None
            return self._row_to_prediction(row)
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get prediction "
                f"{prediction_id}: {e}"
            )
            raise

    async def get_all(self, limit: int = 100) -> list[Prediction]:
        """Get all predictions with optional limit.

        Story 7.4: 预测与统计 API

        Args:
            limit: Maximum number of predictions to return (default: 100)

        Returns:
            List of Prediction models, ordered by created_at descending

        Example:
            >>> predictions = await repo.get_all(limit=50)
            >>> len(predictions)
            50
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM predictions
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = await cursor.fetchall()

            predictions = [self._row_to_prediction(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Retrieved {len(predictions)} predictions"
            )
            return predictions
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['data']} Failed to get predictions: {e}")
            raise

    async def count(self) -> int:
        """Get total count of predictions.

        Story 7.4: 预测与统计 API

        Returns:
            Total number of predictions

        Example:
            >>> total = await repo.count()
            >>> print(f"Total predictions: {total}")
        """
        try:
            async with get_connection() as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM predictions")
                row = await cursor.fetchone()
                return row[0] if row else 0
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['data']} Failed to count predictions: {e}")
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

    async def get_unvalidated_predictions(self) -> list[Prediction]:
        """Get all unvalidated predictions (validated_at is NULL).

        Returns predictions that have not been validated yet,
        regardless of market resolution status.

        Returns:
            List of unvalidated Prediction models

        Example:
            >>> unvalidated = await repo.get_unvalidated_predictions()
            >>> len(unvalidated)
            5
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM predictions
                    WHERE validated_at IS NULL
                    ORDER BY created_at DESC
                    """)
                rows = await cursor.fetchall()

            predictions = [self._row_to_prediction(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} "
                f"unvalidated predictions"
            )
            return predictions
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get unvalidated predictions: {e}"
            )
            raise

    async def get_validated_predictions(self) -> list[Prediction]:
        """Get all validated predictions (validated_at is NOT NULL).

        Returns predictions that have been validated against
        resolved market outcomes.

        Returns:
            List of validated Prediction models

        Example:
            >>> validated = await repo.get_validated_predictions()
            >>> len(validated)
            20
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM predictions
                    WHERE validated_at IS NOT NULL
                    ORDER BY validated_at DESC
                    """)
                rows = await cursor.fetchall()

            predictions = [self._row_to_prediction(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} "
                f"validated predictions"
            )
            return predictions
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get validated predictions: {e}"
            )
            raise

    # ==================== Story 6.2: 准确率统计 ====================

    async def get_all_validated(self) -> list[Prediction]:
        """Get all validated predictions (is_correct is not None).

        Story 6.2: 准确率统计

        This is an alias for get_validated_predictions() with a clearer name
        for accuracy statistics use cases.

        Returns:
            List of validated predictions
        """
        return await self.get_validated_predictions()

    async def get_validated_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Prediction]:
        """Get validated predictions within a date range.

        Story 6.2: 准确率统计

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of validated predictions in the date range
        """
        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT * FROM predictions
                    WHERE is_correct IS NOT NULL
                    AND validated_at >= ?
                    AND validated_at <= ?
                    ORDER BY validated_at DESC
                    """,
                    (start_date.isoformat(), end_date.isoformat()),
                )
                rows = await cursor.fetchall()

            predictions = [self._row_to_prediction(row) for row in rows]
            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} "
                f"validated predictions in date range"
            )
            return predictions
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get validated predictions "
                f"by date range: {e}"
            )
            raise

    async def get_validated_with_market(self) -> list[tuple[Prediction, Market]]:
        """Get all validated predictions with their associated market info.

        Story 6.2: 准确率统计

        Returns:
            List of (Prediction, Market) tuples
        """
        from src.models.market import Market

        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT p.*, m.id as market_id_col, m.title, m.description,
                           m.category, m.yes_price, m.no_price, m.liquidity,
                           m.deadline, m.resolution_status, m.resolution_outcome,
                           m.created_at as market_created_at,
                           m.updated_at as market_updated_at
                    FROM predictions p
                    JOIN markets m ON p.market_id = m.id
                    WHERE p.is_correct IS NOT NULL
                    ORDER BY p.validated_at DESC
                    """)
                rows = await cursor.fetchall()

            results: list[tuple[Prediction, Market]] = []
            for row in rows:
                prediction = self._row_to_prediction(row)
                market = self._row_to_market(row)
                results.append((prediction, market))

            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(results)} "
                f"validated predictions with market info"
            )
            return results
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to get validated predictions "
                f"with market: {e}"
            )
            raise

    def _row_to_market(self, row: aiosqlite.Row) -> Market:
        """Convert a database row to a Market model.

        Args:
            row: Database row from markets table (prefixed columns)

        Returns:
            Market model instance
        """
        from src.models.market import Market, MarketCategory

        # Parse category
        category: MarketCategory | None = None
        if row["category"]:
            try:
                category = MarketCategory(row["category"])
            except ValueError:
                category = None

        # Parse deadline
        deadline: datetime | None = None
        if row["deadline"]:
            try:
                deadline = datetime.fromisoformat(row["deadline"])
            except ValueError:
                deadline = None

        # Parse market_created_at
        market_created_at: datetime | None = None
        if row["market_created_at"]:
            try:
                market_created_at = datetime.fromisoformat(row["market_created_at"])
            except ValueError:
                market_created_at = None

        # Parse market_updated_at
        market_updated_at: datetime | None = None
        if row["market_updated_at"]:
            try:
                market_updated_at = datetime.fromisoformat(row["market_updated_at"])
            except ValueError:
                market_updated_at = None

        return Market(
            id=row["market_id_col"],
            title=row["title"],
            description=row["description"],
            category=category,
            yes_price=row["yes_price"],
            no_price=row["no_price"],
            liquidity=row["liquidity"],
            deadline=deadline,
            resolution_status=row["resolution_status"],
            resolution_outcome=row["resolution_outcome"],
            created_at=market_created_at,
            updated_at=market_updated_at,
        )

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

        # Parse edge
        edge: float | None = None
        if "edge" in row.keys() and row["edge"] is not None:
            edge = row["edge"]

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
            edge=edge,
            actual_outcome=actual_outcome,
            is_correct=is_correct,
            validated_at=validated_at,
            created_at=created_at,
        )

    # ==================== Story 6.4: 预测历史查询 API ====================

    def _get_sort_clause(self, sort: SortParams) -> str:
        """Build SQL ORDER BY clause from sort parameters.

        Args:
            sort: Sort parameters

        Returns:
            SQL ORDER BY clause string
        """
        sort_fields = {
            PredictionSortBy.DATE: "p.created_at",
            PredictionSortBy.CONFIDENCE: "p.confidence",
            PredictionSortBy.ACCURACY: "p.is_correct",
        }

        field = sort_fields.get(sort.sort_by, "p.created_at")
        order = "DESC" if sort.sort_order == SortOrder.DESC else "ASC"

        return f"ORDER BY {field} {order}"

    def _get_status_where_clause(
        self,
        status: PredictionOutcomeStatus,
    ) -> tuple[str, list]:
        """Build SQL WHERE clause for status filter.

        Args:
            status: Status filter

        Returns:
            Tuple of (where_clause, params)
        """
        if status == PredictionOutcomeStatus.CORRECT:
            return "WHERE p.is_correct = 1", []
        elif status == PredictionOutcomeStatus.INCORRECT:
            return "WHERE p.is_correct = 0", []
        elif status == PredictionOutcomeStatus.PENDING:
            return "WHERE p.validated_at IS NULL", []
        else:  # ALL
            return "", []

    async def get_predictions_with_outcome(
        self,
        status: PredictionOutcomeStatus | str = PredictionOutcomeStatus.ALL,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get predictions filtered by outcome status.

        Args:
            status: Filter by prediction outcome status
            pagination: Pagination parameters (default: page=1, per_page=20)
            sort: Sort parameters (default: date desc)

        Returns:
            PredictionQueryResult with predictions and pagination info

        Example:
            >>> result = await repo.get_predictions_with_outcome(
            ...     status="correct",
            ...     pagination=PaginationParams(page=1, per_page=10),
            ...     sort=SortParams(sort_by="confidence", sort_order="desc"),
            ... )
            >>> len(result.predictions)
            10
            >>> result.total
            45
        """
        from src.models.market import Market

        if pagination is None:
            pagination = PaginationParams()
        if sort is None:
            sort = SortParams()

        # Normalize status
        if isinstance(status, str):
            status = PredictionOutcomeStatus(status.lower())

        logger.info(
            f"{OPERATION_EMOJIS['data']} Querying predictions with status: "
            f"{status.value}, page={pagination.page}, per_page={pagination.per_page}"
        )

        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row

                # Build WHERE clause
                where_clause, where_params = self._get_status_where_clause(status)
                sort_clause = self._get_sort_clause(sort)

                # Get total count
                count_sql = f"""
                    SELECT COUNT(*) as total
                    FROM predictions p
                    {where_clause}
                """
                cursor = await conn.execute(count_sql, where_params)
                count_row = await cursor.fetchone()
                total = count_row["total"] if count_row else 0

                # Get paginated results with market info
                offset = (pagination.page - 1) * pagination.per_page
                query_sql = f"""
                    SELECT p.*, m.id as market_id_col, m.title, m.description,
                           m.category, m.yes_price, m.no_price, m.liquidity,
                           m.deadline, m.resolution_status, m.resolution_outcome,
                           m.created_at as market_created_at,
                           m.updated_at as market_updated_at
                    FROM predictions p
                    JOIN markets m ON p.market_id = m.id
                    {where_clause}
                    {sort_clause}
                    LIMIT ? OFFSET ?
                """
                cursor = await conn.execute(
                    query_sql,
                    where_params + [pagination.per_page, offset],
                )
                rows = await cursor.fetchall()

            # Convert rows to (Prediction, Market) tuples
            predictions: list[tuple[Prediction, Market]] = []
            for row in rows:
                prediction = self._row_to_prediction(row)
                market = self._row_to_market(row)
                predictions.append((prediction, market))

            # Calculate pagination info
            has_next = (pagination.page * pagination.per_page) < total
            has_prev = pagination.page > 1

            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} predictions "
                f"(total: {total})"
            )

            return PredictionQueryResult(
                predictions=predictions,
                total=total,
                page=pagination.page,
                per_page=pagination.per_page,
                has_next=has_next,
                has_prev=has_prev,
            )
        except aiosqlite.Error as e:
            logger.error(f"{OPERATION_EMOJIS['data']} Failed to query predictions: {e}")
            raise

    async def get_correct_predictions(
        self,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get all correct predictions.

        Convenience method for get_predictions_with_outcome(status="correct").

        Args:
            pagination: Pagination parameters
            sort: Sort parameters

        Returns:
            PredictionQueryResult with correct predictions

        Example:
            >>> result = await repo.get_correct_predictions()
            >>> all(p.is_correct for p, m in result.predictions)
            True
        """
        return await self.get_predictions_with_outcome(
            status=PredictionOutcomeStatus.CORRECT,
            pagination=pagination,
            sort=sort,
        )

    async def get_incorrect_predictions(
        self,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get all incorrect predictions.

        Convenience method for get_predictions_with_outcome(status="incorrect").

        Args:
            pagination: Pagination parameters
            sort: Sort parameters

        Returns:
            PredictionQueryResult with incorrect predictions

        Example:
            >>> result = await repo.get_incorrect_predictions()
            >>> all(not p.is_correct for p, m in result.predictions)
            True
        """
        return await self.get_predictions_with_outcome(
            status=PredictionOutcomeStatus.INCORRECT,
            pagination=pagination,
            sort=sort,
        )

    async def get_predictions_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> PredictionQueryResult:
        """Get predictions within a confidence range.

        Args:
            min_confidence: Minimum confidence (0-1, inclusive)
            max_confidence: Maximum confidence (0-1, inclusive)
            pagination: Pagination parameters
            sort: Sort parameters

        Returns:
            PredictionQueryResult with predictions in confidence range

        Raises:
            ValueError: If confidence values are invalid

        Example:
            >>> result = await repo.get_predictions_by_confidence_range(
            ...     min_confidence=0.8,
            ...     max_confidence=1.0,
            ... )
            >>> all(
            ...     0.8 <= p.confidence <= 1.0
            ...     for p, m in result.predictions
            ... )
            True
        """
        from src.models.market import Market

        # Validate confidence range
        if not (0 <= min_confidence <= 1):
            raise ValueError(
                f"min_confidence must be between 0 and 1, got {min_confidence}"
            )
        if not (0 <= max_confidence <= 1):
            raise ValueError(
                f"max_confidence must be between 0 and 1, got {max_confidence}"
            )
        if min_confidence > max_confidence:
            raise ValueError(
                f"min_confidence ({min_confidence}) must be <= "
                f"max_confidence ({max_confidence})"
            )

        if pagination is None:
            pagination = PaginationParams()
        if sort is None:
            sort = SortParams()

        logger.info(
            f"{OPERATION_EMOJIS['data']} Querying predictions with confidence: "
            f"[{min_confidence}, {max_confidence}]"
        )

        try:
            async with get_connection() as conn:
                conn.row_factory = aiosqlite.Row

                sort_clause = self._get_sort_clause(sort)

                # Get total count
                count_sql = """
                    SELECT COUNT(*) as total
                    FROM predictions p
                    WHERE p.confidence >= ? AND p.confidence <= ?
                """
                cursor = await conn.execute(
                    count_sql,
                    (min_confidence, max_confidence),
                )
                count_row = await cursor.fetchone()
                total = count_row["total"] if count_row else 0

                # Get paginated results with market info
                offset = (pagination.page - 1) * pagination.per_page
                query_sql = f"""
                    SELECT p.*, m.id as market_id_col, m.title, m.description,
                           m.category, m.yes_price, m.no_price, m.liquidity,
                           m.deadline, m.resolution_status, m.resolution_outcome,
                           m.created_at as market_created_at,
                           m.updated_at as market_updated_at
                    FROM predictions p
                    JOIN markets m ON p.market_id = m.id
                    WHERE p.confidence >= ? AND p.confidence <= ?
                    {sort_clause}
                    LIMIT ? OFFSET ?
                """
                cursor = await conn.execute(
                    query_sql,
                    (min_confidence, max_confidence, pagination.per_page, offset),
                )
                rows = await cursor.fetchall()

            # Convert rows to (Prediction, Market) tuples
            predictions: list[tuple[Prediction, Market]] = []
            for row in rows:
                prediction = self._row_to_prediction(row)
                market = self._row_to_market(row)
                predictions.append((prediction, market))

            # Calculate pagination info
            has_next = (pagination.page * pagination.per_page) < total
            has_prev = pagination.page > 1

            logger.info(
                f"{OPERATION_EMOJIS['data']} Found {len(predictions)} predictions "
                f"in confidence range (total: {total})"
            )

            return PredictionQueryResult(
                predictions=predictions,
                total=total,
                page=pagination.page,
                per_page=pagination.per_page,
                has_next=has_next,
                has_prev=has_prev,
            )
        except aiosqlite.Error as e:
            logger.error(
                f"{OPERATION_EMOJIS['data']} Failed to query predictions by "
                f"confidence range: {e}"
            )
            raise
