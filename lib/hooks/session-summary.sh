#!/bin/bash
# Stop hook — appends a session summary record to today's raw log
#
# Fix: Use Anthropic API directly (curl) instead of `claude -p`.
# Calling `claude -p` inside a Stop hook starts a new Claude Code session,
# which fires another Stop hook when it finishes → infinite recursion.
# A plain curl call to the API has no hook awareness, so it is safe.
set -euo pipefail

LOG_DIR="${C_DAILY_LOG_DIR:-${HOME}/.daily-logs}"
mkdir -p "${LOG_DIR}/raw"

PAYLOAD_FILE=$(mktemp)
trap 'rm -f "$PAYLOAD_FILE"' EXIT
cat > "$PAYLOAD_FILE"

python3 - "$PAYLOAD_FILE" "$LOG_DIR" <<'PYEOF'
import json, sys, os, re, subprocess
from datetime import datetime

with open(sys.argv[1]) as f:
    payload = json.load(f)

log_dir         = sys.argv[2]
ts              = datetime.now().isoformat()
today           = datetime.now().strftime("%Y-%m-%d")
outfile         = os.path.join(log_dir, "raw", f"{today}.jsonl")
transcript_path = payload.get("transcript_path", "")

# ── Step 1: extract basic metadata from transcript ────────────────────────────
first_msg = ""
turns     = 0
cost_usd  = None

if transcript_path and os.path.exists(transcript_path):
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role    = entry.get("type") or entry.get("role", "")
                msg_obj = entry.get("message", {})
                content = msg_obj.get("content", "") if msg_obj else entry.get("content", "")
                if role == "user" and not first_msg:
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                first_msg = block["text"][:100]
                                break
                    elif isinstance(content, str):
                        first_msg = content[:100]
                if role in ("assistant", "user"):
                    turns += 1
                cost_usd = (
                    entry.get("costUSD") or entry.get("cost_usd")
                    or (msg_obj or {}).get("costUSD") or cost_usd
                )
    except Exception:
        pass

record = {
    "type":      "session_summary",
    "timestamp": ts,
    "first_msg": first_msg or "(no message)",
    "turns":     turns // 2,
    "summary":   f"Session: {(first_msg or '(no message)')[:60]}",
}
if cost_usd is not None:
    record["cost_usd"] = float(cost_usd)

# ── Step 2: call Anthropic API directly via curl (NOT `claude -p`) ────────────
#
# `claude -p` would start a new Claude Code process, which fires another
# Stop hook on exit → infinite loop.  curl talks to the API endpoint
# directly and has no hook awareness, so it is safe.
#
# Requires: ANTHROPIC_API_KEY environment variable
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if api_key and transcript_path and os.path.exists(transcript_path):
    try:
        # Build a plain-text excerpt from the transcript (max 40 exchanges)
        messages = []
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role    = entry.get("type") or entry.get("role", "")
                if role not in ("user", "assistant"):
                    continue
                msg_obj = entry.get("message", {})
                content = msg_obj.get("content", "") if msg_obj else entry.get("content", "")
                text = ""
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text += block["text"]
                elif isinstance(content, str):
                    text = content
                if text.strip():
                    messages.append(f"[{role}]: {text[:500]}")

        if messages:
            transcript_text = "\n".join(messages[:40])
            prompt = (
                "You are summarizing a Claude Code session transcript.\n"
                "Extract the following fields in JSON (respond with JSON only, no markdown):\n"
                "- problem: the main issue or task addressed (1-2 sentences)\n"
                "- approaches: list of approaches or options considered (array, one sentence each)\n"
                "- selected: the approach that was ultimately chosen (1 sentence)\n"
                'Example: {"problem":"...","approaches":["...","..."],"selected":"..."}\n\n'
                f"Transcript:\n{transcript_text}"
            )

            # Build the JSON body for the API request
            api_body = json.dumps({
                "model": "claude-haiku-4-5-20251001",  # fast & cheap for summarization
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            })

            result = subprocess.run(
                [
                    "curl", "-fsSL",
                    "https://api.anthropic.com/v1/messages",
                    "-H", "Content-Type: application/json",
                    "-H", f"x-api-key: {api_key}",
                    "-H", "anthropic-version: 2023-06-01",
                    "-d", api_body,
                ],
                capture_output=True, text=True, timeout=30,
            )

            if result.returncode == 0:
                resp = json.loads(result.stdout)
                raw_text = ""
                for block in resp.get("content", []):
                    if block.get("type") == "text":
                        raw_text += block["text"]
                m = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if m:
                    try:
                        record["decision_summary"] = json.loads(m.group())
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass  # decision_summary is optional; never block the main write

# ── Step 3: write the record ──────────────────────────────────────────────────
with open(outfile, "a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
PYEOF