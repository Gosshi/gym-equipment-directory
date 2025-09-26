# 開発メモ: Alembic とジム鮮度キャッシュ自動更新

## 今日やったこと

### 1. 鮮度キャッシュ列の自動更新を導入

- 対象: `gyms.last_verified_at_cached`
- ジムや設備が更新されたら、自動で最新値に更新されるようにした
- PostgreSQL の **トリガ関数**を利用
  - 更新時にトリガ発火
  - 関数 `REFRESH_GYM_FRESHNESS()` が呼ばれて再計算
  - 「ジム自身の `last_verified_at`」と「紐づく設備の `last_verified_at`」の **最大値** をセット

### 2. 多対多テーブルに対応

- 当初は `equipments.gym_id` を参照していたが、実際には中間テーブル `gym_equipments` を使っていた
- 関数を修正し、`gym_equipments JOIN equipments` 経由で最新設備日時を取るよう変更

### 3. Alembic で反映

- マイグレーションファイルを作成し、関数とトリガを組み込み
- 途中で発生したエラー
  - `EXECUTE PROCEDURE` → **Postgres12+ は `EXECUTE FUNCTION` が正**
  - `gyms.last_verified_at` 列が存在しない → `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` を追加
  - `equipments.gym_id` が存在しない → `gym_equipments` 経由に修正
- これにより **`alembic upgrade head` が成功し、鮮度キャッシュの自動更新が完成**

---

## Alembic の基本

### コマンド

- **新しいマイグレーションファイルを作成**
  ```bash
  alembic revision -m "説明文"
  ```
- **差分を自動検出して作成**
  ```bash
  alembic revision --autogenerate -m "説明文"
  ```
- **最新バージョンまで反映**
  ```bash
  alembic upgrade head
  ```
- **1つ前に戻す**
  ```bash
  alembic downgrade -1
  ```
- **現在のバージョンを確認**
  ```bash
  alembic current
  ```

### ディレクトリ構成

- `alembic.ini` : 設定ファイル（DB URL など）
- `migrations/env.py` : 実行環境設定（Base, DB接続など）
- `migrations/versions/*.py` : 個別のマイグレーション
  - `upgrade()` : 適用時の処理
  - `downgrade()` : 巻き戻し時の処理

---

## 今日の成果を一言で

**ジムと設備の更新に合わせて `gyms.last_verified_at_cached` が常に最新化されるよう、  
Alembic マイグレーションを使ってトリガ関数をDBに組み込んだ。**

---

## 次の理解ステップ

1. **簡単な列追加マイグレーションで練習**

   ```bash
   alembic revision -m "add dummy column"
   ```

   ```python
   def upgrade():
       op.add_column("gyms", sa.Column("dummy", sa.String(), nullable=True))

   def downgrade():
       op.drop_column("gyms", "dummy")
   ```

   - `alembic upgrade head` → 列追加
   - `alembic downgrade -1` → 列削除

2. この体験で「Alembic はコードで DB をバージョン管理する仕組み」と理解できる。

---

## 健全性チェック SQL（再掲）

```sql
SELECT COUNT(*) AS bad_rows
FROM gyms g
WHERE g.last_verified_at_cached IS DISTINCT FROM GREATEST(
  COALESCE(g.last_verified_at, '-infinity'::timestamptz),
  COALESCE((SELECT MAX(e.last_verified_at)
              FROM gym_equipments ge
              JOIN equipments e ON e.id = ge.equipment_id
             WHERE ge.gym_id = g.id),
           '-infinity'::timestamptz)
);
```

0件なら整合性はOK。
