"""
tests/test_aggregate.py
Unit tests for aggregate.py
"""
import json
import sys
import tempfile
from pathlib import Path

# Add lib/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from aggregate import build_md, load_jsonl, fmt_time, fmt_tokens


# --- Fixtures ---

def make_session(ts="2026-03-23T10:00:00", **kwargs):
    base = {
        "type":         "session_summary",
        "timestamp":    ts,
        "project_name": "my-project",
        "first_msg":    "Fix the login bug",
        "turns":        6,
        "cost_usd":     0.0100,
        "total_tokens": 5000,
    }
    base.update(kwargs)
    return base


SESSION_A = make_session(
    ts="2026-03-23T10:00:00",
    first_msg="Refactoring auth module",
    turns=12, cost_usd=0.0231, total_tokens=15420,
    project_name="my-app",
)
SESSION_B = make_session(
    ts="2026-03-23T17:42:00",
    first_msg="テストのリファクタリングをしたい",
    turns=8, cost_usd=0.0148, total_tokens=9850,
    project_name="my-app",
)
SESSION_WITH_DECISION = make_session(
    ts="2026-03-23T14:00:00",
    first_msg="Design new API",
    project_name="api-service",
    decision_summary={
        "problem": "Current API is not RESTful",
        "approaches": ["Rewrite from scratch", "Incremental refactor"],
        "selected": "Incremental refactor to avoid breaking changes",
    },
)


# --- Tests ---

class TestFmtTime:
    def test_valid_iso(self):
        assert fmt_time("2026-03-23T10:23:11") == "10:23"

    def test_invalid_returns_original(self):
        assert fmt_time("not-a-date") == "not-a-date"

    def test_empty_string(self):
        assert fmt_time("") == ""


class TestFmtTokens:
    def test_zero_returns_dash(self):
        assert fmt_tokens(0) == "—"

    def test_none_returns_dash(self):
        assert fmt_tokens(None) == "—"

    def test_formats_with_comma(self):
        assert fmt_tokens(15420) == "15,420"

    def test_small_number(self):
        assert fmt_tokens(500) == "500"


class TestBuildMd:
    def test_empty_records(self):
        md = build_md("2026-03-23", [])
        assert "2026-03-23" in md
        assert "No sessions for this day." in md

    def test_header_contains_date(self):
        md = build_md("2026-03-23", [SESSION_A])
        assert "# Daily Log — 2026-03-23" in md

    def test_summary_session_count(self):
        md = build_md("2026-03-23", [SESSION_A, SESSION_B])
        assert "| Sessions | 2 |" in md

    def test_summary_total_cost(self):
        md = build_md("2026-03-23", [SESSION_A, SESSION_B])
        # 0.0231 + 0.0148 = 0.0379
        assert "0.0379" in md

    def test_summary_total_tokens(self):
        md = build_md("2026-03-23", [SESSION_A, SESSION_B])
        # 15420 + 9850 = 25270
        assert "25,270" in md

    def test_sessions_table_header(self):
        md = build_md("2026-03-23", [SESSION_A])
        assert "| Time | Project | Session | Tokens |" in md

    def test_sessions_table_row(self):
        md = build_md("2026-03-23", [SESSION_A])
        assert "my-app" in md
        assert "Refactoring auth module" in md
        assert "15,420" in md

    def test_sessions_sorted_by_time(self):
        md = build_md("2026-03-23", [SESSION_B, SESSION_A])
        idx_a = md.index("10:00")
        idx_b = md.index("17:42")
        assert idx_a < idx_b, "Sessions are not sorted by time"

    def test_no_decision_log_when_absent(self):
        md = build_md("2026-03-23", [SESSION_A, SESSION_B])
        assert "## Decision Log" not in md

    def test_decision_log_present(self):
        md = build_md("2026-03-23", [SESSION_WITH_DECISION])
        assert "## Decision Log" in md
        assert "Current API is not RESTful" in md
        assert "Rewrite from scratch" in md
        assert "Incremental refactor to avoid breaking changes" in md

    def test_decision_log_shows_project(self):
        md = build_md("2026-03-23", [SESSION_WITH_DECISION])
        assert "api-service" in md

    def test_generated_timestamp_present(self):
        md = build_md("2026-03-23", [SESSION_A])
        assert "Generated:" in md

    def test_ignores_non_session_records(self):
        other = {"type": "file_edit", "timestamp": "2026-03-23T09:00:00", "path": "foo.py"}
        md = build_md("2026-03-23", [other, SESSION_A])
        assert "foo.py" not in md
        assert "Refactoring auth module" in md


class TestLoadJsonl:
    def test_loads_valid_jsonl(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(SESSION_A) + "\n")
            f.write(json.dumps(SESSION_B) + "\n")
            path = Path(f.name)
        records = load_jsonl(path)
        assert len(records) == 2
        path.unlink()

    def test_missing_file_returns_empty(self):
        records = load_jsonl(Path("/nonexistent/path.jsonl"))
        assert records == []

    def test_skips_malformed_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(SESSION_A) + "\n")
            f.write("THIS IS NOT JSON\n")
            f.write(json.dumps(SESSION_B) + "\n")
            path = Path(f.name)
        records = load_jsonl(path)
        assert len(records) == 2
        path.unlink()

    def test_skips_empty_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("\n")
            f.write(json.dumps(SESSION_A) + "\n")
            f.write("   \n")
            path = Path(f.name)
        records = load_jsonl(path)
        assert len(records) == 1
        path.unlink()
