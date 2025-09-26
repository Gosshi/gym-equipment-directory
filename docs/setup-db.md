# Alembic & SQLAlchemy セットアップまとめ

## 1. 発生した問題

- エラー内容: `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:driver`
- 原因: `DATABASE_URL` の形式が不正だったため、SQLAlchemy がドライバを解決できなかった。

---

## 2. 解決方法

1. `.env` の `DATABASE_URL` を正しい形式に修正
   - NG: `postgres://...`
   - OK: `postgresql://...` または `postgresql+psycopg2://...`

2. `alembic.ini` または `migrations/env.py` に、正しい `DATABASE_URL` を設定
   - 直書き or 環境変数から読み込む方法のどちらかに統一

3. コンテナを再起動し、Alembic コマンドを再実行
   - `docker compose down`
   - `docker compose up -d --build`
   - `docker compose exec api alembic upgrade head`

---

## 3. 動作確認

- `docker compose exec api python -c "import os;from sqlalchemy import create_engine;print(create_engine(os.getenv('DATABASE_URL')))"`  
  を実行し、`Engine(postgresql+psycopg2://...)` が表示されれば成功。
- Adminer で接続し、テーブルが確認できることをチェック。

---

## 4. 学び

- SQLAlchemy の接続URLは「方言（dialect）+ドライバ」で指定する必要がある。  
  例: `postgresql+psycopg2://user:pass@host:port/dbname`
- Alembic は `alembic.ini` と `env.py` の両方でURL設定が可能。矛盾しないようにする。
- Docker を使えば、WindowsでもMacでも同じ手順で環境を再現できる。

---

## 5. 次のステップ

- モデル定義（`gyms`, `equipments`, `gym_equipments`, など）を追加
- Alembic の `revision --autogenerate` で差分マイグレーションを生成
- 初期データ投入スクリプトを作成し、検索API実装に進む
