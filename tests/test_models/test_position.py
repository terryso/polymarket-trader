"""Tests for Position model.

This module tests the Position model and related enumerations including:
- PositionStatus, PositionOutcome enum values
- Model creation (minimal and full)
- Field validation
- DateTime serialization
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.models import Position, PositionOutcome, PositionStatus


class TestPositionStatus:
    """Tests for PositionStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Test all position status values exist."""
        assert PositionStatus.OPEN.value == "OPEN"
        assert PositionStatus.CLOSED.value == "CLOSED"

    def test_status_count(self) -> None:
        """Test total number of position statuses."""
        assert len(PositionStatus) == 2

    def test_status_is_str_enum(self) -> None:
        """Test PositionStatus is string enum."""
        assert isinstance(PositionStatus.OPEN, str)


class TestPositionOutcome:
    """Tests for PositionOutcome enum."""

    def test_all_outcomes_exist(self) -> None:
        """Test all position outcome values exist."""
        assert PositionOutcome.YES.value == "YES"
        assert PositionOutcome.NO.value == "NO"

    def test_outcome_count(self) -> None:
        """Test total number of position outcomes."""
        assert len(PositionOutcome) == 2


class TestPosition:
    """Tests for Position model."""

    def test_create_position_minimal(self) -> None:
        """Test creating position with required fields only."""
        position = Position(
            id=1,
            market_id="market-123",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            status=PositionStatus.OPEN,
        )

        assert position.id == 1
        assert position.market_id == "market-123"
        assert position.outcome == PositionOutcome.YES
        assert position.shares == 100.0
        assert position.avg_price == 0.45
        assert position.status == PositionStatus.OPEN
        assert position.initial_value is None
        assert position.current_value is None
        assert position.pnl is None
        assert position.opened_at is None
        assert position.closed_at is None

    def test_create_position_full(self) -> None:
        """Test creating position with all fields."""
        position = Position(
            id=1,
            market_id="btc-100k-2026",
            outcome=PositionOutcome.YES,
            shares=222.22,
            avg_price=0.45,
            initial_value=100.0,
            current_value=155.55,
            pnl=55.55,
            status=PositionStatus.OPEN,
            opened_at=datetime(2026, 2, 15, 10, 30, 0),
            closed_at=None,
        )

        assert position.id == 1
        assert position.market_id == "btc-100k-2026"
        assert position.outcome == PositionOutcome.YES
        assert position.shares == 222.22
        assert position.avg_price == 0.45
        assert position.initial_value == 100.0
        assert position.current_value == 155.55
        assert position.pnl == 55.55
        assert position.status == PositionStatus.OPEN
        assert position.opened_at == datetime(2026, 2, 15, 10, 30, 0)
        assert position.closed_at is None

    def test_create_closed_position(self) -> None:
        """Test creating closed position."""
        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            initial_value=45.0,
            current_value=100.0,
            pnl=55.0,
            status=PositionStatus.CLOSED,
            opened_at=datetime(2026, 2, 15, 10, 30, 0),
            closed_at=datetime(2026, 2, 16, 10, 30, 0),
        )

        assert position.status == PositionStatus.CLOSED
        assert position.closed_at is not None

    def test_avg_price_validation_valid(self) -> None:
        """Test valid avg_price range (0-1)."""
        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.0,
            status=PositionStatus.OPEN,
        )
        assert position.avg_price == 0.0

        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=1.0,
            status=PositionStatus.OPEN,
        )
        assert position.avg_price == 1.0

    def test_avg_price_validation_invalid_high(self) -> None:
        """Test avg_price validation rejects values > 1."""
        with pytest.raises(ValueError):
            Position(
                id=1,
                market_id="test",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=1.5,
                status=PositionStatus.OPEN,
            )

    def test_avg_price_validation_invalid_negative(self) -> None:
        """Test avg_price validation rejects negative values."""
        with pytest.raises(ValueError):
            Position(
                id=1,
                market_id="test",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=-0.1,
                status=PositionStatus.OPEN,
            )

    def test_shares_validation_negative(self) -> None:
        """Test shares validation rejects negative values."""
        with pytest.raises(ValueError):
            Position(
                id=1,
                market_id="test",
                outcome=PositionOutcome.YES,
                shares=-100.0,
                avg_price=0.5,
                status=PositionStatus.OPEN,
            )

    def test_shares_validation_zero(self) -> None:
        """Test shares can be zero."""
        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=0.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
        )
        assert position.shares == 0.0

    def test_pnl_can_be_negative(self) -> None:
        """Test pnl can be negative (loss)."""
        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.5,
            pnl=-25.0,
            status=PositionStatus.CLOSED,
        )
        assert position.pnl == -25.0

    def test_datetime_serialization(self) -> None:
        """Test datetime serialization to ISO 8601."""
        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
            opened_at=datetime(2026, 2, 15, 10, 30, 0),
        )

        # model_dump with mode='json' returns ISO string
        data = position.model_dump(mode="json")
        assert data["opened_at"] == "2026-02-15T10:30:00"

    def test_outcome_from_string(self) -> None:
        """Test outcome creation from string."""
        position = Position(
            id=1,
            market_id="test",
            outcome="YES",
            shares=100.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
        )
        assert position.outcome == PositionOutcome.YES

        position = Position(
            id=1,
            market_id="test",
            outcome="NO",
            shares=100.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
        )
        assert position.outcome == PositionOutcome.NO

    def test_status_from_string(self) -> None:
        """Test status creation from string."""
        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.5,
            status="CLOSED",
        )
        assert position.status == PositionStatus.CLOSED

    def test_model_json_export(self) -> None:
        """Test JSON export."""
        position = Position(
            id=1,
            market_id="test-123",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.45,
            status=PositionStatus.OPEN,
        )
        json_str = position.model_dump_json()

        assert '"id":1' in json_str
        assert '"market_id":"test-123"' in json_str
        assert '"outcome":"YES"' in json_str
        assert '"status":"OPEN"' in json_str

    def test_model_config_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled."""
        position = Position(
            id=1,
            market_id="test",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
        )

        # Should validate on assignment
        with pytest.raises(ValueError):
            position.avg_price = 1.5

        # Valid assignment should work
        position.avg_price = 0.6
        assert position.avg_price == 0.6
