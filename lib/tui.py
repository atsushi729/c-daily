#!/usr/bin/env python3
"""
tui.py — curses-based TUI session browser for c-daily.

Layout:
  ┌─ Header ──────────────────────────────────────────────────────────┐
  │ Left pane (session list)  │ Right pane (message viewer)           │
  │                           │                                       │
  ├─ Status bar ──────────────────────────────────────────────────────┤

Keybindings:
  j / ↓       Move down
  k / ↑       Move up
  g / Home    Go to top
  G / End     Go to bottom
  Tab         Switch focus between list and message panes
  Enter       Open selected session (load messages)
  /           Enter filter mode
  Esc         Cancel filter / return to list
  d           Open today's daily summary in default viewer
  r           Refresh session list
  q / Q       Quit
"""
from __future__ import annotations

import curses
import platform
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Optional

# Import session_reader from the same lib directory
_LIB_DIR = Path(__file__).resolve().parent
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from constants import CLAUDE_PROJECTS_DIR  # noqa: E402
from models import MessageRecord, SessionMeta  # noqa: E402
from session_reader import (  # noqa: E402
    display_width,
    load_session_messages,
    load_sessions,
    truncate_to_width,
)

# ── Color pair constants ──────────────────────────────────────────────────────
CP_NORMAL    = 0   # default terminal colors
CP_HEADER    = 1   # header bar
CP_STATUSBAR = 2   # status bar
CP_SELECTED  = 3   # selected list item
CP_DIM       = 4   # secondary/dimmed text
CP_USER      = 5   # user message label
CP_ASSISTANT = 6   # assistant message label
CP_TOOL      = 7   # tool call/result
CP_BORDER    = 8   # pane separators and borders

LEFT_MIN = 28     # minimum left pane width
LEFT_MAX = 45     # maximum left pane width
LEFT_FRAC = 0.36  # fraction of total cols for left pane


def _init_colors() -> bool:
    """Initialize color pairs. Returns False if colors not supported."""
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(CP_HEADER,    curses.COLOR_WHITE,  curses.COLOR_BLUE)
        curses.init_pair(CP_STATUSBAR, curses.COLOR_WHITE,  curses.COLOR_BLACK)
        curses.init_pair(CP_SELECTED,  curses.COLOR_BLACK,  curses.COLOR_CYAN)
        curses.init_pair(CP_DIM,       curses.COLOR_WHITE,  -1)
        curses.init_pair(CP_USER,      curses.COLOR_CYAN,   -1)
        curses.init_pair(CP_ASSISTANT, curses.COLOR_GREEN,  -1)
        curses.init_pair(CP_TOOL,      curses.COLOR_YELLOW, -1)
        curses.init_pair(CP_BORDER,    curses.COLOR_WHITE,  -1)
        return True
    except Exception:
        return False


def _cp(pair: int) -> int:
    """Return curses attribute for a color pair, safe even if colors failed."""
    try:
        return curses.color_pair(pair)
    except Exception:
        return 0


def _safe_addstr(win, y: int, x: int, text: str, attr: int = 0) -> None:
    """Add a string to a window, ignoring out-of-bounds errors."""
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def _wrap_text(text: str, width: int, indent: int = 0) -> list[str]:
    """Wrap text to fit within `width` display columns (single O(n) pass per chunk).
    Continuation lines are indented by `indent` spaces.
    """
    if width <= 0:
        return [text] if text else []
    lines: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        available = width
        prefix = ""
        remaining = para
        while remaining:
            current_w = 0
            split_at = len(remaining)
            last_space = -1
            for i, c in enumerate(remaining):
                ea = unicodedata.east_asian_width(c)
                cw = 2 if ea in ("W", "F") else 1
                if c == " ":
                    last_space = i
                current_w += cw
                if current_w > available:
                    split_at = (last_space + 1) if last_space >= 0 else i
                    break
            if split_at == 0:
                split_at = 1  # always advance at least one char to avoid infinite loop
            lines.append(prefix + remaining[:split_at].rstrip())
            remaining = remaining[split_at:]
            prefix = " " * indent
            available = width - indent
    return lines


# ── Rendered line for the right pane ─────────────────────────────────────────

class _RenderLine:
    __slots__ = ("text", "attr")

    def __init__(self, text: str, attr: int):
        self.text = text
        self.attr = attr


def _render_messages(
    messages: list[MessageRecord], pane_width: int
) -> list[_RenderLine]:
    """
    Convert a list of MessageRecord objects into a flat list of _RenderLine,
    ready for display in the right pane.
    """
    result: list[_RenderLine] = []
    text_width = max(pane_width - 2, 10)  # 2 chars of left margin

    def add(text: str, attr: int) -> None:
        result.append(_RenderLine(text, attr))

    for msg in messages:
        if msg.role == "user":
            add("You", _cp(CP_USER) | curses.A_BOLD)
        else:
            add("Claude", _cp(CP_ASSISTANT) | curses.A_BOLD)

        for line in _wrap_text(msg.content, text_width, indent=2):
            stripped = line.lstrip()
            if stripped.startswith("[Tool:"):
                add("  " + stripped, _cp(CP_TOOL))
            elif stripped.startswith("[Result]"):
                add("  " + stripped, _cp(CP_DIM))
            else:
                add("  " + line, _cp(CP_NORMAL))
        add("", _cp(CP_NORMAL))  # blank line between messages

    return result


def _fmt_tokens(n: int) -> str:
    if n <= 0:
        return "—"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _open_file(path: Path) -> None:
    if platform.system() == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


# ── Main TUI class ────────────────────────────────────────────────────────────

class TUI:
    def __init__(
        self,
        sessions: list[SessionMeta],
        log_dir: Path,
    ):
        self.all_sessions = sessions
        self.log_dir = log_dir

        self.filter_text = ""
        self.filter_mode = False
        self.filtered: list[SessionMeta] = sessions[:]

        self.selected = 0
        self.list_scroll = 0
        self.msg_scroll = 0
        self.focus = "list"

        self._rendered: list[_RenderLine] = []
        self._rendered_for: Optional[str] = None

        self._status_msg = ""

    # ── Filter ───────────────────────────────────────────────────────────────

    def _apply_filter(self) -> None:
        q = self.filter_text.lower()
        if not q:
            self.filtered = self.all_sessions[:]
        else:
            self.filtered = [
                s for s in self.all_sessions
                if q in s.project_name.lower() or q in s.first_msg.lower()
            ]

    def _refresh_sessions(self) -> None:
        self._status_msg = "Refreshing..."
        self.all_sessions = load_sessions(claude_dir=CLAUDE_PROJECTS_DIR)
        self._apply_filter()
        self.selected = min(self.selected, max(0, len(self.filtered) - 1))
        self.list_scroll = 0
        self._rendered_for = None
        self._status_msg = f"Loaded {len(self.all_sessions)} sessions"

    # ── Entry point ──────────────────────────────────────────────────────────

    def run(self) -> None:
        curses.wrapper(self._main)

    def _main(self, stdscr: "curses._CursesWindow") -> None:
        _init_colors()
        curses.curs_set(0)
        stdscr.keypad(True)
        stdscr.timeout(500)  # used to clear transient status messages

        while True:
            rows, cols = stdscr.getmaxyx()
            if rows < 6 or cols < 40:
                stdscr.clear()
                _safe_addstr(stdscr, 0, 0, "Terminal too small (need 40x6 min)")
                stdscr.refresh()
                key = stdscr.getch()
                if key in (ord("q"), ord("Q")):
                    break
                continue

            stdscr.erase()
            left_w = min(LEFT_MAX, max(LEFT_MIN, int(cols * LEFT_FRAC)))
            self._draw(stdscr, rows, cols, left_w)
            stdscr.refresh()

            key = stdscr.getch()
            if key == -1:
                if self._status_msg:
                    self._status_msg = ""
                continue
            if self._handle_key(key, rows, cols, left_w):
                break

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _draw(
        self,
        stdscr: "curses._CursesWindow",
        rows: int,
        cols: int,
        left_w: int,
    ) -> None:
        content_rows = rows - 2   # header + status bar

        self._draw_header(stdscr, cols)
        self._draw_list(stdscr, content_rows, left_w)

        for r in range(1, rows - 1):
            _safe_addstr(stdscr, r, left_w, "|", _cp(CP_BORDER))

        right_x = left_w + 1
        right_w = cols - right_x
        self._draw_messages(stdscr, content_rows, right_x, right_w)
        self._draw_statusbar(stdscr, rows - 1, cols)

    def _draw_header(self, stdscr: "curses._CursesWindow", cols: int) -> None:
        today = date.today().isoformat()
        n = len(self.filtered)
        total = len(self.all_sessions)
        if self.filter_text:
            info = f" [{n}/{total}] filter: {self.filter_text}"
        else:
            info = f" [{total} sessions]"
        title = f" c-daily TUI — {today}{info}"
        title = truncate_to_width(title, cols - 1)
        padding = " " * max(0, cols - display_width(title) - 1)
        _safe_addstr(stdscr, 0, 0, title + padding, _cp(CP_HEADER) | curses.A_BOLD)

    def _draw_list(
        self,
        stdscr: "curses._CursesWindow",
        content_rows: int,
        left_w: int,
    ) -> None:
        if not self.filtered:
            _safe_addstr(stdscr, 2, 1, "No sessions found", _cp(CP_DIM))
            return

        visible = content_rows
        max_sel = max(0, len(self.filtered) - 1)
        self.selected = max(0, min(self.selected, max_sel))
        if self.selected < self.list_scroll:
            self.list_scroll = self.selected
        if self.selected >= self.list_scroll + visible:
            self.list_scroll = self.selected - visible + 1

        proj_w = max(8, left_w - 14)

        for i in range(visible):
            idx = i + self.list_scroll
            if idx >= len(self.filtered):
                break
            s = self.filtered[idx]
            row = i + 1  # row 0 is header

            cursor = "> " if idx == self.selected else "  "
            proj = truncate_to_width(s.project_name, proj_w)
            proj_pad = proj + " " * max(0, proj_w - display_width(proj))
            line = f"{cursor}{proj_pad} {s.fmt_start()} {s.turns:3d}t"
            line = truncate_to_width(line, left_w - 1)

            if idx == self.selected and self.focus == "list":
                attr = _cp(CP_SELECTED) | curses.A_BOLD
            elif idx == self.selected:
                attr = curses.A_BOLD
            else:
                attr = _cp(CP_NORMAL)

            _safe_addstr(stdscr, row, 0, line, attr)

    def _draw_messages(
        self,
        stdscr: "curses._CursesWindow",
        content_rows: int,
        right_x: int,
        right_w: int,
    ) -> None:
        if right_w < 10:
            return
        if not self.filtered:
            _safe_addstr(stdscr, 2, right_x + 1, "No session selected", _cp(CP_DIM))
            return

        s = self.filtered[self.selected]

        header_rows = 3
        h1 = f" {s.project_name} — {s.fmt_date()} {s.fmt_start()}"
        h2 = f" Turns: {s.turns}  Tokens: {_fmt_tokens(s.total_tokens)}  ${s.cost_usd:.4f}"
        sep = " " + "-" * max(0, right_w - 2)

        _safe_addstr(stdscr, 1, right_x,
                     truncate_to_width(h1, right_w),
                     _cp(CP_NORMAL) | curses.A_BOLD)
        _safe_addstr(stdscr, 2, right_x,
                     truncate_to_width(h2, right_w),
                     _cp(CP_DIM))
        _safe_addstr(stdscr, 3, right_x,
                     truncate_to_width(sep, right_w),
                     _cp(CP_BORDER))

        available_rows = content_rows - header_rows

        if not s.messages_loaded:
            _safe_addstr(stdscr, header_rows + 2, right_x + 1,
                         "Press Enter to load messages", _cp(CP_DIM))
            return

        if self._rendered_for != s.session_id:
            self._rendered = _render_messages(s.messages, right_w)
            self._rendered_for = s.session_id
            self.msg_scroll = 0

        total_lines = len(self._rendered)
        max_scroll = max(0, total_lines - available_rows)
        self.msg_scroll = max(0, min(self.msg_scroll, max_scroll))

        for i in range(available_rows):
            line_idx = i + self.msg_scroll
            if line_idx >= total_lines:
                break
            rl = self._rendered[line_idx]
            row = 1 + header_rows + i
            _safe_addstr(stdscr, row, right_x,
                         truncate_to_width(rl.text, right_w - 1), rl.attr)

        if total_lines > available_rows:
            pct = int(self.msg_scroll / max_scroll * 100) if max_scroll else 100
            indicator = f" {pct}%"
            _safe_addstr(
                stdscr,
                1 + header_rows + available_rows - 1,
                right_x + right_w - len(indicator) - 1,
                indicator,
                _cp(CP_DIM),
            )

    def _draw_statusbar(
        self,
        stdscr: "curses._CursesWindow",
        row: int,
        cols: int,
    ) -> None:
        if self.filter_mode:
            bar = f" / {self.filter_text}_"
        elif self._status_msg:
            bar = f" {self._status_msg}"
        else:
            bar = (
                " [q]quit  [j/k]move  [Tab]pane  [Enter]open  "
                "[/]filter  [r]reload  [d]summary"
            )
        padding = " " * max(0, cols - display_width(bar) - 1)
        _safe_addstr(stdscr, row, 0, bar + padding, _cp(CP_STATUSBAR))

    # ── Key handling ─────────────────────────────────────────────────────────

    def _handle_key(
        self,
        key: int,
        rows: int,
        cols: int,
        left_w: int,
    ) -> bool:
        """Return True to quit."""
        if self.filter_mode:
            return self._handle_filter_key(key)

        content_rows = rows - 2

        if key in (ord("q"), ord("Q")):
            return True

        elif key in (ord("j"), curses.KEY_DOWN):
            if self.focus == "list":
                self.selected = min(self.selected + 1, max(0, len(self.filtered) - 1))
                self._rendered_for = None
                self.msg_scroll = 0
            else:
                self.msg_scroll += 1

        elif key in (ord("k"), curses.KEY_UP):
            if self.focus == "list":
                self.selected = max(0, self.selected - 1)
                self._rendered_for = None
                self.msg_scroll = 0
            else:
                self.msg_scroll = max(0, self.msg_scroll - 1)

        elif key in (ord("g"), curses.KEY_HOME):
            if self.focus == "list":
                self.selected = 0
                self.list_scroll = 0
                self._rendered_for = None
                self.msg_scroll = 0
            else:
                self.msg_scroll = 0

        elif key in (ord("G"), curses.KEY_END):
            if self.focus == "list":
                self.selected = max(0, len(self.filtered) - 1)
                self._rendered_for = None
                self.msg_scroll = 0
            else:
                right_w = cols - left_w - 1
                rendered = self._get_rendered(right_w)
                self.msg_scroll = max(0, len(rendered) - (content_rows - 3))

        elif key in (ord("\t"), curses.KEY_BTAB):
            self.focus = "msg" if self.focus == "list" else "list"

        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            if self.filtered:
                s = self.filtered[self.selected]
                if not s.messages_loaded:
                    load_session_messages(s)
                    right_w = cols - left_w - 1
                    self._rendered = _render_messages(s.messages, right_w)
                    self._rendered_for = s.session_id
                    self.msg_scroll = 0
                self.focus = "msg"

        elif key == curses.KEY_RESIZE:
            self._rendered_for = None  # force re-render at new width

        elif key == ord("/"):
            self.filter_mode = True
            self.filter_text = ""

        elif key == 27:  # Escape
            if self.filter_text:
                self.filter_text = ""
                self._apply_filter()
                self.selected = 0
                self.list_scroll = 0
            self.focus = "list"

        elif key == ord("r"):
            self._refresh_sessions()

        elif key == ord("d"):
            self._open_daily_summary()

        elif key == curses.KEY_PPAGE:
            if self.focus == "list":
                self.selected = max(0, self.selected - (content_rows - 1))
            else:
                self.msg_scroll = max(0, self.msg_scroll - (content_rows - 4))

        elif key == curses.KEY_NPAGE:
            if self.focus == "list":
                self.selected = min(
                    len(self.filtered) - 1,
                    self.selected + (content_rows - 1)
                )
            else:
                self.msg_scroll += content_rows - 4

        return False

    def _handle_filter_key(self, key: int) -> bool:
        """Handle key in filter mode. Always returns False."""
        if key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            self.filter_mode = False
            self._apply_filter()
            self.selected = 0
            self.list_scroll = 0
        elif key == 27:  # Escape
            self.filter_mode = False
            self.filter_text = ""
            self._apply_filter()
            self.selected = 0
            self.list_scroll = 0
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.filter_text = self.filter_text[:-1]
        elif 32 <= key < 127:
            self.filter_text += chr(key)
        return False

    def _get_rendered(self, right_w: int) -> list[_RenderLine]:
        if not self.filtered:
            return []
        s = self.filtered[self.selected]
        if not s.messages_loaded:
            return []
        if self._rendered_for != s.session_id:
            self._rendered = _render_messages(s.messages, right_w)
            self._rendered_for = s.session_id
        return self._rendered

    def _open_daily_summary(self) -> None:
        md_file = self.log_dir / f"{date.today().isoformat()}.md"
        if md_file.exists():
            _open_file(md_file)
            self._status_msg = f"Opened {md_file.name}"
        else:
            self._status_msg = f"No summary found: {md_file.name}"


# ── Public entry point ────────────────────────────────────────────────────────

def run_tui(
    log_dir: Path,
    date_filter: Optional[str] = None,
    project_filter: Optional[str] = None,
) -> None:
    """
    Launch the TUI session browser.

    Args:
        log_dir: Path to ~/.daily-logs (for opening daily summaries).
        date_filter: Show only sessions from this date (YYYY-MM-DD).
        project_filter: Show only sessions matching this project substring.
    """
    print("Loading sessions...", end="", flush=True)
    sessions = load_sessions(
        date_filter=date_filter,
        project_filter=project_filter,
        claude_dir=CLAUDE_PROJECTS_DIR,
    )
    print(f"\r{' ' * 20}\r", end="", flush=True)

    app = TUI(sessions=sessions, log_dir=log_dir)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
