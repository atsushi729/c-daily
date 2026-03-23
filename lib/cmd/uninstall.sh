#!/bin/bash
# lib/cmd/uninstall.sh
set -euo pipefail

echo "🗑️  Uninstalling c-daily..."

# Unregister launchd
if [[ "$(uname)" == "Darwin" ]]; then
  PLIST="${HOME}/Library/LaunchAgents/com.c-daily.aggregate.plist"
  if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✅ launchd unregistered"
  fi
fi

# Remove hook scripts
rm -rf "${HOME}/.daily-logs/scripts"
echo "✅ Hook scripts removed"

# Remove hook config from Claude Code settings.json
SETTINGS="${HOME}/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  python3 - <<'PYEOF'
import json, os
path = os.path.expanduser("~/.claude/settings.json")
with open(path) as f:
    d = json.load(f)
d.pop("hooks", None)
with open(path, "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print("✅ Hooks removed from Claude Code settings.json")
PYEOF
fi

echo ""
echo "✅ Uninstall complete"
echo "   Log data (~/.daily-logs/raw/, *.md) has been preserved."
echo "   To remove everything: rm -rf ~/.daily-logs"
