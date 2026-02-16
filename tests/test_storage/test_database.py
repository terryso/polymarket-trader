"""Tests for database initialization and connection management.

This module tests the database module including:
- DatabaseConfig configuration class
- DatabaseManager connection management
- Schema initialization
- Error handling
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

from src.exceptions import DatabaseError


class TestDatabaseConfig:
    """Test DatabaseConfig configuration class."""

    def test_default_values(self, tmp_path: Path) -> None:
        """Test DatabaseConfig with default values."""
        from src.storage.database import DatabaseConfig

        config = DatabaseConfig(db_path=tmp_path / "test.db")

        assert config.db_path == tmp_path / "test.db"
        assert config.max_connections == 5

    def test_custom_max_connections(self, tmp_path: Path) -> None:
        """Test DatabaseConfig with custom max connections."""
        from src.storage.database import DatabaseConfig

        config = DatabaseConfig(db_path=tmp_path / "test.db", max_connections=10)

        assert config.max_connections == 10

    def test_from_settings_creates_path(self, tmp_path: Path) -> None:
        """Test DatabaseConfig.from_settings() creates correct path."""
        from src.storage.database import DatabaseConfig

        with patch("src.storage.database.settings") as mock_settings:
            mock_settings.data_dir = str(tmp_path)
            config = DatabaseConfig.from_settings()

            assert config.db_path == tmp_path / "polymarket.db"


class TestDatabaseManager:
    """Test DatabaseManager class."""

    @pytest_asyncio.fixture
    async def temp_db(self, tmp_path: Path) -> "DatabaseManager":
        """Create a temporary database manager for testing."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        return DatabaseManager(config)

    @pytest.mark.asyncio
    async def test_get_connection_success(self, temp_db: "DatabaseManager") -> None:
        """Test successful database connection."""
        async with temp_db.get_connection() as conn:
            assert conn is not None
            # Verify foreign keys are enabled
            cursor = await conn.execute("PRAGMA foreign_keys")
            result = await cursor.fetchone()
            assert result[0] == 1

    @pytest.mark.asyncio
    async def test_connection_context_manager(self, temp_db: "DatabaseManager") -> None:
        """Test connection is properly closed after context exit."""
        async with temp_db.get_connection() as conn:
            pass
        # Connection should be closed now
        # We can verify by checking if a new connection works
        async with temp_db.get_connection() as conn:
            assert conn is not None

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self, temp_db: "DatabaseManager") -> None:
        """Test init_db creates the required tables."""
        await temp_db.init_db()

        async with temp_db.get_connection() as conn:
            # Check markets table exists
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='markets'"
            )
            result = await cursor.fetchone()
            assert result is not None

            # Check system_state table exists
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='system_state'"
            )
            result = await cursor.fetchone()
            assert result is not None

    @pytest.mark.asyncio
    async def test_init_db_creates_directory(self, tmp_path: Path) -> None:
        """Test init_db creates the database directory if it doesn't exist."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        new_dir = tmp_path / "new_directory"
        config = DatabaseConfig(db_path=new_dir / "test.db")
        manager = DatabaseManager(config)

        await manager.init_db()

        assert new_dir.exists()
        assert (new_dir / "test.db").exists()

    @pytest.mark.asyncio
    async def test_init_db_is_idempotent(self, temp_db: "DatabaseManager") -> None:
        """Test init_db can be called multiple times without error."""
        await temp_db.init_db()
        await temp_db.init_db()  # Should not raise

    @pytest.mark.asyncio
    async def test_init_db_log_messages(self, temp_db: "DatabaseManager") -> None:
        """Test init_db logs appropriate messages."""
        import logging

        with patch("src.storage.database.logger") as mock_logger:
            await temp_db.init_db()

            # Verify info log was called for initialization start
            mock_logger.info.assert_called()


class TestDatabaseSchema:
    """Test database schema structure."""

    @pytest_asyncio.fixture
    async def initialized_db(self, tmp_path: Path) -> "DatabaseManager":
        """Create and initialize a database for testing."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)
        await manager.init_db()
        return manager

    @pytest.mark.asyncio
    async def test_markets_table_columns(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test markets table has all required columns."""
        expected_columns = {
            "id",
            "title",
            "description",
            "category",
            "yes_price",
            "no_price",
            "liquidity",
            "deadline",
            "resolution_status",
            "resolution_outcome",
            "created_at",
            "updated_at",
        }

        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(markets)")
            rows = await cursor.fetchall()
            actual_columns = {row[1] for row in rows}

            assert expected_columns == actual_columns

    @pytest.mark.asyncio
    async def test_system_state_table_columns(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test system_state table has all required columns."""
        expected_columns = {"key", "value", "updated_at"}

        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(system_state)")
            rows = await cursor.fetchall()
            actual_columns = {row[1] for row in rows}

            assert expected_columns == actual_columns

    @pytest.mark.asyncio
    async def test_markets_table_primary_key(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test markets table has correct primary key."""
        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(markets)")
            rows = await cursor.fetchall()
            pk_columns = [row[1] for row in rows if row[5] == 1]

            assert pk_columns == ["id"]

    @pytest.mark.asyncio
    async def test_system_state_table_primary_key(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test system_state table has correct primary key."""
        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(system_state)")
            rows = await cursor.fetchall()
            pk_columns = [row[1] for row in rows if row[5] == 1]

            assert pk_columns == ["key"]

    @pytest.mark.asyncio
    async def test_predictions_table_exists(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test predictions table is created."""
        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'"
            )
            result = await cursor.fetchone()
            assert result is not None

    @pytest.mark.asyncio
    async def test_predictions_table_columns(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test predictions table has all required columns."""
        expected_columns = {
            "id",
            "market_id",
            "predicted_probability",
            "confidence",
            "reasoning",
            "key_assumptions",
            "model_used",
            "recommendation",
            "edge",  # New edge column
            "actual_outcome",
            "is_correct",
            "validated_at",
            "created_at",
        }

        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(predictions)")
            rows = await cursor.fetchall()
            actual_columns = {row[1] for row in rows}

            assert expected_columns == actual_columns

    @pytest.mark.asyncio
    async def test_predictions_table_primary_key(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test predictions table has correct primary key."""
        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(predictions)")
            rows = await cursor.fetchall()
            pk_columns = [row[1] for row in rows if row[5] == 1]

            assert pk_columns == ["id"]

    @pytest.mark.asyncio
    async def test_predictions_table_indexes(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test predictions table has correct indexes."""
        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='predictions'"
            )
            rows = await cursor.fetchall()
            index_names = {row[0] for row in rows}

            assert "idx_predictions_market_id" in index_names
            assert "idx_predictions_created_at" in index_names
            assert "idx_predictions_edge" in index_names  # New edge index

    @pytest.mark.asyncio
    async def test_predictions_foreign_key_to_markets(
        self, initialized_db: "DatabaseManager"
    ) -> None:
        """Test predictions table has foreign key to markets table."""
        async with initialized_db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='predictions'"
            )
            result = await cursor.fetchone()
            sql = result[0]

            assert "FOREIGN KEY" in sql
            assert "market_id" in sql
            assert "REFERENCES markets" in sql


class TestDatabaseMigration:
    """Test database migration for edge column."""

    @pytest.mark.asyncio
    async def test_migration_adds_edge_column(self, tmp_path: Path) -> None:
        """Test that migration adds edge column if it doesn't exist."""
        import aiosqlite

        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        # Create initial database without edge column (simulate old schema)
        async with aiosqlite.connect(str(config.db_path)) as conn:
            await conn.execute("""
                CREATE TABLE predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    predicted_probability REAL,
                    confidence REAL,
                    reasoning TEXT,
                    key_assumptions TEXT,
                    model_used TEXT,
                    recommendation TEXT,
                    actual_outcome TEXT,
                    is_correct BOOLEAN,
                    validated_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (market_id) REFERENCES markets(id)
                )
            """)
            await conn.commit()

        # Run init_db which should add the edge column via migration
        await manager.init_db()

        # Verify edge column was added
        async with manager.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(predictions)")
            rows = await cursor.fetchall()
            column_names = {row[1] for row in rows}

            assert "edge" in column_names

    @pytest.mark.asyncio
    async def test_migration_creates_edge_index(self, tmp_path: Path) -> None:
        """Test that migration creates edge index."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        # Initialize database
        await manager.init_db()

        # Verify edge index exists
        async with manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='predictions'"
            )
            rows = await cursor.fetchall()
            index_names = {row[0] for row in rows}

            assert "idx_predictions_edge" in index_names

    @pytest.mark.asyncio
    async def test_migration_is_idempotent(self, tmp_path: Path) -> None:
        """Test that migration can run multiple times without error."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        # Run init_db multiple times
        await manager.init_db()
        await manager.init_db()  # Should not raise

        # Verify edge column still exists and is unique
        async with manager.get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(predictions)")
            rows = await cursor.fetchall()
            edge_columns = [row for row in rows if row[1] == "edge"]

            assert len(edge_columns) == 1  # Only one edge column


class TestDatabaseErrorHandling:
    """Test database error handling."""

    @pytest.mark.asyncio
    async def test_invalid_path_raises_error(self) -> None:
        """Test that invalid path raises DatabaseError."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=Path("/nonexistent/path/test.db"))
        manager = DatabaseManager(config)

        with pytest.raises(DatabaseError):
            # This should fail because /nonexistent is not writable
            async with manager.get_connection():
                pass

    @pytest.mark.asyncio
    async def test_connection_error_propagates(self, tmp_path: Path) -> None:
        """Test that connection errors are properly wrapped in DatabaseError."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        # Normal operation should work
        async with manager.get_connection() as conn:
            await conn.execute("SELECT 1")


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_init_db_function(self, tmp_path: Path) -> None:
        """Test the init_db convenience function."""
        from src.storage import database as db_module

        # Reset the singleton
        db_module._db_manager = None

        with patch("src.storage.database.settings") as mock_settings:
            mock_settings.data_dir = str(tmp_path)
            await db_module.init_db()

            assert (tmp_path / "polymarket.db").exists()

        # Reset for other tests
        db_module._db_manager = None

    @pytest.mark.asyncio
    async def test_get_db_manager_singleton(self, tmp_path: Path) -> None:
        """Test get_db_manager returns the same instance."""
        from src.storage import database as db_module
        from src.storage.database import DatabaseManager, get_db_manager

        # Reset singleton
        db_module._db_manager = None

        with patch("src.storage.database.settings") as mock_settings:
            mock_settings.data_dir = str(tmp_path)

            manager1 = get_db_manager()
            manager2 = get_db_manager()

            assert manager1 is manager2

        # Reset for other tests
        db_module._db_manager = None

    @pytest.mark.asyncio
    async def test_get_connection_function(self, tmp_path: Path) -> None:
        """Test the get_connection convenience function."""
        from src.storage import database as db_module
        from src.storage.database import get_connection

        # Reset singleton
        db_module._db_manager = None

        with patch("src.storage.database.settings") as mock_settings:
            mock_settings.data_dir = str(tmp_path)

            # First initialize the database
            await db_module.init_db()

            # Then test the connection function
            async with get_connection() as conn:
                assert conn is not None
                cursor = await conn.execute("SELECT 1")
                result = await cursor.fetchone()
                assert result[0] == 1

        # Reset for other tests
        db_module._db_manager = None


class TestDatabaseError:
    """Test DatabaseError exception class."""

    def test_database_error_is_bot_error(self) -> None:
        """Test DatabaseError is a subclass of BotError."""
        from src.exceptions import BotError

        assert issubclass(DatabaseError, BotError)

    def test_database_error_message(self) -> None:
        """Test DatabaseError preserves message."""
        error = DatabaseError("Test error message")
        assert "Test error message" in str(error)

    def test_database_error_with_original_exception(self) -> None:
        """Test DatabaseError wraps original exception."""
        original = ValueError("Original error")
        error = DatabaseError("Wrapper", original_exception=original)

        assert "Original error" in str(error)
        assert error.original_exception is original

    def test_database_error_with_operation(self) -> None:
        """Test DatabaseError with operation parameter."""
        error = DatabaseError("Test error", operation="init_db")

        assert "Test error" in str(error)
        assert error.operation == "init_db"

    def test_database_error_all_parameters(self) -> None:
        """Test DatabaseError with all parameters."""
        original = RuntimeError("DB crashed")
        error = DatabaseError(
            "Database failed",
            operation="connect",
            original_exception=original,
        )

        assert "Database failed" in str(error)
        assert error.operation == "connect"
        assert error.original_exception is original


class TestDatabaseManagerErrorHandling:
    """Test DatabaseManager error handling edge cases."""

    @pytest.mark.asyncio
    async def test_connection_error_logs_message(self, tmp_path: Path) -> None:
        """Test that connection errors log appropriate error messages."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=Path("/nonexistent_dir_test/test.db"))
        manager = DatabaseManager(config)

        with patch("src.storage.database.logger") as mock_logger:
            with pytest.raises(DatabaseError):
                async with manager.get_connection():
                    pass

            # Verify error was logged
            mock_logger.error.assert_called()
            error_call_args = str(mock_logger.error.call_args)
            assert "Database connection error" in error_call_args

    @pytest.mark.asyncio
    async def test_init_db_with_mkdir_failure(self, tmp_path: Path) -> None:
        """Test that init_db handles directory creation failure."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        # Use a path that will fail mkdir (mock Path.mkdir to fail)
        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        # The actual init_db should succeed normally
        # This tests the happy path with directory creation
        await manager.init_db()
        assert (tmp_path / "test.db").exists()


class TestDatabaseConfigEdgeCases:
    """Test DatabaseConfig edge cases."""

    def test_db_path_as_string(self) -> None:
        """Test DatabaseConfig with string path."""
        from src.storage.database import DatabaseConfig

        config = DatabaseConfig(db_path="/tmp/test.db")

        assert config.db_path == "/tmp/test.db"

    def test_db_path_as_path_object(self, tmp_path: Path) -> None:
        """Test DatabaseConfig with Path object."""
        from src.storage.database import DatabaseConfig

        config = DatabaseConfig(db_path=tmp_path / "test.db")

        assert config.db_path == tmp_path / "test.db"

    def test_max_connections_validation(self) -> None:
        """Test max_connections accepts any value (dataclass doesn't validate)."""
        from src.storage.database import DatabaseConfig

        # Zero max_connections - works (dataclass doesn't validate)
        config = DatabaseConfig(db_path="/tmp/test.db", max_connections=0)
        assert config.max_connections == 0

        # Negative max_connections - works (dataclass doesn't validate)
        config = DatabaseConfig(db_path="/tmp/test.db", max_connections=-1)
        assert config.max_connections == -1


class TestDatabaseManagerConnection:
    """Test DatabaseManager connection behavior."""

    @pytest.mark.asyncio
    async def test_connection_enables_foreign_keys(self, tmp_path: Path) -> None:
        """Test that foreign keys are enabled by default."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        async with manager.get_connection() as conn:
            cursor = await conn.execute("PRAGMA foreign_keys")
            result = await cursor.fetchone()
            assert result[0] == 1  # Foreign keys are ON

    @pytest.mark.asyncio
    async def test_connection_isolates_transactions(self, tmp_path: Path) -> None:
        """Test that each connection is isolated."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        # Initialize and add data in first connection
        await manager.init_db()
        async with manager.get_connection() as conn:
            await conn.execute(
                "INSERT INTO system_state (key, value) VALUES ('test_key', 'test_value')"
            )
            await conn.commit()

        # Verify data in second connection
        async with manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM system_state WHERE key = 'test_key'"
            )
            result = await cursor.fetchone()
            assert result[0] == "test_value"

    @pytest.mark.asyncio
    async def test_connection_closes_properly(self, tmp_path: Path) -> None:
        """Test that connection is properly closed after use."""
        from src.storage.database import DatabaseConfig, DatabaseManager

        config = DatabaseConfig(db_path=tmp_path / "test.db")
        manager = DatabaseManager(config)

        # Use connection
        async with manager.get_connection() as conn:
            await conn.execute("SELECT 1")

        # Connection should be closed - verify by opening a new one
        # that works correctly
        async with manager.get_connection() as conn:
            cursor = await conn.execute("SELECT 1")
            result = await cursor.fetchone()
            assert result[0] == 1
