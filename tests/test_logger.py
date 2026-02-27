"""Tests for logging configuration.

This module tests the logging setup from src/utils/logger.py.
"""

import logging
import tempfile
from pathlib import Path

import pytest

from src.utils.logger import (
    LOG_EMOJIS,
    OPERATION_EMOJIS,
    SENSITIVE_PATTERNS,
    SanitizingFilter,
    FileEmojiFormatter,
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

    def test_sanitizes_api_key_camel_case(self) -> None:
        """Test camelCase API keys are sanitized."""
        record = self._create_log_record('apiKey="sk-camelcase12345"')
        self.filter.filter(record)
        # API keys should be masked with ****
        assert "****" in record.msg
        # The full key should not be visible
        assert "camelcase12345" not in record.msg

    def test_sanitizes_api_key_title_case(self) -> None:
        """Test TitleCase API keys are sanitized."""
        record = self._create_log_record('ApiKey="sk-titlecase12345"')
        self.filter.filter(record)
        # API keys should be masked with ****
        assert "****" in record.msg
        # The full key should not be visible
        assert "titlecase12345" not in record.msg

    def test_sanitizes_private_key(self) -> None:
        """Test private keys are sanitized."""
        record = self._create_log_record('pk="mysecretpk123456"')
        self.filter.filter(record)
        assert "[PRIVATE_KEY]" in record.msg
        assert "mysecretpk123456" not in record.msg

    def test_sanitizes_wallet_address(self) -> None:
        """Test wallet addresses are partially masked."""
        record = self._create_log_record(
            "Wallet: 0x1234567890abcdef1234567890abcdef12345678"
        )
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


class TestLogEmojis:
    """Tests for log emoji configuration."""

    def test_emojis_defined(self) -> None:
        """Test log level emojis are defined."""
        assert len(LOG_EMOJIS) > 0

    def test_standard_levels_have_emojis(self) -> None:
        """Test standard log levels have emojis."""
        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in expected_levels:
            assert level in LOG_EMOJIS
            assert len(LOG_EMOJIS[level]) > 0

    def test_info_emoji_is_checkmark(self) -> None:
        """Test INFO level uses checkmark emoji."""
        assert LOG_EMOJIS["INFO"] == "✅"

    def test_warning_emoji_is_warning_sign(self) -> None:
        """Test WARNING level uses warning emoji."""
        assert LOG_EMOJIS["WARNING"] == "⚠️"

    def test_error_emoji_is_cross(self) -> None:
        """Test ERROR level uses cross emoji."""
        assert LOG_EMOJIS["ERROR"] == "❌"


class TestOperationEmojis:
    """Tests for operation-specific emojis."""

    def test_operation_emojis_defined(self) -> None:
        """Test operation emojis are defined."""
        assert len(OPERATION_EMOJIS) > 0

    def test_trade_emoji(self) -> None:
        """Test trade operation emoji."""
        assert OPERATION_EMOJIS["trade"] == "💰"

    def test_analysis_emoji(self) -> None:
        """Test analysis operation emoji."""
        assert OPERATION_EMOJIS["analysis"] == "🧠"

    def test_data_emoji(self) -> None:
        """Test data operation emoji."""
        assert OPERATION_EMOJIS["data"] == "📊"

    def test_network_emoji(self) -> None:
        """Test network operation emoji."""
        assert OPERATION_EMOJIS["network"] == "🌐"


class TestLogFormatWithEmoji:
    """Tests for log format including emoji field."""

    def test_format_contains_emoji_placeholder(self) -> None:
        """Test that log format includes emoji placeholder."""
        import io
        import sys

        # Capture stderr (colorlog outputs to stderr)
        captured_output = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_output

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                logger = get_logger("emoji_test", log_dir=tmpdir)
                logger.info("Test message")

            output = captured_output.getvalue()
            # Should contain emoji (✅ for INFO)
            assert "✅" in output
        finally:
            sys.stderr = old_stderr

    def test_format_structure(self) -> None:
        """Test log format follows specification."""
        import io
        import sys

        captured_output = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_output

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                logger = get_logger("format_test", log_dir=tmpdir)
                logger.info("Format test message")

            output = captured_output.getvalue()
            # Format: {timestamp} | {level:8} | {thread:12} | {module} | {emoji} {message}
            assert "|" in output  # Should have separators
            assert "INFO" in output
            assert "format_test" in output
            assert "✅" in output
            assert "Format test message" in output
        finally:
            sys.stderr = old_stderr

    def test_different_levels_have_different_emojis(self) -> None:
        """Test different log levels produce different emojis."""
        import io
        import sys

        outputs: dict[str, str] = {}

        for level, method in [
            ("DEBUG", "debug"),
            ("INFO", "info"),
            ("WARNING", "warning"),
            ("ERROR", "error"),
            ("CRITICAL", "critical"),
        ]:
            captured_output = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_output

            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    logger = get_logger(
                        f"emoji_{level}_test", log_level="DEBUG", log_dir=tmpdir
                    )
                    getattr(logger, method)(f"{level} message")
                outputs[level] = captured_output.getvalue()
            finally:
                sys.stderr = old_stderr

        # Each level should have its unique emoji
        assert LOG_EMOJIS["DEBUG"] in outputs["DEBUG"]
        assert LOG_EMOJIS["INFO"] in outputs["INFO"]
        assert LOG_EMOJIS["WARNING"] in outputs["WARNING"]
        assert LOG_EMOJIS["ERROR"] in outputs["ERROR"]
        assert LOG_EMOJIS["CRITICAL"] in outputs["CRITICAL"]


class TestFileOutputWithEmoji:
    """Tests for file output including emoji field."""

    def test_file_output_contains_emoji(self) -> None:
        """Test that file log output contains emoji."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger("file_emoji_test", log_dir=tmpdir)
            logger.info("Test file message")

            log_file = Path(tmpdir) / "polymarket_trader.log"
            assert log_file.exists(), "Log file should be created"

            content = log_file.read_text(encoding="utf-8")
            # File should contain INFO emoji (✅)
            assert "✅" in content
            assert "Test file message" in content

    def test_file_format_structure(self) -> None:
        """Test file log format follows specification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger("file_format_test", log_dir=tmpdir)
            logger.warning("Warning test message")

            log_file = Path(tmpdir) / "polymarket_trader.log"
            content = log_file.read_text(encoding="utf-8")

            # Format: {timestamp} | {level:8} | {thread:12} | {module} | {emoji} {message}
            assert "|" in content  # Should have separators
            assert "WARNING" in content
            assert "file_format_test" in content
            assert "⚠️" in content
            assert "Warning test message" in content

    def test_file_different_levels_have_different_emojis(self) -> None:
        """Test different log levels produce different emojis in file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for level, method in [
                ("DEBUG", "debug"),
                ("INFO", "info"),
                ("WARNING", "warning"),
                ("ERROR", "error"),
                ("CRITICAL", "critical"),
            ]:
                logger = get_logger(
                    f"file_{level}_test", log_level="DEBUG", log_dir=tmpdir
                )
                getattr(logger, method)(f"{level} file message")

            log_file = Path(tmpdir) / "polymarket_trader.log"
            content = log_file.read_text(encoding="utf-8")

            # Each level should have its unique emoji in file
            assert LOG_EMOJIS["DEBUG"] in content
            assert LOG_EMOJIS["INFO"] in content
            assert LOG_EMOJIS["WARNING"] in content
            assert LOG_EMOJIS["ERROR"] in content
            assert LOG_EMOJIS["CRITICAL"] in content


class TestFileEmojiFormatter:
    """Tests for FileEmojiFormatter class."""

    def test_formatter_adds_emoji(self) -> None:
        """Test FileEmojiFormatter adds emoji to records."""
        formatter = FileEmojiFormatter("%(emoji)s %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "✅" in result
        assert "Test message" in result
