# SQLAlchemy & Alembic 超入門（実装付き）

## これは何？
- **SQLAlchemy**：Python から DB（PostgreSQL など）を触るためのライブラリ。  
  - **ORM**（Object-Relational Mapping）：Pythonクラス ⇄ DBテーブル を対応させて、SQLを書かずに `.query()` のように操作できる。
- **Alembic**：SQLAlchemy 用の **マイグレーションツール**。  
  - 「モデルが変わったら差分SQL（DDL）を作ってDBを更新」する仕組み。

> メリット  
> - **SQLを手書きしない**で安全にテーブル作成・更新ができる  
> - Windows → Mac でも **同じコマンド**で環境を再現できる（Docker + Alembic）

---

## 0) 前提（インストール済み）
- `requirements.txt` に `fastapi / SQLAlchemy / alembic / psycopg2-binary` が入っている  
- `docker compose up -d` で `api` と `db` が起動する  
- `.env` に `DATABASE_URL=postgresql+psycopg2://appuser:apppass@db:5432/gym_directory`

---

## 1) DB接続と Base の用意

**app/db.py** を以下の形にしておく（Base = モデルの親クラスの“設計図”）
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# すべてのモデルはこの Base を継承する
Base = declarative_base()
