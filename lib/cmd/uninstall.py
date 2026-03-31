#!/usr/bin/env python3
# lib/cmd/uninstall.py — c-daily uninstall subcommand
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def run(log_dir: Path) -> None:
    print("Uninstalling c-daily...")

    # Unregister launchd (macOS only)
    if platform.system() == "Darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / "com.c-daily.aggregate.plist"
        if plist.exists():
            subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
            plist.unlink()
            print("✅ launchd unregistered")

    # Remove hook scripts
    scripts_dir = log_dir / "scripts"
    if scripts_dir.exists():
        shutil.rmtree(scripts_dir)
    print("✅ Hook scripts removed")

    # Remove hook config from Claude Code settings.json
    settings = Path.home() / ".claude" / "settings.json"
    if settings.exists():
        with open(settings, encoding="utf-8") as f:
            d = json.load(f)
        d.pop("hooks", None)
        with open(settings, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        print("✅ Hooks removed from Claude Code settings.json")

    print()
    print("✅ Uninstall complete")
    print("   Log data (~/.daily-logs/raw/, *.md) has been preserved.")
    print("   To remove everything: rm -rf ~/.daily-logs")


if __name__ == "__main__":
    log_dir = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
    run(log_dir)
