#!/bin/bash
# lib/cmd/status.sh
set -euo pipefail

C_DAILY_LOG_DIR="${C_DAILY_LOG_DIR:-${HOME}/.daily-logs}"
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"
TODAY=$(date +%Y-%m-%d)
RAW="${C_DAILY_LOG_DIR}/raw/${TODAY}.jsonl"

echo "📊 c-daily status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Claude Code hook
if [ -f "$CLAUDE_SETTINGS" ] && grep -q "post-tool.sh" "$CLAUDE_SETTINGS" 2>/dev/null; then
  echo "✅ Claude Code hook  : configured"
else
  echo "❌ Claude Code hook  : not configured (run c-daily install)"
fi

# Check launchd (macOS)
if [[ "$(uname)" == "Darwin" ]]; then
  if launchctl list 2>/dev/null | grep -q "com.c-daily.aggregate"; then
    echo "✅ launchd           : registered (daily at 23:58)"
  else
    echo "❌ launchd           : not registered (run c-daily install)"
  fi
fi

# Check today's log
if [ -f "$RAW" ]; then
  COUNT=$(wc -l < "$RAW" | tr -d ' ')
  echo "✅ Today's raw log   : ${COUNT} records ($RAW)"
else
  echo "⚠️  Today's raw log   : none yet (will be recorded when you use Claude Code)"
fi

# Log directory
echo "📁 Log directory     : ${C_DAILY_LOG_DIR}"
MD_COUNT=$(ls "${C_DAILY_LOG_DIR}"/*.md 2>/dev/null | wc -l | tr -d ' ')
echo "📄 Generated Markdown: ${MD_COUNT} files"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
