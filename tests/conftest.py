"""Pytest configuration and fixtures.

This module provides common fixtures and configuration for testing
the Polymarket Trader application.
"""

import asyncio
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def disable_retry_delays() -> Generator[None, None, None]:
    """Disable retry delays in tests to speed up execution.

    This fixture automatically patches the retry decorator's sleep functions
    to eliminate delays during testing, making tests that trigger retry
    logic run instantly.
    """
    import time

    import src.utils.retry as retry_module

    # Store original functions
    original_sleep = time.sleep
    original_async_sleep = asyncio.sleep

    # Replace with no-op versions
    time.sleep = lambda *_: None
    retry_module.asyncio.sleep = AsyncMock()

    yield

    # Restore original functions
    time.sleep = original_sleep
    retry_module.asyncio.sleep = original_async_sleep


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.trading_mode = "paper"
    settings.log_level = "DEBUG"
    settings.initial_capital = 200.0
    settings.min_confidence = 0.75
    settings.min_edge = 0.10

    # LLM settings
    settings.llm = MagicMock()
    settings.llm.api_base = "https://api.test.com"
    settings.llm.api_key = "test_key_1234"
    settings.llm.model = "test-model"
    settings.llm.timeout = 30

    # Polymarket settings
    settings.polymarket = MagicMock()
    settings.polymarket.pk = "test_pk"
    settings.polymarket.proxy_wallet = "0x1234567890abcdef"
    settings.polymarket.trader_address = "0xabcdef1234567890"

    # Trading settings
    settings.trading = MagicMock()
    settings.trading.trade_unit = 10.0
    settings.trading.slippage_tolerance = 0.02
    settings.trading.initial_capital = 200.0

    # Risk settings
    settings.risk = MagicMock()
    settings.risk.max_single_ratio = 0.20
    settings.risk.min_confidence = 0.75
    settings.risk.daily_loss_limit = 0.30
    settings.risk.max_concurrent_trades = 3

    return settings


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger for testing."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    logger.critical = MagicMock()
    return logger


@pytest_asyncio.fixture
async def mock_db_connection() -> AsyncGenerator[AsyncMock, None]:
    """Create mock database connection for testing."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchone = AsyncMock(return_value=None)
    conn.fetchall = AsyncMock(return_value=[])
    conn.commit = AsyncMock()
    conn.rollback = AsyncMock()
    conn.close = AsyncMock()
    yield conn


@pytest.fixture
def sample_market_data() -> dict[str, Any]:
    """Create sample market data for testing."""
    return {
        "id": "test-market-001",
        "title": "Will X happen by 2026?",
        "description": "A test prediction market",
        "category": "politics",
        "yes_price": 0.65,
        "no_price": 0.35,
        "liquidity": 50000.0,
        "deadline": "2026-12-31T23:59:59Z",
        "resolution_status": None,
        "resolution_outcome": None,
    }


@pytest.fixture
def sample_prediction_data() -> dict[str, Any]:
    """Create sample prediction data for testing."""
    return {
        "market_id": "test-market-001",
        "predicted_probability": 0.72,
        "confidence": 0.85,
        "reasoning": "Test reasoning",
        "key_assumptions": ["Assumption 1", "Assumption 2"],
        "recommendation": "BUY_YES",
    }


@pytest.fixture
def sample_trade_data() -> dict[str, Any]:
    """Create sample trade data for testing."""
    return {
        "id": 1,
        "market_id": "test-market-001",
        "trade_type": "BUY_YES",
        "mode": "PAPER",
        "amount": 10.0,
        "price": 0.65,
        "shares": 15.38,
        "status": "FILLED",
    }
