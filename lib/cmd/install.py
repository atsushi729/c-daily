#!/usr/bin/env python3
# lib/cmd/install.py — c-daily install subcommand
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run(lib_dir: Path, log_dir: Path) -> None:
    claude_settings = Path.home() / ".claude" / "settings.json"

    print("Starting c-daily setup...")
    print()

    # --- Dependency check ---
    if not shutil.which("python3"):
        print("❌ python3 not found. Please install it.")
        sys.exit(1)
    if not shutil.which("git"):
        print("❌ git not found. Please install it.")
        sys.exit(1)

    version_info = sys.version_info
    if version_info < (3, 9):
        print(f"❌ Python 3.9 or higher required (current: {version_info.major}.{version_info.minor})")
        sys.exit(1)
    print(f"✅ Python {version_info.major}.{version_info.minor}")

    # --- Create directories ---
    (log_dir / "raw").mkdir(parents=True, exist_ok=True)
    print(f"✅ Log directory: {log_dir}")

    # --- Copy hook scripts ---
    hooks_dir = log_dir / "scripts" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_src = lib_dir / "hooks" / "session_summary.py"
    hook_dst = hooks_dir / "session_summary.py"
    shutil.copy2(hook_src, hook_dst)
    hook_dst.chmod(0o755)
    shutil.copy2(lib_dir / "aggregate.py", log_dir / "scripts" / "aggregate.py")
    print("✅ Hook scripts copied")

    # --- Add hooks to Claude Code settings.json ---
    Path.home().joinpath(".claude").mkdir(exist_ok=True)

    hook_snippet = {
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python3 {hook_dst}",
                        }
                    ]
                }
            ]
        }
    }

    if not claude_settings.exists():
        with open(claude_settings, "w", encoding="utf-8") as f:
            json.dump(hook_snippet, f, indent=2, ensure_ascii=False)
        print("✅ Claude Code settings.json created")
    else:
        with open(claude_settings, encoding="utf-8") as f:
            existing = json.load(f)
        if "hooks" in existing:
            print("⚠️  ~/.claude/settings.json already has a 'hooks' key.")
            print("   Please merge manually:")
            print()
            print(json.dumps(hook_snippet, indent=2, ensure_ascii=False))
            print()
        else:
            existing.update(hook_snippet)
            with open(claude_settings, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            print("✅ Hooks added to Claude Code settings.json")

    # --- Register launchd (macOS only) ---
    if platform.system() == "Darwin":
        plist_dst = Path.home() / "Library" / "LaunchAgents" / "com.c-daily.aggregate.plist"
        python_path = shutil.which("python3") or sys.executable
        username = os.environ.get("USER", Path.home().name)

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.c-daily.aggregate</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>/Users/{username}/.daily-logs/scripts/aggregate.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>23</integer>
        <key>Minute</key><integer>58</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/{username}/.daily-logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/{username}/.daily-logs/launchd-error.log</string>
</dict>
</plist>
"""
        plist_dst.write_text(plist_content, encoding="utf-8")
        subprocess.run(["launchctl", "unload", str(plist_dst)], capture_output=True)
        subprocess.run(["launchctl", "load", str(plist_dst)], check=True)
        print("✅ launchd registered (auto-run daily at 23:58)")

    # --- Done ---
    print()
    print("Setup complete!")
    print()
    print("  c-daily today    → generate today's log now")
    print("  c-daily status   → check status")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    lib_dir = script_dir.parent
    log_dir = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
    run(lib_dir, log_dir)
