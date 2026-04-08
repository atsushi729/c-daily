"""
tests/test_text_utils.py
Unit tests for text_utils.py
"""

from cdl.text_utils import strip_system_blocks


class TestStripSystemBlocks:
    def test_plain_text_unchanged(self):
        assert strip_system_blocks("Hello world") == "Hello world"

    def test_empty_string(self):
        assert strip_system_blocks("") == ""

    def test_removes_single_tag_block(self):
        result = strip_system_blocks(
            "<local-command-caveat>some injected text</local-command-caveat>"
        )
        assert result == ""

    def test_removes_tag_block_with_surrounding_text(self):
        result = strip_system_blocks(
            "User said: <system-reminder>ignore this</system-reminder> please fix the bug"
        )
        assert "ignore this" not in result
        assert "system-reminder" not in result
        assert "User said:" in result
        assert "please fix the bug" in result

    def test_removes_multiple_tag_blocks(self):
        result = strip_system_blocks(
            "<command-name>bash</command-name> hello <command-args>-c ls</command-args>"
        )
        assert "bash" not in result
        assert "-c ls" not in result
        assert "hello" in result

    def test_strips_surrounding_whitespace(self):
        result = strip_system_blocks("  real text  ")
        assert result == "real text"

    def test_multiline_tag_block_removed(self):
        text = "before\n<local-command-stdout>line1\nline2</local-command-stdout>\nafter"
        result = strip_system_blocks(text)
        assert "line1" not in result
        assert "line2" not in result
        assert "before" in result
        assert "after" in result

    def test_tag_with_attributes_removed(self):
        # Tags with attributes like <tag attr="val"> should also be stripped
        result = strip_system_blocks('<user-prompt-submit-hook type="pre">data</user-prompt-submit-hook>')
        assert "data" not in result
