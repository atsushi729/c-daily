"""
constants.py — shared constants for c-daily.

All magic numbers, string literals, and path definitions that are referenced
from more than one module belong here.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Directory / file paths
# ---------------------------------------------------------------------------
CLAUDE_DIR = Path.home() / ".claude"
CLAUDE_PROJECTS_DIR = CLAUDE_DIR / "projects"
CLAUDE_SETTINGS_FILE = CLAUDE_DIR / "settings.json"
DEFAULT_LOG_DIR = Path.home() / ".daily-logs"

# ---------------------------------------------------------------------------
# macOS launchd
# ---------------------------------------------------------------------------
LAUNCHD_LABEL = "com.c-daily.aggregate"
LAUNCHD_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
LAUNCHD_HOUR = 23
LAUNCHD_MINUTE = 58

# ---------------------------------------------------------------------------
# Project directory name decoding
# Segments stripped when converting encoded dir names to human-readable names,
# e.g. "-Users-foo-Desktop-myapp" → "myapp"
# ---------------------------------------------------------------------------
SKIP_PATH_SEGMENTS: frozenset[str] = frozenset(
    {
        "desktop",
        "documents",
        "downloads",
        "src",
        "work",
        "projects",
        "home",
        "users",
        "code",
        "dev",
        "repos",
        "github",
        "workspace",
    }
)

# ---------------------------------------------------------------------------
# Anthropic API
# ---------------------------------------------------------------------------
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

# Model used to generate decision summaries (fast / cheap)
SUMMARY_MODEL = "claude-haiku-4-5-20251001"
SUMMARY_MAX_TOKENS = 512
SUMMARY_MAX_MESSAGES = 40  # max message lines fed to summarization prompt

# ---------------------------------------------------------------------------
# Claude Sonnet 4.6 pricing
# ---------------------------------------------------------------------------
INPUT_COST_PER_TOKEN: float = 3.0 / 1_000_000  # $3 per million input tokens
OUTPUT_COST_PER_TOKEN: float = 15.0 / 1_000_000  # $15 per million output tokens

# ---------------------------------------------------------------------------
# Display / truncation limits
# ---------------------------------------------------------------------------
FIRST_MSG_PREVIEW_LEN = 100  # max characters in first-message preview
TOOL_INPUT_PREVIEW_LEN = 150  # max chars for inline tool input display
TOOL_RESULT_PREVIEW_LEN = 300  # max chars for inline tool result display

# ---------------------------------------------------------------------------
# Minimum supported Python version
# ---------------------------------------------------------------------------
MIN_PYTHON_VERSION = (3, 9)


def validate_date(value: str) -> None:
    """Exit with an error message if value is not a valid YYYY-MM-DD date."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Invalid date format: {value!r}. Expected YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)
