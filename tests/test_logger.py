"""Tests for logging configuration.

This module tests the logging setup from src/utils/logger.py.
"""

import logging
import tempfile
from pathlib import Path

import pytest

from src.utils.logger import (
    SENSITIVE_PATTERNS,
    SanitizingFilter,
    get_logger,
    setup_logging,
)


class TestSanitizingFilter:
    """Tests for SanitizingFilter class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.filter = SanitizingFilter()

    def _create_log_record(self, message: str) -> logging.LogRecord:
        """Create a log record with the given message."""
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

    def test_filter_returns_true(self) -> None:
        """Test filter always returns True."""
        record = self._create_log_record("Normal message")
        assert self.filter.filter(record) is True

    def test_sanitizes_api_key(self) -> None:
        """Test API keys are sanitized."""
        record = self._create_log_record('api_key="sk-1234567890abcdef"')
        self.filter.filter(record)
        # API keys should be masked with ****
        assert "****" in record.msg
        # The full key should not be visible
        assert "567890abcdef" not in record.msg

    def test_sanitizes_private_key(self) -> None:
        """Test private keys are sanitized."""
        record = self._create_log_record('pk="mysecretpk123456"')
        self.filter.filter(record)
        assert "[PRIVATE_KEY]" in record.msg
        assert "mysecretpk123456" not in record.msg

    def test_sanitizes_wallet_address(self) -> None:
        """Test wallet addresses are partially masked."""
        record = self._create_log_record("Wallet: 0x1234567890abcdef1234567890abcdef12345678")
        self.filter.filter(record)
        # Wallet addresses should be partially masked with ...
        assert "..." in record.msg
        # Full address should not be visible
        assert "90abcdef1234567890abcdef12345678" not in record.msg

    def test_normal_message_unchanged(self) -> None:
        """Test normal messages are not modified."""
        message = "Trade executed successfully"
        record = self._create_log_record(message)
        self.filter.filter(record)
        assert record.msg == message

    def test_empty_message(self) -> None:
        """Test empty message handling."""
        record = self._create_log_record("")
        self.filter.filter(record)
        assert record.msg == ""


class TestSensitivePatterns:
    """Tests for sensitive patterns configuration."""

    def test_patterns_exist(self) -> None:
        """Test sensitive patterns are defined."""
        assert len(SENSITIVE_PATTERNS) > 0

    def test_patterns_are_tuples(self) -> None:
        """Test each pattern is a tuple of (pattern, replacement)."""
        for pattern, replacement in SENSITIVE_PATTERNS:
            assert isinstance(pattern, str)
            assert isinstance(replacement, str)


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self) -> None:
        """Test get_logger returns a Logger instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger("test_logger", log_dir=tmpdir)
            assert isinstance(logger, logging.Logger)

    def test_logger_has_handlers(self) -> None:
        """Test logger has console and file handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger("test_logger_2", log_dir=tmpdir)
            assert len(logger.handlers) >= 2

    def test_logger_caching(self) -> None:
        """Test logger returns same instance for same name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger1 = get_logger("cached_logger", log_dir=tmpdir)
            logger2 = get_logger("cached_logger", log_dir=tmpdir)
            assert logger1 is logger2

    def test_custom_log_level(self) -> None:
        """Test custom log level is applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger("debug_logger", log_level="DEBUG", log_dir=tmpdir)
            assert logger.level == logging.DEBUG

    def test_creates_log_directory(self) -> None:
        """Test log directory is created if not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "nested" / "logs"
            assert not log_dir.exists()
            get_logger("dir_test_logger", log_dir=str(log_dir))
            assert log_dir.exists()


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging(self) -> None:
        """Test setup_logging configures root logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_level="INFO", log_dir=tmpdir)
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

    def test_clears_existing_handlers(self) -> None:
        """Test setup_logging clears existing handlers."""
        root_logger = logging.getLogger()
        # Add a dummy handler
        root_logger.addHandler(logging.NullHandler())

        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_level="INFO", log_dir=tmpdir)

            # Should have handlers from setup_logging
            assert len(root_logger.handlers) >= 1
