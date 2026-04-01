"""
models.py — shared dataclasses for c-daily.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class MessageRecord:
    """A single message (user or assistant) within a session transcript."""

    role: str      # "user" or "assistant"
    content: str   # rendered text
    timestamp: str


@dataclass
class SessionMeta:
    """
    Metadata for a single Claude Code session.

    Messages are loaded lazily via load_session_messages(); check
    messages_loaded before assuming the list is populated.
    """

    session_id: str
    project_dir: str    # raw encoded directory name from ~/.claude/projects/
    project_name: str   # decoded human-readable name
    file_path: Path
    first_msg: str      # first user message preview (≤ FIRST_MSG_PREVIEW_LEN chars)
    turns: int          # number of user turns
    total_tokens: int
    cost_usd: float
    start_time: Optional[datetime]
    messages: list[MessageRecord] = field(default_factory=list)
    messages_loaded: bool = False

    def fmt_start(self) -> str:
        """Return local start time as HH:MM."""
        if not self.start_time:
            return "--:--"
        local = self.start_time
        if local.tzinfo:
            local = local.astimezone().replace(tzinfo=None)
        return local.strftime("%H:%M")

    def fmt_date(self) -> str:
        """Return local start date as YYYY-MM-DD."""
        if not self.start_time:
            return "----"
        local = self.start_time
        if local.tzinfo:
            local = local.astimezone().replace(tzinfo=None)
        return local.strftime("%Y-%m-%d")
