# Backend Testing Guide

このドキュメントでは、バックエンド API/DB レイヤーのテスト実行方法と運用方針をまとめています。CI では `--cov-fail-under=90` を必須チェックとして設定しているため、ローカルでも同等の条件で実行してください。

## 1. セットアップ

### 1.1 テスト用 Postgres の起動

```bash
docker compose -f docker-compose.test.yml up -d
```

> 既存の `docker-compose.yml` では開発用の DB/サービスが立ち上がるため、テスト実行時は `docker-compose.test.yml` を利用します。ポート/ユーザー名は `TEST_POSTGRES_*` 環境変数で上書き可能です。

### 1.2 Python 依存関係

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

- Python 3.11 以上を前提としています。
- `pytest`, `pytest-asyncio`, `pytest-cov`, `freezegun`, `httpx`, `faker`, `python-dotenv` などの依存を追加済みです。

### 1.3 環境変数

最低限、以下の環境変数を設定してください。

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/gym_test"
export SEED_TEST_MODE=1
```

`.env.test` が存在する場合は自動で読み込まれます。`SEED_TEST_MODE=1` を指定すると `scripts/seed.py` がテスト専用のミニマルデータセットで動作し、緯度経度の揺らぎが ±50m 程度に抑えられます。

## 2. テスト実行

### 2.1 コマンド

```bash
SEED_TEST_MODE=1 pytest --cov=app --cov-report=term-missing --cov-fail-under=90
```

- `pytest.ini` で `backend/tests` のみを探索対象に設定しています。
- `freezegun` により `datetime.utcnow()` は常に `2025-01-01T00:00:00Z` に固定され、`faker` もシード固定済みのため、テスト結果は再現性があります。
- 失敗時には `backend/tests/conftest.py` が自動的に以下をダンプします。
  - 最後に実行された SQL ステートメント（最大 20 件）
  - 直近の HTTP リクエスト/レスポンス（httpx イベントフックで収集）

### 2.2 テスト階層

- `backend/tests/api/` … `/gyms/search`・`/gyms/{slug}` など API 統合テスト
- `backend/tests/db/` … `scripts/seed.py` の DB ヘルパーや制約検証
- `backend/tests/utils/` … ハバースイン距離計算など共通ユーティリティ

## 3. カバレッジ基準

- `coverage.ini` でブランチカバレッジを有効化し、`fail_under = 90` を設定しています。
- `term-missing` を使って不足行を可視化できます。閾値を下回った場合はテスト追加または不要コードの削除をご検討ください。

## 4. トラブルシューティング

- **DB マイグレーションの失敗**: `backend/tests/conftest.py` で Alembic を自動適用しています。エラーが出る場合は `alembic upgrade head` を手動実行し、`TEST_DATABASE_URL` の設定を見直してください。
- **ポート競合**: 既に 5433 が使用中の場合は `TEST_POSTGRES_PORT` で別ポートを指定し、`TEST_DATABASE_URL` も合わせて変更してください。
- **ログ解析**: テスト失敗時に出力される SQL/HTTP ログを参照してください。それでも不足する場合は `SQLALCHEMY_ECHO=1` を追加するなどして追加ログを採取できます。

## 5. シードデータ方針

- テストモードでは `scripts/seed.py` が固定スキーマの少量データ（複数都市・設備パターン）を投入します。
- 市区町村ごとに座標アンカーを持ち、緯度経度の揺らぎは ±50m 以内に収めています。
- `last_verified_at_cached` や `created_at` も固定オフセットで設定し、ソート条件（freshness/created_at/distance/score）が安定するよう調整済みです。

以上を守ればローカルでも CI と同じ条件でバックエンドテストを安全に実行できます。
