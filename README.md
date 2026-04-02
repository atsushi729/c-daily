# 🗂️ c-daily

**A CLI tool that automatically records Claude Code activity and generates daily Markdown reviews**

[![CI](https://github.com/atsushi729/c-daily/actions/workflows/ci.yml/badge.svg)](https://github.com/atsushi729/c-daily/actions)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)  
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

# 📋 Daily Log — 2026-03-23

## 📊 Summary

| Type             | Count |
| ---------------- | ----- |
| ✏️ File Edits    | 8     |
| ⚡ Commands Run  | 5     |
| 💬 Chat Sessions | 3     |

## ⏱️ Timeline

### 10:xx

- `10:23` ✏️ Edit: src/auth/login.py
- `10:31` ⚡ Run: pytest tests/test_auth.py

### 14:xx

- `14:05` 💬 Session end: Implementing JWT refresh tokens (12 turns, $0.0231)

## ✨ Features

- **Zero-effort recording** — just use Claude Code and logs are captured automatically
- **Auto-generated at 23:58 daily** — macOS launchd outputs Markdown before midnight
- **No external dependencies** — uses Python standard library only
- **Designed for future extensibility** — JSONL format allows Git hooks and other tools to append entries

## 📦 Installation

### Option 1: curl (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/atsushi729/c-daily/main/install.sh | bash
c-daily install
```

### Option 2: Homebrew

```bash
brew tap atsushi729/c-daily
brew install c-daily
c-daily install
```

### Option 3: git clone

```bash
git clone https://github.com/atsushi729/c-daily ~/.local/share/c-daily
ln -sf ~/.local/share/c-daily/bin/c-daily ~/.local/bin/c-daily
c-daily install
```

## 🔧 Requirements

| Item        | Version      |
| ----------- | ------------ |
| macOS       | 12 Monterey+ |
| Python      | 3.9+         |
| Claude Code | Latest       |

## 🚀 Usage

```bash
c-daily install        # Initial setup (registers hooks and launchd)
c-daily today          # Generate and display today's log as Markdown
c-daily show 2026-03-22  # Display log for a specific date
c-daily status         # Check that hooks are working correctly
c-daily raw            # Display raw log (JSONL)
c-daily uninstall      # Remove all settings (log data is preserved)
```

## 📁 Log Storage

```
~/.daily-logs/
├── 2026-03-23.md        # Generated Markdown
├── 2026-03-24.md
└── raw/
    └── 2026-03-23.jsonl # Raw log (JSONL format)
```

The log directory can be changed via environment variable:

```bash
export C_DAILY_LOG_DIR="$HOME/Documents/logs"
```

## 🗺️ Roadmap

- [ ] Linux (systemd timer) support
- [ ] Automatic Git hook setup
- [ ] Weekly summary (`c-daily weekly`)
- [ ] Obsidian vault output
- [ ] Multi-project cross-view

## 🧪 Development

### Running tests

```bash
python3 -m pytest tests/ -v
```

### Linting and type checking

```bash
ruff check lib/ tests/        # lint
ruff format lib/ tests/       # format
mypy lib/ tests/              # type check
```

Run all checks at once:

```bash
ruff check lib/ tests/ && ruff format --check lib/ tests/ && mypy lib/ tests/
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE)
