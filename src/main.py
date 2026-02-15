"""Main entry point for the Polymarket Trader application.

This module provides the main entry point for starting the trading system.
"""

import asyncio
import signal
import sys
from typing import Optional

from src.config import settings
from src.exceptions import BotError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Application:
    """Main application class for Polymarket Trader."""

    def __init__(self) -> None:
        """Initialize the application."""
        self._shutdown_event: Optional[asyncio.Event] = None
        self._running = False

    async def startup(self) -> None:
        """Perform application startup tasks."""
        logger.info("🚀 Starting Polymarket Trader...")
        logger.info(f"📋 Mode: {settings.trading_mode}")
        logger.info(f"💰 Initial Capital: ${settings.initial_capital}")
        # TODO: Initialize database, scheduler, and other components
        self._running = True
        logger.info("✅ Application started successfully")

    async def shutdown(self) -> None:
        """Perform graceful shutdown."""
        logger.info("🛑 Shutting down Polymarket Trader...")
        self._running = False
        # TODO: Close database connections, stop scheduler, etc.
        logger.info("👋 Application stopped")

    async def run(self) -> None:
        """Run the main application loop."""
        await self.startup()

        self._shutdown_event = asyncio.Event()

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self._handle_signal())
            )

        # Wait for shutdown signal
        await self._shutdown_event.wait()
        await self.shutdown()

    async def _handle_signal(self) -> None:
        """Handle shutdown signals."""
        logger.info("📡 Received shutdown signal")
        if self._shutdown_event:
            self._shutdown_event.set()


async def main() -> None:
    """Main entry point."""
    try:
        app = Application()
        await app.run()
    except BotError as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"🔥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
