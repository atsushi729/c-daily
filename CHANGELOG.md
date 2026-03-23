# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Linux (systemd timer) support
- Automatic Git hook setup
- Weekly summary (`c-daily weekly`)

## [0.1.0] - 2026-03-23

### Added
- `c-daily install` — sets up Claude Code hooks and launchd
- `c-daily today` — generates and opens today's daily Markdown
- `c-daily show [DATE]` — generates and opens Markdown for a specified date
- `c-daily status` — checks that hooks and launchd are working
- `c-daily raw [DATE]` — displays raw JSONL log
- `c-daily uninstall` — removes all settings
- PostToolUse hook for automatic recording of file edits and command runs
- Stop hook for automatic session summary recording
- `C_DAILY_LOG_DIR` environment variable to customize log directory
- macOS launchd auto-execution at 23:58 daily
- Homebrew Tap distribution Formula
