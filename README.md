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
> - Docker Compose の DB サービス名: `db`（PostgreSQL 16）
> - アプリはコンテナ間で DB に接続する
> - 接続文字列（**固定**）  
>   `DATABASE_URL=postgresql+asyncpg://appuser:apppass@db:5432/gym_directory`

1. コンテナ起動（DB と Adminer）
   ```bash
   docker compose up -d db adminer
   docker compose exec db pg_isready -U appuser -d gym_directory
```

2. **マイグレーション適用（必須）**

   * コンテナ内で実行（import パスが確実）

   ```bash
   docker compose exec api bash -lc '
     export DATABASE_URL="postgresql+asyncpg://appuser:apppass@db:5432/gym_directory"
     alembic upgrade head
   '
   ```

3. **シード投入**

   ```bash
   docker compose exec api bash -lc '
     export DATABASE_URL="postgresql+asyncpg://appuser:apppass@db:5432/gym_directory"
     export PYTHONPATH=/app
     python -m scripts.seed
   '
   ```

4. スキーマ確認（任意）

   ```bash
   docker compose exec db psql -U appuser -d gym_directory -c "\dt"
   # gyms / equipments / gym_equipments / sources が表示されればOK
   ```

---

## アプリ起動

### ローカルで uvicorn を起動する場合

```bash
export DATABASE_URL="postgresql+asyncpg://appuser:apppass@127.0.0.1:5432/gym_directory"
python -m uvicorn app.api.main:app --reload --port 8001
```

### Compose の `api` サービスで起動する場合

* `.env` に **必ず** 次を入れておく：

  ```
  DATABASE_URL=postgresql+asyncpg://appuser:apppass@db:5432/gym_directory
  ```
* 起動：

  ```bash
  docker compose up -d api
  ```

---

## 動作確認（/gyms/search）

> 例では pref/city と seed 済みデータを想定。環境に合わせて調整してください。

```bash
# 1) freshness（最新順）
curl -sS 'http://localhost:8001/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=5' | jq .

# 2) richness（設備スコア順 / any）
curl -sS 'http://localhost:8001/gyms/search?pref=chiba&city=funabashi&equipments=squat-rack,dumbbell&equipment_match=any&sort=richness&per_page=10' | jq .

# 3) name 昇順（keyset）
curl -sS 'http://localhost:8001/gyms/search?pref=chiba&city=funabashi&sort=gym_name&per_page=5' | jq .

# 4) created_at 降順（keyset）
curl -sS 'http://localhost:8001/gyms/search?pref=chiba&city=funabashi&sort=created_at&per_page=5' | jq .

# 5) ページング継続（例：1ページ目の page_token を使って2ページ目を取得）
TOKEN=$(curl -sS 'http://localhost:8001/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=2' | jq -r '.page_token')
curl -sS "http://localhost:8001/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=2&page_token=${TOKEN}" | jq .
```

### よくあるハマりどころ

* **DBを作り直したら**、必ず `alembic upgrade head` → `python -m scripts.seed` の順に実行。
* ローカル uvicorn のときは `@127.0.0.1:5432`、コンテナ内からは `@db:5432` を使う。
* `DATABASE_URL` は **.env** と **起動シェルの環境変数**の優先度に注意（起動前に `echo $DATABASE_URL` で確認）。


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
curl -sS 'http://localhost:8001/gyms/search?pref=chiba&city=funabashi&sort=freshness&per_page=5' | jq .
curl -sS 'http://localhost:8001/gyms/search?pref=chiba&city=funabashi&equipments=squat-rack,dumbbell&equipment_match=any&sort=richness' | jq .
```
