#!/usr/bin/env python3
"""
session_reader.py — reads ~/.claude/projects/ JSONL transcripts.

Provides fast metadata loading and lazy full-message loading.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure lib/ is importable regardless of working directory
_LIB_DIR = Path(__file__).resolve().parent
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from constants import (  # noqa: E402
    CLAUDE_PROJECTS_DIR,
    FIRST_MSG_PREVIEW_LEN,
    INPUT_COST_PER_TOKEN,
    OUTPUT_COST_PER_TOKEN,
    SKIP_PATH_SEGMENTS,
    TOOL_INPUT_PREVIEW_LEN,
    TOOL_RESULT_PREVIEW_LEN,
)
from models import MessageRecord, SessionMeta  # noqa: E402

# Re-export for consumers that import these names from session_reader
__all__ = [
    "CLAUDE_PROJECTS_DIR",
    "MessageRecord",
    "SessionMeta",
    "compute_project_stats",
    "decode_project_name",
    "display_width",
    "load_jsonl",
    "load_session_messages",
    "load_session_meta",
    "load_sessions",
    "truncate_to_width",
]


def decode_project_name(encoded: str) -> str:
    """Convert encoded dir name (e.g. -Users-foo-Desktop-myapp) to project name (myapp)."""
    parts = [p for p in encoded.split("-") if p]
    meaningful: list[str] = []
    for part in reversed(parts):
        if part.lower() in SKIP_PATH_SEGMENTS:
            break
        meaningful.append(part)
    if meaningful:
        return "-".join(reversed(meaningful))
    return parts[-1] if parts else encoded


def _char_width(c: str) -> int:
    ea = unicodedata.east_asian_width(c)
    return 2 if ea in ("W", "F") else 1


def display_width(s: str) -> int:
    """Return terminal display width of a string, counting CJK chars as 2."""
    if not any(ord(c) >= 128 for c in s):
        return len(s)
    return sum(_char_width(c) for c in s)


def truncate_to_width(s: str, max_width: int) -> str:
    """Truncate string so its display width does not exceed max_width."""
    result: list[str] = []
    current = 0
    for c in s:
        cw = _char_width(c)
        if current + cw > max_width:
            break
        result.append(c)
        current += cw
    return "".join(result)


def _extract_text(content, plain_only: bool = False) -> str:
    """Extract text from a message content value (str or list of blocks).

    plain_only=True returns only literal text blocks, joined with spaces (used
    for first-message previews).  plain_only=False (default) also renders
    tool_use/tool_result blocks, joined with newlines (used for message display).
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            elif not plain_only:
                if btype == "tool_use":
                    name = block.get("name", "tool")
                    inp = block.get("input", {})
                    inp_str = json.dumps(inp, ensure_ascii=False)
                    if len(inp_str) > TOOL_INPUT_PREVIEW_LEN:
                        inp_str = inp_str[:TOOL_INPUT_PREVIEW_LEN] + "..."
                    parts.append(f"[Tool: {name}] {inp_str}")
                elif btype == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, list):
                        for item in inner:
                            if isinstance(item, dict) and item.get("type") == "text":
                                t = item.get("text", "").strip()
                                if t:
                                    parts.append(f"[Result] {t[:TOOL_RESULT_PREVIEW_LEN]}")
                    elif isinstance(inner, str) and inner.strip():
                        parts.append(f"[Result] {inner[:TOOL_RESULT_PREVIEW_LEN]}")
        sep = " " if plain_only else "\n"
        return sep.join(parts)
    return str(content).strip()


def load_jsonl(path: Path) -> list[dict]:
    """Parse all lines of a JSONL file, skipping blank and malformed lines."""
    records: list[dict] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return records


def _build_session_meta(
    path: Path,
    records: list[dict],
    project_name: Optional[str] = None,
) -> Optional[SessionMeta]:
    """Build a SessionMeta from pre-parsed records (no file I/O)."""
    if not records:
        return None

    session_id = path.stem
    project_dir = path.parent.name
    if project_name is None:
        project_name = decode_project_name(project_dir)

    first_msg = ""
    turns = 0
    total_input = 0
    total_output = 0
    timestamps: list[str] = []

    for rec in records:
        rec_type = rec.get("type", "")
        ts = rec.get("timestamp", "")
        if ts:
            timestamps.append(ts)

        if rec_type == "user":
            turns += 1
            msg = rec.get("message", {})
            if not isinstance(msg, dict):
                continue
            if not first_msg:
                text = _extract_text(msg.get("content", ""), plain_only=True)
                if text:
                    first_msg = text[:FIRST_MSG_PREVIEW_LEN]

        elif rec_type == "assistant":
            msg = rec.get("message", {})
            if not isinstance(msg, dict):
                continue
            usage = msg.get("usage", {})
            if isinstance(usage, dict):
                total_input += usage.get("input_tokens", 0) or 0
                total_output += usage.get("output_tokens", 0) or 0

    total_tokens = total_input + total_output
    cost_usd = (
        total_input * INPUT_COST_PER_TOKEN
        + total_output * OUTPUT_COST_PER_TOKEN
    )

    start_time = None
    if timestamps:
        parsed: list[datetime] = []
        for t in timestamps:
            try:
                parsed.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
            except (ValueError, TypeError):
                pass
        if parsed:
            start_time = min(parsed)

    return SessionMeta(
        session_id=session_id,
        project_dir=project_dir,
        project_name=project_name,
        file_path=path,
        first_msg=first_msg or "(empty session)",
        turns=turns,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        start_time=start_time,
    )


def _build_messages(records: list[dict]) -> list[MessageRecord]:
    """Extract MessageRecord list from pre-parsed records (no file I/O)."""
    messages: list[MessageRecord] = []
    for rec in records:
        rec_type = rec.get("type", "")
        if rec_type not in ("user", "assistant"):
            continue
        ts = rec.get("timestamp", "")
        msg = rec.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", "")
        text = _extract_text(content)
        if not text:
            continue
        messages.append(MessageRecord(role=rec_type, content=text, timestamp=ts))
    return messages


def load_session_meta(
    path: Path, project_name: Optional[str] = None
) -> Optional[SessionMeta]:
    """Load metadata for a single session JSONL file (messages not populated)."""
    return _build_session_meta(path, load_jsonl(path), project_name)


def load_session_messages(meta: SessionMeta) -> None:
    """Populate meta.messages in-place. No-op if already loaded."""
    if meta.messages_loaded:
        return
    meta.messages = _build_messages(load_jsonl(meta.file_path))
    meta.messages_loaded = True


def _sort_key(s: SessionMeta) -> datetime:
    """Comparable sort key from start_time (all returned values are naive)."""
    if s.start_time is None:
        return datetime.min
    if s.start_time.tzinfo is not None:
        return s.start_time.replace(tzinfo=None)
    return s.start_time


def load_sessions(
    date_filter: Optional[str] = None,
    project_filter: Optional[str] = None,
    claude_dir: Path = CLAUDE_PROJECTS_DIR,
) -> list[SessionMeta]:
    """
    Load metadata for all sessions under claude_dir.

    Args:
        date_filter: ISO date YYYY-MM-DD. If given, only sessions starting on that
                     local date are returned.
        project_filter: Case-insensitive substring to match against project_name.
        claude_dir: Base directory; defaults to ~/.claude/projects/.

    Returns:
        Sessions sorted by start_time descending (most recent first).
    """
    sessions: list[SessionMeta] = []

    if not claude_dir.is_dir():
        return sessions

    target_date = None
    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            pass

    for project_path in claude_dir.iterdir():
        if not project_path.is_dir():
            continue
        proj_name = decode_project_name(project_path.name)
        if project_filter and project_filter.lower() not in proj_name.lower():
            continue

        for jsonl_path in project_path.glob("*.jsonl"):
            if target_date is not None:
                mtime_date = datetime.fromtimestamp(jsonl_path.stat().st_mtime).date()
                if abs((mtime_date - target_date).days) > 2:
                    continue

            meta = load_session_meta(jsonl_path, project_name=proj_name)
            if meta is None:
                continue

            if target_date is not None and meta.start_time is not None:
                local = meta.start_time
                if local.tzinfo:
                    local = local.astimezone().replace(tzinfo=None)
                if local.date() != target_date:
                    continue

            sessions.append(meta)

    sessions.sort(key=_sort_key, reverse=True)
    return sessions


def compute_project_stats(
    date_filter: str,
    claude_dir: Path = CLAUDE_PROJECTS_DIR,
) -> list[dict]:
    """
    Compute per-project stats for a given date from transcripts.
    Each JSONL file is read only once (metadata and tool stats extracted together).

    Returns a list of dicts with keys:
        project_name, sessions, turns, total_tokens, cost_usd,
        files_edited, commands_run
    """
    target_date = None
    try:
        target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
    except ValueError:
        return []

    if not claude_dir.is_dir():
        return []

    stats: dict[str, dict] = {}

    for project_path in claude_dir.iterdir():
        if not project_path.is_dir():
            continue
        proj_name = decode_project_name(project_path.name)

        for jsonl_path in project_path.glob("*.jsonl"):
            mtime_date = datetime.fromtimestamp(jsonl_path.stat().st_mtime).date()
            if abs((mtime_date - target_date).days) > 2:
                continue

            records = load_jsonl(jsonl_path)
            if not records:
                continue

            meta = _build_session_meta(jsonl_path, records, project_name=proj_name)
            if meta is None:
                continue

            if meta.start_time is not None:
                local = meta.start_time
                if local.tzinfo:
                    local = local.astimezone().replace(tzinfo=None)
                if local.date() != target_date:
                    continue

            if proj_name not in stats:
                stats[proj_name] = {
                    "project_name": proj_name,
                    "sessions": 0,
                    "turns": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "files_edited": set(),
                    "commands_run": 0,
                }
            s = stats[proj_name]
            s["sessions"] += 1
            s["turns"] += meta.turns
            s["total_tokens"] += meta.total_tokens
            s["cost_usd"] += meta.cost_usd

            # Extract tool stats directly from raw records — no rendering needed
            for rec in records:
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message", {})
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name", "")
                    inp = block.get("input", {})
                    if not isinstance(inp, dict):
                        continue
                    if name in ("Edit", "Write"):
                        fp = inp.get("file_path") or inp.get("path", "")
                        if fp:
                            s["files_edited"].add(fp)
                    elif name == "Bash":
                        s["commands_run"] += 1

    result = []
    for s in stats.values():
        result.append({
            "project_name": s["project_name"],
            "sessions": s["sessions"],
            "turns": s["turns"],
            "total_tokens": s["total_tokens"],
            "cost_usd": s["cost_usd"],
            "files_edited": len(s["files_edited"]),
            "commands_run": s["commands_run"],
        })
    result.sort(key=lambda x: x["cost_usd"], reverse=True)
    return result
