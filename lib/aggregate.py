#!/usr/bin/env python3
"""
c-daily aggregate.py
JSONL raw log → daily Markdown generator
"""
import json
import sys
import os
from datetime import datetime, date
from collections import defaultdict
from pathlib import Path

LOG_BASE = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
RAW_DIR  = LOG_BASE / "raw"


def load_jsonl(filepath: Path) -> list[dict]:
    records = []
    if not filepath.exists():
        return records
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def fmt_time(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%H:%M")
    except Exception:
        return ts


def build_md(target_date: str, records: list[dict]) -> str:
    lines = [f"# 📋 Daily Log — {target_date}", ""]

    if not records:
        lines.append("> No logs for this day.")
        return "\n".join(lines)

    by_type: dict[str, list] = defaultdict(list)
    for r in records:
        by_type[r.get("type", "other")].append(r)

    # --- Summary ---
    lines += [
        "## 📊 Summary", "",
        "| Type | Count |",
        "|------|-------|",
        f"| ✏️ File Edits      | {len(by_type['file_edit'])} |",
        f"| ⚡ Commands Run    | {len(by_type['command'])} |",
        f"| 💬 Chat Sessions   | {len(by_type['session_summary'])} |",
        f"| 🌿 Git Commits     | {len(by_type['git'])} |",
        f"| **Total**          | **{len(records)}** |",
        "",
    ]

    # --- Timeline ---
    lines += ["## ⏱️ Timeline", ""]
    prev_hour = None
    for r in sorted(records, key=lambda r: r.get("timestamp", "")):
        t    = fmt_time(r.get("timestamp", ""))
        hour = t[:2] if len(t) >= 2 else "??"
        if hour != prev_hour:
            lines.append(f"### {hour}:xx")
            prev_hour = hour
        lines.append(f"- `{t}` {r.get('summary', '')}")
    lines.append("")

    # --- Edited files ---
    if by_type["file_edit"]:
        lines += ["## ✏️ Edited Files", ""]
        path_times: dict[str, list] = defaultdict(list)
        for r in by_type["file_edit"]:
            path_times[r.get("path", "")].append(fmt_time(r.get("timestamp", "")))
        for path, times in sorted(path_times.items()):
            lines.append(f"- `{path}` _{', '.join(times)}_")
        lines.append("")

    # --- Command history ---
    if by_type["command"]:
        lines += ["## ⚡ Commands Run", ""]
        for r in by_type["command"]:
            lines.append(f"- `{fmt_time(r.get('timestamp',''))}` `{r.get('command','')}`")
        lines.append("")

    # --- Session summary ---
    if by_type["session_summary"]:
        lines += ["## 💬 Claude Code Sessions", ""]
        for r in by_type["session_summary"]:
            t     = fmt_time(r.get("timestamp", ""))
            msg   = r.get("first_msg", "")
            meta  = []
            if r.get("turns"):  meta.append(f"{r['turns']} turns")
            if r.get("cost_usd"): meta.append(f"${r['cost_usd']:.4f}")
            meta_str = f" _({', '.join(meta)})_" if meta else ""
            lines.append(f"- `{t}` {msg}{meta_str}")
        lines.append("")

    # --- Decision log ---
    sessions_with_decisions = [r for r in by_type["session_summary"] if r.get("decision_summary")]
    if sessions_with_decisions:
        lines += ["## 🎯 Decision Log", ""]
        for r in sessions_with_decisions:
            t  = fmt_time(r.get("timestamp", ""))
            ds = r["decision_summary"]
            lines.append(f"### `{t}` Session")
            if ds.get("problem"):
                lines.append(f"**Problem:** {ds['problem']}")
                lines.append("")
            if ds.get("approaches"):
                lines.append("**Approaches considered:**")
                for ap in ds["approaches"]:
                    lines.append(f"- {ap}")
                lines.append("")
            if ds.get("selected"):
                lines.append(f"**Selected:** {ds['selected']}")
            lines.append("")

    # --- Project activity summary ---
    project_edits: dict[str, list] = defaultdict(list)
    for r in by_type["file_edit"]:
        path = r.get("path", "")
        # use top-level directory as the project name
        parts = path.strip("/").split("/")
        project = parts[1] if path.startswith("/") and len(parts) > 2 else (parts[0] if parts else "unknown")
        project_edits[project].append(path)
    if project_edits:
        lines += ["## 📁 Project Activity", ""]
        for project, paths in sorted(project_edits.items()):
            unique_files = sorted(set(paths))
            lines.append(f"**{project}** — {len(unique_files)} file(s) edited")
            for p in unique_files[:10]:
                lines.append(f"  - `{p}`")
            if len(unique_files) > 10:
                lines.append(f"  - _...and {len(unique_files) - 10} more_")
            lines.append("")

    # --- Git commits ---
    if by_type["git"]:
        lines += ["## 🌿 Git Commits", ""]
        for r in by_type["git"]:
            t    = fmt_time(r.get("timestamp", ""))
            repo = r.get("repo", "")
            msg  = r.get("message", "")
            h    = r.get("hash", "")[:7]
            lines.append(f"- `{t}` [{repo}] `{h}` {msg}")
        lines.append("")

    lines += ["---", f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_", ""]
    return "\n".join(lines)


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    records = load_jsonl(RAW_DIR / f"{target}.jsonl")
    out = LOG_BASE / f"{target}.md"
    LOG_BASE.mkdir(parents=True, exist_ok=True)
    out.write_text(build_md(target, records), encoding="utf-8")
    print(f"✅ {out} ({len(records)} records)")


if __name__ == "__main__":
    main()
