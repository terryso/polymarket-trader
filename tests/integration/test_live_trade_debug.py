"""Integration test for debugging live trading issues.

This test helps diagnose:
- API key configuration
- Network connectivity
- Signature generation
- Real trade execution

Run with: pytest tests/integration/test_live_trade_debug.py::test_live_trade_small_no -v -s -m integration
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.api.polymarket import PolymarketClient
from src.core.state import ThreadSafeState
from src.models.market import Market
from src.models.prediction import PredictionResult, Recommendation
from src.storage.repositories import position_repo as position_repo_module
from src.storage.repositories import statistics_repo as statistics_repo_module
from src.storage.repositories import trade_repo as trade_repo_module
from src.storage.repositories.position_repo import PositionRepository
from src.storage.repositories.statistics_repo import StatisticsRepository
from src.storage.repositories.trade_repo import TradeRepository
from src.trading.live_trading import LiveTradingExecutor
from src.trading.position_manager import PositionManager
from src.trading.risk_control import RiskCheckResult, RiskController

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Market ID for "Will Bitcoin reach $80,000 in February?"
BITCOIN_80K_FEB_MARKET_ID = "0xbfccf9f1597b7c4a06d72f39ddb81f0347c4555b98e578f546bdfb2d5af6b18e"


def _load_env_and_get_creds():
    """Load .env file and return credentials.

    This bypasses pytest's env var isolation by directly reading the .env file.
    """
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"

    if not env_file.exists():
        raise FileNotFoundError(f".env file not found at {env_file}")

    # Load with override to ensure values are set
    load_dotenv(env_file, override=True)

    # Return credentials directly from os.environ
    pk = os.getenv("PK", "")
    proxy_wallet = os.getenv("YOUR_PROXY_WALLET", "")

    if not pk:
        raise ValueError("PK not found in .env file")
    if not proxy_wallet:
        raise ValueError("YOUR_PROXY_WALLET not found in .env file")

    return pk, proxy_wallet


def _create_test_get_connection(db_path: str):
    """Create a get_connection function for test database."""
    from contextlib import asynccontextmanager
    import aiosqlite

    @asynccontextmanager
    async def get_connection():
        async with aiosqlite.connect(db_path) as conn:
            yield conn

    return get_connection


@pytest_asyncio.fixture
async def real_db():
    """Use the real database for this test."""
    db_path = "data/polymarket.db"

    # Save original get_connection functions
    original_position_get_conn = position_repo_module.get_connection
    original_trade_get_conn = trade_repo_module.get_connection
    original_stats_get_conn = statistics_repo_module.get_connection

    # Replace with test database connection
    test_get_conn = _create_test_get_connection(db_path)
    position_repo_module.get_connection = test_get_conn
    trade_repo_module.get_connection = test_get_conn
    statistics_repo_module.get_connection = test_get_conn

    yield db_path

    # Restore original functions
    position_repo_module.get_connection = original_position_get_conn
    trade_repo_module.get_connection = original_trade_get_conn
    statistics_repo_module.get_connection = original_stats_get_conn


@pytest_asyncio.fixture
async def position_repo(real_db) -> PositionRepository:
    """Create PositionRepository with real database."""
    repo = PositionRepository()
    yield repo


@pytest_asyncio.fixture
async def trade_repo(real_db) -> TradeRepository:
    """Create TradeRepository with real database."""
    repo = TradeRepository()
    yield repo


@pytest_asyncio.fixture
async def test_state() -> ThreadSafeState:
    """Create a fresh ThreadSafeState instance for testing."""
    state = ThreadSafeState(initial_capital=200.0)
    yield state


@pytest_asyncio.fixture
async def position_manager(
    position_repo: PositionRepository,
    test_state: ThreadSafeState,
) -> PositionManager:
    """Create PositionManager instance."""
    manager = PositionManager(repository=position_repo, state=test_state)
    yield manager


@pytest.fixture
def bitcoin_80k_market() -> Market:
    """Get the Bitcoin $80k February market from database."""
    import aiosqlite
    import asyncio

    async def get_market() -> Market | None:
        db_path = "data/polymarket.db"
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM markets WHERE id = ?", (BITCOIN_80K_FEB_MARKET_ID,)
            )
            row = await cursor.fetchone()

            if row is None:
                return None

            from src.storage.repositories.market_repo import MarketRepository
            repo = MarketRepository()
            return repo._row_to_market(row)

    market = asyncio.run(get_market())
    if market is None:
        pytest.skip(f"Market {BITCOIN_80K_FEB_MARKET_ID} not found in database")
    return market


@pytest.fixture
def test_amount() -> float:
    """Get test amount from environment or default to 5.0.

    Note: Polymarket CLOB API requires minimum 5 shares per order.
    For expensive shares (e.g., NO at $0.99), need at least $4.95.
    Default is $5.0 to be safe.
    """
    return float(os.getenv("LIVE_TEST_AMOUNT", "5.0"))


@pytest.mark.asyncio
async def test_live_trade_small_no(
    bitcoin_80k_market: Market,
    test_amount: float,
    trade_repo: TradeRepository,
    position_repo: PositionRepository,
    position_manager: PositionManager,
    test_state: ThreadSafeState,
) -> None:
    """Test live trading with small amount (0.001 USD) on Bitcoin $80k market."""

    print("\n" + "=" * 60)
    print("LIVE TRADE TEST - Loading Credentials")
    print("=" * 60)

    # Load credentials from .env file
    try:
        pk, proxy_wallet = _load_env_and_get_creds()
        print(f"✅ Credentials loaded:")
        print(f"   PK: {pk[:10]}...{pk[-6:]}")
        print(f"   Proxy Wallet: {proxy_wallet[:10]}...{proxy_wallet[-4:]}")
    except Exception as e:
        pytest.fail(f"❌ Failed to load credentials: {e}")

    print("\n" + "-" * 60)
    print("Step 1: Initializing Polymarket Client...")
    print("-" * 60)

    try:
        # Set environment variables for PolymarketClient to read
        os.environ["PK"] = pk
        os.environ["YOUR_PROXY_WALLET"] = proxy_wallet

        # CRITICAL: Trick settings into thinking we're not in pytest
        # so it will read from environment variables
        import src.config as config_module
        original_is_running_tests = config_module._is_running_tests
        config_module._is_running_tests = lambda: False

        # Clear settings cache
        from src.config import get_settings
        get_settings.cache_clear()

        # Now create client - settings will read from env vars
        client = PolymarketClient()

        # Restore original function
        config_module._is_running_tests = original_is_running_tests

        print("✅ PolymarketClient initialized")

        # Verify client has the key and signer
        if hasattr(client._client, 'signer') and client._client.signer:
            signer_addr = client._client.signer.address()
            print(f"✅ Signer address: {signer_addr[:10]}...{signer_addr[-4:]}")
            print(f"   Proxy wallet:   {proxy_wallet[:10]}...{proxy_wallet[-4:]}")
            if signer_addr.lower() != proxy_wallet.lower():
                print(f"⚠️  WARNING: Signer address != Proxy wallet address")
                print(f"   This may cause signature validation errors!")
        else:
            print("⚠️  Warning: Client signer verification failed")

    except Exception as e:
        pytest.fail(f"❌ Failed to initialize PolymarketClient: {e}")

    # Check wallet balance
    print("\n" + "-" * 60)
    print("Step 2: Checking Wallet Balance...")
    print("-" * 60)

    try:
        balance = client.get_wallet_balance()
        if balance.is_success:
            print(f"✅ USDC Balance: ${balance.usdc_balance:.2f}")
        else:
            print(f"⚠️  Could not fetch balance: {balance.error}")
    except Exception as e:
        print(f"⚠️  Balance check failed: {e}")

    # Display market info
    print("\n" + "-" * 60)
    print("Step 3: Market Data")
    print("-" * 60)

    print(f"Market ID: {bitcoin_80k_market.id}")
    print(f"Title: {bitcoin_80k_market.title}")
    print(f"YES Price: {bitcoin_80k_market.yes_price}")
    print(f"NO Price: {bitcoin_80k_market.no_price}")
    print(f"Liquidity: ${bitcoin_80k_market.liquidity or 0:.2f}")

    if bitcoin_80k_market.clob_token_ids:
        print(f"Token IDs: {bitcoin_80k_market.clob_token_ids}")
    else:
        print("⚠️  No token IDs in database, will fetch from API")

    # Create LiveTradingExecutor
    print("\n" + "-" * 60)
    print("Step 4: Creating Live Trading Executor...")
    print("-" * 60)

    live_executor = LiveTradingExecutor(
        client=client,
        trade_repo=trade_repo,
        position_manager=position_manager,
        state=test_state,
    )
    print("✅ LiveTradingExecutor created")

    # Create prediction for BUY_NO
    print("\n" + "-" * 60)
    print("Step 5: Creating Prediction...")
    print("-" * 60)

    prediction = PredictionResult(
        predicted_probability=0.30,
        confidence=0.85,
        reasoning="Test prediction - betting NO that Bitcoin reaches $80k in February",
        key_assumptions=["Bitcoin price stays below $80k"],
        recommendation=Recommendation.BUY_NO,
        edge=0.20,
    )

    print(f"Recommendation: {prediction.recommendation.value}")
    print(f"Predicted probability: {prediction.predicted_probability}")
    print(f"Confidence: {prediction.confidence}")
    print(f"Edge: {prediction.edge}")

    # Execute the trade
    print("\n" + "-" * 60)
    print(f"Step 6: Executing Live Trade (${test_amount} USD on NO)...")
    print("-" * 60)

    try:
        result = await live_executor.execute_trade(
            market=bitcoin_80k_market,
            prediction=prediction,
            amount=test_amount,
        )

        if result.success:
            print("\n" + "=" * 60)
            print("✅ TRADE SUCCESSFUL!")
            print("=" * 60)
            print(f"Order ID: {result.order_id}")
            print(f"Trade ID: {result.trade.id if result.trade else 'N/A'}")
            print(f"Position ID: {result.position.id if result.position else 'N/A'}")
            print(f"Amount: ${result.trade.amount if result.trade else 'N/A'}")
            print(f"Price: {result.trade.price if result.trade else 'N/A'}")
            print(f"Shares: {result.trade.shares if result.trade else 'N/A'}")

            # Verify trade was saved to database
            if result.trade:
                db_trade = await trade_repo.get_by_id(result.trade.id)
                if db_trade:
                    print(f"\n✅ Trade saved to database: id={db_trade.id}")
                else:
                    print(f"\n⚠️  Trade not found in database")

            # Verify position was created
            if result.position:
                db_position = await position_repo.get_by_id(result.position.id)
                if db_position:
                    print(f"✅ Position saved to database: id={db_position.id}")
                    print(f"   Shares: {db_position.shares}")
                    print(f"   Avg Price: {db_position.avg_price}")
                else:
                    print(f"⚠️  Position not found in database")
        else:
            print("\n" + "=" * 60)
            print("❌ TRADE FAILED!")
            print("=" * 60)
            print(f"Error: {result.error_message}")

            # Diagnostic information
            print("\n" + "-" * 60)
            print("DIAGNOSTIC INFORMATION")
            print("-" * 60)

            error_msg_lower = str(result.error_message).lower()

            if "signature" in error_msg_lower:
                print("⚠️  Signature Error Detected!")
                print("\nPossible causes:")
                print("1. Private key is incorrect or malformed")
                print("2. Private key format issue (should be hex without 0x prefix)")
                print("3. Clock synchronization issue (check system time)")
                print("\nTo fix:")
                print("- Verify PK in .env file matches your Polymarket wallet")
                print("- Ensure PK doesn't have '0x' prefix")
                print("- Check system time is accurate")

            elif "network" in error_msg_lower or "connection" in error_msg_lower:
                print("⚠️  Network Error Detected!")
                print("\nPossible causes:")
                print("1. Internet connection issue")
                print("2. Polymarket API is down")
                print("3. Firewall blocking requests")

            elif "auth" in error_msg_lower or "unauthorized" in error_msg_lower:
                print("⚠️  Authentication Error Detected!")
                print("\nPossible causes:")
                print("1. Invalid credentials")
                print("2. Proxy wallet address mismatch")

            elif "private key" in error_msg_lower:
                print("⚠️  Private Key Error Detected!")
                print("\nThis usually means the client wasn't initialized with a key.")
                print(f"PK loaded: {pk[:10]}...{pk[-6:]}")
                print(f"Client has key: {hasattr(client._client, 'key') and client._client.key is not None}")

            pytest.fail(f"Trade failed: {result.error_message}")

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ UNEXPECTED ERROR!")
        print("=" * 60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")

        import traceback
        print("\nTraceback:")
        traceback.print_exc()

        pytest.fail(f"Unexpected error: {e}")
