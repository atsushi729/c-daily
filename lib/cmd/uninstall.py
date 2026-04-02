#!/usr/bin/env python3
# lib/cmd/uninstall.py — c-daily uninstall subcommand
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parent.parent  # lib/cmd/ → lib/
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from constants import CLAUDE_SETTINGS_FILE, LAUNCHD_PLIST_PATH  # noqa: E402


def run(log_dir: Path) -> None:
    print("Uninstalling c-daily...")

    # Unregister launchd (macOS only)
    if platform.system() == "Darwin" and LAUNCHD_PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST_PATH)], capture_output=True)
        LAUNCHD_PLIST_PATH.unlink()
        print("✅ launchd unregistered")

    # Remove hook scripts
    scripts_dir = log_dir / "scripts"
    if scripts_dir.exists():
        shutil.rmtree(scripts_dir)
    print("✅ Hook scripts removed")

    # Remove hook config from Claude Code settings.json
    if CLAUDE_SETTINGS_FILE.exists():
        with open(CLAUDE_SETTINGS_FILE, encoding="utf-8") as f:
            d = json.load(f)
        d.pop("hooks", None)
        with open(CLAUDE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        print("✅ Hooks removed from Claude Code settings.json")

    print()
    print("✅ Uninstall complete")
    print("   Log data (~/.daily-logs/raw/, *.md) has been preserved.")
    print("   To remove everything: rm -rf ~/.daily-logs")


if __name__ == "__main__":
    log_dir = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
    run(log_dir)
