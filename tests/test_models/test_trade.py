"""Tests for Trade model.

This module tests the Trade model and related enumerations including:
- TradeType, TradeMode, TradeStatus enum values
- Model creation (minimal and full)
- Field validation
- DateTime serialization
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.models import Trade, TradeMode, TradeStatus, TradeType


class TestTradeType:
    """Tests for TradeType enum."""

    def test_all_types_exist(self) -> None:
        """Test all trade type values exist."""
        assert TradeType.BUY_YES.value == "BUY_YES"
        assert TradeType.BUY_NO.value == "BUY_NO"
        assert TradeType.SELL.value == "SELL"

    def test_type_count(self) -> None:
        """Test total number of trade types."""
        assert len(TradeType) == 3

    def test_type_is_str_enum(self) -> None:
        """Test TradeType is string enum."""
        assert isinstance(TradeType.BUY_YES, str)


class TestTradeMode:
    """Tests for TradeMode enum."""

    def test_all_modes_exist(self) -> None:
        """Test all trade mode values exist."""
        assert TradeMode.PAPER.value == "PAPER"
        assert TradeMode.LIVE.value == "LIVE"

    def test_mode_count(self) -> None:
        """Test total number of trade modes."""
        assert len(TradeMode) == 2


class TestTradeStatus:
    """Tests for TradeStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Test all trade status values exist."""
        assert TradeStatus.PENDING.value == "PENDING"
        assert TradeStatus.FILLED.value == "FILLED"
        assert TradeStatus.CANCELLED.value == "CANCELLED"

    def test_status_count(self) -> None:
        """Test total number of trade statuses."""
        assert len(TradeStatus) == 3


class TestTrade:
    """Tests for Trade model."""

    def test_create_trade_minimal(self) -> None:
        """Test creating trade with required fields only."""
        trade = Trade(
            id=1,
            market_id="market-123",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.65,
            status=TradeStatus.FILLED,
        )

        assert trade.id == 1
        assert trade.market_id == "market-123"
        assert trade.trade_type == TradeType.BUY_YES
        assert trade.mode == TradeMode.PAPER
        assert trade.amount == 100.0
        assert trade.price == 0.65
        assert trade.status == TradeStatus.FILLED
        assert trade.shares is None
        assert trade.llm_prediction_id is None
        assert trade.position_id is None
        assert trade.created_at is None

    def test_create_trade_full(self) -> None:
        """Test creating trade with all fields."""
        trade = Trade(
            id=1,
            market_id="btc-100k-2026",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.45,
            shares=222.22,
            status=TradeStatus.FILLED,
            llm_prediction_id=5,
            position_id=10,
            created_at=datetime(2026, 2, 15, 10, 30, 0),
        )

        assert trade.id == 1
        assert trade.market_id == "btc-100k-2026"
        assert trade.trade_type == TradeType.BUY_YES
        assert trade.mode == TradeMode.PAPER
        assert trade.amount == 100.0
        assert trade.price == 0.45
        assert trade.shares == 222.22
        assert trade.status == TradeStatus.FILLED
        assert trade.llm_prediction_id == 5
        assert trade.position_id == 10
        assert trade.created_at == datetime(2026, 2, 15, 10, 30, 0)

    def test_price_validation_valid(self) -> None:
        """Test valid price range (0-1)."""
        trade = Trade(
            id=1,
            market_id="test",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.0,
            status=TradeStatus.FILLED,
        )
        assert trade.price == 0.0

        trade = Trade(
            id=1,
            market_id="test",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=1.0,
            status=TradeStatus.FILLED,
        )
        assert trade.price == 1.0

    def test_price_validation_invalid_high(self) -> None:
        """Test price validation rejects values > 1."""
        with pytest.raises(ValueError):
            Trade(
                id=1,
                market_id="test",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=100.0,
                price=1.5,
                status=TradeStatus.FILLED,
            )

    def test_price_validation_invalid_negative(self) -> None:
        """Test price validation rejects negative values."""
        with pytest.raises(ValueError):
            Trade(
                id=1,
                market_id="test",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=100.0,
                price=-0.1,
                status=TradeStatus.FILLED,
            )

    def test_amount_validation_negative(self) -> None:
        """Test amount validation rejects negative values."""
        with pytest.raises(ValueError):
            Trade(
                id=1,
                market_id="test",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=-100.0,
                price=0.5,
                status=TradeStatus.FILLED,
            )

    def test_shares_validation_negative(self) -> None:
        """Test shares validation rejects negative values."""
        with pytest.raises(ValueError):
            Trade(
                id=1,
                market_id="test",
                trade_type=TradeType.BUY_YES,
                mode=TradeMode.PAPER,
                amount=100.0,
                price=0.5,
                shares=-10.0,
                status=TradeStatus.FILLED,
            )

    def test_datetime_serialization(self) -> None:
        """Test datetime serialization to ISO 8601."""
        trade = Trade(
            id=1,
            market_id="test",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.5,
            status=TradeStatus.FILLED,
            created_at=datetime(2026, 2, 15, 10, 30, 0),
        )

        # model_dump with mode='json' returns ISO string
        data = trade.model_dump(mode="json")
        assert data["created_at"] == "2026-02-15T10:30:00"

    def test_trade_type_from_string(self) -> None:
        """Test trade type creation from string."""
        trade = Trade(
            id=1,
            market_id="test",
            trade_type="BUY_YES",
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.5,
            status=TradeStatus.FILLED,
        )
        assert trade.trade_type == TradeType.BUY_YES

    def test_trade_mode_from_string(self) -> None:
        """Test trade mode creation from string."""
        trade = Trade(
            id=1,
            market_id="test",
            trade_type=TradeType.BUY_YES,
            mode="LIVE",
            amount=100.0,
            price=0.5,
            status=TradeStatus.FILLED,
        )
        assert trade.mode == TradeMode.LIVE

    def test_trade_status_from_string(self) -> None:
        """Test trade status creation from string."""
        trade = Trade(
            id=1,
            market_id="test",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.5,
            status="PENDING",
        )
        assert trade.status == TradeStatus.PENDING

    def test_model_json_export(self) -> None:
        """Test JSON export."""
        trade = Trade(
            id=1,
            market_id="test-123",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.65,
            status=TradeStatus.FILLED,
        )
        json_str = trade.model_dump_json()

        assert '"id":1' in json_str
        assert '"market_id":"test-123"' in json_str
        assert '"trade_type":"BUY_YES"' in json_str

    def test_model_config_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled."""
        trade = Trade(
            id=1,
            market_id="test",
            trade_type=TradeType.BUY_YES,
            mode=TradeMode.PAPER,
            amount=100.0,
            price=0.5,
            status=TradeStatus.FILLED,
        )

        # Should validate on assignment
        with pytest.raises(ValueError):
            trade.price = 1.5

        # Valid assignment should work
        trade.price = 0.7
        assert trade.price == 0.7
