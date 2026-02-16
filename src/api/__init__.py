"""External API clients: Polymarket, LLM.

This module provides API client wrappers for external services.

Usage:
    from src.api import PolymarketClient, GammaMarket, LLMClient

    # Polymarket client
    client = PolymarketClient()

    # Get all markets (CLOB API)
    markets = client.get_markets()

    # Get active markets (Gamma API with filtering)
    active = client.get_active_markets(limit=10, min_volume_24h=100000)

    # LLM client
    with LLMClient() as llm:
        response = llm.chat([{"role": "user", "content": "Hello!"}])
"""

from __future__ import annotations

from src.api.llm import LLMClient
from src.api.polymarket import GammaMarket, PolymarketClient

__all__ = ["PolymarketClient", "GammaMarket", "LLMClient"]
