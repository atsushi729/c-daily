#!/bin/bash
# PostToolUse hook — appends a JSONL record to today's raw log
set -euo pipefail

LOG_DIR="${C_DAILY_LOG_DIR:-${HOME}/.daily-logs}"
mkdir -p "${LOG_DIR}/raw"

PAYLOAD_FILE=$(mktemp)
trap "rm -f '$PAYLOAD_FILE'" EXIT
cat > "$PAYLOAD_FILE"

python3 - "$PAYLOAD_FILE" "$LOG_DIR" <<'PYEOF'
import json, sys, os, subprocess
from datetime import datetime

with open(sys.argv[1]) as f:
    payload = json.load(f)

log_dir = sys.argv[2]
tool    = payload.get("tool_name", "")
inp     = payload.get("tool_input", {})
cwd     = payload.get("cwd", ".")
ts      = datetime.now().isoformat()
today   = datetime.now().strftime("%Y-%m-%d")
outfile = os.path.join(log_dir, "raw", f"{today}.jsonl")

def append(record):
    with open(outfile, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
    path = inp.get("file_path") or inp.get("notebook_path", "")
    append({"type": "file_edit", "timestamp": ts, "path": path,
            "summary": f"Edited {path}"})

elif tool == "Bash":
    cmd = inp.get("command", "")
    append({"type": "command", "timestamp": ts, "command": cmd[:120],
            "summary": f"$ {cmd[:80]}"})
    # also capture git commits
    if "git commit" in cmd:
        try:
            result = subprocess.run(
                ["git", "-C", cwd, "log", "-1", "--pretty=format:%H\t%s"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.split("\t", 1)
                append({
                    "type":    "git",
                    "timestamp": ts,
                    "repo":    os.path.basename(os.path.abspath(cwd)),
                    "hash":    parts[0] if parts else "",
                    "message": parts[1] if len(parts) > 1 else "",
                    "summary": f"git commit: {parts[1][:60] if len(parts) > 1 else ''}",
                })
        except Exception:
            pass
PYEOF
