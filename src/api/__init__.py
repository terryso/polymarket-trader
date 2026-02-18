"""External API clients: Polymarket, LLM, Telegram.

This module provides API client wrappers for external services.

Usage:
    from src.api import PolymarketClient, GammaMarket, LLMClient, TelegramClient

    # Polymarket client
    client = PolymarketClient()

    # Get all markets (CLOB API)
    markets = client.get_markets()

    # Get active markets (Gamma API with filtering)
    active = client.get_active_markets(limit=10, min_volume_24h=100000)

    # LLM client
    with LLMClient() as llm:
        response = llm.chat([{"role": "user", "content": "Hello!"}])

    # Telegram client (async)
    async with TelegramClient() as tg:
        me = await tg.get_me()
"""

from __future__ import annotations

from src.api.llm import LLMClient
from src.api.polymarket import GammaMarket, PolymarketClient
from src.api.telegram import TelegramClient

__all__ = ["PolymarketClient", "GammaMarket", "LLMClient", "TelegramClient"]
