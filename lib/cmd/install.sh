#!/bin/bash
# lib/cmd/install.sh — c-daily install subcommand
set -euo pipefail

C_DAILY_LIB="$(cd "$(dirname "$0")/.." && pwd)"
C_DAILY_LOG_DIR="${C_DAILY_LOG_DIR:-${HOME}/.daily-logs}"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

echo "🔧 Starting c-daily setup..."
echo ""

# --- Dependency check ---
_check_dep() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌ $1 not found. Please install it."
    exit 1
  fi
}
_check_dep python3
_check_dep git

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED="3.9"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)"; then
  echo "✅ Python ${PYTHON_VERSION}"
else
  echo "❌ Python 3.9 or higher required (current: ${PYTHON_VERSION})"
  exit 1
fi

# --- Create directories ---
mkdir -p "${C_DAILY_LOG_DIR}/raw"
echo "✅ Log directory: ${C_DAILY_LOG_DIR}"

# --- Copy hook scripts ---
mkdir -p "${C_DAILY_LOG_DIR}/scripts/hooks"
cp "$C_DAILY_LIB/hooks/post-tool.sh"       "${C_DAILY_LOG_DIR}/scripts/hooks/"
cp "$C_DAILY_LIB/hooks/session-summary.sh" "${C_DAILY_LOG_DIR}/scripts/hooks/"
chmod +x "${C_DAILY_LOG_DIR}/scripts/hooks/post-tool.sh"
chmod +x "${C_DAILY_LOG_DIR}/scripts/hooks/session-summary.sh"
cp "$C_DAILY_LIB/aggregate.py" "${C_DAILY_LOG_DIR}/scripts/"
echo "✅ Hook scripts copied"

# --- Add hooks to Claude Code settings.json ---
mkdir -p "${HOME}/.claude"

HOOK_SNIPPET=$(cat <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.daily-logs/scripts/hooks/post-tool.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.daily-logs/scripts/hooks/session-summary.sh"
          }
        ]
      }
    ]
  }
}
JSON
)

if [ ! -f "$CLAUDE_SETTINGS" ]; then
  echo "$HOOK_SNIPPET" > "$CLAUDE_SETTINGS"
  echo "✅ Claude Code settings.json created"
else
  # Check if existing file already has a hooks key
  if python3 -c "import json,sys; d=json.load(open('$CLAUDE_SETTINGS')); sys.exit(0 if 'hooks' in d else 1)" 2>/dev/null; then
    echo "⚠️  ~/.claude/settings.json already has a 'hooks' key."
    echo "   Please merge manually:"
    echo ""
    echo "$HOOK_SNIPPET"
    echo ""
  else
    python3 - <<PYEOF
import json
with open('$CLAUDE_SETTINGS', 'r') as f:
    existing = json.load(f)
hook_config = json.loads('''$HOOK_SNIPPET''')
existing.update(hook_config)
with open('$CLAUDE_SETTINGS', 'w') as f:
    json.dump(existing, f, indent=2, ensure_ascii=False)
print("✅ Hooks added to Claude Code settings.json")
PYEOF
  fi
fi

# --- Register launchd (macOS only) ---
if [[ "$(uname)" == "Darwin" ]]; then
  PLIST_DST="${HOME}/Library/LaunchAgents/com.c-daily.aggregate.plist"
  PYTHON_PATH=$(which python3)
  USERNAME=$(whoami)

  cat > "$PLIST_DST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.c-daily.aggregate</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>/Users/${USERNAME}/.daily-logs/scripts/aggregate.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>23</integer>
        <key>Minute</key><integer>58</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/${USERNAME}/.daily-logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/${USERNAME}/.daily-logs/launchd-error.log</string>
</dict>
</plist>
PLIST

  launchctl unload "$PLIST_DST" 2>/dev/null || true
  launchctl load "$PLIST_DST"
  echo "✅ launchd registered (auto-run daily at 23:58)"
fi

# --- Done ---
echo ""
echo "🎉 Setup complete!"
echo ""
echo "  c-daily today    → generate today's log now"
echo "  c-daily status   → check status"
