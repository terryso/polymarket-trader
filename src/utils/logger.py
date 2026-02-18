"""Logging configuration for the Polymarket Trader application.

This module provides a colored logging setup with both console and file output,
following the architecture specification. Console output goes to stderr with
colors, file output goes to logs/polymarket_trader.log with rotation.
"""

from __future__ import annotations

__all__ = [
    "LOG_EMOJIS",
    "OPERATION_EMOJIS",
    "SENSITIVE_PATTERNS",
    "SanitizingFilter",
    "EmojiFormatter",
    "FileEmojiFormatter",
    "ErrorLogFormatter",
    "get_logger",
    "setup_logging",
    "setup_error_log_handler",
]

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
import colorlog


# Emoji mappings for log levels
LOG_EMOJIS: dict[str, str] = {
    "DEBUG": "🔍",
    "INFO": "✅",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔥",
    "NOTSET": "",
}

# Operation-specific emojis (for use in log messages)
OPERATION_EMOJIS: dict[str, str] = {
    "trade": "💰",
    "analysis": "🧠",
    "data": "📊",
    "network": "🌐",
}


# Sensitive patterns for log sanitization
SENSITIVE_PATTERNS = [
    # API Keys - show only first 4 characters (matches api_key, api-key, apiKey, ApiKey)
    (r'(api[_-]?key|apiKey|ApiKey)["\s:=]+["\']?([a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]*["\']?', r'\1"\2****"'),
    (r'(LLM_API_KEY=["\']?)([a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]*', r'\g<1>\2****'),
    # Private keys - completely hide
    (r'(pk|private[_-]?key["\s:=]+)["\']?[a-zA-Z0-9]+["\']?', r'\1[PRIVATE_KEY]'),
    (r'(PK=["\']?)[a-zA-Z0-9]+', r'\g<1>[PRIVATE_KEY]'),
    # Wallet addresses - show first 6 and last 4 characters
    (r'(0x[a-fA-F0-9]{6})[a-fA-F0-9]+([a-fA-F0-9]{4})', r'\1...\2'),
]


class SanitizingFilter(logging.Filter):
    """Log filter that sanitizes sensitive information."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize the log message."""
        message = record.getMessage()
        for pattern, replacement in SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        # Update the message
        record.msg = message
        record.args = ()
        return True


class EmojiFormatter(colorlog.ColoredFormatter):
    """Formatter that adds emoji to log messages based on level."""

    def format(self, record: logging.LogRecord) -> str:
        """Add emoji to the log record before formatting.

        Args:
            record: The log record to format.

        Returns:
            Formatted log message with emoji.
        """
        # Add emoji based on level
        record.emoji = LOG_EMOJIS.get(record.levelname, "")
        return super().format(record)


class FileEmojiFormatter(logging.Formatter):
    """Formatter for file output that adds emoji based on level."""

    def format(self, record: logging.LogRecord) -> str:
        """Add emoji to the log record before formatting.

        Args:
            record: The log record to format.

        Returns:
            Formatted log message with emoji.
        """
        record.emoji = LOG_EMOJIS.get(record.levelname, "")
        return super().format(record)


class ErrorLogFormatter(logging.Formatter):
    """Formatter for dedicated error log file with JSON-like structure."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with extra context.

        Args:
            record: The log record to format.

        Returns:
            Formatted log message with context.
        """
        record.emoji = LOG_EMOJIS.get(record.levelname, "")
        base_message = super().format(record)

        # Add extra fields if present
        extra = getattr(record, "extra", None) or getattr(record, "__dict__", {})
        context_parts = []

        # Extract context and traceback from extra
        if "context" in extra and extra["context"]:
            context_parts.append(f"context={extra['context']}")
        if "traceback" in extra and extra["traceback"]:
            context_parts.append(f"traceback={extra['traceback']}")

        if context_parts:
            base_message = f"{base_message} | {' | '.join(context_parts)}"

        return base_message


def get_logger(
    name: str,
    log_level: str | None = None,
    log_dir: str | None = None
) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Return existing logger if already configured
    if logger.handlers:
        return logger

    # Disable propagation to root logger to avoid duplicate logs
    logger.propagate = False

    # Get configuration from environment or defaults
    effective_log_level = log_level if log_level is not None else os.getenv("LOG_LEVEL", "INFO")
    effective_log_dir = log_dir if log_dir is not None else os.getenv("LOG_DIR", "logs")

    # Set logger level
    logger.setLevel(getattr(logging, effective_log_level.upper(), logging.INFO))

    # Console handler with colorlog
    console_format = (
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(threadName)-12s | "
        "%(name)s | %(emoji)s %(message)s%(reset)s"
    )
    console_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(EmojiFormatter(
        console_format,
        log_colors=console_colors,
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    console_handler.addFilter(SanitizingFilter())
    logger.addHandler(console_handler)

    # File handler with rotation
    log_path = Path(effective_log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    file_format = (
        "%(asctime)s | %(levelname)-8s | %(threadName)-12s | "
        "%(name)s | %(emoji)s %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_path / "polymarket_trader.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(FileEmojiFormatter(
        file_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    file_handler.addFilter(SanitizingFilter())
    logger.addHandler(file_handler)

    return logger


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """Setup root logger configuration.

    Args:
        log_level: Logging level
        log_dir: Directory for log files
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Get a configured logger for the application
    app_logger = get_logger("polymarket_trader", log_level, log_dir)
    root_logger.addHandler(app_logger.handlers[0])
    root_logger.addHandler(app_logger.handlers[1])

    # Add dedicated error log handler
    error_handler = setup_error_log_handler(log_dir)
    root_logger.addHandler(error_handler)


def setup_error_log_handler(log_dir: str = "logs") -> RotatingFileHandler:
    """Setup dedicated error log file handler.

    Creates a rotating file handler that only captures ERROR and CRITICAL
    level messages, separate from the main log file.

    Args:
        log_dir: Directory for log files

    Returns:
        Configured RotatingFileHandler for error logs
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    error_handler = RotatingFileHandler(
        log_path / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    # Use special formatter with extra context
    error_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(emoji)s %(message)s"
    error_handler.setFormatter(ErrorLogFormatter(error_format, datefmt="%Y-%m-%d %H:%M:%S"))
    error_handler.addFilter(SanitizingFilter())

    return error_handler
