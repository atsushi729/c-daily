#!/usr/bin/env python3
"""
c-daily aggregate.py
JSONL raw log → daily Markdown generator
"""
import sys
import os
from datetime import datetime, date
from pathlib import Path

# Add lib directory to path so session_reader is importable
_LIB_DIR = Path(__file__).resolve().parent
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from session_reader import load_jsonl, compute_project_stats  # noqa: E402

LOG_BASE = Path(os.environ.get("C_DAILY_LOG_DIR", Path.home() / ".daily-logs"))
RAW_DIR  = LOG_BASE / "raw"


def fmt_time(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%H:%M")
    except Exception:
        return ts


def fmt_tokens(n) -> str:
    if not n:
        return "—"
    return f"{int(n):,}"


def build_md(target_date: str, records: list[dict]) -> str:
    lines = [f"# Daily Log — {target_date}", ""]

    sessions = [r for r in records if r.get("type") == "session_summary"]

    if not sessions:
        lines.append("> No sessions for this day.")
        return "\n".join(lines)

    sessions_sorted = sorted(sessions, key=lambda r: r.get("timestamp", ""))
    total_cost   = sum(r.get("cost_usd", 0) or 0 for r in sessions)
    total_tokens = sum(r.get("total_tokens", 0) or 0 for r in sessions)

    # ── Summary ───────────────────────────────────────────────────────────────
    lines += [
        "## Summary", "",
        "| | |",
        "|---|---|",
        f"| Sessions | {len(sessions)} |",
        f"| Total Cost | ${total_cost:.4f} |",
        f"| Total Tokens | {fmt_tokens(total_tokens)} |",
        "",
    ]

    # ── Sessions table ────────────────────────────────────────────────────────
    lines += [
        "## Sessions", "",
        "| Time | Project | Session | Tokens |",
        "|------|---------|---------|--------|",
    ]
    for r in sessions_sorted:
        t       = fmt_time(r.get("timestamp", ""))
        project = r.get("project_name", "—")
        msg     = r.get("first_msg", "—")
        tokens  = fmt_tokens(r.get("total_tokens"))
        lines.append(f"| {t} | {project} | {msg} | {tokens} |")
    lines.append("")

    # ── Decision Log ──────────────────────────────────────────────────────────
    sessions_with_decisions = [r for r in sessions_sorted if r.get("decision_summary")]
    if sessions_with_decisions:
        lines += ["## Decision Log", ""]
        for r in sessions_with_decisions:
            t       = fmt_time(r.get("timestamp", ""))
            project = r.get("project_name", "")
            header  = f"### {t}"
            if project and project != "unknown":
                header += f" — {project}"
            lines.append(header)
            ds = r["decision_summary"]
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

    # ── Transcript stats (from ~/.claude/projects/) ───────────────────────────
    try:
        proj_stats = compute_project_stats(target_date)
        if proj_stats:
            lines += ["## Claude Sessions by Project", ""]
            lines += [
                "| Project | Sessions | Turns | Files Edited | Commands | Tokens | Cost |",
                "|---------|----------|-------|--------------|----------|--------|------|",
            ]
            for p in proj_stats:
                lines.append(
                    f"| {p['project_name']} "
                    f"| {p['sessions']} "
                    f"| {p['turns']} "
                    f"| {p['files_edited']} "
                    f"| {p['commands_run']} "
                    f"| {fmt_tokens(p['total_tokens'])} "
                    f"| ${p['cost_usd']:.4f} |"
                )
            lines.append("")
    except Exception:
        pass  # transcript stats are supplementary; never block main output

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
