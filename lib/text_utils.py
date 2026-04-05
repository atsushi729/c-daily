from __future__ import annotations

import re

_SYSTEM_TAG_RE = re.compile(
    r"<[a-zA-Z][a-zA-Z0-9_-]*(?:\s[^>]*)?>.*?</[a-zA-Z][a-zA-Z0-9_-]*>",
    re.DOTALL,
)


def strip_system_blocks(text: str) -> str:
    """Strip XML-style system tag blocks (e.g. <local-command-caveat>) from text."""
    return _SYSTEM_TAG_RE.sub("", text).strip()
