"""
cdl/cmd/tui.py — cdl tui subcommand handler.

Usage:
  cdl tui                  Browse all sessions
  cdl tui session [DATE]   Browse sessions (optional date filter YYYY-MM-DD)
  cdl tui project          Browse projects; Enter drills into sessions
  cdl tui daily            Browse daily summaries
"""

import sys
from pathlib import Path

from cdl.constants import validate_date


def run(lib_dir: Path, log_dir: Path) -> None:
    args = sys.argv[2:]
    subcmd = args[0] if args else "session"

    if subcmd == "project":
        from cdl.tui import run_tui_project

        run_tui_project(log_dir=log_dir)

    elif subcmd == "daily":
        from cdl.tui import run_tui_daily

        run_tui_daily(log_dir=log_dir)

    else:
        # "session" subcommand, or legacy bare date argument (e.g. cdl tui 2026-04-01)
        date_filter = (
            (args[1] if len(args) > 1 else None) if subcmd == "session" else subcmd
        )  # backward compat
        if date_filter is not None:
            validate_date(date_filter)

        from cdl.tui import run_tui

        run_tui(log_dir=log_dir, date_filter=date_filter)
