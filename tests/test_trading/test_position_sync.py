"""Tests for PositionSyncService.

Story 5.7: 同步实际持仓
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.polymarket import BalanceItem, BalanceResult
from src.models.position import Position, PositionOutcome, PositionStatus
from src.trading.position_sync import (
    PositionSyncResult,
    PositionSyncService,
    PositionSyncStatus,
)


class TestPositionSyncResult:
    """测试 PositionSyncResult dataclass."""

    def test_default_values(self) -> None:
        """测试默认值."""
        result = PositionSyncResult()
        assert result.new_positions == 0
        assert result.updated_positions == 0
        assert result.closed_positions == 0
        assert result.unchanged_positions == 0
        assert result.total_fetched == 0
        assert result.error is None
        assert result.is_success is True
        assert result.total_processed == 0

    def test_with_error(self) -> None:
        """测试错误状态."""
        result = PositionSyncResult(error="Test error")
        assert result.is_success is False

    def test_total_processed(self) -> None:
        """测试总计处理数量."""
        result = PositionSyncResult(
            new_positions=5,
            updated_positions=3,
            unchanged_positions=2,
            closed_positions=1,
        )
        assert result.total_processed == 11


class TestPositionSyncStatus:
    """测试 PositionSyncStatus dataclass."""

    def test_default_values(self) -> None:
        """测试默认值."""
        status = PositionSyncStatus()
        assert status.last_sync_at is None
        assert status.is_syncing is False
        assert status.can_sync is False
        assert status.last_error is None
        assert status.total_positions == 0


class TestPositionSyncService:
    """测试 PositionSyncService."""

    @pytest.fixture
    def mock_position_repo(self) -> AsyncMock:
        """Mock PositionRepository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_position_repo: AsyncMock) -> PositionSyncService:
        """创建测试用服务."""
        service = PositionSyncService()
        service._position_repo = mock_position_repo
        return service

    def test_can_sync_true(self, service: PositionSyncService) -> None:
        """测试 can_sync 为 True 的条件."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"
            assert service.can_sync is True

    def test_can_sync_false_no_pk(self, service: PositionSyncService) -> None:
        """测试缺少 pk 时 can_sync 为 False."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.polymarket.pk = ""
            mock_settings.polymarket.proxy_wallet = "0x1234"
            assert service.can_sync is False

    def test_can_sync_false_no_wallet(self, service: PositionSyncService) -> None:
        """测试缺少 wallet 时 can_sync 为 False."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = ""
            assert service.can_sync is False

    @pytest.mark.asyncio
    async def test_sync_positions_paper_mode(self, service: PositionSyncService) -> None:
        """测试 Paper 模式下返回提示信息."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "paper"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"

            result = await service.sync_positions()

            assert result.is_success is False
            assert "Paper 模式无真实持仓" in result.error

    @pytest.mark.asyncio
    async def test_sync_positions_already_syncing(
        self, service: PositionSyncService
    ) -> None:
        """测试同步进行中时的处理."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"

            service._syncing = True

            result = await service.sync_positions()

            assert result.is_success is False
            assert "already in progress" in result.error

    @pytest.mark.asyncio
    async def test_sync_positions_no_credentials(
        self, service: PositionSyncService
    ) -> None:
        """测试缺少凭证时的处理."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = ""
            mock_settings.polymarket.proxy_wallet = ""

            result = await service.sync_positions()

            assert result.is_success is False
            assert "not configured" in result.error

    @pytest.mark.asyncio
    async def test_get_sync_status(
        self, service: PositionSyncService, mock_position_repo: AsyncMock
    ) -> None:
        """测试获取同步状态."""
        mock_position_repo.get_open_positions.return_value = [
            Position(
                id=1,
                market_id="market-1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.5,
                status=PositionStatus.OPEN,
            )
        ]

        # Mock _get_last_sync_time
        async def mock_get_last_sync() -> datetime | None:
            return datetime(2024, 1, 1, 12, 0, 0)

        service._get_last_sync_time = mock_get_last_sync

        status = await service.get_sync_status()

        assert status.last_sync_at == datetime(2024, 1, 1, 12, 0, 0)
        assert status.is_syncing is False
        assert status.total_positions == 1


class TestPositionSyncServiceIntegration:
    """集成测试 (使用 mock API)."""

    @pytest.fixture
    def mock_position_repo(self) -> AsyncMock:
        """Mock PositionRepository."""
        repo = AsyncMock()
        repo.get_open_positions.return_value = []
        repo.save.return_value = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=100.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
        )
        repo.update.return_value = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=200.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
        )
        return repo

    @pytest.fixture
    def service(self, mock_position_repo: AsyncMock) -> PositionSyncService:
        """创建测试用服务."""
        service = PositionSyncService()
        service._position_repo = mock_position_repo
        return service

    @pytest.mark.asyncio
    async def test_sync_new_positions(
        self, service: PositionSyncService, mock_position_repo: AsyncMock
    ) -> None:
        """测试同步新持仓."""
        # Setup
        mock_balance_result = BalanceResult(
            balances=[
                BalanceItem(
                    condition_id="test-market",
                    outcome="YES",
                    shares=100.0,
                )
            ],
            error=None,
        )

        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"

            with patch("src.trading.position_sync.PolymarketClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_balances.return_value = mock_balance_result
                mock_client_class.return_value = mock_client

                # Mock _ensure_market_exists and _set_last_sync_time
                service._ensure_market_exists = AsyncMock()
                service._set_last_sync_time = AsyncMock()

                result = await service.sync_positions()

                assert result.is_success is True
                assert result.new_positions == 1
                assert result.total_fetched == 1

    @pytest.mark.asyncio
    async def test_sync_closes_missing_positions(
        self, service: PositionSyncService, mock_position_repo: AsyncMock
    ) -> None:
        """测试关闭链上不存在的持仓."""
        # Setup: local has position, but chain has nothing
        mock_position_repo.get_open_positions.return_value = [
            Position(
                id=1,
                market_id="old-market",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.5,
                status=PositionStatus.OPEN,
            )
        ]

        mock_balance_result = BalanceResult(
            balances=[],  # No balances on chain
            error=None,
        )

        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"

            with patch("src.trading.position_sync.PolymarketClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_balances.return_value = mock_balance_result
                mock_client_class.return_value = mock_client

                service._set_last_sync_time = AsyncMock()

                result = await service.sync_positions()

                assert result.is_success is True
                assert result.closed_positions == 1

    @pytest.mark.asyncio
    async def test_sync_updates_changed_positions(
        self, service: PositionSyncService, mock_position_repo: AsyncMock
    ) -> None:
        """测试更新已变化的持仓."""
        # Setup: local has position with different shares
        mock_position_repo.get_open_positions.return_value = [
            Position(
                id=1,
                market_id="test-market",
                outcome=PositionOutcome.YES,
                shares=100.0,  # Local has 100
                avg_price=0.5,
                initial_value=50.0,
                current_value=50.0,
                pnl=0.0,
                status=PositionStatus.OPEN,
            )
        ]

        mock_balance_result = BalanceResult(
            balances=[
                BalanceItem(
                    condition_id="test-market",
                    outcome="YES",
                    shares=200.0,  # Chain has 200
                )
            ],
            error=None,
        )

        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"

            with patch("src.trading.position_sync.PolymarketClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_balances.return_value = mock_balance_result
                mock_client_class.return_value = mock_client

                service._set_last_sync_time = AsyncMock()

                result = await service.sync_positions()

                assert result.is_success is True
                assert result.updated_positions == 1
                assert result.new_positions == 0
