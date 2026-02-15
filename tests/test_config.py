"""Tests for configuration management.

This module tests the configuration loading and validation from src/config.py.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.config import (
    LLMSettings,
    PolymarketSettings,
    RiskControlSettings,
    Settings,
    TradingSettings,
    MarketFilterSettings,
    get_settings,
)


class TestLLMSettings:
    """Tests for LLMSettings class."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        settings = LLMSettings()
        assert settings.api_base == "https://open.bigmodel.cn/api/paas/v4"
        assert settings.api_key == ""
        assert settings.model == "glm-4"
        assert settings.timeout == 30

    def test_custom_values(self) -> None:
        """Test custom values can be set."""
        settings = LLMSettings(
            api_base="https://api.example.com",
            api_key="test_key_123",
            model="gpt-4",
            timeout=60,
        )
        assert settings.api_base == "https://api.example.com"
        assert settings.api_key == "test_key_123"
        assert settings.model == "gpt-4"
        assert settings.timeout == 60

    def test_env_prefix(self) -> None:
        """Test environment variable prefix works correctly."""
        with patch.dict(os.environ, {"LLM_API_KEY": "env_key_456"}):
            settings = LLMSettings()
            assert settings.api_key == "env_key_456"


class TestPolymarketSettings:
    """Tests for PolymarketSettings class."""

    def test_default_values(self) -> None:
        """Test default values are empty strings."""
        settings = PolymarketSettings()
        assert settings.pk == ""
        assert settings.proxy_wallet == ""
        assert settings.trader_address == ""

    def test_custom_values_via_env(self) -> None:
        """Test custom values can be set via environment variables."""
        with patch.dict(os.environ, {
            "PK": "test_private_key",
            "YOUR_PROXY_WALLET": "0x1234567890abcdef",
            "BOT_TRADER_ADDRESS": "0xabcdef1234567890",
        }):
            settings = PolymarketSettings()
            assert settings.pk == "test_private_key"
            assert settings.proxy_wallet == "0x1234567890abcdef"
            assert settings.trader_address == "0xabcdef1234567890"


class TestTradingSettings:
    """Tests for TradingSettings class."""

    def test_default_values(self) -> None:
        """Test default trading values."""
        settings = TradingSettings()
        assert settings.trade_unit == 10.0
        assert settings.slippage_tolerance == 0.02
        assert settings.pct_profit == 0.03
        assert settings.pct_loss == -0.025
        assert settings.initial_capital == 200.0

    def test_custom_values_via_env(self) -> None:
        """Test custom trading values via environment variables."""
        with patch.dict(os.environ, {
            "TRADE_UNIT": "50.0",
            "SLIPPAGE_TOLERANCE": "0.05",
            "INITIAL_CAPITAL": "1000.0",
        }):
            settings = TradingSettings()
            assert settings.trade_unit == 50.0
            assert settings.slippage_tolerance == 0.05
            assert settings.initial_capital == 1000.0


class TestRiskControlSettings:
    """Tests for RiskControlSettings class."""

    def test_default_values(self) -> None:
        """Test default risk control values."""
        settings = RiskControlSettings()
        assert settings.max_single_ratio == 0.20
        assert settings.min_confidence == 0.75
        assert settings.min_edge == 0.10
        assert settings.max_concurrent_trades == 3
        assert settings.daily_loss_limit == 0.30
        assert settings.consecutive_losses_limit == 3
        assert settings.capital_threshold == 100.0

    def test_custom_values_via_env(self) -> None:
        """Test custom risk control values via environment variables."""
        with patch.dict(os.environ, {
            "MAX_SINGLE_RATIO": "0.15",
            "MIN_CONFIDENCE": "0.80",
            "MAX_CONCURRENT_TRADES": "5",
        }):
            settings = RiskControlSettings()
            assert settings.max_single_ratio == 0.15
            assert settings.min_confidence == 0.80
            assert settings.max_concurrent_trades == 5


class TestMarketFilterSettings:
    """Tests for MarketFilterSettings class."""

    def test_default_values(self) -> None:
        """Test default market filter values."""
        settings = MarketFilterSettings()
        assert settings.min_liquidity == 10000.0
        assert settings.min_deadline_days == 7

    def test_custom_values_via_env(self) -> None:
        """Test custom market filter values via environment variables."""
        with patch.dict(os.environ, {
            "MIN_LIQUIDITY": "50000.0",
            "MIN_DEADLINE_DAYS": "14",
        }):
            settings = MarketFilterSettings()
            assert settings.min_liquidity == 50000.0
            assert settings.min_deadline_days == 14


class TestSettings:
    """Tests for main Settings class."""

    def test_default_values(self) -> None:
        """Test default settings values."""
        settings = Settings()
        assert settings.trading_mode == "paper"
        assert settings.log_level == "INFO"

    def test_nested_settings(self) -> None:
        """Test nested settings are properly initialized."""
        settings = Settings()
        assert isinstance(settings.llm, LLMSettings)
        assert isinstance(settings.polymarket, PolymarketSettings)
        assert isinstance(settings.trading, TradingSettings)
        assert isinstance(settings.risk, RiskControlSettings)
        assert isinstance(settings.market_filter, MarketFilterSettings)

    def test_convenience_properties(self) -> None:
        """Test convenience properties."""
        settings = Settings()
        assert settings.initial_capital == settings.trading.initial_capital
        assert settings.min_confidence == settings.risk.min_confidence

    def test_trading_mode_validation(self) -> None:
        """Test trading mode accepts valid values."""
        settings_paper = Settings(trading_mode="paper")
        assert settings_paper.trading_mode == "paper"

        settings_live = Settings(trading_mode="live")
        assert settings_live.trading_mode == "live"

    def test_invalid_trading_mode(self) -> None:
        """Test invalid trading mode raises error."""
        with pytest.raises(PydanticValidationError):
            Settings(trading_mode="invalid")  # type: ignore


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_settings_instance(self) -> None:
        """Test get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caching(self) -> None:
        """Test get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
