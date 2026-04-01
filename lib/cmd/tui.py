"""
cmd/tui.py — c-daily tui subcommand handler.

Usage:
  c-daily tui            Browse all sessions
  c-daily tui [DATE]     Start with sessions filtered to DATE (YYYY-MM-DD)
"""
import sys
from pathlib import Path


def run(lib_dir: Path, log_dir: Path) -> None:
    # Optional date argument from sys.argv
    args = sys.argv[2:]
    date_filter = args[0] if args else None

    # Add lib_dir to path so tui.py can import session_reader
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))

    from tui import run_tui
    run_tui(log_dir=log_dir, date_filter=date_filter)
