"""
diff_utils.py — extract file-edit diffs from JSONL session records.
"""

from __future__ import annotations

import difflib
from typing import Any

__all__ = ["extract_edit_diffs"]


def extract_edit_diffs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return Edit/Write operations with unified diff lines.

    Each item:
        file_path: str
        tool: "Edit" | "Write"
        timestamp: str
        diff_lines: list of {"type": "header"|"hunk"|"added"|"removed"|"context", "text": str}
    """
    edits = []
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        ts = rec.get("timestamp", "")
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
            if name == "Edit":
                file_path = inp.get("file_path", "")
                old = inp.get("old_string", "")
                new = inp.get("new_string", "")
                diff_lines = _make_diff(old.splitlines(), new.splitlines())
                edits.append({
                    "file_path": file_path,
                    "tool": "Edit",
                    "timestamp": ts,
                    "diff_lines": diff_lines,
                })
            elif name == "Write":
                file_path = inp.get("file_path", "")
                written = inp.get("content", "")
                diff_lines = _make_diff([], written.splitlines())
                edits.append({
                    "file_path": file_path,
                    "tool": "Write",
                    "timestamp": ts,
                    "diff_lines": diff_lines,
                })
    return edits


def _make_diff(old_lines: list[str], new_lines: list[str]) -> list[dict[str, str]]:
    raw = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=3))
    result = []
    for line in raw:
        if line.startswith("--- ") or line.startswith("+++ "):
            result.append({"type": "header", "text": line})
        elif line.startswith("@@"):
            result.append({"type": "hunk", "text": line})
        elif line.startswith("+"):
            result.append({"type": "added", "text": line[1:]})
        elif line.startswith("-"):
            result.append({"type": "removed", "text": line[1:]})
        else:
            result.append({"type": "context", "text": line[1:] if line.startswith(" ") else line})
    return result
