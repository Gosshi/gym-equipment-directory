# ingest / Admin 承認運用ガイド

本番 PostgreSQL への接続、シード投入、ingest の手動実行、Admin 承認フローをまとめた
運用ドキュメント。Render の環境変数入力例やトラブルシュート、将来の自動化メモも含める。

## 1. 本番 DB 接続
- Render の **Internal Database URL** を `DATABASE_URL` として利用する。
  - 例: `postgresql://<USER>:<PASSWORD>@<HOST>:5432/<DB_NAME>?sslmode=require`
  - Render ダッシュボード > Web Service > Environment > Environment Variables で
    `DATABASE_URL` を追加し、上記 URL を値に貼り付ける。
- ローカルから本番 DB へ接続確認する場合の例:
  ```bash
  DATABASE_URL="postgresql://<USER>:<PASSWORD>@<HOST>:5432/<DB_NAME>?sslmode=require"
  pg_isready --dbname "$DATABASE_URL"
  psql "$DATABASE_URL" -c '\dt'
  ```
- Compose 経由で API コンテナから疎通確認する場合:
  ```bash
  docker compose --env-file .env.prod exec api pg_isready --dbname "$DATABASE_URL"
  docker compose --env-file .env.prod exec api psql "$DATABASE_URL" -c 'select now()'
  ```

## 2. シード投入（ダミーデータ）
- Alembic 適用後、`scripts/seed.py` を使って最低限のデータを投入する。
- 本番相当環境での実行例（`APP_ENV=prod` で bulk は禁止される点に注意）:
  ```bash
  # env.prod に DATABASE_URL / APP_ENV=prod を設定済みとする
  docker compose --env-file .env.prod exec api \
    python -m scripts.seed --equip-only

  docker compose --env-file .env.prod exec api \
    python -m scripts.seed --bulk-gyms 0 --equip-per-gym 8 --bulk-region tokyo-east
  ```
  - 大量投入が必要な場合でも `--bulk-gyms` は本番では 0 または未指定にする。
  - Render の Environment Variables に `APP_ENV=prod` と `DATABASE_URL` を登録しておく。

## 3. ingest 手動実行
- ベースの 3 ステップ: `fetch` → `parse` → `normalize`。`scripts/ingest` を直接叩く。
- 代表的な例（墨田区の municipal ソースを本番相当で 100 件取得、200 件まで parse/normalize）:
  ```bash
  # DSN を DATABASE_URL に合わせる
  DSN="$DATABASE_URL" make ENV_FILE=.env.prod ingest-fetch-municipal-sumida
  DSN="$DATABASE_URL" make ENV_FILE=.env.prod ingest-parse-municipal-sumida
  DSN="$DATABASE_URL" make ENV_FILE=.env.prod ingest-normalize-municipal-sumida
  ```
- 任意ソースをまとめて回す場合は `ingest-run` を利用:
  ```bash
  SOURCE=municipal_koto DSN="$DATABASE_URL" LIMIT=200 \
    make ENV_FILE=.env.prod ingest-run
  ```
- 速度調整や検証だけ行いたい場合は `LIMIT` や `--dry-run` を付ける。

## 4. Admin 承認フロー
- `/admin/candidates` API を `ADMIN_UI_TOKEN` で保護する。Render では Web Service の
  Environment Variables に `ADMIN_UI_TOKEN` を設定し、フロント/CLI から Bearer 認証で
  送る。
- 確認〜承認の典型シーケンス:
  ```bash
  BASE_URL="https://api-xxx.onrender.com"  # Render の backend URL
  TOKEN="$ADMIN_UI_TOKEN"

  # 未承認候補の一覧
  curl -s -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/admin/candidates?status=new&limit=20" | jq

  # 承認プレビュー（dry-run）
  curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true}' \
    "$BASE_URL/admin/candidates/123/approve" | jq

  # 実承認
  curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": false}' \
    "$BASE_URL/admin/candidates/123/approve" | jq
  ```
- Bulk 承認/却下を行う場合は `/admin/candidates/approve-bulk` / `reject-bulk` に対して
  JSON 配列を送る。`operator` クエリでオペレーター名を残すと監査ログの追跡に便利。

## 5. トラブルシュート
- DB 接続確認
  - `pg_isready --dbname "$DATABASE_URL"` で疎通をチェック。
  - 失敗した場合は `render.yaml` / Render 環境変数の `DATABASE_URL` 漏れやホスト名
    を再確認し、再度 `pg_isready` を実行。
- ingest 失敗時の再実行指針
  - `LIMIT` 付きで小さく再実行し、問題の URL/レコードを切り分ける。
  - `--dry-run` で parse/normalize のみ通し、データ破壊を防ぎつつログを確認。
- ログの確認
  - Compose 本番相当: `docker compose --env-file .env.prod logs -f api`
  - Render: Dashboard > Web Service > Logs でリアルタイム確認。
  - 失敗時は API ログに加え、PostgreSQL のログも併せて確認する。
    ```bash
    docker compose --env-file .env.prod exec db \
      tail -n 100 /var/log/postgresql/postgresql-*.log
    ```

## 6. 将来の自動化メモ
- cron / worker への移行時は以下をジョブ化する。
  - `scripts.ingest` の `fetch` → `parse` → `normalize` 3 ステップを 1 ジョブにまとめ、
    `SOURCE` と `LIMIT` を引数化。
  - `scripts.seed` は `--equip-only` など安全なフラグのみを許可し、`APP_ENV=prod` では
    bulk を拒否するポリシーをジョブでも踏襲。
  - Admin 承認は Slack 通知と組み合わせ、`/admin/candidates` の新規到着を通知して
    手動承認の待ち行列を短縮する。
- Render から cron/worker に移す場合も、ここで記載した `DATABASE_URL` / `ADMIN_UI_TOKEN`
  などの環境変数をそのままシークレット管理に渡せば差分を最小化できる。
