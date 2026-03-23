"""
tests/test_aggregate.py
aggregate.py のユニットテスト
"""
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# lib/ をパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from aggregate import build_md, load_jsonl, fmt_time


# --- フィクスチャ ---

def make_record(rtype, ts="2026-03-23T10:00:00", **kwargs):
    base = {"timestamp": ts, "source": "claude-code", "type": rtype}
    base.update(kwargs)
    return base


FILE_EDIT = make_record(
    "file_edit", ts="2026-03-23T10:23:11",
    path="src/app.py", tool="write_file",
    summary="✏️ 編集: src/app.py"
)
COMMAND = make_record(
    "command", ts="2026-03-23T10:31:05",
    command="pytest tests/", tool="bash",
    summary="⚡ 実行: pytest tests/"
)
SESSION = make_record(
    "session_summary", ts="2026-03-23T11:00:00",
    first_msg="認証モジュールのリファクタリング",
    turns=12, cost_usd=0.0231,
    summary="💬 セッション終了: 認証モジュールのリファクタリング"
)
GIT = make_record(
    "git", ts="2026-03-23T14:05:00",
    repo="my-app", hash="abc1234",
    message="feat: add JWT refresh",
    summary="🌿 [my-app] feat: add JWT refresh"
)


# --- テスト ---

class TestFmtTime:
    def test_valid_iso(self):
        assert fmt_time("2026-03-23T10:23:11") == "10:23"

    def test_invalid_returns_original(self):
        assert fmt_time("not-a-date") == "not-a-date"

    def test_empty_string(self):
        assert fmt_time("") == ""


class TestBuildMd:
    def test_empty_records(self):
        md = build_md("2026-03-23", [])
        assert "2026-03-23" in md
        assert "ログはありません" in md

    def test_header_contains_date(self):
        md = build_md("2026-03-23", [FILE_EDIT])
        assert "# 📋 Daily Log — 2026-03-23" in md

    def test_file_edit_in_timeline(self):
        md = build_md("2026-03-23", [FILE_EDIT])
        assert "src/app.py" in md
        assert "10:23" in md

    def test_file_edit_in_file_list(self):
        md = build_md("2026-03-23", [FILE_EDIT])
        assert "## ✏️ 編集ファイル" in md

    def test_command_in_timeline(self):
        md = build_md("2026-03-23", [COMMAND])
        assert "pytest tests/" in md

    def test_session_summary_section(self):
        md = build_md("2026-03-23", [SESSION])
        assert "## 💬 Claude Code セッション" in md
        assert "認証モジュールのリファクタリング" in md
        assert "12 turns" in md
        assert "$0.0231" in md

    def test_git_section(self):
        md = build_md("2026-03-23", [GIT])
        assert "## 🌿 Git コミット" in md
        assert "feat: add JWT refresh" in md
        assert "abc1234" in md

    def test_summary_counts(self):
        records = [FILE_EDIT, FILE_EDIT, COMMAND, SESSION]
        md = build_md("2026-03-23", records)
        assert "| ✏️ ファイル編集   | 2 |" in md
        assert "| ⚡ コマンド実行   | 1 |" in md
        assert "| 💬 会話セッション | 1 |" in md

    def test_timeline_sorted_by_time(self):
        late  = make_record("command", ts="2026-03-23T15:00:00", command="ls", summary="⚡ ls")
        early = make_record("file_edit", ts="2026-03-23T09:00:00", path="a.py", summary="✏️ a.py")
        md = build_md("2026-03-23", [late, early])
        idx_early = md.index("09:")
        idx_late  = md.index("15:")
        assert idx_early < idx_late, "タイムラインが時刻順になっていない"

    def test_duplicate_paths_aggregated(self):
        r1 = make_record("file_edit", ts="2026-03-23T10:00:00", path="src/app.py", summary="✏️")
        r2 = make_record("file_edit", ts="2026-03-23T11:00:00", path="src/app.py", summary="✏️")
        md = build_md("2026-03-23", [r1, r2])
        # ファイル一覧で同じパスが1行にまとまっているか
        edit_section = md.split("## ✏️ 編集ファイル")[1].split("##")[0]
        assert edit_section.count("src/app.py") == 1

    def test_generated_timestamp_present(self):
        md = build_md("2026-03-23", [FILE_EDIT])
        assert "Generated:" in md


class TestLoadJsonl:
    def test_loads_valid_jsonl(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(FILE_EDIT) + "\n")
            f.write(json.dumps(COMMAND) + "\n")
            path = Path(f.name)
        records = load_jsonl(path)
        assert len(records) == 2
        path.unlink()

    def test_missing_file_returns_empty(self):
        records = load_jsonl(Path("/nonexistent/path.jsonl"))
        assert records == []

    def test_skips_malformed_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(FILE_EDIT) + "\n")
            f.write("THIS IS NOT JSON\n")
            f.write(json.dumps(COMMAND) + "\n")
            path = Path(f.name)
        records = load_jsonl(path)
        assert len(records) == 2
        path.unlink()

    def test_skips_empty_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("\n")
            f.write(json.dumps(FILE_EDIT) + "\n")
            f.write("   \n")
            path = Path(f.name)
        records = load_jsonl(path)
        assert len(records) == 1
        path.unlink()
