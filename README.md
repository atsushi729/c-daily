# cdl

A CLI tool that automatically records Claude Code sessions and generates daily Markdown reports.

[![CI](https://github.com/atsushi729/c-daily/actions/workflows/ci.yml/badge.svg)](https://github.com/atsushi729/c-daily/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

> Demo video coming soon

## Overview

Just use Claude Code as usual. `cdl` captures each session automatically via a Stop hook, and generates a Markdown report every night at 23:58 via launchd.

- Zero-effort recording — no manual steps after setup
- No external dependencies — Python standard library only
- Browsable via TUI or web UI

## Commands

| Command | Description |
|---|---|
| `cdl install` | Initial setup — registers Claude Code hook and launchd |
| `cdl today` | Generate and open today's report |
| `cdl show [DATE]` | Generate and open report for a specific date (e.g. `2026-04-07`) |
| `cdl tui` | Browse sessions in a terminal UI |
| `cdl tui session [DATE]` | Browse sessions filtered by date |
| `cdl tui project` | Browse by project |
| `cdl tui daily` | Browse daily summaries |
| `cdl web` | Open web UI in browser |
| `cdl web --port PORT` | Open web UI on a specific port (default: 8765) |
| `cdl status` | Check hook and launchd status |
| `cdl raw [DATE]` | Print raw JSONL log |
| `cdl uninstall` | Remove hooks and launchd (log data is preserved) |
| `cdl version` | Show version |

Short aliases: `t` → `tui`, `w` → `web`

## Installation

**Try without installing:**

```bash
uvx cdl today
```

**Permanent install (recommended):**

```bash
pipx install cdl
cdl install
```

**git clone:**

```bash
git clone https://github.com/atsushi729/c-daily
cd c-daily
python3 bin/cdl install
```

After install, run `cdl install` once to register the Claude Code hook and launchd.

## Log Storage

```
~/.daily-logs/
├── 2026-04-07.md        # Generated Markdown report
└── raw/
    └── 2026-04-07.jsonl # Raw session records
```

Override the directory:

```bash
export C_DAILY_LOG_DIR="$HOME/Documents/logs"
```

## Requirements

- macOS 12+
- Python 3.9+
- Claude Code

## License

[MIT](LICENSE)
