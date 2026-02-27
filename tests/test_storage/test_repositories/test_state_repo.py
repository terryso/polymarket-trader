"""Tests for StateRepository.

Story 8.4: Auto Recovery Mechanism
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.storage.repositories.state_repo import StateRepository


class TestStateRepository:
    """Test cases for StateRepository."""

    @pytest.fixture
    def state_repo(self) -> StateRepository:
        """Create a StateRepository instance."""
        return StateRepository()

    @pytest.fixture
    def mock_connection(self) -> MagicMock:
        """Create a mock database connection."""
        conn = MagicMock()
        conn.execute = AsyncMock()
        conn.commit = AsyncMock()
        conn.fetchone = AsyncMock()
        conn.fetchall = AsyncMock(return_value=[])
        return conn

    def test_key_constants(self, state_repo: StateRepository) -> None:
        """Test that key constants are defined correctly."""
        assert StateRepository.KEY_CAPITAL == "current_capital"
        assert StateRepository.KEY_DAILY_PNL == "daily_pnl"
        assert StateRepository.KEY_CONSECUTIVE_LOSSES == "consecutive_losses"
        assert StateRepository.KEY_OPEN_POSITIONS == "open_positions_count"
        assert StateRepository.KEY_TRADING_ENABLED == "trading_enabled"
        assert StateRepository.KEY_REDUCED_MODE == "reduced_mode"
        assert StateRepository.KEY_LAST_MARKET_FETCH == "last_market_fetch"
        assert StateRepository.KEY_START_TIME == "start_time"
        assert StateRepository.KEY_LAST_ERROR == "last_error"

    def test_serialize_value_none(self, state_repo: StateRepository) -> None:
        """Test serializing None value."""
        assert state_repo._serialize_value(None) == "null"

    def test_serialize_value_bool(self, state_repo: StateRepository) -> None:
        """Test serializing boolean values."""
        assert state_repo._serialize_value(True) == "true"
        assert state_repo._serialize_value(False) == "false"

    def test_serialize_value_int(self, state_repo: StateRepository) -> None:
        """Test serializing integer values."""
        assert state_repo._serialize_value(123) == "123"
        assert state_repo._serialize_value(0) == "0"
        assert state_repo._serialize_value(-456) == "-456"

    def test_serialize_value_float(self, state_repo: StateRepository) -> None:
        """Test serializing float values."""
        assert state_repo._serialize_value(45.67) == "45.67"
        assert state_repo._serialize_value(0.0) == "0.0"
        assert state_repo._serialize_value(-12.34) == "-12.34"

    def test_serialize_value_datetime(self, state_repo: StateRepository) -> None:
        """Test serializing datetime values."""
        dt = datetime(2026, 2, 17, 12, 30, 45)
        result = state_repo._serialize_value(dt)
        assert result == "2026-02-17T12:30:45"

    def test_serialize_value_dict(self, state_repo: StateRepository) -> None:
        """Test serializing dictionary values."""
        data = {"key": "value", "number": 42}
        result = state_repo._serialize_value(data)
        assert '"key": "value"' in result
        assert '"number": 42' in result

    def test_serialize_value_list(self, state_repo: StateRepository) -> None:
        """Test serializing list values."""
        data = [1, 2, 3]
        result = state_repo._serialize_value(data)
        assert result == "[1, 2, 3]"

    def test_serialize_value_string(self, state_repo: StateRepository) -> None:
        """Test serializing string values."""
        assert state_repo._serialize_value("hello") == "hello"

    def test_deserialize_value_null(self, state_repo: StateRepository) -> None:
        """Test deserializing null value."""
        assert state_repo._deserialize_value("null") is None

    def test_deserialize_value_bool(self, state_repo: StateRepository) -> None:
        """Test deserializing boolean values."""
        assert state_repo._deserialize_value("true") is True
        assert state_repo._deserialize_value("false") is False

    def test_deserialize_value_int(self, state_repo: StateRepository) -> None:
        """Test deserializing integer values."""
        assert state_repo._deserialize_value("123") == 123
        assert state_repo._deserialize_value("0") == 0
        assert state_repo._deserialize_value("-456") == -456

    def test_deserialize_value_float(self, state_repo: StateRepository) -> None:
        """Test deserializing float values."""
        assert state_repo._deserialize_value("45.67") == 45.67
        assert state_repo._deserialize_value("0.0") == 0.0
        assert state_repo._deserialize_value("-12.34") == -12.34

    def test_deserialize_value_dict(self, state_repo: StateRepository) -> None:
        """Test deserializing dictionary values."""
        result = state_repo._deserialize_value('{"key": "value"}')
        assert result == {"key": "value"}

    def test_deserialize_value_list(self, state_repo: StateRepository) -> None:
        """Test deserializing list values."""
        result = state_repo._deserialize_value("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_deserialize_value_string(self, state_repo: StateRepository) -> None:
        """Test deserializing string values (fallback)."""
        assert state_repo._deserialize_value("hello") == "hello"

    def test_deserialize_value_invalid_json(self, state_repo: StateRepository) -> None:
        """Test deserializing invalid JSON returns as string."""
        result = state_repo._deserialize_value("{invalid json")
        assert result == "{invalid json"

    @pytest.mark.asyncio
    async def test_save_state(
        self, state_repo: StateRepository, mock_connection: MagicMock
    ) -> None:
        """Test saving state to database."""
        state = {
            "current_capital": 150.0,
            "trading_enabled": True,
            "consecutive_losses": 2,
        }

        with patch(
            "src.storage.repositories.state_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(
                return_value=mock_connection
            )
            mock_get_conn.return_value.__aexit__ = AsyncMock()

            await state_repo.save_state(state)

            # Verify execute was called for each key
            assert mock_connection.execute.call_count == 3
            mock_connection.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_state_empty(
        self, state_repo: StateRepository, mock_connection: MagicMock
    ) -> None:
        """Test loading state when database is empty."""
        mock_connection.fetchall.return_value = []

        with patch(
            "src.storage.repositories.state_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(
                return_value=mock_connection
            )
            mock_get_conn.return_value.__aexit__ = AsyncMock()

            state = await state_repo.load_state()

            assert state == {}
            mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_state_with_data(
        self, state_repo: StateRepository, mock_connection: MagicMock
    ) -> None:
        """Test loading state with data."""

        # Create mock rows with proper dictionary-like access
        class MockRow:
            def __init__(self, data: dict):
                self._data = data

            def __getitem__(self, key: str):
                return self._data[key]

        mock_row1 = MockRow(
            {
                "key": "current_capital",
                "value": "150.0",
                "updated_at": "2026-02-17T12:00:00",
            }
        )
        mock_row2 = MockRow(
            {
                "key": "trading_enabled",
                "value": "true",
                "updated_at": "2026-02-17T12:00:00",
            }
        )

        # Create a mock cursor that returns the rows
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [mock_row1, mock_row2]

        # Set up execute to return the mock cursor
        async def mock_execute(*args, **kwargs):
            return mock_cursor

        mock_connection.execute = mock_execute

        with patch(
            "src.storage.repositories.state_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(
                return_value=mock_connection
            )
            mock_get_conn.return_value.__aexit__ = AsyncMock()

            state = await state_repo.load_state()

            assert state["current_capital"] == 150.0
            assert state["trading_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_state_value(
        self, state_repo: StateRepository, mock_connection: MagicMock
    ) -> None:
        """Test getting a single state value."""

        # Create a mock row with proper __getitem__ support
        class MockRow:
            def __init__(self, data: dict):
                self._data = data

            def __getitem__(self, key: str):
                return self._data[key]

        mock_row = MockRow({"value": "150.0"})

        # Create a mock cursor that returns the row
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = mock_row

        # Set up execute to return the mock cursor
        async def mock_execute(*args, **kwargs):
            return mock_cursor

        mock_connection.execute = mock_execute

        with patch(
            "src.storage.repositories.state_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(
                return_value=mock_connection
            )
            mock_get_conn.return_value.__aexit__ = AsyncMock()

            value = await state_repo.get_state_value("current_capital")

            assert value == 150.0

    @pytest.mark.asyncio
    async def test_get_state_value_not_found(
        self, state_repo: StateRepository, mock_connection: MagicMock
    ) -> None:
        """Test getting a state value that doesn't exist."""
        mock_connection.fetchone.return_value = None

        with patch(
            "src.storage.repositories.state_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(
                return_value=mock_connection
            )
            mock_get_conn.return_value.__aexit__ = AsyncMock()

            value = await state_repo.get_state_value("nonexistent")

            assert value is None

    @pytest.mark.asyncio
    async def test_set_state_value(
        self, state_repo: StateRepository, mock_connection: MagicMock
    ) -> None:
        """Test setting a single state value."""
        with patch(
            "src.storage.repositories.state_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(
                return_value=mock_connection
            )
            mock_get_conn.return_value.__aexit__ = AsyncMock()

            await state_repo.set_state_value("current_capital", 150.0)

            mock_connection.execute.assert_called_once()
            mock_connection.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_state(
        self, state_repo: StateRepository, mock_connection: MagicMock
    ) -> None:
        """Test clearing all state."""
        with patch(
            "src.storage.repositories.state_repo.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(
                return_value=mock_connection
            )
            mock_get_conn.return_value.__aexit__ = AsyncMock()

            await state_repo.clear_state()

            mock_connection.execute.assert_called_once()
            mock_connection.commit.assert_called_once()


class TestStateRepositorySerializationRoundTrip:
    """Test serialization/deserialization round trips."""

    @pytest.fixture
    def state_repo(self) -> StateRepository:
        """Create a StateRepository instance."""
        return StateRepository()

    def test_roundtrip_none(self, state_repo: StateRepository) -> None:
        """Test round trip for None."""
        serialized = state_repo._serialize_value(None)
        deserialized = state_repo._deserialize_value(serialized)
        assert deserialized is None

    def test_roundtrip_bool(self, state_repo: StateRepository) -> None:
        """Test round trip for boolean."""
        for value in [True, False]:
            serialized = state_repo._serialize_value(value)
            deserialized = state_repo._deserialize_value(serialized)
            assert deserialized == value

    def test_roundtrip_int(self, state_repo: StateRepository) -> None:
        """Test round trip for integer."""
        for value in [0, 123, -456, 1000000]:
            serialized = state_repo._serialize_value(value)
            deserialized = state_repo._deserialize_value(serialized)
            assert deserialized == value

    def test_roundtrip_float(self, state_repo: StateRepository) -> None:
        """Test round trip for float."""
        for value in [0.0, 45.67, -12.34, 3.14159]:
            serialized = state_repo._serialize_value(value)
            deserialized = state_repo._deserialize_value(serialized)
            assert deserialized == value

    def test_roundtrip_dict(self, state_repo: StateRepository) -> None:
        """Test round trip for dictionary."""
        value = {"key": "value", "number": 42, "nested": {"a": 1}}
        serialized = state_repo._serialize_value(value)
        deserialized = state_repo._deserialize_value(serialized)
        assert deserialized == value

    def test_roundtrip_list(self, state_repo: StateRepository) -> None:
        """Test round trip for list."""
        value = [1, 2, 3, "four", {"five": 5}]
        serialized = state_repo._serialize_value(value)
        deserialized = state_repo._deserialize_value(serialized)
        assert deserialized == value

    def test_roundtrip_datetime(self, state_repo: StateRepository) -> None:
        """Test round trip for datetime (as ISO string)."""
        dt = datetime(2026, 2, 17, 12, 30, 45)
        serialized = state_repo._serialize_value(dt)
        # Datetime serializes to ISO string, deserializes as string
        assert serialized == "2026-02-17T12:30:45"
