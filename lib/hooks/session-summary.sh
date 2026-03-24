#!/bin/bash
# Stop hook — appends a session summary record to today's raw log
set -euo pipefail

LOG_DIR="${C_DAILY_LOG_DIR:-${HOME}/.daily-logs}"
mkdir -p "${LOG_DIR}/raw"

PAYLOAD_FILE=$(mktemp)
trap 'rm -f "$PAYLOAD_FILE"' EXIT
cat > "$PAYLOAD_FILE"

python3 - "$PAYLOAD_FILE" "$LOG_DIR" <<'PYEOF'
import json, sys, os
from datetime import datetime

with open(sys.argv[1]) as f:
    payload = json.load(f)

log_dir        = sys.argv[2]
ts             = datetime.now().isoformat()
today          = datetime.now().strftime("%Y-%m-%d")
outfile        = os.path.join(log_dir, "raw", f"{today}.jsonl")
transcript_path = payload.get("transcript_path", "")

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
                role = entry.get("role") or entry.get("type", "")
                if role == "user" and not first_msg:
                    content = entry.get("content", "")
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                first_msg = block["text"][:100]
                                break
                    elif isinstance(content, str):
                        first_msg = content[:100]
                if role in ("assistant", "user"):
                    turns += 1
                cost_usd = entry.get("costUSD") or entry.get("cost_usd") or cost_usd
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

# Extract decision summary from transcript using claude CLI
if transcript_path and os.path.exists(transcript_path):
    try:
        # Build plain text from transcript for summarization
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
                role = entry.get("role") or entry.get("type", "")
                if role not in ("user", "assistant"):
                    continue
                content = entry.get("content", "")
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
            transcript_text = "\n".join(messages[:40])  # limit to first 40 turns
            prompt = (
                "You are summarizing a Claude Code session transcript.\n"
                "Extract the following 3 fields in JSON (respond with JSON only):\n"
                "- problem: the main issue or task addressed (1-2 sentences)\n"
                "- approaches: list of approaches or options considered (array, one sentence each)\n"
                "- selected: the approach that was ultimately chosen (1 sentence)\n"
                'Example: {"problem":"...", "approaches":["...","..."], "selected":"..."}\n\n'
                f"Transcript:\n{transcript_text}"
            )
            import subprocess
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                raw = result.stdout.strip()
                # Extract JSON from response
                import re
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                if m:
                    try:
                        decision = json.loads(m.group())
                        record["decision_summary"] = decision
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

with open(outfile, "a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
PYEOF
