# ジオコーディング & 鮮度キャッシュ運用手順

ジム住所から緯度経度を補完し、最新の確認日時を検索スコアに反映させるための手順をまとめます。
`make geocode-*` / `make freshness` ターゲットと組み合わせて、`.env` / `.env.prod` いずれの環境でも
同じ操作で実行できます。

## 1. 概要
- `scripts/tools/geocode_missing.py`: 住所に緯度経度が入っていない gyms / gym_candidates を
  ジオコーディングします。
- `scripts/update_freshness.py`: `gym_equipments.last_verified_at` から `gyms.last_verified_at_cached`
  を再計算し、検索スコアに反映させます。
- Makefile の `geocode-gyms` / `geocode-candidates` / `freshness` / `geocode-and-freshness` が共通の
  運用フローを提供します。

## 2. 前提条件
- `.env`（ローカル）または `.env.prod`（本番相当）に必要な環境変数を定義しておく。
  - 例: `DATABASE_URL`、`OPENCAGE_API_KEY`（OpenCage でのジオコーディングに必須）。
- Alembic で最新マイグレーションまで適用済みであること。
- `docker compose --env-file <ENV_FILE> up -d` で API / DB コンテナを起動済みであること。
- 操作するデータベースに対して十分な権限を持っていること（特に本番環境）。

## 3. ローカル開発環境での手順例 (`.env`)
```bash
# 1. コンテナ起動
docker compose --env-file .env up -d

# 2. scraped 由来の gyms のみジオコーディング
make ENV_FILE=.env geocode-gyms

# 3. 鮮度キャッシュを更新
make ENV_FILE=.env freshness
```

必要に応じて、候補データも以下で補完できます。

```bash
make ENV_FILE=.env geocode-candidates
```

## 4. 本番相当 (`.env.prod`) での手順例
```bash
# 本番 DB に対する一括実行（慎重に！）
make ENV_FILE=.env.prod geocode-and-freshness
```
`geocode-and-freshness` は `geocode-gyms` → `freshness` を順番に呼び出すラッパーです。同様に
`ENV_FILE=.env.prod` を指定すれば、本番相当の docker compose 構成でも同じ手順で実行できます。

## 5. dry-run の使い方
データを書き換えずにジオコーディング対象とサマリを確認するには `--dry-run` を付けます。
`.env.prod` を指定すれば本番データでも安全に検証できます。

```bash
docker compose --env-file .env.prod exec api \
  python -m scripts.tools.geocode_missing \
    --target gyms \
    --origin scraped \
    --dry-run
```

## 6. 追加のヒント
- `--limit` で処理件数を制御できます。大規模なバッチを分割したい場合に便利です。
- `--origin scraped` は `official_url` が `manual:` ではない gyms のみに限定したいときに利用してください。
- Makefile のターゲットは `ENV_FILE` に応じて自動的に `docker compose --env-file <ENV_FILE>` を呼び
  出します。`ENV_FILE` を省略した場合は `.env` が使われます。
