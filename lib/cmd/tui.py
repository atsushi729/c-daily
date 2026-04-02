"""
cmd/tui.py — c-daily tui subcommand handler.

Usage:
  c-daily tui                  Browse all sessions
  c-daily tui session [DATE]   Browse sessions (optional date filter YYYY-MM-DD)
  c-daily tui project          Browse projects; Enter drills into sessions
  c-daily tui daily            Browse daily summaries
"""

import sys
from pathlib import Path

_CMD_DIR = Path(__file__).resolve().parent.parent  # lib/cmd/ → lib/
if str(_CMD_DIR) not in sys.path:
    sys.path.insert(0, str(_CMD_DIR))

from constants import validate_date  # noqa: E402


def run(lib_dir: Path, log_dir: Path) -> None:
    args = sys.argv[2:]
    subcmd = args[0] if args else "session"

    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))

    if subcmd == "project":
        from tui import run_tui_project

        run_tui_project(log_dir=log_dir)

    elif subcmd == "daily":
        from tui import run_tui_daily

        run_tui_daily(log_dir=log_dir)

    else:
        # "session" subcommand, or legacy bare date argument (e.g. c-daily tui 2026-04-01)
        if subcmd == "session":
            date_filter = args[1] if len(args) > 1 else None
        else:
            date_filter = subcmd  # backward compat
        if date_filter is not None:
            validate_date(date_filter)

        from tui import run_tui

        run_tui(log_dir=log_dir, date_filter=date_filter)
