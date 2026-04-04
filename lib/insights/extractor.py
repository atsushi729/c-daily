"""
insights/extractor.py - Aggregates session data for the web UI.

Public API:
    activity_heatmap(days) -> dict[str, float]   {YYYY-MM-DD: cost_usd}
    project_list()         -> list[dict]          all projects, aggregated
    project_detail(name)   -> dict | None         single project + sessions
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

_LIB_DIR = Path(__file__).resolve().parent.parent
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from constants import CLAUDE_PROJECTS_DIR  # noqa: E402
from models import SessionMeta  # noqa: E402
from session_reader import (  # noqa: E402
    _build_session_meta,
    decode_project_name,
    load_jsonl,
    load_session_messages,
    load_session_meta,
)


def _extract_tool_stats(records: list[dict[str, Any]]) -> tuple[set[str], int]:
    """Return (files_edited_set, commands_run) from raw JSONL records."""
    files: set[str] = set()
    cmds = 0
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        content = rec.get("message", {}).get("content", [])
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
                    files.add(str(fp))
            elif name == "Bash":
                cmds += 1
    return files, cmds


def _to_local(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def activity_heatmap(
    days: int = 90,
    claude_dir: Path = CLAUDE_PROJECTS_DIR,
) -> dict[str, float]:
    """Return {YYYY-MM-DD: cost_usd} for the last `days` days."""
    end = date.today()
    start = end - timedelta(days=days - 1)
    result: dict[str, float] = {}

    if not claude_dir.is_dir():
        return result

    for project_path in claude_dir.iterdir():
        if not project_path.is_dir():
            continue
        proj_name = decode_project_name(project_path.name)
        for jsonl_path in project_path.glob("*.jsonl"):
            records = load_jsonl(jsonl_path)
            meta = _build_session_meta(jsonl_path, records, project_name=proj_name)
            if meta is None or meta.start_time is None:
                continue
            d = _to_local(meta.start_time).date()
            if d < start or d > end:
                continue
            ds = d.isoformat()
            result[ds] = result.get(ds, 0.0) + meta.cost_usd

    return result


def project_list(claude_dir: Path = CLAUDE_PROJECTS_DIR) -> list[dict[str, Any]]:
    """Return all projects sorted by total cost descending."""
    if not claude_dir.is_dir():
        return []

    stats: dict[str, dict[str, Any]] = {}

    for project_path in claude_dir.iterdir():
        if not project_path.is_dir():
            continue
        proj_name = decode_project_name(project_path.name)

        for jsonl_path in project_path.glob("*.jsonl"):
            records = load_jsonl(jsonl_path)
            meta = _build_session_meta(jsonl_path, records, project_name=proj_name)
            if meta is None:
                continue

            if proj_name not in stats:
                stats[proj_name] = {
                    "name": proj_name,
                    "sessions": 0,
                    "turns": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "files_edited": set(),
                    "commands_run": 0,
                    "last_active": None,
                }
            s = stats[proj_name]
            s["sessions"] += 1
            s["turns"] += meta.turns
            s["total_tokens"] += meta.total_tokens
            s["cost_usd"] += meta.cost_usd

            if meta.start_time is not None:
                local_dt = _to_local(meta.start_time)
                if s["last_active"] is None or local_dt > s["last_active"]:
                    s["last_active"] = local_dt

            files, cmds = _extract_tool_stats(records)
            s["files_edited"] |= files
            s["commands_run"] += cmds

    result = []
    for s in stats.values():
        last = s["last_active"].strftime("%Y-%m-%d") if s["last_active"] else "—"
        result.append({
            "name": s["name"],
            "sessions": s["sessions"],
            "turns": s["turns"],
            "total_tokens": s["total_tokens"],
            "cost_usd": s["cost_usd"],
            "files_edited": len(s["files_edited"]),
            "commands_run": s["commands_run"],
            "last_active": last,
        })
    result.sort(key=lambda x: x["cost_usd"], reverse=True)
    return result


def project_detail(
    project_name: str,
    claude_dir: Path = CLAUDE_PROJECTS_DIR,
) -> dict[str, Any] | None:
    """Return detailed stats + session list for one project, or None if not found."""
    if not claude_dir.is_dir():
        return None

    sessions: list[dict[str, Any]] = []
    agg: dict[str, Any] = {
        "sessions": 0,
        "turns": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "files_edited": set(),
        "commands_run": 0,
    }

    for project_path in claude_dir.iterdir():
        if not project_path.is_dir():
            continue
        if decode_project_name(project_path.name).lower() != project_name.lower():
            continue

        for jsonl_path in project_path.glob("*.jsonl"):
            records = load_jsonl(jsonl_path)
            meta = _build_session_meta(jsonl_path, records, project_name=project_name)
            if meta is None:
                continue

            local_dt = _to_local(meta.start_time) if meta.start_time else None
            files, cmds = _extract_tool_stats(records)

            sessions.append({
                "session_id": meta.session_id,
                "date": local_dt.strftime("%Y-%m-%d") if local_dt else "—",
                "time": local_dt.strftime("%H:%M") if local_dt else "—",
                "first_msg": meta.first_msg,
                "turns": meta.turns,
                "total_tokens": meta.total_tokens,
                "cost_usd": meta.cost_usd,
                "files_edited": len(files),
                "commands_run": cmds,
            })

            agg["sessions"] += 1
            agg["turns"] += meta.turns
            agg["total_tokens"] += meta.total_tokens
            agg["cost_usd"] += meta.cost_usd
            agg["files_edited"] |= files
            agg["commands_run"] += cmds

    if not sessions:
        return None

    sessions.sort(key=lambda x: (x["date"], x["time"]), reverse=True)

    return {
        "name": project_name,
        "stats": {**agg, "files_edited": len(agg["files_edited"])},
        "sessions": sessions,
    }


def session_messages(
    project_name: str,
    session_id: str,
    claude_dir: Path = CLAUDE_PROJECTS_DIR,
) -> SessionMeta | None:
    """Return a SessionMeta with messages loaded for the given session, or None."""
    if not claude_dir.is_dir():
        return None

    for project_path in claude_dir.iterdir():
        if not project_path.is_dir():
            continue
        if decode_project_name(project_path.name).lower() != project_name.lower():
            continue
        jsonl_path = project_path / f"{session_id}.jsonl"
        try:
            meta = load_session_meta(jsonl_path, project_name=project_name)
        except (FileNotFoundError, OSError):
            continue
        if meta is None:
            return None
        load_session_messages(meta)
        return meta

    return None
