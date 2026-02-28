"""Pytest configuration for integration tests.

This module loads environment variables from .env file for integration tests.
Unit tests should remain isolated from environment variables.

IMPORTANT: Integration tests use a separate test database to avoid
polluting production data. The test database is created in a temporary
directory and cleaned up after each test session.
"""

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Load .env file for integration tests (makes real API calls)
load_dotenv()

# Global test database path (set in session fixture)
_test_db_path: str | None = None


@pytest.fixture(scope="session")
def test_db_path() -> str:
    """Get the test database path for the session.

    Creates a temporary directory and returns the path to a test database file.
    The database file is cleaned up after the session ends.

    Returns:
        str: Path to the test database file
    """
    global _test_db_path
    if _test_db_path is None:
        temp_dir = tempfile.mkdtemp(prefix="polymarket_test_")
        _test_db_path = os.path.join(temp_dir, "test.db")
    return _test_db_path


@pytest_asyncio.fixture(scope="session")
async def setup_test_database(test_db_path: str) -> AsyncIterator[None]:
    """Set up the test database for integration tests.

    This fixture:
    1. Creates the test database with the required schema
    2. Patches the database manager to use the test database
    3. Cleans up after all tests complete

    Note: This fixture is NOT autouse to avoid affecting unit tests.
    Integration tests should explicitly use this fixture.

    Args:
        test_db_path: Path to the test database file
    """
    from src.storage import database as db_module

    # Reset the database manager singleton
    db_module._db_manager = None

    # Create test database directory
    Path(test_db_path).parent.mkdir(parents=True, exist_ok=True)

    # Create the database with schema
    await _create_test_db_schema(test_db_path)

    # Override DatabaseConfig.from_settings to use test database
    original_from_settings = db_module.DatabaseConfig.from_settings

    def patched_from_settings():
        return db_module.DatabaseConfig(db_path=test_db_path)

    db_module.DatabaseConfig.from_settings = staticmethod(patched_from_settings)

    yield

    # Restore original method
    db_module.DatabaseConfig.from_settings = original_from_settings

    # Reset the database manager singleton
    db_module._db_manager = None

    # Clean up test database
    if _test_db_path and os.path.exists(_test_db_path):
        os.unlink(_test_db_path)
        # Try to remove the temp directory if empty
        try:
            os.rmdir(os.path.dirname(_test_db_path))
        except OSError:
            pass


async def _create_test_db_schema(db_path: str) -> None:
    """Create the test database schema.

    Args:
        db_path: Path to the test database file
    """
    async with aiosqlite.connect(db_path) as conn:
        # Markets table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                yes_price REAL,
                no_price REAL,
                liquidity REAL,
                deadline DATETIME,
                resolution_status TEXT,
                resolution_outcome TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                slug TEXT
            )
        """)

        # Predictions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                predicted_probability REAL,
                confidence REAL,
                reasoning TEXT,
                key_assumptions TEXT,
                model_used TEXT,
                recommendation TEXT,
                edge REAL,
                actual_outcome TEXT,
                is_correct INTEGER,
                validated_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Positions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                shares REAL NOT NULL,
                avg_price REAL NOT NULL,
                initial_value REAL,
                current_value REAL,
                pnl REAL,
                status TEXT,
                opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME
            )
        """)

        # Trades table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                shares REAL,
                status TEXT,
                llm_prediction_id INTEGER,
                position_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                polymarket_order_id TEXT
            )
        """)

        # Statistics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                mode TEXT NOT NULL,
                starting_capital REAL,
                ending_capital REAL,
                total_pnl REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # System state table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.commit()
