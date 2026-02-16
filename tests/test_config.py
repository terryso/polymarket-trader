"""Tests for configuration management.

This module tests the configuration loading and validation from src/config.py.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.config import (
    LLMSettings,
    MarketFilterSettings,
    PolymarketSettings,
    RiskControlSettings,
    Settings,
    TradingSettings,
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


class TestLLMSettingsLiveModeValidation:
    """Tests for LLMSettings validation in live trading mode."""

    def test_empty_api_key_allowed_in_paper_mode(self) -> None:
        """Test empty API key is allowed in paper mode (default)."""
        with patch.dict(
            os.environ, {"TRADING_MODE": "paper", "LLM_API_KEY": ""}, clear=False
        ):
            # Should not raise - empty API key allowed in paper mode
            settings = LLMSettings()
            assert settings.api_key == ""

    def test_empty_api_key_allowed_in_paper_mode_explicit(self) -> None:
        """Test empty API key is allowed when TRADING_MODE is explicitly paper."""
        with patch.dict(
            os.environ, {"TRADING_MODE": "paper", "LLM_API_KEY": ""}, clear=False
        ):
            settings = LLMSettings()
            assert settings.api_key == ""

    def test_empty_api_key_rejected_in_live_mode(self) -> None:
        """Test empty API key raises error in live mode."""
        with patch.dict(
            os.environ, {"TRADING_MODE": "live", "LLM_API_KEY": ""}, clear=False
        ):
            with pytest.raises(PydanticValidationError) as exc_info:
                LLMSettings()
            assert "LLM_API_KEY is required when TRADING_MODE=live" in str(
                exc_info.value
            )

    def test_valid_api_key_accepted_in_live_mode(self) -> None:
        """Test non-empty API key is accepted in live mode."""
        with patch.dict(
            os.environ,
            {"TRADING_MODE": "live", "LLM_API_KEY": "sk-valid-key-123"},
            clear=False,
        ):
            settings = LLMSettings()
            assert settings.api_key == "sk-valid-key-123"

    def test_api_key_validation_via_constructor(self) -> None:
        """Test API key validation works when passed via constructor."""
        # Valid key in live mode should work
        with patch.dict(os.environ, {"TRADING_MODE": "live"}, clear=False):
            settings = LLMSettings(api_key="valid-key")
            assert settings.api_key == "valid-key"

    def test_api_key_empty_via_constructor_in_live_mode(self) -> None:
        """Test empty API key via constructor raises error in live mode."""
        with patch.dict(os.environ, {"TRADING_MODE": "live"}, clear=False):
            with pytest.raises(PydanticValidationError) as exc_info:
                LLMSettings(api_key="")
            assert "LLM_API_KEY is required when TRADING_MODE=live" in str(
                exc_info.value
            )


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
        with patch.dict(
            os.environ,
            {
                "PK": "test_private_key",
                "YOUR_PROXY_WALLET": "0x1234567890abcdef",
                "BOT_TRADER_ADDRESS": "0xabcdef1234567890",
            },
        ):
            settings = PolymarketSettings()
            assert settings.pk == "test_private_key"
            assert settings.proxy_wallet == "0x1234567890abcdef"
            assert settings.trader_address == "0xabcdef1234567890"


class TestPolymarketSettingsLiveModeValidation:
    """Tests for PolymarketSettings validation in live trading mode."""

    def test_empty_pk_allowed_in_paper_mode(self) -> None:
        """Test empty private key is allowed in paper mode."""
        with patch.dict(os.environ, {"TRADING_MODE": "paper", "PK": ""}, clear=False):
            settings = PolymarketSettings()
            assert settings.pk == ""

    def test_empty_proxy_wallet_allowed_in_paper_mode(self) -> None:
        """Test empty proxy wallet is allowed in paper mode."""
        with patch.dict(
            os.environ, {"TRADING_MODE": "paper", "YOUR_PROXY_WALLET": ""}, clear=False
        ):
            settings = PolymarketSettings()
            assert settings.proxy_wallet == ""

    def test_empty_trader_address_allowed_in_paper_mode(self) -> None:
        """Test empty trader address is allowed in paper mode."""
        with patch.dict(
            os.environ, {"TRADING_MODE": "paper", "BOT_TRADER_ADDRESS": ""}, clear=False
        ):
            settings = PolymarketSettings()
            assert settings.trader_address == ""

    def test_empty_pk_rejected_in_live_mode(self) -> None:
        """Test empty private key raises error in live mode."""
        with patch.dict(os.environ, {"TRADING_MODE": "live", "PK": ""}, clear=False):
            with pytest.raises(PydanticValidationError) as exc_info:
                PolymarketSettings()
            assert "PK (private key) is required when TRADING_MODE=live" in str(
                exc_info.value
            )

    def test_empty_proxy_wallet_rejected_in_live_mode(self) -> None:
        """Test empty proxy wallet raises error in live mode."""
        with patch.dict(
            os.environ,
            {
                "TRADING_MODE": "live",
                "PK": "valid_pk",
                "YOUR_PROXY_WALLET": "",
                "BOT_TRADER_ADDRESS": "0xvalid",
            },
            clear=False,
        ):
            with pytest.raises(PydanticValidationError) as exc_info:
                PolymarketSettings()
            assert "YOUR_PROXY_WALLET is required when TRADING_MODE=live" in str(
                exc_info.value
            )

    def test_empty_trader_address_rejected_in_live_mode(self) -> None:
        """Test empty trader address raises error in live mode."""
        with patch.dict(
            os.environ,
            {
                "TRADING_MODE": "live",
                "PK": "valid_pk",
                "YOUR_PROXY_WALLET": "0xvalid",
                "BOT_TRADER_ADDRESS": "",
            },
            clear=False,
        ):
            with pytest.raises(PydanticValidationError) as exc_info:
                PolymarketSettings()
            assert "BOT_TRADER_ADDRESS is required when TRADING_MODE=live" in str(
                exc_info.value
            )

    def test_all_credentials_valid_in_live_mode(self) -> None:
        """Test all valid credentials are accepted in live mode."""
        with patch.dict(
            os.environ,
            {
                "TRADING_MODE": "live",
                "PK": "0xabcdef1234567890",
                "YOUR_PROXY_WALLET": "0x1234567890abcdef",
                "BOT_TRADER_ADDRESS": "0xfedcba0987654321",
            },
            clear=False,
        ):
            settings = PolymarketSettings()
            assert settings.pk == "0xabcdef1234567890"
            assert settings.proxy_wallet == "0x1234567890abcdef"
            assert settings.trader_address == "0xfedcba0987654321"

    def test_pk_validation_via_constructor_in_live_mode(self) -> None:
        """Test PK validation via constructor in live mode using env vars."""
        with patch.dict(
            os.environ,
            {
                "TRADING_MODE": "live",
                "PK": "valid_pk",
                "YOUR_PROXY_WALLET": "0x1",
                "BOT_TRADER_ADDRESS": "0x2",
            },
            clear=False,
        ):
            # All credentials via env vars should work
            settings = PolymarketSettings()
            assert settings.pk == "valid_pk"
            assert settings.proxy_wallet == "0x1"
            assert settings.trader_address == "0x2"

    def test_pk_empty_via_constructor_rejected_in_live_mode(self) -> None:
        """Test empty PK raises error in live mode using env vars."""
        with patch.dict(
            os.environ,
            {
                "TRADING_MODE": "live",
                "PK": "",
                "YOUR_PROXY_WALLET": "0x1",
                "BOT_TRADER_ADDRESS": "0x2",
            },
            clear=False,
        ):
            with pytest.raises(PydanticValidationError) as exc_info:
                PolymarketSettings()
            assert "PK (private key) is required when TRADING_MODE=live" in str(
                exc_info.value
            )


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
        with patch.dict(
            os.environ,
            {
                "TRADE_UNIT": "50.0",
                "SLIPPAGE_TOLERANCE": "0.05",
                "INITIAL_CAPITAL": "1000.0",
            },
        ):
            settings = TradingSettings()
            assert settings.trade_unit == 50.0
            assert settings.slippage_tolerance == 0.05
            assert settings.initial_capital == 1000.0


class TestRiskControlSettings:
    """Tests for RiskControlSettings class."""

    def test_default_values(self) -> None:
        """Test default risk control values."""
        settings = RiskControlSettings()
        # 资金管理
        assert settings.max_single_ratio == 0.20
        assert settings.min_bet == 5.0
        # 熔断机制
        assert settings.consecutive_losses_limit == 3
        assert settings.reduce_ratio_after_losses == 0.10
        assert settings.daily_loss_limit == 0.30
        assert settings.capital_threshold == 100.0
        assert settings.reduce_ratio_low_capital == 0.10
        # 置信度门槛
        assert settings.min_confidence == 0.75
        assert settings.min_edge == 0.10
        # 持仓限制
        assert settings.max_position_per_market == 0.40
        assert settings.max_open_markets == 3
        # Backward compatibility
        assert settings.max_concurrent_trades == 3

    def test_custom_values_via_env(self) -> None:
        """Test custom risk control values via environment variables."""
        with patch.dict(
            os.environ,
            {
                "MAX_SINGLE_RATIO": "0.15",
                "MIN_BET": "10.0",
                "MIN_CONFIDENCE": "0.80",
                "MAX_OPEN_MARKETS": "5",
                "REDUCE_RATIO_AFTER_LOSSES": "0.05",
                "REDUCE_RATIO_LOW_CAPITAL": "0.08",
                "MAX_POSITION_PER_MARKET": "0.30",
            },
        ):
            settings = RiskControlSettings()
            assert settings.max_single_ratio == 0.15
            assert settings.min_bet == 10.0
            assert settings.min_confidence == 0.80
            assert settings.max_open_markets == 5
            assert settings.reduce_ratio_after_losses == 0.05
            assert settings.reduce_ratio_low_capital == 0.08
            assert settings.max_position_per_market == 0.30


class TestMarketFilterSettings:
    """Tests for MarketFilterSettings class."""

    def test_default_values(self) -> None:
        """Test default market filter values."""
        settings = MarketFilterSettings()
        assert settings.min_liquidity == 10000.0
        assert settings.min_deadline_days == 7

    def test_custom_values_via_env(self) -> None:
        """Test custom market filter values via environment variables."""
        with patch.dict(
            os.environ,
            {
                "MIN_LIQUIDITY": "50000.0",
                "MIN_DEADLINE_DAYS": "14",
            },
        ):
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


class TestTradingSettingsValidation:
    """Tests for TradingSettings validation."""

    def test_slippage_tolerance_valid_range(self) -> None:
        """Test slippage_tolerance accepts valid values in 0-1 range."""
        with patch.dict(os.environ, {"SLIPPAGE_TOLERANCE": "0.0"}):
            settings_min = TradingSettings()
            assert settings_min.slippage_tolerance == 0.0

        with patch.dict(os.environ, {"SLIPPAGE_TOLERANCE": "1.0"}):
            settings_max = TradingSettings()
            assert settings_max.slippage_tolerance == 1.0

    def test_slippage_tolerance_invalid_above_1(self) -> None:
        """Test slippage_tolerance rejects values above 1."""
        with patch.dict(os.environ, {"SLIPPAGE_TOLERANCE": "1.5"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

    def test_slippage_tolerance_invalid_negative(self) -> None:
        """Test slippage_tolerance rejects negative values."""
        with patch.dict(os.environ, {"SLIPPAGE_TOLERANCE": "-0.1"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

    def test_pct_profit_valid_range(self) -> None:
        """Test pct_profit accepts valid values in 0-1 range."""
        with patch.dict(os.environ, {"PCT_PROFIT": "0.0"}):
            settings_min = TradingSettings()
            assert settings_min.pct_profit == 0.0

        with patch.dict(os.environ, {"PCT_PROFIT": "1.0"}):
            settings_max = TradingSettings()
            assert settings_max.pct_profit == 1.0

    def test_pct_profit_invalid_above_1(self) -> None:
        """Test pct_profit rejects values above 1."""
        with patch.dict(os.environ, {"PCT_PROFIT": "1.5"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

    def test_pct_loss_valid_range(self) -> None:
        """Test pct_loss accepts valid values in -1 to 0 range."""
        with patch.dict(os.environ, {"PCT_LOSS": "-1.0"}):
            settings_min = TradingSettings()
            assert settings_min.pct_loss == -1.0

        with patch.dict(os.environ, {"PCT_LOSS": "0.0"}):
            settings_max = TradingSettings()
            assert settings_max.pct_loss == 0.0

    def test_pct_loss_invalid_positive(self) -> None:
        """Test pct_loss rejects positive values."""
        with patch.dict(os.environ, {"PCT_LOSS": "0.1"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

    def test_pct_loss_invalid_below_minus_1(self) -> None:
        """Test pct_loss rejects values below -1."""
        with patch.dict(os.environ, {"PCT_LOSS": "-1.5"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

    def test_trade_unit_must_be_positive(self) -> None:
        """Test trade_unit rejects non-positive values."""
        with patch.dict(os.environ, {"TRADE_UNIT": "0"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

        with patch.dict(os.environ, {"TRADE_UNIT": "-10.0"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

    def test_initial_capital_must_be_positive(self) -> None:
        """Test initial_capital rejects non-positive values."""
        with patch.dict(os.environ, {"INITIAL_CAPITAL": "0"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()

        with patch.dict(os.environ, {"INITIAL_CAPITAL": "-100.0"}):
            with pytest.raises(PydanticValidationError):
                TradingSettings()


class TestRiskControlSettingsValidation:
    """Tests for RiskControlSettings validation."""

    def test_max_single_ratio_valid_range(self) -> None:
        """Test max_single_ratio accepts valid values in 0-1 range."""
        with patch.dict(os.environ, {"MAX_SINGLE_RATIO": "0.0"}):
            settings_min = RiskControlSettings()
            assert settings_min.max_single_ratio == 0.0

        with patch.dict(os.environ, {"MAX_SINGLE_RATIO": "1.0"}):
            settings_max = RiskControlSettings()
            assert settings_max.max_single_ratio == 1.0

    def test_max_single_ratio_invalid_above_1(self) -> None:
        """Test max_single_ratio rejects values above 1."""
        with patch.dict(os.environ, {"MAX_SINGLE_RATIO": "1.5"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_max_single_ratio_invalid_negative(self) -> None:
        """Test max_single_ratio rejects negative values."""
        with patch.dict(os.environ, {"MAX_SINGLE_RATIO": "-0.1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_min_confidence_valid_range(self) -> None:
        """Test min_confidence accepts valid values in 0-1 range."""
        with patch.dict(os.environ, {"MIN_CONFIDENCE": "0.0"}):
            settings_min = RiskControlSettings()
            assert settings_min.min_confidence == 0.0

        with patch.dict(os.environ, {"MIN_CONFIDENCE": "1.0"}):
            settings_max = RiskControlSettings()
            assert settings_max.min_confidence == 1.0

    def test_min_confidence_invalid_above_1(self) -> None:
        """Test min_confidence rejects values above 1."""
        with patch.dict(os.environ, {"MIN_CONFIDENCE": "1.5"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_min_edge_valid_range(self) -> None:
        """Test min_edge accepts valid values in 0-1 range."""
        with patch.dict(os.environ, {"MIN_EDGE": "0.0"}):
            settings_min = RiskControlSettings()
            assert settings_min.min_edge == 0.0

        with patch.dict(os.environ, {"MIN_EDGE": "1.0"}):
            settings_max = RiskControlSettings()
            assert settings_max.min_edge == 1.0

    def test_min_edge_invalid_above_1(self) -> None:
        """Test min_edge rejects values above 1."""
        with patch.dict(os.environ, {"MIN_EDGE": "1.5"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_daily_loss_limit_valid_range(self) -> None:
        """Test daily_loss_limit accepts valid values in 0-1 range."""
        with patch.dict(os.environ, {"DAILY_LOSS_LIMIT": "0.0"}):
            settings_min = RiskControlSettings()
            assert settings_min.daily_loss_limit == 0.0

        with patch.dict(os.environ, {"DAILY_LOSS_LIMIT": "1.0"}):
            settings_max = RiskControlSettings()
            assert settings_max.daily_loss_limit == 1.0

    def test_daily_loss_limit_invalid_above_1(self) -> None:
        """Test daily_loss_limit rejects values above 1."""
        with patch.dict(os.environ, {"DAILY_LOSS_LIMIT": "1.5"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_max_concurrent_trades_must_be_positive(self) -> None:
        """Test max_concurrent_trades rejects non-positive values."""
        with patch.dict(os.environ, {"MAX_CONCURRENT_TRADES": "0"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

        with patch.dict(os.environ, {"MAX_CONCURRENT_TRADES": "-1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_consecutive_losses_limit_must_be_positive(self) -> None:
        """Test consecutive_losses_limit rejects non-positive values."""
        with patch.dict(os.environ, {"CONSECUTIVE_LOSSES_LIMIT": "0"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_capital_threshold_must_be_positive(self) -> None:
        """Test capital_threshold rejects non-positive values."""
        with patch.dict(os.environ, {"CAPITAL_THRESHOLD": "0"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

        with patch.dict(os.environ, {"CAPITAL_THRESHOLD": "-50.0"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()


class TestMarketFilterSettingsValidation:
    """Tests for MarketFilterSettings validation."""

    def test_min_liquidity_must_be_positive(self) -> None:
        """Test min_liquidity rejects non-positive values."""
        with patch.dict(os.environ, {"MIN_LIQUIDITY": "0"}):
            with pytest.raises(PydanticValidationError):
                MarketFilterSettings()

        with patch.dict(os.environ, {"MIN_LIQUIDITY": "-1000.0"}):
            with pytest.raises(PydanticValidationError):
                MarketFilterSettings()

    def test_min_deadline_days_must_be_positive(self) -> None:
        """Test min_deadline_days rejects non-positive values."""
        with patch.dict(os.environ, {"MIN_DEADLINE_DAYS": "0"}):
            with pytest.raises(PydanticValidationError):
                MarketFilterSettings()

        with patch.dict(os.environ, {"MIN_DEADLINE_DAYS": "-1"}):
            with pytest.raises(PydanticValidationError):
                MarketFilterSettings()


class TestRiskControlSettingsValidationExtra:
    """Additional tests for RiskControlSettings validation."""

    def test_min_confidence_invalid_negative(self) -> None:
        """Test min_confidence rejects negative values."""
        with patch.dict(os.environ, {"MIN_CONFIDENCE": "-0.1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_min_edge_invalid_negative(self) -> None:
        """Test min_edge rejects negative values."""
        with patch.dict(os.environ, {"MIN_EDGE": "-0.1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()


class TestSettingsValidation:
    """Tests for Settings class validation."""

    def test_log_level_valid_values(self) -> None:
        """Test log_level accepts valid logging levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(log_level=level)
            assert settings.log_level == level

    def test_log_level_case_insensitive(self) -> None:
        """Test log_level is case insensitive."""
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"

        settings = Settings(log_level="Warning")
        assert settings.log_level == "WARNING"

    def test_log_level_invalid_value(self) -> None:
        """Test log_level rejects invalid values."""
        with pytest.raises(PydanticValidationError):
            Settings(log_level="INVALID")

    def test_log_level_via_env(self) -> None:
        """Test log_level can be set via environment variable."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.log_level == "DEBUG"


class TestRiskControlSettingsEnvAliases:
    """Tests for RiskControlSettings environment variable aliases."""

    def test_consecutive_losses_limit_env_alias(self) -> None:
        """Test CONSECUTIVE_LOSSES_LIMIT env var is loaded correctly."""
        with patch.dict(os.environ, {"CONSECUTIVE_LOSSES_LIMIT": "5"}):
            settings = RiskControlSettings()
            assert settings.consecutive_losses_limit == 5

    def test_capital_threshold_env_alias(self) -> None:
        """Test CAPITAL_THRESHOLD env var is loaded correctly."""
        with patch.dict(os.environ, {"CAPITAL_THRESHOLD": "200.0"}):
            settings = RiskControlSettings()
            assert settings.capital_threshold == 200.0


class TestRiskControlSettingsExtended:
    """Tests for extended RiskControlSettings (Story 4.1)."""

    def test_min_bet_default(self) -> None:
        """Test min_bet default value."""
        settings = RiskControlSettings()
        assert settings.min_bet == 5.0

    def test_reduce_ratio_after_losses_default(self) -> None:
        """Test reduce_ratio_after_losses default value."""
        settings = RiskControlSettings()
        assert settings.reduce_ratio_after_losses == 0.10

    def test_reduce_ratio_low_capital_default(self) -> None:
        """Test reduce_ratio_low_capital default value."""
        settings = RiskControlSettings()
        assert settings.reduce_ratio_low_capital == 0.10

    def test_max_position_per_market_default(self) -> None:
        """Test max_position_per_market default value."""
        settings = RiskControlSettings()
        assert settings.max_position_per_market == 0.40

    def test_max_open_markets_default(self) -> None:
        """Test max_open_markets default value."""
        settings = RiskControlSettings()
        assert settings.max_open_markets == 3

    def test_min_bet_must_be_positive(self) -> None:
        """Test min_bet must be positive."""
        with patch.dict(os.environ, {"MIN_BET": "-1.0"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

        with patch.dict(os.environ, {"MIN_BET": "0.0"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_reduce_ratio_after_losses_range_validation(self) -> None:
        """Test reduce_ratio_after_losses range validation (0-1)."""
        with patch.dict(os.environ, {"REDUCE_RATIO_AFTER_LOSSES": "1.5"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

        with patch.dict(os.environ, {"REDUCE_RATIO_AFTER_LOSSES": "-0.1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_reduce_ratio_low_capital_range_validation(self) -> None:
        """Test reduce_ratio_low_capital range validation (0-1)."""
        with patch.dict(os.environ, {"REDUCE_RATIO_LOW_CAPITAL": "1.5"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

        with patch.dict(os.environ, {"REDUCE_RATIO_LOW_CAPITAL": "-0.1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_max_position_per_market_range_validation(self) -> None:
        """Test max_position_per_market range validation (0-1)."""
        with patch.dict(os.environ, {"MAX_POSITION_PER_MARKET": "1.5"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

        with patch.dict(os.environ, {"MAX_POSITION_PER_MARKET": "-0.1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_max_open_markets_must_be_positive(self) -> None:
        """Test max_open_markets must be positive."""
        with patch.dict(os.environ, {"MAX_OPEN_MARKETS": "0"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

        with patch.dict(os.environ, {"MAX_OPEN_MARKETS": "-1"}):
            with pytest.raises(PydanticValidationError):
                RiskControlSettings()

    def test_max_open_markets_too_large_validation(self) -> None:
        """Test max_open_markets too large raises validation error."""
        with patch.dict(os.environ, {"MAX_OPEN_MARKETS": "25"}):
            with pytest.raises(PydanticValidationError) as exc_info:
                RiskControlSettings()
        assert "MAX_OPEN_MARKETS should not exceed 20" in str(exc_info.value)

    def test_max_open_markets_accepts_20(self) -> None:
        """Test max_open_markets accepts value up to 20."""
        with patch.dict(os.environ, {"MAX_OPEN_MARKETS": "20"}):
            settings = RiskControlSettings()
            assert settings.max_open_markets == 20

    def test_env_override_min_bet(self) -> None:
        """Test environment variable override for min_bet."""
        with patch.dict(os.environ, {"MIN_BET": "10.0"}):
            settings = RiskControlSettings()
            assert settings.min_bet == 10.0

    def test_env_override_reduce_ratio_after_losses(self) -> None:
        """Test environment variable override for reduce_ratio_after_losses."""
        with patch.dict(os.environ, {"REDUCE_RATIO_AFTER_LOSSES": "0.15"}):
            settings = RiskControlSettings()
            assert settings.reduce_ratio_after_losses == 0.15

    def test_env_override_reduce_ratio_low_capital(self) -> None:
        """Test environment variable override for reduce_ratio_low_capital."""
        with patch.dict(os.environ, {"REDUCE_RATIO_LOW_CAPITAL": "0.12"}):
            settings = RiskControlSettings()
            assert settings.reduce_ratio_low_capital == 0.12

    def test_env_override_max_position_per_market(self) -> None:
        """Test environment variable override for max_position_per_market."""
        with patch.dict(os.environ, {"MAX_POSITION_PER_MARKET": "0.35"}):
            settings = RiskControlSettings()
            assert settings.max_position_per_market == 0.35

    def test_env_override_max_open_markets(self) -> None:
        """Test environment variable override for max_open_markets."""
        with patch.dict(os.environ, {"MAX_OPEN_MARKETS": "5"}):
            settings = RiskControlSettings()
            assert settings.max_open_markets == 5

    def test_backward_compatibility_max_concurrent_trades(self) -> None:
        """Test backward compatibility with MAX_CONCURRENT_TRADES."""
        with patch.dict(os.environ, {"MAX_CONCURRENT_TRADES": "7"}):
            settings = RiskControlSettings()
            assert settings.max_concurrent_trades == 7


class TestSettingsRiskControlExtended:
    """Tests for Settings with extended RiskControlSettings (Story 4.1)."""

    def test_settings_contains_extended_risk_params(self) -> None:
        """Test Settings contains extended risk control parameters."""
        settings = Settings()
        assert settings.risk.min_bet == 5.0
        assert settings.risk.reduce_ratio_after_losses == 0.10
        assert settings.risk.reduce_ratio_low_capital == 0.10
        assert settings.risk.max_position_per_market == 0.40
        assert settings.risk.max_open_markets == 3

    def test_settings_env_override_extended_params(self) -> None:
        """Test Settings environment variable override for extended params."""
        with patch.dict(
            os.environ,
            {
                "MIN_BET": "15.0",
                "REDUCE_RATIO_AFTER_LOSSES": "0.08",
            },
        ):
            settings = Settings()
            assert settings.risk.min_bet == 15.0
            assert settings.risk.reduce_ratio_after_losses == 0.08
