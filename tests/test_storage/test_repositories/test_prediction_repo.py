"""Tests for PredictionRepository."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.prediction import Prediction, Recommendation
from src.storage.repositories.prediction_repo import PredictionRepository


class TestPredictionRepository:
    """Tests for PredictionRepository class."""

    @pytest.fixture
    def repo(self) -> PredictionRepository:
        """Create a PredictionRepository instance for testing."""
        return PredictionRepository()

    @pytest.fixture
    def sample_prediction(self) -> Prediction:
        """Create a sample Prediction for testing."""
        return Prediction(
            market_id="test-market-123",
            predicted_probability=0.75,
            confidence=0.85,
            reasoning="Strong indicators point to YES",
            key_assumptions=["Economic stability", "Policy support"],
            model_used="glm-4",
            recommendation=Recommendation.BUY_YES,
        )

    @pytest.fixture
    def sample_prediction_minimal(self) -> Prediction:
        """Create a minimal Prediction for testing."""
        return Prediction(
            market_id="test-market-456",
            predicted_probability=0.60,
            confidence=0.70,
        )

    # ==================== save_prediction tests ====================

    @pytest.mark.asyncio
    async def test_save_prediction_success(
        self, repo: PredictionRepository, sample_prediction: Prediction
    ) -> None:
        """Test successful prediction save with UPSERT (default)."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction_id = await repo.save_prediction(sample_prediction)

            assert prediction_id == 1
            # With upsert=True, execute is called twice (DELETE + INSERT)
            assert mock_conn.execute.call_count == 2
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_prediction_without_upsert(
        self, repo: PredictionRepository, sample_prediction: Prediction
    ) -> None:
        """Test prediction save with upsert=False (always insert)."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction_id = await repo.save_prediction(sample_prediction, upsert=False)

            assert prediction_id == 1
            # With upsert=False, execute is called once (INSERT only)
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_prediction_upsert_replaces_existing(
        self, repo: PredictionRepository, sample_prediction: Prediction
    ) -> None:
        """Test that UPSERT deletes existing prediction before insert."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 2  # New ID after replace

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction_id = await repo.save_prediction(sample_prediction)

            assert prediction_id == 2
            # Verify DELETE was called first
            first_call = mock_conn.execute.call_args_list[0]
            assert "DELETE FROM predictions" in first_call[0][0]
            assert first_call[0][1] == (sample_prediction.market_id,)

    @pytest.mark.asyncio
    async def test_save_prediction_minimal(
        self, repo: PredictionRepository, sample_prediction_minimal: Prediction
    ) -> None:
        """Test saving a prediction with minimal fields."""
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 2

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction_id = await repo.save_prediction(
                sample_prediction_minimal, upsert=False
            )

            assert prediction_id == 2

    @pytest.mark.asyncio
    async def test_save_prediction_serializes_key_assumptions(
        self, repo: PredictionRepository
    ) -> None:
        """Test that key_assumptions list is serialized to JSON."""
        prediction = Prediction(
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            key_assumptions=["A", "B", "C"],
        )

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.save_prediction(prediction, upsert=False)

            # Verify JSON serialization in INSERT call (second call)
            insert_call = mock_conn.execute.call_args
            params = insert_call[0][1]
            import json

            assert params[4] == json.dumps(["A", "B", "C"])

    @pytest.mark.asyncio
    async def test_save_prediction_database_error(
        self, repo: PredictionRepository, sample_prediction: Prediction
    ) -> None:
        """Test that database errors are wrapped in DatabaseError."""
        import aiosqlite

        from src.exceptions import DatabaseError

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Database error"))

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.save_prediction(sample_prediction)

            assert "Failed to save prediction" in str(exc_info.value)

    # ==================== get_predictions_by_market tests ====================

    @pytest.mark.asyncio
    async def test_get_predictions_by_market_found(
        self, repo: PredictionRepository
    ) -> None:
        """Test retrieving predictions for a market that has predictions."""
        mock_rows = []
        for i in range(2):
            row = self._create_mock_row(
                prediction_id=i + 1,
                market_id="test-market-123",
                predicted_probability=0.70 + i * 0.05,
                confidence=0.80 + i * 0.05,
                reasoning=f"Reasoning {i}",
                key_assumptions='["Assumption 1"]',
                model_used="glm-4",
                recommendation="BUY_YES",
            )
            mock_rows.append(row)

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_rows)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            predictions = await repo.get_predictions_by_market("test-market-123")

            assert len(predictions) == 2
            assert predictions[0].market_id == "test-market-123"
            assert predictions[0].key_assumptions == ["Assumption 1"]

    @pytest.mark.asyncio
    async def test_get_predictions_by_market_empty(
        self, repo: PredictionRepository
    ) -> None:
        """Test retrieving predictions for a market with no predictions."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            predictions = await repo.get_predictions_by_market("non-existent-market")

            assert predictions == []

    @pytest.mark.asyncio
    async def test_get_predictions_by_market_database_error(
        self, repo: PredictionRepository
    ) -> None:
        """Test that database errors are raised properly."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Database error"))

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(aiosqlite.Error):
                await repo.get_predictions_by_market("test-market")

    # ==================== get_pending_predictions tests ====================

    @pytest.mark.asyncio
    async def test_get_pending_predictions_found(
        self, repo: PredictionRepository
    ) -> None:
        """Test retrieving pending predictions."""
        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="pending-market",
            predicted_probability=0.75,
            confidence=0.85,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[mock_row])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            predictions = await repo.get_pending_predictions()

            assert len(predictions) == 1
            # Verify query joins with markets table
            call_args = mock_conn.execute.call_args
            assert "JOIN markets m" in call_args[0][0]
            assert "resolution_status IS NULL" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_pending_predictions_empty(
        self, repo: PredictionRepository
    ) -> None:
        """Test retrieving pending predictions when none exist."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            predictions = await repo.get_pending_predictions()

            assert predictions == []

    @pytest.mark.asyncio
    async def test_get_pending_predictions_database_error(
        self, repo: PredictionRepository
    ) -> None:
        """Test that database errors are raised properly."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Database error"))

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(aiosqlite.Error):
                await repo.get_pending_predictions()

    # ==================== get_latest_prediction tests ====================

    @pytest.mark.asyncio
    async def test_get_latest_prediction_found(
        self, repo: PredictionRepository
    ) -> None:
        """Test retrieving the latest prediction for a market."""
        mock_row = self._create_mock_row(
            prediction_id=5,
            market_id="test-market-123",
            predicted_probability=0.80,
            confidence=0.90,
            reasoning="Latest reasoning",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market-123")

            assert prediction is not None
            assert prediction.id == 5
            assert prediction.predicted_probability == 0.80
            # Verify query has ORDER BY and LIMIT
            call_args = mock_conn.execute.call_args
            assert "ORDER BY created_at DESC" in call_args[0][0]
            assert "LIMIT 1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_latest_prediction_not_found(
        self, repo: PredictionRepository
    ) -> None:
        """Test retrieving latest prediction when market has no predictions."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("non-existent-market")

            assert prediction is None

    @pytest.mark.asyncio
    async def test_get_latest_prediction_database_error(
        self, repo: PredictionRepository
    ) -> None:
        """Test that database errors are raised properly."""
        import aiosqlite

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Database error"))

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(aiosqlite.Error):
                await repo.get_latest_prediction("test-market")

    # ==================== update_prediction_result tests ====================

    @pytest.mark.asyncio
    async def test_update_prediction_result_success(
        self, repo: PredictionRepository
    ) -> None:
        """Test successful prediction result update returns True."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.update_prediction_result(
                prediction_id=1,
                actual_outcome="YES",
                is_correct=True,
            )

            assert result is True
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()
            # Verify parameters
            call_args = mock_conn.execute.call_args
            params = call_args[0][1]
            assert params[0] == "YES"
            assert params[1] is True
            assert params[3] == 1

    @pytest.mark.asyncio
    async def test_update_prediction_result_not_found(
        self, repo: PredictionRepository
    ) -> None:
        """Test update returns False when prediction not found."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.update_prediction_result(
                prediction_id=999,
                actual_outcome="YES",
                is_correct=True,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_update_prediction_result_incorrect(
        self, repo: PredictionRepository
    ) -> None:
        """Test updating prediction result as incorrect."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            result = await repo.update_prediction_result(
                prediction_id=1,
                actual_outcome="NO",
                is_correct=False,
            )

            assert result is True
            call_args = mock_conn.execute.call_args
            params = call_args[0][1]
            assert params[0] == "NO"
            assert params[1] is False

    @pytest.mark.asyncio
    async def test_update_prediction_result_database_error(
        self, repo: PredictionRepository
    ) -> None:
        """Test that database errors are wrapped in DatabaseError."""
        import aiosqlite

        from src.exceptions import DatabaseError

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Database error"))

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.update_prediction_result(1, "YES", True)

            assert "Failed to update prediction" in str(exc_info.value)

    # ==================== _row_to_prediction edge cases ====================

    @pytest.mark.asyncio
    async def test_row_to_prediction_with_null_fields(
        self, repo: PredictionRepository
    ) -> None:
        """Test that NULL fields are handled correctly."""
        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            reasoning=None,
            key_assumptions=None,
            model_used=None,
            recommendation=None,
            actual_outcome=None,
            is_correct=None,
            validated_at=None,
            created_at=None,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.reasoning is None
            assert prediction.key_assumptions is None
            assert prediction.model_used is None
            assert prediction.recommendation is None
            assert prediction.actual_outcome is None
            assert prediction.is_correct is None
            assert prediction.validated_at is None
            assert prediction.created_at is None

    @pytest.mark.asyncio
    async def test_row_to_prediction_with_valid_datetime(
        self, repo: PredictionRepository
    ) -> None:
        """Test that datetime fields are parsed correctly."""
        test_created = "2026-02-15T10:30:00"
        test_validated = "2026-02-16T14:00:00"

        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            created_at=test_created,
            validated_at=test_validated,
            actual_outcome="YES",
            is_correct=1,  # SQLite stores boolean as int
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.created_at == datetime.fromisoformat(test_created)
            assert prediction.validated_at == datetime.fromisoformat(test_validated)
            assert prediction.actual_outcome == "YES"
            assert prediction.is_correct is True

    @pytest.mark.asyncio
    async def test_row_to_prediction_with_invalid_recommendation(
        self, repo: PredictionRepository
    ) -> None:
        """Test that invalid recommendation values are handled gracefully."""
        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            recommendation="INVALID_VALUE",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.recommendation is None

    @pytest.mark.asyncio
    async def test_row_to_prediction_with_invalid_datetime(
        self, repo: PredictionRepository
    ) -> None:
        """Test that invalid datetime values are handled gracefully."""
        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            created_at="not-a-valid-datetime",
            validated_at="also-invalid",
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.created_at is None
            assert prediction.validated_at is None

    @pytest.mark.asyncio
    async def test_row_to_prediction_with_json_key_assumptions(
        self, repo: PredictionRepository
    ) -> None:
        """Test that key_assumptions JSON is deserialized correctly."""
        import json

        assumptions = ["First assumption", "Second assumption", "Third"]
        assumptions_json = json.dumps(assumptions)

        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            key_assumptions=assumptions_json,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.key_assumptions == assumptions

    # ==================== Foreign key constraint tests ====================

    @pytest.mark.asyncio
    async def test_save_prediction_foreign_key_constraint(
        self, repo: PredictionRepository
    ) -> None:
        """Test that saving prediction with non-existent market_id fails.

        This test verifies that the foreign key constraint on predictions
        table is enforced when market_id does not exist in markets table.
        """
        import aiosqlite

        from src.exceptions import DatabaseError

        prediction = Prediction(
            market_id="non-existent-market",
            predicted_probability=0.75,
            confidence=0.85,
        )

        # Mock a foreign key constraint violation
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.IntegrityError("FOREIGN KEY constraint failed")
        )

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            with pytest.raises(DatabaseError) as exc_info:
                await repo.save_prediction(prediction)

            # Verify the error is related to database operation
            assert "Failed to save prediction" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_prediction_with_valid_market_reference(
        self, repo: PredictionRepository
    ) -> None:
        """Test that saving prediction succeeds when market exists.

        This test verifies that the foreign key constraint allows
        insertion when a valid market_id is provided.
        """
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        prediction = Prediction(
            market_id="existing-market-123",
            predicted_probability=0.75,
            confidence=0.85,
        )

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction_id = await repo.save_prediction(prediction, upsert=False)

            assert prediction_id == 1

    # ==================== Edge field tests ====================

    @pytest.mark.asyncio
    async def test_save_prediction_with_edge(
        self, repo: PredictionRepository
    ) -> None:
        """Test that edge field is saved to database."""
        prediction = Prediction(
            market_id="test-market-edge",
            predicted_probability=0.80,
            confidence=0.85,
            edge=0.15,
        )

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.save_prediction(prediction, upsert=False)

            # Verify edge is in INSERT statement
            insert_call = mock_conn.execute.call_args
            sql = insert_call[0][0]
            params = insert_call[0][1]

            assert "edge" in sql
            assert params[7] == 0.15  # edge is the 8th parameter

    @pytest.mark.asyncio
    async def test_save_prediction_with_none_edge(
        self, repo: PredictionRepository
    ) -> None:
        """Test that None edge value is handled correctly."""
        prediction = Prediction(
            market_id="test-market-no-edge",
            predicted_probability=0.75,
            confidence=0.85,
            # edge is None by default
        )

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            await repo.save_prediction(prediction, upsert=False)

            # Verify edge (None) is in INSERT statement
            insert_call = mock_conn.execute.call_args
            params = insert_call[0][1]

            assert params[7] is None  # edge is the 8th parameter

    @pytest.mark.asyncio
    async def test_row_to_prediction_with_edge(
        self, repo: PredictionRepository
    ) -> None:
        """Test that edge field is parsed from database row."""
        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.80,
            confidence=0.85,
            edge=0.15,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.edge == 0.15

    @pytest.mark.asyncio
    async def test_row_to_prediction_with_null_edge(
        self, repo: PredictionRepository
    ) -> None:
        """Test that NULL edge is parsed as None."""
        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.75,
            confidence=0.85,
            edge=None,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.edge is None

    @pytest.mark.asyncio
    async def test_row_to_prediction_edge_zero(
        self, repo: PredictionRepository
    ) -> None:
        """Test that edge=0 is parsed correctly (not confused with None)."""
        mock_row = self._create_mock_row(
            prediction_id=1,
            market_id="test-market",
            predicted_probability=0.65,
            confidence=0.85,
            edge=0.0,
        )

        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=mock_row)

        mock_conn = AsyncMock()
        mock_conn.row_factory = MagicMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch(
            "src.storage.repositories.prediction_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_conn

            prediction = await repo.get_latest_prediction("test-market")

            assert prediction is not None
            assert prediction.edge == 0.0

    # ==================== Helper methods ====================

    def _create_mock_row(
        self,
        prediction_id: int,
        market_id: str,
        predicted_probability: float,
        confidence: float,
        reasoning: str | None = None,
        key_assumptions: str | None = None,
        model_used: str | None = None,
        recommendation: str | None = None,
        edge: float | None = None,
        actual_outcome: str | None = None,
        is_correct: int | None = None,
        validated_at: str | None = None,
        created_at: str | None = None,
    ) -> MagicMock:
        """Create a mock database row for testing."""
        mock_row = MagicMock()
        data = {
            "id": prediction_id,
            "market_id": market_id,
            "predicted_probability": predicted_probability,
            "confidence": confidence,
            "reasoning": reasoning,
            "key_assumptions": key_assumptions,
            "model_used": model_used,
            "recommendation": recommendation,
            "edge": edge,
            "actual_outcome": actual_outcome,
            "is_correct": is_correct,
            "validated_at": validated_at,
            "created_at": created_at,
        }

        # Mock keys() method for checking column existence
        mock_row.keys = MagicMock(return_value=list(data.keys()))

        # Use side_effect to properly implement __getitem__
        def getitem(key: str) -> Any:
            return data[key]

        mock_row.__getitem__.side_effect = getitem

        return mock_row
