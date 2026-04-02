#!/usr/bin/env python3
# lib/cmd/status.py — c-daily status subcommand
import os
import platform
import subprocess
import sys
from datetime import date
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parent.parent  # lib/cmd/ → lib/
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from constants import (  # noqa: E402
    CLAUDE_SETTINGS_FILE,
    LAUNCHD_HOUR,
    LAUNCHD_LABEL,
    LAUNCHD_MINUTE,
)

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def run(log_dir: Path) -> None:
    today = date.today().isoformat()
    raw_file = log_dir / "raw" / f"{today}.jsonl"

    print("📊 c-daily status")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Check Claude Code hook — single stat() call avoids TOCTOU
    try:
        settings_text = (
            CLAUDE_SETTINGS_FILE.read_text()
            if CLAUDE_SETTINGS_FILE.stat().st_size <= _MAX_FILE_SIZE
            else ""
        )
        hook_configured = "session_summary.py" in settings_text
    except OSError:
        hook_configured = False

    if hook_configured:
        print("✅ Claude Code hook  : configured")
    else:
        print("❌ Claude Code hook  : not configured (run c-daily install)")

    # Check launchd (macOS)
    if platform.system() == "Darwin":
        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        if LAUNCHD_LABEL in result.stdout:
            time_str = f"{LAUNCHD_HOUR:02d}:{LAUNCHD_MINUTE:02d}"
            print(f"✅ launchd           : registered (daily at {time_str})")
        else:
            print("❌ launchd           : not registered (run c-daily install)")

    # Check today's log — single stat() call avoids TOCTOU
    try:
        raw_size = raw_file.stat().st_size
        if raw_size > _MAX_FILE_SIZE:
            print(f"✅ Today's raw log   : (file too large to count) ({raw_file})")
        else:
            count = sum(1 for line in raw_file.read_text().splitlines() if line.strip())
            print(f"✅ Today's raw log   : {count} records ({raw_file})")
    except OSError:
        print("⚠️  Today's raw log   : none yet (will be recorded when you use Claude Code)")

    # Log directory
    print(f"📁 Log directory     : {log_dir}")
    md_count = len(list(log_dir.glob("*.md")))
    print(f"📄 Generated Markdown: {md_count} files")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    log_dir = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
    run(log_dir)
