# 運用・デプロイ手順書

本ドキュメントでは、env ファイルの準備から Docker Compose による本番相当環境の立ち上げ、Render へのデプロイ、および保守用スクリプトの実行手順をまとめます。

## 1. env ファイルの準備
1. テンプレートをコピーする
   ```bash
   cp .env.example .env
   cp .env.prod.example .env.prod
   ```
2. `.env`（ローカル開発）と `.env.prod`（本番 / Render）に対して、PostgreSQL の接続情報や `DATABASE_URL`、`ADMIN_UI_TOKEN`、`OPENCAGE_API_KEY` などのシークレットを入力する。
3. Docker Compose が利用するファイルを `COMPOSE_ENV_FILE=.env`（開発）または `COMPOSE_ENV_FILE=.env.prod`（本番）に設定しておく。

## 2. 本番相当スタックの起動
1. `.env.prod` を読み込んでコンテナを立ち上げる
   ```bash
   docker compose --env-file .env.prod up -d
   ```
2. 必要に応じて DB マイグレーションを実行する
   ```bash
   docker compose --env-file .env.prod exec api alembic upgrade head
   ```
3. API のヘルスチェック
   ```bash
   curl http://localhost:${APP_PORT:-8080}/healthz
   ```
4. ログ確認（任意）
   ```bash
   docker compose --env-file .env.prod logs -f api
   ```

## 3. ジオコーディング / 鮮度更新ジョブ
スタックが立ち上がったら、以下の CLI を API コンテナ内で実行する。

```bash
# 緯度経度が欠損しているジムをスクレイプ結果から補完
docker compose --env-file .env.prod exec api \
  python -m scripts.tools.geocode_missing \
    --target gyms \
    --origin scraped

# 検索スコアに利用する鮮度キャッシュを更新
docker compose --env-file .env.prod exec api \
  python -m scripts.update_freshness
```

`.env` を使うローカル開発時も、`--env-file .env` に差し替えれば同じコマンドで実行できる。

## 4. Render デプロイ手順
Render 向けの Blueprint は [`infra/render.yaml`](../infra/render.yaml) に格納されている。新規 Web Service を作成する際は以下を参照。

1. [Render ダッシュボード](https://dashboard.render.com/)で Web Service を作成し、GitHub の本リポジトリを選択する。
2. 設定画面で "Use existing render.yaml" を選び、`infra/render.yaml` を参照させる。
3. `envVars` に記載されている `DATABASE_URL`、`OPENCAGE_API_KEY`、`ADMIN_UI_TOKEN` などのシークレットを Render 側のダッシュボードで入力する。
4. Render のヘルスチェックは `/healthz` を参照するため、ローカルでも同エンドポイントが 200 を返すことを確認してからデプロイを進める。

## 5. よく使うコマンド
- `docker compose --env-file .env.prod up -d`
- `docker compose --env-file .env.prod exec api python -m scripts.tools.geocode_missing --target gyms --origin scraped`
- `docker compose --env-file .env.prod exec api python -m scripts.update_freshness`
- `curl http://localhost:${APP_PORT:-8080}/healthz`

## 6. シャットダウンと後片付け
```bash
docker compose --env-file .env.prod down
```
永続化ボリュームは残したまま、コンテナだけを停止する。
