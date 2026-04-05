"""
insights/_templates.py - HTML/CSS generation for the web UI.

All functions return complete HTML strings. No external dependencies.
"""

from __future__ import annotations

import html as _html_lib
from datetime import date, datetime as _dt, timedelta
from typing import Any
from urllib.parse import quote


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #0d1117;
  --surface:   #161b22;
  --surface2:  #1c2128;
  --border:    #30363d;
  --text:      #c9d1d9;
  --muted:     #8b949e;
  --accent:    #58a6ff;
  --green:     #3fb950;

  --h0: #161b22;
  --h1: #0e4429;
  --h2: #006d32;
  --h3: #26a641;
  --h4: #39d353;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 14px;
  line-height: 1.6;
  min-height: 100vh;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Layout */
.site-header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.site-header h1 { font-size: 16px; font-weight: 600; color: var(--text); }
.site-header .back { font-size: 13px; color: var(--muted); }

main { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }

/* Section */
section { margin-bottom: 40px; }
section h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

/* Calendar heatmap */
.calendar-wrap { overflow-x: auto; }
.calendar {
  display: inline-grid;
  grid-template-rows: repeat(7, 11px);
  grid-auto-flow: column;
  grid-auto-columns: 11px;
  gap: 3px;
  padding: 4px 0 8px;
}
.day {
  width: 11px; height: 11px;
  border-radius: 2px;
  background: var(--h0);
  cursor: default;
}
.day.level-1 { background: var(--h1); }
.day.level-2 { background: var(--h2); }
.day.level-3 { background: var(--h3); }
.day.level-4 { background: var(--h4); }
.day.empty   { background: transparent; }

.legend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted);
}
.legend-cell {
  width: 11px; height: 11px; border-radius: 2px;
  background: var(--h0);
}
.legend-cell.l1 { background: var(--h1); }
.legend-cell.l2 { background: var(--h2); }
.legend-cell.l3 { background: var(--h3); }
.legend-cell.l4 { background: var(--h4); }

/* Table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 8px 12px;
  color: var(--muted);
  font-weight: 500;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.data-table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: var(--surface2); }
.data-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.data-table .muted { color: var(--muted); font-size: 12px; }

/* Stat cards */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 32px;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
}
.stat-card .label { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.stat-card .value { font-size: 22px; font-weight: 600; color: var(--text); }
.stat-card .value.green { color: var(--green); }

/* Empty state */
.empty { color: var(--muted); font-size: 13px; padding: 24px 0; }

/* Session detail */
.session-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 28px;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
}
.session-meta span { color: var(--muted); }
.session-meta span strong { color: var(--text); }

.messages { display: flex; flex-direction: column; gap: 18px; padding: 8px 0; }

.msg {
  display: flex;
  flex-direction: column;
  max-width: 72%;
}
.msg.user      { align-self: flex-end;   align-items: flex-end; }
.msg.assistant { align-self: flex-start; align-items: flex-start; }

.msg-meta {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 5px;
}
.msg-meta .ts { font-weight: 400; text-transform: none; letter-spacing: 0; opacity: 0.6; }

.msg.user      .msg-meta { color: var(--accent); }
.msg.assistant .msg-meta { color: var(--green); }

.msg-bubble {
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-x: auto;
  color: var(--text);
}

.msg.user .msg-bubble {
  background: #1a2d4a;
  border-radius: 14px 14px 4px 14px;
  border: 1px solid #2a4a6e;
}
.msg.assistant .msg-bubble {
  background: var(--surface);
  border-radius: 14px 14px 14px 4px;
  border: 1px solid var(--border);
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROLE_LABELS = {"user": "You", "assistant": "Claude", "tool_result": "Tool Result"}


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html_lib.escape(title)} — c-daily</title>
  <style>{_CSS}</style>
</head>
<body>
{body}
</body>
</html>"""


def _fmt_tokens(n: int) -> str:
    return f"{n:,}" if n else "—"


def _fmt_cost(v: float) -> str:
    return f"${v:.4f}"


def _cost_to_level(cost: float) -> int:
    if cost <= 0:
        return 0
    if cost < 0.01:
        return 1
    if cost < 0.05:
        return 2
    if cost < 0.20:
        return 3
    return 4


# ---------------------------------------------------------------------------
# Calendar heatmap
# ---------------------------------------------------------------------------

def _build_calendar(heatmap: dict[str, float], days: int = 90) -> str:
    today = date.today()
    end = today
    start = end - timedelta(days=days - 1)

    # Align calendar_start to Sunday (Python weekday: 0=Mon, 6=Sun)
    days_since_sunday = (start.weekday() + 1) % 7
    cal_start = start - timedelta(days=days_since_sunday)

    # Align cal_end to Saturday
    days_to_saturday = (5 - today.weekday()) % 7
    cal_end = today + timedelta(days=days_to_saturday)

    cells: list[str] = []
    current = cal_start
    while current <= cal_end:
        if current < start or current > today:
            cells.append('<div class="day empty"></div>')
        else:
            ds = current.isoformat()
            cost = heatmap.get(ds, 0.0)
            level = _cost_to_level(cost)
            tip = f"{ds}: {_fmt_cost(cost)}" if cost > 0 else ds
            cells.append(f'<div class="day level-{level}" title="{tip}"></div>')
        current += timedelta(days=1)

    legend = (
        '<div class="legend">'
        '<span>Less</span>'
        '<div class="legend-cell"></div>'
        '<div class="legend-cell l1"></div>'
        '<div class="legend-cell l2"></div>'
        '<div class="legend-cell l3"></div>'
        '<div class="legend-cell l4"></div>'
        '<span>More</span>'
        '</div>'
    )

    return (
        '<div class="calendar-wrap">'
        f'<div class="calendar">{"".join(cells)}</div>'
        f'{legend}'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

def index_html(heatmap: dict[str, float], projects: list[dict[str, Any]]) -> str:
    calendar_html = _build_calendar(heatmap)

    if projects:
        rows = []
        for p in projects:
            name = p["name"]
            href = f"/project/{quote(name)}"
            rows.append(
                f'<tr>'
                f'<td><a href="{href}">{_html_lib.escape(name)}</a></td>'
                f'<td class="num">{p["sessions"]}</td>'
                f'<td class="num">{p["turns"]}</td>'
                f'<td class="num">{p["files_edited"]}</td>'
                f'<td class="num">{p["commands_run"]}</td>'
                f'<td class="num">{_fmt_tokens(p["total_tokens"])}</td>'
                f'<td class="num">{_fmt_cost(p["cost_usd"])}</td>'
                f'<td class="muted">{p["last_active"]}</td>'
                f'</tr>'
            )
        table = (
            '<table class="data-table">'
            '<thead><tr>'
            '<th>Project</th><th>Sessions</th><th>Turns</th>'
            '<th>Files Edited</th><th>Commands</th>'
            '<th>Tokens</th><th>Cost</th><th>Last Active</th>'
            '</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody>'
            '</table>'
        )
    else:
        table = '<p class="empty">No projects found in ~/.claude/projects/</p>'

    body = """
<header class="site-header">
  <h1>c-daily insights</h1>
</header>
<main>
  <section>
    <h2>Activity — last 90 days</h2>
    {calendar}
  </section>
  <section>
    <h2>Projects</h2>
    {table}
  </section>
</main>""".format(calendar=calendar_html, table=table)

    return _page("Overview", body)


# ---------------------------------------------------------------------------
# Project detail page
# ---------------------------------------------------------------------------

def project_html(detail: dict[str, Any]) -> str:
    name = detail["name"]
    st = detail["stats"]

    cards = (
        '<div class="stat-cards">'
        f'<div class="stat-card"><div class="label">Sessions</div><div class="value">{st["sessions"]}</div></div>'
        f'<div class="stat-card"><div class="label">Turns</div><div class="value">{st["turns"]}</div></div>'
        f'<div class="stat-card"><div class="label">Files Edited</div><div class="value">{st["files_edited"]}</div></div>'
        f'<div class="stat-card"><div class="label">Commands Run</div><div class="value">{st["commands_run"]}</div></div>'
        f'<div class="stat-card"><div class="label">Tokens</div><div class="value">{_fmt_tokens(st["total_tokens"])}</div></div>'
        f'<div class="stat-card"><div class="label">Total Cost</div><div class="value green">{_fmt_cost(st["cost_usd"])}</div></div>'
        '</div>'
    )

    if detail["sessions"]:
        rows = []
        for s in detail["sessions"]:
            href = f'/project/{quote(name)}/session/{s["session_id"]}'
            first_msg = _html_lib.escape(s["first_msg"])
            rows.append(
                f'<tr style="cursor:pointer" onclick="location.href=\'{_html_lib.escape(href)}\'">'
                f'<td>{s["date"]}</td>'
                f'<td>{s["time"]}</td>'
                f'<td class="muted"><a href="{href}">{first_msg}</a></td>'
                f'<td class="num">{s["turns"]}</td>'
                f'<td class="num">{s["files_edited"]}</td>'
                f'<td class="num">{s["commands_run"]}</td>'
                f'<td class="num">{_fmt_tokens(s["total_tokens"])}</td>'
                f'<td class="num">{_fmt_cost(s["cost_usd"])}</td>'
                f'</tr>'
            )
        table = (
            '<table class="data-table">'
            '<thead><tr>'
            '<th>Date</th><th>Time</th><th>First Message</th>'
            '<th>Turns</th><th>Files</th><th>Cmds</th>'
            '<th>Tokens</th><th>Cost</th>'
            '</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody>'
            '</table>'
        )
    else:
        table = '<p class="empty">No sessions found.</p>'

    body = """
<header class="site-header">
  <a class="back" href="/">← All projects</a>
  <h1>{name}</h1>
</header>
<main>
  {cards}
  <section>
    <h2>Sessions</h2>
    {table}
  </section>
</main>""".format(name=_html_lib.escape(name), cards=cards, table=table)

    return _page(_html_lib.escape(name), body)


# ---------------------------------------------------------------------------
# Session detail page
# ---------------------------------------------------------------------------

def session_html(project_name: str, meta: "Any") -> str:
    """Render a full session transcript as a chat view."""
    from models import MessageRecord  # local import to keep this module light

    local_dt = None
    if meta.start_time is not None:
        dt = meta.start_time
        if dt.tzinfo:
            dt = dt.astimezone().replace(tzinfo=None)
        local_dt = dt

    date_str = local_dt.strftime("%Y-%m-%d") if local_dt else "—"
    time_str = local_dt.strftime("%H:%M") if local_dt else "—"
    project_href = f"/project/{quote(project_name)}"

    session_meta_html = (
        '<div class="session-meta">'
        f'<span>Date: <strong>{date_str} {time_str}</strong></span>'
        f'<span>Turns: <strong>{meta.turns}</strong></span>'
        f'<span>Tokens: <strong>{_fmt_tokens(meta.total_tokens)}</strong></span>'
        f'<span>Cost: <strong>{_fmt_cost(meta.cost_usd)}</strong></span>'
        '</div>'
    )

    msg_blocks: list[str] = []
    for msg in meta.messages:
        role = msg.role
        if role == "tool_result":
            continue
        label = _ROLE_LABELS.get(role, role)
        ts_str = ""
        if msg.timestamp:
            try:
                t = _dt.fromisoformat(msg.timestamp.replace("Z", "+00:00"))
                t = t.astimezone().replace(tzinfo=None)
                ts_str = t.strftime("%H:%M:%S")
            except Exception:
                pass
        ts_html = f'<span class="ts">{ts_str}</span>' if ts_str else ""
        body = _html_lib.escape(msg.content)
        msg_blocks.append(
            f'<div class="msg {role}">'
            f'<div class="msg-meta"><span>{label}</span>{ts_html}</div>'
            f'<div class="msg-bubble">{body}</div>'
            f'</div>'
        )

    messages_html = (
        f'<div class="messages">{"".join(msg_blocks)}</div>'
        if msg_blocks
        else '<p class="empty">No messages found.</p>'
    )

    body = """
<header class="site-header">
  <a class="back" href="{project_href}">← {project_name}</a>
  <h1>{date_str} {time_str}</h1>
</header>
<main>
  {meta}
  <section>
    <h2>Conversation</h2>
    {messages}
  </section>
</main>""".format(
        project_href=project_href,
        project_name=_html_lib.escape(project_name),
        date_str=date_str,
        time_str=time_str,
        meta=session_meta_html,
        messages=messages_html,
    )

    return _page(f"{_html_lib.escape(project_name)} / {date_str}", body)


# ---------------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------------

def not_found_html(path: str) -> str:
    body = f"""
<header class="site-header">
  <a class="back" href="/">← Back</a>
  <h1>Not found</h1>
</header>
<main>
  <p class="empty">No page at <code>{path}</code></p>
</main>"""
    return _page("Not found", body)
