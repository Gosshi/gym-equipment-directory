# AGENTS.md — Contributing Guide

本プロジェクトへのコントリビューション方法をまとめたガイドです。
開発環境、コーディング規約、ブランチ運用、PR 作成フローなどを統一し、スムーズかつ安全な開発を実現します。

---

## 📌 環境

- **Python 3.11** を利用してください
- 設定は **`pyproject.toml`** に集約
- 推奨ツール:
  - [`ruff`](https://docs.astral.sh/ruff/)（lint / format）
  - [`pytest`](https://docs.pytest.org/)（テスト）
  - [`gh`](https://cli.github.com/)（GitHub CLI）

---

## 🧹 コーディング規約

### フォーマット

- 行長: **100 文字以内**
- 文字列: **ダブルクォート (`"`)**
- インデント: **スペース**
- Docstring: **PEP 257** 準拠（コード例は正しい構文で記載）

実行例:

```bash
ruff format .
```

### Lint

- 有効ルールセット: **E, F, I, UP**
- 例外:
  - `__init__.py`: **`F401`（未使用 import）を許可**（再エクスポート用途）
  - `migrations/`: **`E501`（行長超過）を無視**

実行例:

```bash
ruff check . --fix
```

### 型ヒント

- すべての公開関数・メソッドに型ヒントを付与してください

### Definition of Done

- フロント: `next build` が成功し、`next start` 起動後 `GET /` が 200。
- バックエンド: `alembic upgrade head` 成功、`uvicorn` 起動後 `GET /healthz` または `GET /readyz` が 200。
- Lint / format / typecheck / pytest（軽量セット）が緑。

### レビュー前チェック

- 「起動スモーク OK」「lint/format OK」「型 OK」「軽量テスト OK」に ✅。
- lint/format の「OK」はバックエンド（`ruff check`, `ruff format --check`）とフロントエンド（`npm --prefix frontend run lint`, `npm --prefix frontend run format:check`）の双方が通っている状態を指します。

---

## 🧪 テスト

- フレームワーク: **pytest**
- 重要機能（検索・ページネーション・例外処理など）には必ずテストを追加すること
- 実行例:

  ```bash
  pytest -q
  ```

---

## 🌱 ブランチ運用

- `main`: 常にデプロイ可能な安定版
- `feature/*`: 機能追加
- `fix/*`: バグ修正
- `chore/*`: 設定・雑務

例:

```
feature/add-search-pagination
fix/typo-in-model
chore/update-ci-config
```

---

## 📝 コミットメッセージ

- **Conventional Commits** を推奨
  - `feat: ○○を追加`
  - `fix: △△のバグを修正`
  - `chore: CI 設定を更新`

- 1 コミット = 1 つの論理的変更 を意識してください

---

## 🔄 PR 作成（日本語）

- **PR タイトル・本文は日本語**
- **CI がグリーンでない PR はレビュー依頼しない**（落ちている状態では Draft のままにし、原因とリカバリ方針を記載）
- `gh pr create` の使用例:

```bash
# 変更をコミット
git add -A
git commit -m "feat: 検索スコア機能を追加"

# ブランチを push
git push -u origin feature/add-search-score

# 日本語で PR を作成（Draft 推奨）
gh pr create \
  --title "feat: 検索スコア機能の追加" \
  --body "## 概要
- 検索APIにスコアリングを追加
- Ruff スタイルに準拠してコードを整形

## 動作確認
- pytest 成功
- ruff check 成功

## 影響範囲
- /gyms/search のソートに影響
" \
  --base main \
  --head feature/add-search-score \
  --draft
```

- CI が失敗している場合は **Ready for review にしないこと**

### PR 本文テンプレート

以下のテンプレートをベースにし、箇条書きで簡潔にまとめてください。

```
## 目的
- 何を解決する PR なのか

## 変更点
- 主な実装や設定の追加・修正内容

## 確認手順
- [ ] ローカルでの起動確認
- [ ] lint / format / test 実行結果

## CI
- [ ] GitHub Actions が全て成功
```

---

## 🔍 CI/CD

- CI では以下を必ず実行
  - バックエンド: `ruff check .`, `ruff format --check .`, `pytest`
  - フロントエンド: `npm --prefix frontend run lint`（ESLint）, `npm --prefix frontend run format:check`（Prettier）, `npm --prefix frontend run test:unit`

- **CI が落ちている PR はマージ不可。**落ちている場合はレビュー依頼せず、必ず修正コミットまたはリトライを入れてください。

---

## 📖 ドキュメント

- `README.md`: ユーザー向け
- `AGENTS.md`: 開発者向け（本ファイル）
- FE10 改善計画関連ドキュメント:
  - [docs/roadmap-next.md](docs/roadmap-next.md)
  - [docs/architecture.md](docs/architecture.md)
  - [docs/testing-strategy.md](docs/testing-strategy.md)
  - [docs/performance.md](docs/performance.md)
  - [docs/accessibility.md](docs/accessibility.md)
  - [docs/backlog.md](docs/backlog.md)
  - [docs/fe10-progress.md](docs/fe10-progress.md)
- API 仕様変更時は OpenAPI Docs を更新し、PR に含めてください

---

## 🧭 まとめ

- **Python 3.11**, **Ruff**, **pytest** を基本ツールとする
- スタイル / テスト / CI に準拠しない PR は受け付けない
- **PR は日本語で書く**
- **エラーがある状態を「完了」としない**（CI, lint, テストすべて）
