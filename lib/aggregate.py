#!/usr/bin/env python3
"""
c-daily aggregate.py
JSONL rawログ → 日次Markdown生成
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
        lines.append("> この日のログはありません。")
        return "\n".join(lines)

    by_type: dict[str, list] = defaultdict(list)
    for r in records:
        by_type[r.get("type", "other")].append(r)

    # --- サマリー ---
    lines += [
        "## 📊 サマリー", "",
        "| 種別 | 件数 |",
        "|------|------|",
        f"| ✏️ ファイル編集   | {len(by_type['file_edit'])} |",
        f"| ⚡ コマンド実行   | {len(by_type['command'])} |",
        f"| 💬 会話セッション | {len(by_type['session_summary'])} |",
        f"| 🌿 Gitコミット    | {len(by_type['git'])} |",
        f"| **合計**         | **{len(records)}** |",
        "",
    ]

    # --- タイムライン ---
    lines += ["## ⏱️ タイムライン", ""]
    prev_hour = None
    for r in sorted(records, key=lambda r: r.get("timestamp", "")):
        t    = fmt_time(r.get("timestamp", ""))
        hour = t[:2] if len(t) >= 2 else "??"
        if hour != prev_hour:
            lines.append(f"### {hour}:xx")
            prev_hour = hour
        lines.append(f"- `{t}` {r.get('summary', '')}")
    lines.append("")

    # --- 編集ファイル一覧 ---
    if by_type["file_edit"]:
        lines += ["## ✏️ 編集ファイル", ""]
        path_times: dict[str, list] = defaultdict(list)
        for r in by_type["file_edit"]:
            path_times[r.get("path", "")].append(fmt_time(r.get("timestamp", "")))
        for path, times in sorted(path_times.items()):
            lines.append(f"- `{path}` _{', '.join(times)}_")
        lines.append("")

    # --- コマンド履歴 ---
    if by_type["command"]:
        lines += ["## ⚡ 実行コマンド", ""]
        for r in by_type["command"]:
            lines.append(f"- `{fmt_time(r.get('timestamp',''))}` `{r.get('command','')}`")
        lines.append("")

    # --- 会話サマリー ---
    if by_type["session_summary"]:
        lines += ["## 💬 Claude Code セッション", ""]
        for r in by_type["session_summary"]:
            t     = fmt_time(r.get("timestamp", ""))
            msg   = r.get("first_msg", "")
            meta  = []
            if r.get("turns"):  meta.append(f"{r['turns']} turns")
            if r.get("cost_usd"): meta.append(f"${r['cost_usd']:.4f}")
            meta_str = f" _({', '.join(meta)})_" if meta else ""
            lines.append(f"- `{t}` {msg}{meta_str}")
        lines.append("")

    # --- Gitコミット ---
    if by_type["git"]:
        lines += ["## 🌿 Git コミット", ""]
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
    print(f"✅ {out} ({len(records)} 件)")


if __name__ == "__main__":
    main()
