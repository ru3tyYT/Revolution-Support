"""Module entry point for running the Discord Support Bot with `python -m bot`.

This file allows the bot to be executed as a module:
    python -m bot

The bot will load configuration from environment variables and start
connecting to Discord.
"""

import sys

from bot.main import main


if __name__ == "__main__":
    sys.exit(main())
