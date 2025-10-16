# Gym Equipment Directory

ジムの設備情報を統一フォーマットで整理し、横比較・鮮度維持を可能にするMVP。  
現在は環境構築段階。

---

## 🚀 技術スタック

- Backend: Python (FastAPI)
- DB: PostgreSQL (via Docker)
- Infra: Docker / docker-compose
- ORM / Migration: SQLAlchemy + Alembic
- Admin: Adminer (DB管理UI)
- Frontend: Next.js (TypeScript + Tailwind) — `frontend/README.md` を参照

---

## 📦 セットアップ手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/yourname/gym-equipment-directory.git
cd gym-equipment-directory
```

### 2. 環境変数ファイルを作成

```bash
cp .env.example .env
```

必要に応じて .env を編集。

### 3. コンテナ起動

```bash
docker compose up -d --build
```

### 4. 動作確認

```bash
curl http://localhost:8000/health
# => {"status":"ok","env":"dev"}
```

- Swagger UI: http://localhost:8000/docs
- Adminer: http://localhost:8080
  - System: PostgreSQL
  - Server: db
  - User: appuser
  - Password: apppass
  - Database: gym_directory

## 🌐 フロントエンド開発

- `frontend/` ディレクトリに Next.js ベースのフロントエンドを追加しました。
- 初回は以下を実行してください。
  ```bash
  cd frontend
  npm install
  cp .env.example .env.local
  npm run dev
  ```
- `/health` をコールするトップページが表示されます。詳細な手順や環境変数の説明は
  `frontend/README.md` を参照してください。

## 📂 ディレクトリ構成（現在）

```bash
gym-equipment-directory/
├─ app/
│  ├─ main.py        # FastAPIエントリポイント
│  ├─ db.py          # DB接続
├─ migrations/        # Alembic用（まだ未使用）
├─ .env.example
├─ docker-compose.yml
├─ Dockerfile
├─ requirements.txt
└─ README.md
```

## Docs

- [MVP 定義](docs/MVP.md)
- [ユーザテスト計画](docs/USER_TEST_PLAN.md)
- [Go To Market](docs/GO_TO_MARKET.md)

## 🔐 Admin 候補モデレーション API

スクレイピング候補を人手で審査するための API を追加しました。`/admin/candidates`
配下に以下の機能を揃えています。

- 一覧取得・詳細確認・部分更新
- 承認: 公開テーブルへの upsert（`dry_run` 指定でプレビューのみ実行も可能）
- 却下: 理由付きで候補を非承認扱いに変更

### Admin UI

- `.env` に `ADMIN_UI_TOKEN` を設定すると、Next.js フロントの `/admin` 配下を同じトークンで保護します。
- ブラウザで `http://localhost:3000/admin/login` にアクセス → トークンを入力すると Cookie に保存され、`/admin/candidates` へ遷移します。
- 一覧から候補を選択すると詳細画面に移動し、以下を UI 上で実行できます。
  - フィールドの編集 (`PATCH /admin/candidates/{id}`)
  - Dry-run 承認（差分プレビュー表示）
  - 本承認（成功時に `/gyms/{slug}` へのリンク付きトーストを表示）
  - 却下（理由必須）
- 承認 API のレート制限(HTTP 429)には UI 側で自動リトライ（Retry-After 対応）を実装しています。

## 🏋️ Ingest パイプラインの使い方

`site_a` のスクレイピングフローをローカルで試す場合は、以下のコマンドを順番に実行します。

1. 依存関係をインストール
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```
2. ダミー HTML を保存
   ```bash
   make ingest-fetch-site-a
   ```
3. HTML を解析して候補テーブルへ反映
   ```bash
   make ingest-parse-site-a
   ```
4. 候補データを正規化
   ```bash
   make ingest-normalize-site-a
   ```

各ターゲットは `--limit 10` で固定実行されます。必要に応じて下記のように直接コマンドを
呼び出し、件数などのオプションを調整してください。

```bash
python -m scripts.ingest fetch --source site_a --limit 5
```

## 📝 今後の予定（M1スコープ）

- [ ] SQLAlchemyモデル定義
- [ ] Alembic初期マイグレーション
- [ ] gyms / equipments / gym_equipments データ投入
- [ ] 検索API /gyms/search
- [ ] 店舗詳細API /gyms/{slug}
- [ ] フロント：検索〜詳細ページ実装

---

了解！README に追記する文面と、動作確認の再実行コマンドをまとめました。
そのままコピペで使えるようにしてあります。

---

## 初期セットアップ（DB初期化 → マイグレーション → シード）

> 前提:
>
> - Docker Compose の DB サービス名: `db`（PostgreSQL 16）
> - アプリはコンテナ間で DB に接続する
> - 接続文字列（**固定**）  
>   `DATABASE_URL=postgresql+asyncpg://appuser:apppass@db:5432/gym_directory`

1. コンテナ起動（DB と Adminer）
   ```bash
   docker compose up -d db adminer
   docker compose exec db pg_isready -U appuser -d gym_directory
   ```

````

2. **マイグレーション適用（必須）**

   * コンテナ内で実行（import パスが確実）

   ```bash
   docker compose exec api bash -lc '
     export DATABASE_URL="postgresql+asyncpg://appuser:apppass@db:5432/gym_directory"
     alembic upgrade head
   '
````

3. **シード投入**

   ```bash
   docker compose exec api bash -lc '
     export DATABASE_URL="postgresql+asyncpg://appuser:apppass@db:5432/gym_directory"
     export PYTHONPATH=/app
     python -m scripts.seed
   '
   ```

4. **大量ダミーデータ投入（任意）**

   ```bash
   docker compose exec api bash -lc '
     export DATABASE_URL="postgresql+asyncpg://appuser:apppass@db:5432/gym_directory"
     export PYTHONPATH=/app
     python -m scripts.seed_bulk --count 500
   '
   ```

   - `--count` は 300〜800 件程度で調整可能（既定値 500）。
   - 千葉県・東京都・茨城県の主要市区町村を対象に、住所と緯度経度をランダム生成します。
   - スラッグは `bulk-` プレフィックスで一意化しており、再実行しても既存レコードと衝突しません。
   - 装置マスタのみ投入したい場合は `make seed-equip` を利用できます。

5. スキーマ確認（任意）

   ```bash
   docker compose exec db psql -U appuser -d gym_directory -c "\dt"
   # gyms / equipments / gym_equipments / sources が表示されればOK
   ```

---

## アプリ起動

### ローカルで uvicorn を起動する場合

```bash
export DATABASE_URL="postgresql+asyncpg://appuser:apppass@127.0.0.1:5432/gym_directory"
python -m uvicorn app.api.main:app --reload --port 8000
```

### Compose の `api` サービスで起動する場合

- `.env` に **必ず** 次を入れておく：

  ```
  DATABASE_URL=postgresql+asyncpg://appuser:apppass@db:5432/gym_directory
  ```

- 起動：

  ```bash
  docker compose up -d api
  ```

---

## 動作確認（/gyms/search）

> 例では pref/city と seed 済みデータを想定。環境に合わせて調整してください。

```bash
# 1) freshness（最新順）
curl -sS 'http://localhost:8000/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=5' | jq .

# 2) richness（設備スコア順 / any）
curl -sS 'http://localhost:8000/gyms/search?pref=chiba&city=funabashi&equipments=squat-rack,dumbbell&equipment_match=any&sort=richness&per_page=10' | jq .

# 3) name 昇順（keyset）
curl -sS 'http://localhost:8000/gyms/search?pref=chiba&city=funabashi&sort=gym_name&per_page=5' | jq .

# 4) created_at 降順（keyset）
curl -sS 'http://localhost:8000/gyms/search?pref=chiba&city=funabashi&sort=created_at&per_page=5' | jq .

# 5) ページング継続（例：1ページ目の page_token を使って2ページ目を取得）
TOKEN=$(curl -sS 'http://localhost:8000/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=2' | jq -r '.page_token')
curl -sS "http://localhost:8000/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=2&page_token=${TOKEN}" | jq .
```

### ページネーション仕様

- クエリパラメータ
  - `page`: 1 始まりのページ番号（既定値 1）
  - `per_page` / `page_size`: 1 ページの件数（既定値 20、最大 50）
- レスポンスには `total`, `page`, `per_page`, `items`, `page_token` が含まれ、後方互換を維持しています。
- `page` が最終ページを超えた場合はサーバー側で自動的に最終ページに調整され、空配列が返らないようになっています。
- フロントエンドは検索条件変更時に `page=1` へリセットし、URL クエリと状態を同期させています。

### 手動確認チェックリスト（フロントエンド）

1. `alembic upgrade head`
2. `python -m scripts.seed_bulk --count 500`
3. `npm run dev`（またはビルド後の `npm run start`）で `/gyms` 検索ページを開く。
4. キーワード・カテゴリ・距離を変更しながらページャを操作し、`page` / `page_size` を含む URL クエリが更新されること、リロードや URL 共有で状態が復元されることを確認。
5. ページ番号を最終ページ超過に変更しても自動で最後のページに戻ること、0 件時のプレースホルダ表示を確認。
6. `/gyms/nearby` を含む地図連動ビューでも一覧選択とピン表示が従来通り動作し、ページ切替で不要にカメラが揺れないことを確認。

### seed_bulk の既知の制約

- 住所と緯度経度は市区町村ごとのバウンディングボックスからランダムサンプリングしているため、極端に狭い距離条件では精度が落ちる場合があります。
- スクリプトを再実行すると追加でジムが挿入されます（重複はしません）。不要な場合は DB をリセットしてから再投入してください。
- 画像や大容量アセットは含まれていません。手元での表示確認用データセットとして活用してください。

### よくあるハマりどころ

- **DBを作り直したら**、必ず `alembic upgrade head` → `python -m scripts.seed` の順に実行。
- ローカル uvicorn のときは `@127.0.0.1:5432`、コンテナ内からは `@db:5432` を使う。
- `DATABASE_URL` は **.env** と **起動シェルの環境変数**の優先度に注意（起動前に `echo $DATABASE_URL` で確認）。

### 運用Tips：記事ページから生成されたジムの整理

`/introduction/post_*.html` や `tr_detail.html` 等の「記事ページ単体」を誤って承認してしまった既存レコードは、以下の手順で紹介トップのジムに設備を集約してから削除できます。事前に `gym_equipments` に `(gym_id, equipment_id)` のユニークインデックスがあることを確認してください（`CREATE UNIQUE INDEX IF NOT EXISTS gym_equipments_gym_id_equipment_id_key ON gym_equipments (gym_id, equipment_id);`）。

1. 記事ジム → 紹介トップジムの対応表を作成し、設備を upsert で移管

   ```sql
   WITH article_gym AS (
       SELECT
           g.id AS article_gym_id,
           regexp_replace(
               g.official_url,
               '(.*(/sports_center[0-9]+/introduction))/?.*$',
               '\1/'
           ) AS intro_url
       FROM gyms AS g
       WHERE g.official_url ~ '/introduction/(post_|tr_detail\\.html|trainingmachine\\.html|notes\\.html)$'
   ),
   gym_pair AS (
       SELECT
           a.article_gym_id,
           intro.id AS intro_gym_id
       FROM article_gym AS a
       JOIN gyms AS intro ON intro.official_url = a.intro_url
   ),
   moved AS (
       INSERT INTO gym_equipments AS ge (
           gym_id,
           equipment_id,
           availability,
           count,
           max_weight_kg,
           notes,
           verification_status,
           last_verified_at,
           source_id,
           created_at,
           updated_at
       )
       SELECT
           gp.intro_gym_id,
           e.equipment_id,
           e.availability,
           e.count,
           CASE WHEN e.max_weight_kg < 0 THEN NULL ELSE e.max_weight_kg END,
           e.notes,
           e.verification_status,
           e.last_verified_at,
           e.source_id,
           NOW(),
           NOW()
       FROM gym_equipments AS e
       JOIN gym_pair AS gp ON e.gym_id = gp.article_gym_id
       ON CONFLICT (gym_id, equipment_id) DO UPDATE SET
           availability = EXCLUDED.availability,
           count = EXCLUDED.count,
           max_weight_kg = EXCLUDED.max_weight_kg,
           notes = EXCLUDED.notes,
           verification_status = EXCLUDED.verification_status,
           last_verified_at = EXCLUDED.last_verified_at,
           source_id = EXCLUDED.source_id,
           updated_at = NOW()
       RETURNING gp.article_gym_id
   )
   DELETE FROM gym_equipments WHERE gym_id IN (SELECT article_gym_id FROM gym_pair);
   DELETE FROM gyms WHERE id IN (SELECT article_gym_id FROM gym_pair);
   ```

2. 念のため残存データの重量を正規化（負値を NULL 化）

   ```sql
   UPDATE gym_equipments SET max_weight_kg = NULL WHERE max_weight_kg < 0;
   ```

実行後は `SELECT * FROM gyms WHERE official_url ~ '/introduction/(post_|tr_detail\\.html|trainingmachine\\.html|notes\\.html)$';` を確認し、記事ページ由来のジムが消えていることを検証してください。

---

# 動作確認コマンドの再掲（最短セット）

```bash
# 0) コンテナ起動
docker compose up -d db adminer api

# 1) マイグレーション（初回 or DB作り直し時）
docker compose exec api bash -lc '
  export DATABASE_URL="postgresql+asyncpg://appuser:apppass@db:5432/gym_directory"
  alembic upgrade head
'

# 2) シード
docker compose exec api bash -lc '
  export DATABASE_URL="postgresql+asyncpg://appuser:apppass@db:5432/gym_directory"
  export PYTHONPATH=/app
  python -m scripts.seed
'

# 3) エンドポイント疎通（代表例）
curl -sS 'http://localhost:8000/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=5' | jq .
curl -sS 'http://localhost:8000/gyms/search?pref=chiba&city=funabashi&equipments=squat-rack,dumbbell&equipment_match=any&sort=richness' | jq .
```

---

## 追加エンドポイント（Meta / Suggest）

- Meta
  - `GET /meta/prefectures` — 登録済みジムの都道府県スラッグを重複なしで返却（空/NULL除外）
  - `GET /meta/cities?pref=chiba` — 指定都道府県内の市区町村スラッグと件数を返却（既存）
  - `GET /meta/equipment-categories` — 登録済み設備カテゴリを重複なしで返却（空/NULL除外）
- Suggest
  - `GET /suggest/equipments?q=ベンチ&limit=5` — equipments.name を ILIKE 部分一致で検索し、名前配列を返却

動作例（ローカル）

```bash
curl -sS 'http://localhost:8000/meta/prefectures' | jq .
curl -sS 'http://localhost:8000/meta/equipment-categories' | jq .
curl -sS 'http://localhost:8000/suggest/equipments?q=ベンチ&limit=5' | jq .
```

## 動作確認（/gyms/nearby）

> 事前に `alembic upgrade head` と `python -m scripts.seed` を実施し、
> `gyms.latitude/longitude` が入っていることを前提にしています。

```bash
# 近い順（半径5km）
curl -sS 'http://localhost:8000/gyms/nearby?lat=35.0&lng=139.0&radius_km=5&per_page=10' | jq .

# 次ページ（page_token をそのまま利用）
TOKEN=$(curl -sS 'http://localhost:8000/gyms/nearby?lat=35.0&lng=139.0&radius_km=5&per_page=2' | jq -r '.page_token')
curl -sS "http://localhost:8000/gyms/nearby?lat=35.0&lng=139.0&radius_km=5&per_page=2&page_token=${TOKEN}" | jq .
```

## マイグレーション（pg_trgm + GIN index）

ILIKE 検索最適化のため、`pg_trgm` 拡張と `equipments.name` への GIN インデックスを追加しました。

Docker 環境で適用:

```bash
docker compose up -d
docker compose exec api alembic upgrade head
```

Makefile を使う場合:

```bash
make up
make migrate
```

ローカル環境（Docker未使用）の場合:

```bash
export DATABASE_URL=postgresql+psycopg2://appuser:apppass@localhost:5432/gym_directory
alembic upgrade head
```

---

## コミット前の自動整形・Lint（pre-commit）

このリポジトリはコミット時に Ruff のフォーマットと自動修正（--fix）を実行します。

手順:

- 開発用ツールをインストール: `pip install -r requirements-dev.txt`
- Git フックを有効化: `make pre-commit-install`
- 必要に応じて全ファイルに実行: `make pre-commit-run`

実行される内容:

- `ruff --fix`（Lint の自動修正）
- `ruff format`（コード整形）

## /gyms/search スコアソート

総合スコア = `freshness(0.6) + richness(0.4)`（値は .env で調整可能）

```bash
# 1ページ目（score がデフォルト）
curl -sG --data-urlencode "pref=chiba" \
         --data-urlencode "city=funabashi" \
         --data-urlencode "per_page=3" \
         "http://localhost:8000/gyms/search" | jq

# 次ページ
pt=$(curl -sG --data-urlencode "sort=score" --data-urlencode "per_page=3" \
      "http://localhost:8000/gyms/search" | jq -r .page_token)
curl -sG --data-urlencode "sort=score" --data-urlencode "per_page=3" \
         --data-urlencode "page_token=$pt" \
         "http://localhost:8000/gyms/search" | jq
```

## 🧪 テスト

- E2E テストの背景や手順は [docs/testing/e2e.md](docs/testing/e2e.md) を参照してください。
- ローカルでの最小実行例: `(cd frontend && npm ci && npm run e2e:install && npm run test:e2e)`
