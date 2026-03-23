# Contributing to c-daily

c-daily へのコントリビューションを歓迎します！

## 開発環境のセットアップ

```bash
git clone https://github.com/Atsushi Hatakeyama/c-daily
cd c-daily
pip install pytest
pytest tests/ -v
```

## Issue の報告

バグ報告・機能リクエストは [GitHub Issues](https://github.com/Atsushi Hatakeyama/c-daily/issues) へ。

**バグ報告時に含めてほしい情報:**
- OS とバージョン (`sw_vers` の出力)
- Python バージョン (`python3 --version`)
- Claude Code バージョン
- `c-daily status` の出力
- 再現手順と期待する動作

## Pull Request

1. このリポジトリを Fork する
2. feature ブランチを切る: `git checkout -b feat/my-feature`
3. テストを書いて通す: `pytest tests/`
4. コミット: [Conventional Commits](https://www.conventionalcommits.org/) 形式で
   - `feat:` 新機能
   - `fix:` バグ修正
   - `docs:` ドキュメントのみの変更
   - `test:` テストの追加・修正
   - `chore:` ビルド・CI等
5. PR を送る

## 将来のロードマップ（コントリビューション歓迎）

- [ ] Linux (systemd timer) 対応
- [ ] Git hook の自動設定
- [ ] Obsidian vault への出力
- [ ] 週次サマリー (`c-daily weekly`)
- [ ] 複数プロジェクト対応

## コードの方針

- **シェルスクリプト**: POSIX準拠、`shellcheck` を通す
- **Python**: 標準ライブラリのみ使用（外部依存なし）、型ヒントを推奨
- **テスト**: `pytest`、新機能には必ずテストを追加
