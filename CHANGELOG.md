# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Linux (systemd timer) 対応
- Git hook 自動設定
- 週次サマリー (`c-daily weekly`)

## [0.1.0] - 2026-03-23

### Added
- `c-daily install` — Claude Code hookとlaunchdのセットアップ
- `c-daily today` — 今日の日次Markdownを生成して開く
- `c-daily show [DATE]` — 指定日のMarkdownを生成して開く
- `c-daily status` — hookとlaunchdの動作確認
- `c-daily raw [DATE]` — 生JSONL表示
- `c-daily uninstall` — 全設定の削除
- PostToolUse hook によるファイル編集・コマンド実行の自動記録
- Stop hook によるセッションサマリーの自動記録
- `C_DAILY_LOG_DIR` 環境変数でログ保存先をカスタマイズ可能
- macOS launchd による毎日 23:58 の自動実行
- Homebrew Tap 配布用 Formula
