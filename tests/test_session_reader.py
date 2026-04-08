"""
tests/test_session_reader.py
Unit tests for session_reader.py and models.py
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cdl.models import SessionMeta
from cdl.session_reader import (
    _extract_text,
    _has_user_text,
    _is_system_text,
    decode_project_name,
    load_session_meta,
)


# ---------------------------------------------------------------------------
# decode_project_name
# ---------------------------------------------------------------------------

class TestDecodeProjectName:
    def test_simple_app_name(self):
        assert decode_project_name("-Users-foo-Desktop-myapp") == "myapp"

    def test_hyphenated_project_name(self):
        # Segments that aren't in SKIP_PATH_SEGMENTS should all be preserved
        assert decode_project_name("-Users-foo-Desktop-my-project") == "my-project"

    def test_skips_common_path_segments(self):
        # "src" is in SKIP_PATH_SEGMENTS, stops there
        assert decode_project_name("-Users-foo-src-mylib") == "mylib"

    def test_skips_multiple_known_segments(self):
        # Scans from the right: "api" not skipped, stops
        result = decode_project_name("-Users-foo-Documents-work-api")
        assert result == "api"

    def test_single_segment(self):
        assert decode_project_name("myproject") == "myproject"

    def test_all_segments_skipped_falls_back_to_last(self):
        # All parts are known skip segments — fall back to last part
        result = decode_project_name("-users-desktop-documents")
        assert result == "documents"


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_string_content(self):
        assert _extract_text("  hello  ") == "hello"

    def test_empty_string(self):
        assert _extract_text("") == ""

    def test_list_with_text_block(self):
        content = [{"type": "text", "text": "hello world"}]
        assert _extract_text(content) == "hello world"

    def test_list_multiple_text_blocks_plain(self):
        content = [
            {"type": "text", "text": "foo"},
            {"type": "text", "text": "bar"},
        ]
        result = _extract_text(content, plain_only=True)
        assert "foo" in result
        assert "bar" in result

    def test_tool_use_block_included_by_default(self):
        content = [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]
        result = _extract_text(content, plain_only=False)
        assert "[Tool: Bash]" in result

    def test_tool_use_block_excluded_in_plain_mode(self):
        content = [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]
        result = _extract_text(content, plain_only=True)
        assert "[Tool: Bash]" not in result

    def test_tool_result_string_content(self):
        content = [{"type": "tool_result", "content": "output here"}]
        result = _extract_text(content)
        assert "[Result]" in result
        assert "output here" in result

    def test_tool_result_list_content(self):
        content = [{"type": "tool_result", "content": [{"type": "text", "text": "got it"}]}]
        result = _extract_text(content)
        assert "got it" in result

    def test_non_dict_items_in_list_skipped(self):
        content = ["not a dict", {"type": "text", "text": "real"}]
        assert _extract_text(content) == "real"

    def test_non_list_non_str_fallback(self):
        result = _extract_text(42)
        assert result == "42"


# ---------------------------------------------------------------------------
# _is_system_text / _has_user_text
# ---------------------------------------------------------------------------

class TestIsSystemText:
    def test_plain_text_is_not_system(self):
        assert not _is_system_text("Fix the login bug")

    def test_local_command_caveat_is_system(self):
        assert _is_system_text("<local-command-caveat>some text</local-command-caveat>")

    def test_system_reminder_is_system(self):
        assert _is_system_text("<system-reminder>reminder content</system-reminder>")

    def test_command_name_is_system(self):
        assert _is_system_text("<command-name>bash</command-name>")

    def test_leading_whitespace_stripped_before_check(self):
        assert _is_system_text("  <system-reminder>x</system-reminder>")


class TestHasUserText:
    def test_plain_string_is_user_text(self):
        assert _has_user_text("real user message")

    def test_empty_string_is_not_user_text(self):
        assert not _has_user_text("")

    def test_system_string_is_not_user_text(self):
        assert not _has_user_text("<system-reminder>x</system-reminder>")

    def test_list_with_real_text_block(self):
        content = [{"type": "text", "text": "please help me"}]
        assert _has_user_text(content)

    def test_list_with_only_system_text_block(self):
        content = [{"type": "text", "text": "<command-name>foo</command-name>"}]
        assert not _has_user_text(content)

    def test_list_with_no_text_blocks(self):
        content = [{"type": "tool_result", "content": "output"}]
        assert not _has_user_text(content)

    def test_empty_list(self):
        assert not _has_user_text([])


# ---------------------------------------------------------------------------
# load_session_meta
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


class TestLoadSessionMeta:
    def _make_records(self, first_msg: str = "Fix the bug", turns: int = 2) -> list[dict]:
        records = []
        for i in range(turns):
            ts = f"2026-03-23T10:0{i}:00"
            records.append({
                "type": "user",
                "timestamp": ts,
                "message": {"content": first_msg if i == 0 else "follow-up"},
            })
            records.append({
                "type": "assistant",
                "timestamp": ts,
                "message": {
                    "content": [{"type": "text", "text": "Sure!"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            })
        return records

    def test_returns_session_meta(self):
        with tempfile.TemporaryDirectory() as d:
            project_dir = Path(d) / "-Users-foo-Desktop-myapp"
            project_dir.mkdir()
            p = project_dir / "abc123.jsonl"
            _write_jsonl(p, self._make_records())
            meta = load_session_meta(p)
        assert meta is not None
        assert meta.session_id == "abc123"
        assert meta.project_name == "myapp"

    def test_first_msg_captured(self):
        with tempfile.TemporaryDirectory() as d:
            project_dir = Path(d) / "-Users-foo-Desktop-myapp"
            project_dir.mkdir()
            p = project_dir / "abc123.jsonl"
            _write_jsonl(p, self._make_records(first_msg="Please refactor auth"))
            meta = load_session_meta(p)
        assert meta is not None
        assert "Please refactor auth" in meta.first_msg

    def test_turns_counted(self):
        with tempfile.TemporaryDirectory() as d:
            project_dir = Path(d) / "-Users-foo-Desktop-myapp"
            project_dir.mkdir()
            p = project_dir / "abc123.jsonl"
            _write_jsonl(p, self._make_records(turns=3))
            meta = load_session_meta(p)
        assert meta is not None
        assert meta.turns == 3

    def test_tokens_accumulated(self):
        with tempfile.TemporaryDirectory() as d:
            project_dir = Path(d) / "-Users-foo-Desktop-myapp"
            project_dir.mkdir()
            p = project_dir / "abc123.jsonl"
            # 2 turns × (100 input + 50 output) = 300 total tokens
            _write_jsonl(p, self._make_records(turns=2))
            meta = load_session_meta(p)
        assert meta is not None
        assert meta.total_tokens == 300

    def test_returns_none_for_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "empty.jsonl"
            p.write_text("", encoding="utf-8")
            meta = load_session_meta(p)
        assert meta is None

    def test_project_name_override(self):
        with tempfile.TemporaryDirectory() as d:
            project_dir = Path(d) / "-Users-foo-Desktop-myapp"
            project_dir.mkdir()
            p = project_dir / "abc123.jsonl"
            _write_jsonl(p, self._make_records())
            meta = load_session_meta(p, project_name="custom-name")
        assert meta is not None
        assert meta.project_name == "custom-name"


# ---------------------------------------------------------------------------
# SessionMeta.fmt_start / fmt_date
# ---------------------------------------------------------------------------

def _make_meta(**kwargs) -> SessionMeta:
    defaults = dict(
        session_id="s1",
        project_dir="-Users-foo-myapp",
        project_name="myapp",
        file_path=Path("/tmp/s1.jsonl"),
        first_msg="hello",
        turns=1,
        total_tokens=100,
        cost_usd=0.001,
        start_time=None,
    )
    defaults.update(kwargs)
    return SessionMeta(**defaults)


class TestSessionMetaFormatters:
    def test_fmt_start_no_time(self):
        meta = _make_meta(start_time=None)
        assert meta.fmt_start() == "--:--"

    def test_fmt_date_no_time(self):
        meta = _make_meta(start_time=None)
        assert meta.fmt_date() == "----"

    def test_fmt_start_naive_datetime(self):
        meta = _make_meta(start_time=datetime(2026, 3, 23, 14, 35, 0))
        assert meta.fmt_start() == "14:35"

    def test_fmt_date_naive_datetime(self):
        meta = _make_meta(start_time=datetime(2026, 3, 23, 14, 35, 0))
        assert meta.fmt_date() == "2026-03-23"

    def test_fmt_start_aware_datetime(self):
        # UTC datetime — converted to local; just check it returns HH:MM format
        aware = datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc)
        meta = _make_meta(start_time=aware)
        result = meta.fmt_start()
        assert len(result) == 5
        assert result[2] == ":"

    def test_fmt_date_aware_datetime(self):
        aware = datetime(2026, 3, 23, 12, 0, 0, tzinfo=timezone.utc)
        meta = _make_meta(start_time=aware)
        result = meta.fmt_date()
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"
