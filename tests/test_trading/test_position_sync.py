"""Tests for PositionCacheService.

Story 5.7: 同步实际持仓
Tech-Spec: 持仓数据源重构 - Polymarket 作为单一数据源
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.polymarket import BalanceItem, BalanceResult
from src.models.position import (
    CacheFreshness,
    Position,
    PositionOutcome,
    PositionStatus,
)
from src.trading.position_sync import (
    CacheRefreshResult,
    PositionCacheService,
    CacheStatus,
    # Backward compatibility aliases
    PositionSyncResult,
    PositionSyncService,
    PositionSyncStatus,
)


class TestCacheRefreshResult:
    """测试 CacheRefreshResult 数据class (原 PositionSyncResult)."""

    def test_default_values(self) -> None:
        """测试默认值."""
        result = CacheRefreshResult()
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
        result = CacheRefreshResult(error="Test error")
        assert result.is_success is False

    def test_total_processed(self) -> None:
        """测试总计处理数量."""
        result = CacheRefreshResult(
            new_positions=5,
            updated_positions=3,
            unchanged_positions=2,
            closed_positions=1,
        )
        assert result.total_processed == 11


class TestCacheStatus:
    """测试 CacheStatus 数据class (原 PositionSyncStatus)."""

    def test_default_values(self) -> None:
        """测试默认值."""
        status = CacheStatus()
        assert status.cache_updated_at is None
        assert status.is_refreshing is False
        assert status.can_refresh is False
        assert status.last_error is None
        assert status.total_positions == 0
        assert status.cache_freshness == CacheFreshness.EXPIRED

    # Backward compatibility
    # Backward compatibility
    def test_last_sync_at_alias(self) -> None:
        """测试 last_sync_at 别名（向后兼容）."""
        status = CacheStatus(cache_updated_at=datetime(2024, 1, 1, 12, 0, 0))
        # Access through deprecated property - this should work
        assert status.last_sync_at == datetime(2024, 1, 1, 12, 0, 0)
        assert hasattr(status, "last_sync_at")


class TestPositionCacheService:
    """测试 PositionCacheService (原 PositionSyncService)."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test."""
        PositionCacheService._reset_instance()

    @pytest.fixture
    def mock_position_repo(self) -> AsyncMock:
        """Mock PositionRepository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_position_repo: AsyncMock) -> PositionCacheService:
        """创建测试用服务."""
        service = PositionCacheService()
        service._position_repo = mock_position_repo
        return service

    def test_can_refresh_true(self, service: PositionCacheService) -> None:
        """测试 can_refresh 为 True 的条件."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"
            assert service.can_refresh is True

    def test_can_refresh_false_no_pk(self, service: PositionCacheService) -> None:
        """测试缺少 pk 时 can_refresh 为 False."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.polymarket.pk = ""
            mock_settings.polymarket.proxy_wallet = "0x1234"
            assert service.can_refresh is False

    def test_can_refresh_false_no_wallet(self, service: PositionCacheService) -> None:
        """测试缺少 wallet 时 can_refresh 为 False."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = ""
            assert service.can_refresh is False

    @pytest.mark.asyncio
    async def test_refresh_cache_paper_mode(
        self, service: PositionCacheService
    ) -> None:
        """测试 Paper 模式下返回提示信息."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "paper"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"

            result = await service.refresh_cache()

            assert result.is_success is False
            assert "Paper 模式无真实持仓" in result.error

    @pytest.mark.asyncio
    async def test_refresh_cache_already_refreshing(
        self, service: PositionCacheService
    ) -> None:
        """测试刷新进行中时的处理."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"
            mock_settings.position_cache.min_refresh_interval = 10

            # Acquire the lock to simulate a refresh in progress
            await service._refresh_lock.acquire()

            result = await service.refresh_cache()

            assert result.is_success is False
            assert "already in progress" in result.error

            # Release the lock for cleanup
            service._refresh_lock.release()

    @pytest.mark.asyncio
    async def test_refresh_cache_no_credentials(
        self, service: PositionCacheService
    ) -> None:
        """测试缺少凭证时的处理."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = ""
            mock_settings.polymarket.proxy_wallet = ""

            result = await service.refresh_cache()

            assert result.is_success is False
            assert "not configured" in result.error

    @pytest.mark.asyncio
    async def test_refresh_cache_throttled(self, service: PositionCacheService) -> None:
        """测试刷新限流."""
        with patch("src.trading.position_sync.settings") as mock_settings:
            mock_settings.trading_mode = "live"
            mock_settings.polymarket.pk = "test-pk"
            mock_settings.polymarket.proxy_wallet = "0x1234"
            mock_settings.position_cache.min_refresh_interval = 10
            with patch("src.trading.position_sync.PolymarketClient"):
                pass
                # Mock _get_cache_updated_time to return recent time
                service._get_cache_updated_time = AsyncMock(return_value=datetime.now())
                result = await service.refresh_cache()
                assert result.is_success is False
                assert "throttled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_get_cache_status(
        self, service: PositionCacheService, mock_position_repo: AsyncMock
    ) -> None:
        """测试获取缓存状态."""
        mock_position_repo.get_open_positions.return_value = [
            Position(
                id=1,
                market_id="market-1",
                outcome=PositionOutcome.YES,
                shares=100.0,
                avg_price=0.5,
                status=PositionStatus.OPEN,
                opened_at=datetime.now(),
            )
        ]

        # Mock _get_cache_updated_time to return recent time (fresh)
        async def mock_get_cache_updated() -> datetime | None:
            return datetime.now() - timedelta(seconds=30)  # 30 seconds ago, within TTL

        service._get_cache_updated_time = mock_get_cache_updated

        status = await service.get_cache_status()

        assert status.cache_updated_at is not None
        assert status.is_refreshing is False
        assert status.total_positions == 1
        assert status.cache_freshness == CacheFreshness.FRESH

    @pytest.mark.asyncio
    async def test_get_cache_status_stale(
        self, service: PositionCacheService, mock_position_repo: AsyncMock
    ) -> None:
        """测试过期缓存状态."""
        mock_position_repo.get_open_positions.return_value = []

        # Mock _get_cache_updated_time to return old time (71 seconds ago = stale)
        async def mock_get_cache_updated() -> datetime | None:
            return datetime.now() - timedelta(seconds=71)

        service._get_cache_updated_time = mock_get_cache_updated

        status = await service.get_cache_status()

        assert status.cache_freshness == CacheFreshness.STALE
        assert status.cache_age_seconds > 60

    @pytest.mark.asyncio
    async def test_get_cache_status_expired(
        self, service: PositionCacheService, mock_position_repo: AsyncMock
    ) -> None:
        """测试无缓存状态."""
        mock_position_repo.get_open_positions.return_value = []

        # Mock _get_cache_updated_time to return None
        async def mock_get_cache_updated() -> datetime | None:
            return None

        service._get_cache_updated_time = mock_get_cache_updated

        status = await service.get_cache_status()

        assert status.cache_freshness == CacheFreshness.EXPIRED
        assert status.cache_age_seconds == 0
        assert status.cache_updated_at is None


class TestPositionCacheServiceIntegration:
    """集成测试 (使用 mock API)."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test."""
        PositionCacheService._reset_instance()

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
            opened_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        repo.update.return_value = Position(
            id=1,
            market_id="test-market",
            outcome=PositionOutcome.YES,
            shares=200.0,
            avg_price=0.5,
            status=PositionStatus.OPEN,
            opened_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        return repo

    @pytest.fixture
    def service(self, mock_position_repo: AsyncMock) -> PositionCacheService:
        """创建测试用服务."""
        service = PositionCacheService()
        service._position_repo = mock_position_repo
        return service

    @pytest.mark.asyncio
    async def test_refresh_new_positions(
        self, service: PositionCacheService, mock_position_repo: AsyncMock
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
            mock_settings.position_cache.min_refresh_interval = (
                10  # Required for throttling check
            )
            with patch(
                "src.trading.position_sync.PolymarketClient"
            ) as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_balances.return_value = mock_balance_result
                mock_client_class.return_value = mock_client
                # Mock _ensure_market_exists and _set_cache_updated_time
                service._ensure_market_exists = AsyncMock()
                service._set_cache_updated_time = AsyncMock()

                result = await service.refresh_cache()

                assert result.is_success is True
                assert result.new_positions == 1
                assert result.total_fetched == 1
                assert result.refreshed_at is not None

                mock_position_repo.save.assert_called_once()
                service._set_cache_updated_time.assert_called_once()
                service._ensure_market_exists.assert_called_once()

                # Backward compatibility
                assert isinstance(result, PositionSyncResult)

                assert result.new_positions == 1
                assert result.last_sync_at is not None  # deprecated field

                assert result.refreshed_at is not None  # new field

    @pytest.mark.asyncio
    async def test_refresh_closes_missing_positions(
        self, service: PositionCacheService, mock_position_repo: AsyncMock
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
                opened_at=datetime(2024, 1, 1, 12, 0, 0),
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
            mock_settings.position_cache.min_refresh_interval = (
                10  # Required for throttling check
            )
            with patch(
                "src.trading.position_sync.PolymarketClient"
            ) as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_balances.return_value = mock_balance_result
                mock_client_class.return_value = mock_client
                service._set_cache_updated_time = AsyncMock()

                result = await service.refresh_cache()

                assert result.is_success is True
                assert result.closed_positions == 1
                # Backward compatibility
                assert isinstance(result, PositionSyncResult)

    @pytest.mark.asyncio
    async def test_refresh_updates_changed_positions(
        self, service: PositionCacheService, mock_position_repo: AsyncMock
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
                opened_at=datetime(2024, 1, 1, 12, 0, 0),
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
            mock_settings.position_cache.min_refresh_interval = (
                10  # Required for throttling check
            )
            with patch(
                "src.trading.position_sync.PolymarketClient"
            ) as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_balances.return_value = mock_balance_result
                mock_client_class.return_value = mock_client
                service._set_cache_updated_time = AsyncMock()
                service._get_cache_updated_time = AsyncMock(
                    return_value=datetime(2024, 1, 1, 12, 0, 0)
                )
                result = await service.refresh_cache()

                assert result.is_success is True
                assert result.updated_positions == 1
                assert result.new_positions == 0
                # Backward compatibility
                assert isinstance(result, PositionSyncResult)
