"""Database initialization and connection management.

This module provides SQLite database support using aiosqlite for async operations.
It implements connection pooling and schema initialization following the
architecture specification.

Usage:
    from src.storage.database import init_db, get_connection

    # Initialize database
    await init_db()

    # Use connection
    async with get_connection() as conn:
        await conn.execute("SELECT * FROM markets")
"""

from __future__ import annotations

__all__ = [
    "DatabaseConfig",
    "DatabaseManager",
    "get_db_manager",
    "init_db",
    "get_connection",
]

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from src.config import settings
from src.exceptions import DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings.

    Attributes:
        db_path: Path to the SQLite database file (string or Path object)
        max_connections: Maximum concurrent connections (for future pooling support)
    """

    db_path: str | Path
    max_connections: int = 5  # Reserved for future connection pooling

    @classmethod
    def from_settings(cls) -> "DatabaseConfig":
        """Create DatabaseConfig from global settings.

        Returns:
            DatabaseConfig instance with path from settings
        """
        from pathlib import Path

        db_path = Path(settings.data_dir) / "polymarket.db"
        return cls(db_path=db_path)


class DatabaseManager:
    """Async database connection manager.

    Provides connection management and schema initialization for SQLite
    database using aiosqlite.

    Attributes:
        _config: Database configuration
        _db_path: String path to database file
        _lock: Async lock for thread-safe operations
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize database manager.

        Args:
            config: Database configuration
        """
        self._config = config
        self._db_path = str(config.db_path)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get database connection as async context manager.

        Yields:
            aiosqlite.Connection: Database connection

        Raises:
            DatabaseError: If connection fails
        """
        async with self._lock:
            try:
                conn: aiosqlite.Connection = await aiosqlite.connect(self._db_path)
                # Enable foreign key constraints
                await conn.execute("PRAGMA foreign_keys = ON")
                try:
                    yield conn
                finally:
                    await conn.close()
            except aiosqlite.Error as e:
                logger.error(f"❌ Database connection error: {e}")
                raise DatabaseError(
                    f"Failed to connect to database: {e}",
                    operation="connect",
                    original_exception=e,
                ) from e

    async def init_db(self) -> None:
        """Initialize database schema.

        Creates the markets and system_state tables if they don't exist.
        Also creates the database directory if it doesn't exist.

        Raises:
            DatabaseError: If schema initialization fails
        """
        from pathlib import Path

        logger.info(f"📊 Initializing database at {self._db_path}...")

        # Ensure directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            async with self.get_connection() as conn:
                # Create markets table
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
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create system_state table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_state (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create predictions table
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
                        is_correct BOOLEAN,
                        validated_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (market_id) REFERENCES markets(id)
                    )
                """)

                # Migration: Add edge column if it doesn't exist (for existing databases)
                # This must run BEFORE creating the edge index
                cursor = await conn.execute("PRAGMA table_info(predictions)")
                columns = await cursor.fetchall()
                column_names = {col[1] for col in columns}

                if "edge" not in column_names:
                    logger.info(
                        "📊 Migrating database: adding edge column to predictions table"
                    )
                    await conn.execute("ALTER TABLE predictions ADD COLUMN edge REAL")

                # Create positions table (Story 4.5)
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
                        closed_at DATETIME,
                        FOREIGN KEY (market_id) REFERENCES markets(id)
                    )
                """)

                # Create indexes for predictions table
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_predictions_market_id
                    ON predictions(market_id)
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_predictions_created_at
                    ON predictions(created_at)
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_predictions_edge
                    ON predictions(edge)
                """)

                # Create indexes for positions table (Story 4.5)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_positions_market_id
                    ON positions(market_id)
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_positions_status
                    ON positions(status)
                """)

                await conn.commit()

            logger.info(f"✅ Database initialized at {self._db_path}")
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise DatabaseError(
                f"Failed to initialize database: {e}",
                operation="init_db",
                original_exception=e,
            ) from e


# Module-level singleton
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get database manager singleton instance.

    Returns:
        DatabaseManager: The database manager instance
    """
    global _db_manager
    if _db_manager is None:
        config = DatabaseConfig.from_settings()
        _db_manager = DatabaseManager(config)
    return _db_manager


async def init_db() -> None:
    """Initialize the database.

    Convenience function that initializes the database using
    the global database manager.
    """
    manager = get_db_manager()
    await manager.init_db()


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Get database connection.

    Convenience function that returns a connection from
    the global database manager.

    Yields:
        aiosqlite.Connection: Database connection
    """
    manager = get_db_manager()
    conn: aiosqlite.Connection
    async with manager.get_connection() as conn:
        yield conn
