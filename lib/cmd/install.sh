#!/bin/bash
# lib/cmd/install.sh — c-daily install サブコマンド
set -euo pipefail

C_DAILY_LIB="$(cd "$(dirname "$0")/.." && pwd)"
C_DAILY_LOG_DIR="${C_DAILY_LOG_DIR:-${HOME}/.daily-logs}"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

echo "🔧 c-daily セットアップを開始します..."
echo ""

# --- 依存チェック ---
_check_dep() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌ $1 が見つかりません。インストールしてください。"
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
  echo "❌ Python 3.9 以上が必要です (現在: ${PYTHON_VERSION})"
  exit 1
fi

# --- ディレクトリ作成 ---
mkdir -p "${C_DAILY_LOG_DIR}/raw"
echo "✅ ログディレクトリ: ${C_DAILY_LOG_DIR}"

# --- hookスクリプトをコピー ---
mkdir -p "${C_DAILY_LOG_DIR}/scripts/hooks"
cp "$C_DAILY_LIB/hooks/post-tool.sh"       "${C_DAILY_LOG_DIR}/scripts/hooks/"
cp "$C_DAILY_LIB/hooks/session-summary.sh" "${C_DAILY_LOG_DIR}/scripts/hooks/"
chmod +x "${C_DAILY_LOG_DIR}/scripts/hooks/post-tool.sh"
chmod +x "${C_DAILY_LOG_DIR}/scripts/hooks/session-summary.sh"
cp "$C_DAILY_LIB/aggregate.py" "${C_DAILY_LOG_DIR}/scripts/"
echo "✅ hookスクリプトをコピー"

# --- Claude Code settings.json にhookを追記 ---
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
  echo "✅ Claude Code settings.json を作成"
else
  # 既存ファイルにhooksキーがあるかチェック
  if python3 -c "import json,sys; d=json.load(open('$CLAUDE_SETTINGS')); sys.exit(0 if 'hooks' in d else 1)" 2>/dev/null; then
    echo "⚠️  ~/.claude/settings.json に既に 'hooks' キーがあります。"
    echo "   手動でマージしてください:"
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
print("✅ Claude Code settings.json にhookを追記")
PYEOF
  fi
fi

# --- launchd 登録（macOSのみ） ---
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
  echo "✅ launchd 登録完了 (毎日 23:58 に自動実行)"
fi

# --- 完了メッセージ ---
echo ""
echo "🎉 セットアップ完了！"
echo ""
echo "  c-daily today    → 今日のログを今すぐ生成"
echo "  c-daily status   → 動作確認"
