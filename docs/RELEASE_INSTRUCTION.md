# リリース手順: Neon (Postgres) への初期マイグレーション適用

本手順は、Neon 上の本番 PostgreSQL に対してローカル環境から Alembic の初期マイグレーションを
実行し、必要なテーブルを作成するためのものです。Python 3.11 環境とリポジトリが手元にあること、
Neon の接続文字列を取得済みであることを前提としています。

## 1. 環境変数 `DATABASE_URL` をセット
Neon の接続文字列を `postgresql+asyncpg://` 形式に変換し、シェルでエクスポートします。

```bash
export DATABASE_URL="postgresql+asyncpg://<user>:<password>@<neon_host>:5432/<database>"
```

> メモ: `postgres://` で始まる場合は `postgresql+asyncpg://` に置き換えてください。

## 2. Alembic でスキーマを作成
リポジトリルートで Alembic を実行し、最新バージョンまでマイグレーションを適用します。

```bash
alembic upgrade head
```

成功すると、Neon 上に `gyms` / `equipments` / `gym_equipments` などのテーブルが作成されます。

## 3. （任意）初期シードデータを投入
最小限のジム設備データが必要な場合は、同じ `DATABASE_URL` を使ってシードを流します。

```bash
python scripts/seed_minimal_gyms.py --dsn "$DATABASE_URL"
```

`--payload` を指定しなければ `scripts/data/seed_minimal_gyms.json` が利用されます。シードは
冪等で、既存レコードがあれば upsert されます。

## 4. Render / Vercel 環境変数の設定
本番デプロイ後に、各サービスの環境変数を設定してください。

### Backend (Render Web Service)
- `DATABASE_URL`: Neon の接続文字列（`postgresql+asyncpg://` 形式）
- `APP_ENV`: `prod`
- `APP_PORT`: `8000`
- `LOG_LEVEL`: `INFO`
- `ALLOW_ORIGINS`: フロントエンドの公開 URL
- `RATE_LIMIT_ENABLED`: `1`
- `SECRET_KEY`: ランダムなシークレット
- `ADMIN_UI_TOKEN`: `/admin` 用のアクセストークン
- `OPENCAGE_API_KEY`: ジオコーディング API キー
- `SENTRY_DSN` / `SENTRY_TRACES_RATE` / `RELEASE`: 監視・トレーシング設定
- `SCORE_W_FRESH` / `SCORE_W_RICH` / `FRESHNESS_WINDOW_DAYS`: 検索スコア調整
- `META_CACHE_TTL_SECONDS`: メタ情報キャッシュ TTL
- `ALEMBIC_STARTUP_MAX_ATTEMPTS` / `ALEMBIC_STARTUP_RETRY_SECONDS` /
  `ALEMBIC_EXIT_ON_FAILURE`: マイグレーション起動リトライ設定

### Frontend (Vercel)
- `NEXT_PUBLIC_API_BASE_URL`: Backend の公開 URL
- `NEXT_PUBLIC_API_BASE`（必要に応じて）: Backend の公開 URL
- `NEXT_PUBLIC_BACKEND_URL`（必要に応じて）: Backend の公開 URL
- `NEXT_PUBLIC_AUTH_MODE`: `stub` など利用する認証モード
- `ADMIN_UI_TOKEN`: `/admin` 向けに Backend と同じトークンを設定
- `NEXT_PUBLIC_OAUTH_PROVIDER` / `NEXT_PUBLIC_OAUTH_CLIENT_ID` /
  `NEXT_PUBLIC_OAUTH_REDIRECT_URI`: OAuth を有効にする場合のみ設定
- `NODE_ENV`: `production`
