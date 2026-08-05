"""CUPS Bot — entry point.

Architecture:
    Titan (framework)  ←  CUPS Bot  →  CUPS Platform (service)

Titan Core does not know about CUPS.
CUPS Platform does not know about Titan.
CUPS Bot is the application that connects them.

Required environment variable:
    BOT_TOKEN — Telegram bot token (set via Replit Secrets)
"""

from __future__ import annotations

import os
import sys

from titan import Titan

from cups.service import CUPSService
from cups.domain.project import ProductType

# Import handler modules
from handlers.start import register as register_start
from handlers.addbot import register as register_addbot
from handlers.plan import register as register_plan


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print(
            "[CUPS Bot] ERROR: BOT_TOKEN environment variable is not set.\n"
            "Set it via Replit Secrets before running the bot.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Shared CUPS service — bot and API use the same cups.db
    service = CUPSService()

    bot = Titan(token)

    # Register all routers
    bot.include(register_start(service))
    bot.include(register_addbot(service))
    bot.include(register_plan(service))

    print("[CUPS Bot] Starting... Press Ctrl+C to stop.")
    bot.run()


if __name__ == "__main__":
    # Run from project root: python apps/cups-bot/main.py
    # PYTHONPATH must include src/ so `import cups` resolves correctly.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    main()
