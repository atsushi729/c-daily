#!/bin/bash
# lib/cmd/uninstall.sh
set -euo pipefail

echo "🗑️  c-daily をアンインストールします..."

# launchd解除
if [[ "$(uname)" == "Darwin" ]]; then
  PLIST="${HOME}/Library/LaunchAgents/com.c-daily.aggregate.plist"
  if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✅ launchd 解除"
  fi
fi

# hookスクリプト削除
rm -rf "${HOME}/.daily-logs/scripts"
echo "✅ hookスクリプト削除"

# Claude Code settings.jsonからhook設定を除去
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
print("✅ Claude Code settings.json からhookを削除")
PYEOF
fi

echo ""
echo "✅ アンインストール完了"
echo "   ログデータ (~/.daily-logs/raw/, *.md) は保持しています。"
echo "   完全に削除する場合: rm -rf ~/.daily-logs"
