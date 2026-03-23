# 🗂️ c-daily

**Claude Code の作業を自動記録し、毎日 Markdown で振り返れる CLI ツール**

[![CI](https://github.com/Atsushi Hatakeyama/c-daily/actions/workflows/ci.yml/badge.svg)](https://github.com/Atsushi Hatakeyama/c-daily/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

```
# 📋 Daily Log — 2026-03-23

## 📊 サマリー
| 種別             | 件数 |
|------------------|------|
| ✏️ ファイル編集  |  8   |
| ⚡ コマンド実行  |  5   |
| 💬 会話セッション|  3   |

## ⏱️ タイムライン
### 10:xx
- `10:23` ✏️ 編集: src/auth/login.py
- `10:31` ⚡ 実行: pytest tests/test_auth.py

### 14:xx
- `14:05` 💬 セッション終了: JWTリフレッシュトークンの実装 (12 turns, $0.0231)
```

## ✨ 特徴

- **ゼロ操作で記録** — Claude Code を使うだけで自動ログ取得
- **毎日 23:58 に自動生成** — macOS launchd で日付をまたぐ前に Markdown 出力
- **外部依存ゼロ** — Python 標準ライブラリのみ使用
- **将来の拡張に備えた設計** — JSONL 形式で Git hook や他ツールも追記可能

## 📦 インストール

### 方法 1: curl（推奨）

```bash
curl -fsSL https://raw.githubusercontent.com/Atsushi Hatakeyama/c-daily/main/install.sh | bash
c-daily install
```

### 方法 2: Homebrew

```bash
brew tap Atsushi Hatakeyama/c-daily
brew install c-daily
c-daily install
```

### 方法 3: git clone

```bash
git clone https://github.com/Atsushi Hatakeyama/c-daily ~/.local/share/c-daily
ln -sf ~/.local/share/c-daily/bin/c-daily ~/.local/bin/c-daily
c-daily install
```

## 🔧 動作要件

| 項目 | バージョン |
|------|-----------|
| macOS | 12 Monterey 以降 |
| Python | 3.9 以上 |
| Claude Code | 最新版 |

## 🚀 使い方

```bash
c-daily install        # 初回セットアップ（hookとlaunchd登録）
c-daily today          # 今日のログをMarkdownで生成・表示
c-daily show 2026-03-22  # 特定日のログを表示
c-daily status         # hookが正常に動いているか確認
c-daily raw            # 生ログ(JSONL)を表示
c-daily uninstall      # 全設定を削除（ログデータは保持）
```

## 📁 ログの保存先

```
~/.daily-logs/
├── 2026-03-23.md        # 生成済み Markdown
├── 2026-03-24.md
└── raw/
    └── 2026-03-23.jsonl # 生ログ（JSONL形式）
```

ログの保存先は環境変数で変更できます:

```bash
export C_DAILY_LOG_DIR="$HOME/Documents/logs"
```

## 🗺️ ロードマップ

- [ ] Linux (systemd timer) 対応
- [ ] Git hook の自動設定
- [ ] 週次サマリー (`c-daily weekly`)
- [ ] Obsidian vault への出力
- [ ] 複数プロジェクト横断ビュー

## 🤝 Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 License

[MIT](LICENSE)
