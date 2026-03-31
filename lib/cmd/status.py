#!/usr/bin/env python3
# lib/cmd/status.py — c-daily status subcommand
import os
import platform
import subprocess
from datetime import date
from pathlib import Path


def run(log_dir: Path) -> None:
    claude_settings = Path.home() / ".claude" / "settings.json"
    today = date.today().isoformat()
    raw_file = log_dir / "raw" / f"{today}.jsonl"

    print("📊 c-daily status")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Check Claude Code hook
    if claude_settings.exists() and "session_summary.py" in claude_settings.read_text():
        print("✅ Claude Code hook  : configured")
    else:
        print("❌ Claude Code hook  : not configured (run c-daily install)")

    # Check launchd (macOS)
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["launchctl", "list"], capture_output=True, text=True
        )
        if "com.c-daily.aggregate" in result.stdout:
            print("✅ launchd           : registered (daily at 23:58)")
        else:
            print("❌ launchd           : not registered (run c-daily install)")

    # Check today's log
    if raw_file.exists():
        count = sum(1 for line in raw_file.read_text().splitlines() if line.strip())
        print(f"✅ Today's raw log   : {count} records ({raw_file})")
    else:
        print("⚠️  Today's raw log   : none yet (will be recorded when you use Claude Code)")

    # Log directory
    print(f"📁 Log directory     : {log_dir}")
    md_count = len(list(log_dir.glob("*.md")))
    print(f"📄 Generated Markdown: {md_count} files")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    import os
    log_dir = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
    run(log_dir)
