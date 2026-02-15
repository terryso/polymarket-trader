"""Logging configuration for the Polymarket Trader application.

This module provides a colored logging setup with both console and file output,
following the architecture specification.
"""

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import colorlog


# Sensitive patterns for log sanitization
SENSITIVE_PATTERNS = [
    # API Keys - show only first 4 characters
    (r'(api[_-]?key["\s:=]+)["\']?([a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]*["\']?', r'\1"\2****"'),
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


def get_logger(
    name: str,
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None
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

    # Get configuration from environment or defaults
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_dir = log_dir or os.getenv("LOG_DIR", "logs")

    # Set logger level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler with colorlog
    console_format = (
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(threadName)-12s | "
        "%(name)s | %(message)s%(reset)s"
    )
    console_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter(
        console_format,
        log_colors=console_colors,
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    console_handler.addFilter(SanitizingFilter())
    logger.addHandler(console_handler)

    # File handler with rotation
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    file_format = (
        "%(asctime)s | %(levelname)-8s | %(threadName)-12s | "
        "%(name)s | %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_path / "polymarket_trader.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
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
