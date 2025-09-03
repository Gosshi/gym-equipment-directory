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