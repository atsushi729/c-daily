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

import contextlib
import curses
import platform
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

# Import session_reader from the same lib directory
_LIB_DIR = Path(__file__).resolve().parent
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from constants import CLAUDE_PROJECTS_DIR  # noqa: E402
from models import MessageRecord, ProjectItem, SessionMeta  # noqa: E402
from session_reader import (  # noqa: E402
    load_session_messages,
    load_sessions,
)

# ── Color pair constants ──────────────────────────────────────────────────────
CP_NORMAL = 0  # default terminal colors
CP_HEADER = 1  # header bar
CP_STATUSBAR = 2  # status bar
CP_SELECTED = 3  # selected list item
CP_DIM = 4  # secondary/dimmed text
CP_USER = 5  # user message label
CP_ASSISTANT = 6  # assistant message label
CP_TOOL = 7  # tool call/result
CP_BORDER = 8  # pane separators and borders
CP_USER_TEXT = 9   # user message body text
CP_ASST_TEXT = 10  # assistant message body text

LEFT_MIN = 28  # minimum left pane width
LEFT_MAX = 45  # maximum left pane width
LEFT_FRAC = 0.36  # fraction of total cols for left pane


def _init_colors() -> bool:
    """Initialize color pairs. Returns False if colors not supported."""
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(CP_HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(CP_STATUSBAR, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(CP_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(CP_DIM, curses.COLOR_WHITE, -1)
        curses.init_pair(CP_USER, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(CP_ASSISTANT, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(CP_TOOL, curses.COLOR_YELLOW, -1)
        curses.init_pair(CP_BORDER, curses.COLOR_WHITE, -1)
        curses.init_pair(CP_USER_TEXT, curses.COLOR_CYAN, -1)
        curses.init_pair(CP_ASST_TEXT, curses.COLOR_WHITE, -1)
        return True
    except Exception:
        return False


def _cp(pair: int) -> int:
    """Return curses attribute for a color pair, safe even if colors failed."""
    try:
        return curses.color_pair(pair)
    except Exception:
        return 0


def _safe_addstr(win: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
    """Add a string to a window, ignoring out-of-bounds errors."""
    with contextlib.suppress(curses.error):
        win.addstr(y, x, text, attr)


def _draw_header_line(stdscr: curses.window, title: str, cols: int) -> None:
    title = truncate_to_width(title, cols - 1)
    padding = " " * max(0, cols - display_width(title) - 1)
    _safe_addstr(stdscr, 0, 0, title + padding, _cp(CP_HEADER) | curses.A_BOLD)


def _draw_statusbar_line(stdscr: curses.window, row: int, cols: int, bar: str) -> None:
    padding = " " * max(0, cols - display_width(bar) - 1)
    _safe_addstr(stdscr, row, 0, bar + padding, _cp(CP_STATUSBAR))


def _char_width(c: str) -> int:
    ea = unicodedata.east_asian_width(c)
    return 2 if ea in ("W", "F") else 1


def display_width(s: str) -> int:
    """Return terminal display width of a string, counting CJK chars as 2."""
    if not any(ord(c) >= 128 for c in s):
        return len(s)
    return sum(_char_width(c) for c in s)


def truncate_to_width(s: str, max_width: int) -> str:
    """Truncate string so its display width does not exceed max_width."""
    result: list[str] = []
    current = 0
    for c in s:
        cw = _char_width(c)
        if current + cw > max_width:
            break
        result.append(c)
        current += cw
    return "".join(result)


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


def _render_messages(messages: list[MessageRecord], pane_width: int) -> list[_RenderLine]:
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
            label_attr = _cp(CP_USER) | curses.A_BOLD
            text_attr = _cp(CP_USER_TEXT)
            label_core = " You "
            show_label = True
        elif msg.role == "assistant":
            label_attr = _cp(CP_ASSISTANT) | curses.A_BOLD
            text_attr = _cp(CP_ASST_TEXT)
            label_core = " Claude "
            show_label = True
        else:
            text_attr = _cp(CP_DIM)
            show_label = False

        if show_label:
            # Pad to pane width so the background color fills the entire row
            label = label_core + " " * max(0, pane_width - len(label_core) - 1)
            add(label, label_attr)

        for line in _wrap_text(msg.content, text_width - 2, indent=0):
            stripped = line.lstrip()
            if stripped.startswith("[Tool:"):
                add("│ " + stripped, _cp(CP_TOOL))
            elif stripped.startswith("[Result]"):
                add("│ " + stripped, _cp(CP_DIM))
            else:
                add("│ " + line, text_attr)
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
        self._rendered_for: str | None = None

        self._status_msg = ""

    # ── Filter ───────────────────────────────────────────────────────────────

    def _apply_filter(self) -> None:
        q = self.filter_text.lower()
        if not q:
            self.filtered = self.all_sessions[:]
        else:
            self.filtered = [
                s
                for s in self.all_sessions
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

    def _main(self, stdscr: curses.window) -> None:
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
        stdscr: curses.window,
        rows: int,
        cols: int,
        left_w: int,
    ) -> None:
        content_rows = rows - 2  # header + status bar

        self._draw_header(stdscr, cols)
        self._draw_list(stdscr, content_rows, left_w)

        for r in range(1, rows - 1):
            _safe_addstr(stdscr, r, left_w, "|", _cp(CP_BORDER))

        right_x = left_w + 1
        right_w = cols - right_x
        self._draw_messages(stdscr, content_rows, right_x, right_w)
        self._draw_statusbar(stdscr, rows - 1, cols)

    def _draw_header(self, stdscr: curses.window, cols: int) -> None:
        today = date.today().isoformat()
        n = len(self.filtered)
        total = len(self.all_sessions)
        if self.filter_text:
            info = f" [{n}/{total}] filter: {self.filter_text}"
        else:
            info = f" [{total} sessions]"
        _draw_header_line(stdscr, f" c-daily TUI — {today}{info}", cols)

    def _draw_list(
        self,
        stdscr: curses.window,
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
            title = s.first_msg or s.project_name
            proj = truncate_to_width(title, proj_w)
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
        stdscr: curses.window,
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
        session_title = s.first_msg or s.project_name
        h1 = f" {session_title} — {s.fmt_date()} {s.fmt_start()}"
        h2 = f" Turns: {s.turns}  Tokens: {_fmt_tokens(s.total_tokens)}  ${s.cost_usd:.4f}"
        sep = " " + "-" * max(0, right_w - 2)

        _safe_addstr(
            stdscr, 1, right_x, truncate_to_width(h1, right_w), _cp(CP_NORMAL) | curses.A_BOLD
        )
        _safe_addstr(stdscr, 2, right_x, truncate_to_width(h2, right_w), _cp(CP_DIM))
        _safe_addstr(stdscr, 3, right_x, truncate_to_width(sep, right_w), _cp(CP_BORDER))

        available_rows = content_rows - header_rows

        if not s.messages_loaded:
            _safe_addstr(
                stdscr, header_rows + 2, right_x + 1, "Press Enter to load messages", _cp(CP_DIM)
            )
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
            _safe_addstr(stdscr, row, right_x, truncate_to_width(rl.text, right_w - 1), rl.attr)

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
        stdscr: curses.window,
        row: int,
        cols: int,
    ) -> None:
        if self.filter_mode:
            bar = f" / {self.filter_text}_"
        elif self._status_msg:
            bar = f" {self._status_msg}"
        elif self.focus == "msg":
            bar = " [q]quit  [j/k]scroll  [Esc/Tab]back to list  [/]filter  [r]reload  [d]summary"
        else:
            bar = " [q]quit  [j/k]move  [Tab]pane  [Enter]open  [/]filter  [r]reload  [d]summary"
        _draw_statusbar_line(stdscr, row, cols, bar)

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
                self.selected = min(len(self.filtered) - 1, self.selected + (content_rows - 1))
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


# ── Project browser ──────────────────────────────────────────────────────────


class ProjectTUI:
    """Two-pane project browser.

    Left pane: projects sorted by cost (descending).
    Right pane: sessions for the selected project.
    Enter: exits and signals the caller to open a session browser for that project.
    """

    def __init__(self, sessions: list[SessionMeta]):
        grouped: dict[str, list[SessionMeta]] = {}
        for s in sessions:
            grouped.setdefault(s.project_name, []).append(s)

        self.projects: list[ProjectItem] = []
        for name, slist in grouped.items():
            slist_sorted = sorted(
                slist,
                key=lambda x: (x.start_time or datetime.min).replace(tzinfo=None),
                reverse=True,
            )
            self.projects.append(
                ProjectItem(
                    name=name,
                    session_count=len(slist),
                    turns=sum(s.turns for s in slist),
                    total_tokens=sum(s.total_tokens for s in slist),
                    cost_usd=sum(s.cost_usd for s in slist),
                    sessions=slist_sorted,
                )
            )
        self.projects.sort(key=lambda p: p.cost_usd, reverse=True)

        self.selected = 0
        self.scroll = 0
        self._selected_project: ProjectItem | None = None

    def run(self) -> ProjectItem | None:
        curses.wrapper(self._main)
        return self._selected_project

    def _main(self, stdscr: curses.window) -> None:
        _init_colors()
        curses.curs_set(0)
        stdscr.keypad(True)

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
            if key in (ord("q"), ord("Q")):
                break
            elif key in (ord("j"), curses.KEY_DOWN):
                self.selected = min(self.selected + 1, max(0, len(self.projects) - 1))
            elif key in (ord("k"), curses.KEY_UP):
                self.selected = max(0, self.selected - 1)
            elif key in (ord("g"), curses.KEY_HOME):
                self.selected = 0
                self.scroll = 0
            elif key in (ord("G"), curses.KEY_END):
                self.selected = max(0, len(self.projects) - 1)
            elif key == curses.KEY_PPAGE:
                self.selected = max(0, self.selected - (rows - 3))
            elif key == curses.KEY_NPAGE:
                self.selected = min(len(self.projects) - 1, self.selected + (rows - 3))
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")) and self.projects:
                self._selected_project = self.projects[self.selected]
                break

    def _draw(self, stdscr: curses.window, rows: int, cols: int, left_w: int) -> None:
        content_rows = rows - 2
        self._draw_header(stdscr, cols)
        self._draw_project_list(stdscr, content_rows, left_w)
        for r in range(1, rows - 1):
            _safe_addstr(stdscr, r, left_w, "|", _cp(CP_BORDER))
        right_x = left_w + 1
        right_w = cols - right_x
        self._draw_session_list(stdscr, content_rows, right_x, right_w)
        self._draw_statusbar(stdscr, rows - 1, cols)

    def _draw_header(self, stdscr: curses.window, cols: int) -> None:
        today = date.today().isoformat()
        _draw_header_line(
            stdscr, f" c-daily TUI — Projects — {today}  [{len(self.projects)} projects]", cols
        )

    def _draw_project_list(self, stdscr: curses.window, content_rows: int, left_w: int) -> None:
        if not self.projects:
            _safe_addstr(stdscr, 2, 1, "No projects found", _cp(CP_DIM))
            return

        visible = content_rows
        max_sel = max(0, len(self.projects) - 1)
        self.selected = max(0, min(self.selected, max_sel))
        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + visible:
            self.scroll = self.selected - visible + 1

        name_w = max(8, left_w - 16)

        for i in range(visible):
            idx = i + self.scroll
            if idx >= len(self.projects):
                break
            p = self.projects[idx]
            row = i + 1
            cursor = "> " if idx == self.selected else "  "
            name = truncate_to_width(p.name, name_w)
            name_pad = name + " " * max(0, name_w - display_width(name))
            line = f"{cursor}{name_pad} {p.session_count:3d}s ${p.cost_usd:.3f}"
            line = truncate_to_width(line, left_w - 1)
            attr = _cp(CP_SELECTED) | curses.A_BOLD if idx == self.selected else _cp(CP_NORMAL)
            _safe_addstr(stdscr, row, 0, line, attr)

    def _draw_session_list(
        self, stdscr: curses.window, content_rows: int, right_x: int, right_w: int
    ) -> None:
        if not self.projects or right_w < 10:
            return
        p = self.projects[self.selected]

        h1 = f" {p.name}  —  {p.session_count} sessions  ${p.cost_usd:.4f}"
        h2 = f" Turns: {p.turns}  Tokens: {_fmt_tokens(p.total_tokens)}"
        sep = " " + "-" * max(0, right_w - 2)
        _safe_addstr(
            stdscr, 1, right_x, truncate_to_width(h1, right_w), _cp(CP_NORMAL) | curses.A_BOLD
        )
        _safe_addstr(stdscr, 2, right_x, truncate_to_width(h2, right_w), _cp(CP_DIM))
        _safe_addstr(stdscr, 3, right_x, truncate_to_width(sep, right_w), _cp(CP_BORDER))

        available = content_rows - 3
        for i, s in enumerate(p.sessions[:available]):
            preview = s.first_msg.replace("\n", " ").replace("\r", " ")
            line = f" {s.fmt_date()} {s.fmt_start()}  {s.turns:3d}t  {preview}"
            _safe_addstr(
                stdscr, 4 + i, right_x, truncate_to_width(line, right_w - 1), _cp(CP_NORMAL)
            )

    def _draw_statusbar(self, stdscr: curses.window, row: int, cols: int) -> None:
        _draw_statusbar_line(
            stdscr, row, cols, " [q]quit  [j/k]move  [Enter]open sessions  [g/G]top/bottom  (session browser: [q]back here)"
        )


# ── Daily summary browser ─────────────────────────────────────────────────────


class DailyTUI:
    """Two-pane daily summary browser.

    Left pane: list of daily log files (YYYY-MM-DD.md), newest first.
    Right pane: rendered content of the selected file.
    Tab switches focus; j/k navigates; Enter opens the file externally.
    """

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.files: list[Path] = sorted(log_dir.glob("????-??-??.md"), reverse=True)

        self.selected = 0
        self.scroll = 0
        self.content_scroll = 0
        self.focus = "list"
        self._content_cache: dict[str, list[str]] = {}

    def run(self) -> None:
        curses.wrapper(self._main)

    def _main(self, stdscr: curses.window) -> None:
        _init_colors()
        curses.curs_set(0)
        stdscr.keypad(True)
        stdscr.timeout(500)

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
                continue
            if key in (ord("q"), ord("Q")):
                break
            elif key in (ord("\t"), curses.KEY_BTAB):
                self.focus = "content" if self.focus == "list" else "list"
            elif key in (ord("j"), curses.KEY_DOWN):
                if self.focus == "list":
                    self.selected = min(self.selected + 1, max(0, len(self.files) - 1))
                    self.content_scroll = 0
                else:
                    self.content_scroll += 1
            elif key in (ord("k"), curses.KEY_UP):
                if self.focus == "list":
                    self.selected = max(0, self.selected - 1)
                    self.content_scroll = 0
                else:
                    self.content_scroll = max(0, self.content_scroll - 1)
            elif key in (ord("g"), curses.KEY_HOME):
                if self.focus == "list":
                    self.selected = 0
                    self.scroll = 0
                    self.content_scroll = 0
                else:
                    self.content_scroll = 0
            elif key in (ord("G"), curses.KEY_END):
                if self.focus == "list":
                    self.selected = max(0, len(self.files) - 1)
                    self.content_scroll = 0
            elif key == curses.KEY_PPAGE:
                if self.focus == "list":
                    self.selected = max(0, self.selected - (rows - 3))
                else:
                    self.content_scroll = max(0, self.content_scroll - (rows - 5))
            elif key == curses.KEY_NPAGE:
                if self.focus == "list":
                    self.selected = min(len(self.files) - 1, self.selected + (rows - 3))
                else:
                    self.content_scroll += rows - 5
            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                if self.files:
                    _open_file(self.files[self.selected])
            elif key == curses.KEY_RESIZE:
                self._content_cache.clear()

    def _get_content_lines(self, path: Path, width: int) -> list[str]:
        key = f"{path}:{width}"
        if key not in self._content_cache:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                text = "(Unable to read file)"
            lines: list[str] = []
            for raw_line in text.split("\n"):
                wrapped = _wrap_text(raw_line, width - 2)
                lines.extend(wrapped if wrapped else [""])
            self._content_cache[key] = lines
        return self._content_cache[key]

    def _draw(self, stdscr: curses.window, rows: int, cols: int, left_w: int) -> None:
        content_rows = rows - 2
        self._draw_header(stdscr, cols)
        self._draw_file_list(stdscr, content_rows, left_w)
        for r in range(1, rows - 1):
            _safe_addstr(stdscr, r, left_w, "|", _cp(CP_BORDER))
        right_x = left_w + 1
        right_w = cols - right_x
        self._draw_content(stdscr, content_rows, right_x, right_w)
        self._draw_statusbar(stdscr, rows - 1, cols)

    def _draw_header(self, stdscr: curses.window, cols: int) -> None:
        today = date.today().isoformat()
        _draw_header_line(
            stdscr,
            f" c-daily TUI — Daily Summaries — {today}  [{len(self.files)} files]",
            cols,
        )

    def _draw_file_list(self, stdscr: curses.window, content_rows: int, left_w: int) -> None:
        if not self.files:
            _safe_addstr(stdscr, 2, 1, "No daily logs found", _cp(CP_DIM))
            return

        visible = content_rows
        max_sel = max(0, len(self.files) - 1)
        self.selected = max(0, min(self.selected, max_sel))
        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + visible:
            self.scroll = self.selected - visible + 1

        for i in range(visible):
            idx = i + self.scroll
            if idx >= len(self.files):
                break
            f = self.files[idx]
            row = i + 1
            cursor = "> " if idx == self.selected else "  "
            date_str = f.stem
            try:
                size = f.stat().st_size
                size_str = f"{size // 1024}K" if size >= 1024 else f"{size}B"
            except OSError:
                size_str = "?"
            line = f"{cursor}{date_str}  {size_str:>6}"
            line = truncate_to_width(line, left_w - 1)
            is_sel = idx == self.selected
            if is_sel and self.focus == "list":
                attr = _cp(CP_SELECTED) | curses.A_BOLD
            elif is_sel:
                attr = curses.A_BOLD
            else:
                attr = _cp(CP_NORMAL)
            _safe_addstr(stdscr, row, 0, line, attr)

    def _draw_content(
        self, stdscr: curses.window, content_rows: int, right_x: int, right_w: int
    ) -> None:
        if not self.files or right_w < 10:
            return

        f = self.files[self.selected]
        lines = self._get_content_lines(f, right_w)

        total = len(lines)
        available = content_rows - 1
        max_scroll = max(0, total - available)
        self.content_scroll = max(0, min(self.content_scroll, max_scroll))

        for i in range(available):
            line_idx = i + self.content_scroll
            if line_idx >= total:
                break
            line = lines[line_idx]
            if line.startswith("# "):
                attr = _cp(CP_USER) | curses.A_BOLD
            elif line.startswith("## "):
                attr = _cp(CP_ASSISTANT) | curses.A_BOLD
            elif line.startswith("### "):
                attr = _cp(CP_TOOL) | curses.A_BOLD
            elif line.startswith("|"):
                attr = _cp(CP_DIM)
            else:
                attr = _cp(CP_NORMAL)
            _safe_addstr(stdscr, 1 + i, right_x, truncate_to_width(" " + line, right_w - 1), attr)

        if total > available and max_scroll:
            pct = int(self.content_scroll / max_scroll * 100)
            indicator = f" {pct}%"
            _safe_addstr(
                stdscr,
                available,
                right_x + right_w - len(indicator) - 1,
                indicator,
                _cp(CP_DIM),
            )

    def _draw_statusbar(self, stdscr: curses.window, row: int, cols: int) -> None:
        _draw_statusbar_line(
            stdscr, row, cols, " [q]quit  [j/k]move  [Tab]pane  [Enter]open  [g/G]top/bottom"
        )


# ── Public entry point ────────────────────────────────────────────────────────


def run_tui(
    log_dir: Path,
    date_filter: str | None = None,
    project_filter: str | None = None,
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
    with contextlib.suppress(KeyboardInterrupt):
        app.run()


def run_tui_project(log_dir: Path) -> None:
    """Launch the project browser; Enter opens a session browser for the chosen project."""
    print("Loading sessions...", end="", flush=True)
    sessions = load_sessions(claude_dir=CLAUDE_PROJECTS_DIR)
    print(f"\r{' ' * 20}\r", end="", flush=True)

    ptui = ProjectTUI(sessions=sessions)
    while True:
        ptui._selected_project = None
        selected = None
        with contextlib.suppress(KeyboardInterrupt):
            selected = ptui.run()

        if selected is None:
            break

        app = TUI(sessions=selected.sessions, log_dir=log_dir)
        with contextlib.suppress(KeyboardInterrupt):
            app.run()
        # After session browser exits, loop back to project browser


def run_tui_daily(log_dir: Path) -> None:
    """Launch the daily summary browser."""
    dtui = DailyTUI(log_dir=log_dir)
    with contextlib.suppress(KeyboardInterrupt):
        dtui.run()
