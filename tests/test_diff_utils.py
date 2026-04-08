"""
tests/test_diff_utils.py
Unit tests for diff_utils.py
"""

from cdl.diff_utils import _make_diff, extract_edit_diffs


def _make_record(tool_name: str, inp: dict, ts: str = "2026-03-23T10:00:00") -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "content": [
                {"type": "tool_use", "name": tool_name, "input": inp}
            ]
        },
    }


class TestMakeDiff:
    def test_empty_to_empty(self):
        result = _make_diff([], [])
        assert result == []

    def test_added_lines(self):
        result = _make_diff([], ["hello", "world"])
        types = [d["type"] for d in result]
        assert "added" in types
        texts = [d["text"] for d in result if d["type"] == "added"]
        assert "hello" in texts
        assert "world" in texts

    def test_removed_lines(self):
        result = _make_diff(["old line"], [])
        types = [d["type"] for d in result]
        assert "removed" in types

    def test_header_present_when_diff_exists(self):
        result = _make_diff(["old"], ["new"])
        types = [d["type"] for d in result]
        assert "header" in types

    def test_hunk_present_when_diff_exists(self):
        result = _make_diff(["old"], ["new"])
        types = [d["type"] for d in result]
        assert "hunk" in types

    def test_context_lines_included(self):
        # Lines surrounding the change should appear as context
        old = ["a", "b", "c", "d", "e"]
        new = ["a", "b", "X", "d", "e"]
        result = _make_diff(old, new)
        types = [d["type"] for d in result]
        assert "context" in types

    def test_no_diff_for_identical_content(self):
        result = _make_diff(["same"], ["same"])
        assert result == []


class TestExtractEditDiffs:
    def test_empty_records(self):
        assert extract_edit_diffs([]) == []

    def test_skips_non_assistant_records(self):
        rec = {
            "type": "user",
            "timestamp": "2026-03-23T10:00:00",
            "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {}}]},
        }
        assert extract_edit_diffs([rec]) == []

    def test_edit_tool_extracted(self):
        rec = _make_record("Edit", {
            "file_path": "foo.py",
            "old_string": "x = 1",
            "new_string": "x = 2",
        })
        result = extract_edit_diffs([rec])
        assert len(result) == 1
        assert result[0]["file_path"] == "foo.py"
        assert result[0]["tool"] == "Edit"
        assert result[0]["timestamp"] == "2026-03-23T10:00:00"
        assert isinstance(result[0]["diff_lines"], list)

    def test_write_tool_extracted(self):
        rec = _make_record("Write", {
            "file_path": "new_file.py",
            "content": "print('hello')",
        })
        result = extract_edit_diffs([rec])
        assert len(result) == 1
        assert result[0]["tool"] == "Write"
        assert result[0]["file_path"] == "new_file.py"
        # Write diffs from empty → content, so all lines are added
        types = [d["type"] for d in result[0]["diff_lines"]]
        assert "added" in types

    def test_other_tool_names_skipped(self):
        rec = _make_record("Bash", {"command": "ls"})
        assert extract_edit_diffs([rec]) == []

    def test_multiple_edits_in_one_record(self):
        rec = {
            "type": "assistant",
            "timestamp": "2026-03-23T10:00:00",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {
                        "file_path": "a.py", "old_string": "1", "new_string": "2",
                    }},
                    {"type": "tool_use", "name": "Write", "input": {
                        "file_path": "b.py", "content": "x = 3",
                    }},
                ]
            },
        }
        result = extract_edit_diffs([rec])
        assert len(result) == 2
        assert {r["file_path"] for r in result} == {"a.py", "b.py"}

    def test_skips_record_with_non_list_content(self):
        rec = {
            "type": "assistant",
            "timestamp": "2026-03-23T10:00:00",
            "message": {"content": "plain string not a list"},
        }
        assert extract_edit_diffs([rec]) == []
