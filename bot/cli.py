"""CLI entry point for the Discord Support Bot.

This module provides the entry point for console script entry points as
defined in pyproject.toml. It re-exports the main() function from bot.main.
"""

import sys

from bot.main import main


if __name__ == "__main__":
    sys.exit(main())
