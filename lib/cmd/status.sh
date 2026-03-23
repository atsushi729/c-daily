#!/bin/bash
# lib/cmd/status.sh
set -euo pipefail

C_DAILY_LOG_DIR="${C_DAILY_LOG_DIR:-${HOME}/.daily-logs}"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"
TODAY=$(date +%Y-%m-%d)
RAW="${C_DAILY_LOG_DIR}/raw/${TODAY}.jsonl"

echo "📊 c-daily ステータス"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Claude Code hook確認
if [ -f "$CLAUDE_SETTINGS" ] && grep -q "post-tool.sh" "$CLAUDE_SETTINGS" 2>/dev/null; then
  echo "✅ Claude Code hook  : 設定済み"
else
  echo "❌ Claude Code hook  : 未設定 (c-daily install を実行してください)"
fi

# launchd確認（macOS）
if [[ "$(uname)" == "Darwin" ]]; then
  if launchctl list 2>/dev/null | grep -q "com.c-daily.aggregate"; then
    echo "✅ launchd           : 登録済み (毎日 23:58)"
  else
    echo "❌ launchd           : 未登録 (c-daily install を実行してください)"
  fi
fi

# 今日のログ確認
if [ -f "$RAW" ]; then
  COUNT=$(wc -l < "$RAW" | tr -d ' ')
  echo "✅ 今日のrawログ     : ${COUNT} 件 ($RAW)"
else
  echo "⚠️  今日のrawログ     : まだありません (Claude Codeを使うと記録されます)"
fi

# ログディレクトリ
echo "📁 ログディレクトリ  : ${C_DAILY_LOG_DIR}"
MD_COUNT=$(ls "${C_DAILY_LOG_DIR}"/*.md 2>/dev/null | wc -l | tr -d ' ')
echo "📄 生成済みMarkdown  : ${MD_COUNT} 件"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
