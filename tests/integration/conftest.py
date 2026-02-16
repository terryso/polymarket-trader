"""Pytest configuration for integration tests.

This module loads environment variables from .env file for integration tests.
Unit tests should remain isolated from environment variables.
"""

from dotenv import load_dotenv

# Load .env file for integration tests (makes real API calls)
load_dotenv()
