#!/usr/bin/env python3
# lib/cmd/install.py — c-daily install subcommand
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

from constants import (  # noqa: E402
    CLAUDE_SETTINGS_FILE,
    LAUNCHD_HOUR,
    LAUNCHD_LABEL,
    LAUNCHD_MINUTE,
    LAUNCHD_PLIST_PATH,
    MIN_PYTHON_VERSION,
)


def run(lib_dir: Path, log_dir: Path) -> None:
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
    if version_info < MIN_PYTHON_VERSION:
        print(
            f"❌ Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} or higher required"
            f" (current: {version_info.major}.{version_info.minor})"
        )
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
    hook_dst.chmod(0o700)
    shutil.copy2(lib_dir / "text_utils.py", hooks_dir / "text_utils.py")
    shutil.copy2(lib_dir / "aggregate.py", log_dir / "scripts" / "aggregate.py")
    print("✅ Hook scripts copied")

    # --- Add hooks to Claude Code settings.json ---
    CLAUDE_SETTINGS_FILE.parent.mkdir(exist_ok=True)

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

    if not CLAUDE_SETTINGS_FILE.exists():
        with open(CLAUDE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(hook_snippet, f, indent=2, ensure_ascii=False)
        print("✅ Claude Code settings.json created")
    else:
        with open(CLAUDE_SETTINGS_FILE, encoding="utf-8") as f:
            existing = json.load(f)
        if "hooks" in existing:
            print("⚠️  ~/.claude/settings.json already has a 'hooks' key.")
            print("   Please merge manually:")
            print()
            print(json.dumps(hook_snippet, indent=2, ensure_ascii=False))
            print()
        else:
            existing.update(hook_snippet)
            with open(CLAUDE_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            print("✅ Hooks added to Claude Code settings.json")

    # --- Register launchd (macOS only) ---
    if platform.system() == "Darwin":
        python_path = shutil.which("python3") or sys.executable
        home_dir = Path.home()

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{home_dir}/.daily-logs/scripts/aggregate.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>{LAUNCHD_HOUR}</integer>
        <key>Minute</key><integer>{LAUNCHD_MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{home_dir}/.daily-logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>{home_dir}/.daily-logs/launchd-error.log</string>
</dict>
</plist>
"""
        LAUNCHD_PLIST_PATH.write_text(plist_content, encoding="utf-8")
        subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST_PATH)], capture_output=True)
        subprocess.run(["launchctl", "load", str(LAUNCHD_PLIST_PATH)], check=True)
        print(f"✅ launchd registered (auto-run daily at {LAUNCHD_HOUR:02d}:{LAUNCHD_MINUTE:02d})")

    this_bin = Path(sys.argv[0]).resolve()
    dl_link = this_bin.parent / "dl"
    try:
        dl_link.unlink(missing_ok=True)
        dl_link.symlink_to(this_bin)
        print(f"✅ Short alias `dl` linked at {dl_link}")
    except OSError as e:
        print(f"⚠️  Could not create `dl` alias: {e}")

    # --- Done ---
    print()
    print("Setup complete!")
    print()
    print("  dl today    → generate today's log now")
    print("  dl status   → check status")
    print("  (c-daily also works)")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    lib_dir = script_dir.parent
    log_dir = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
    run(lib_dir, log_dir)
