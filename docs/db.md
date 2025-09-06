# データベース設計ドキュメント（MVP版）

目的：ジム設備の情報を統一フォーマットで保持し、**検索（一覧）→ 詳細**が高速かつ整合的に動くこと。  
本ドキュメントは「列定義 / 制約 / インデックス / ルール / 例」を明記します。

---

## 0. 全体像（ER 概要）

- **gyms** … ジム（店舗）マスタ
- **equipments** … 設備マスタ（標準化された設備種別）
- **gym_equipments** … ジム × 設備 の関係（有/無/不明、台数、最大重量、最終確認、出典 等）
- **sources** … 情報の出典（公式サイト、ユーザー投稿、掲示、SNS等）
- **user_submissions** … ユーザーからの投稿（後で検証して反映）

主な関係：
- `gym_equipments.gym_id → gyms.id`（多対一）
- `gym_equipments.equipment_id → equipments.id`（多対一）
- `gym_equipments.source_id → sources.id`（多対一／任意）
- `user_submissions.gym_id → gyms.id`（多対一）
- `user_submissions.equipment_id → equipments.id`（任意・SET NULL）

---

## 1) テーブル：gyms（ジム）

### 目的
店舗の基本属性と、一覧ソート用に**最終更新日のキャッシュ**を保持。

### カラム定義
| 列名 | 型 | NULL | 既定値 | 説明 |
|---|---|---|---|---|
| id | INTEGER (PK) | NO | | 主キー |
| name | VARCHAR | NO | | 店舗名（例：ダミージム 船橋イースト） |
| chain_name | VARCHAR | YES | | チェーン名（Anytime 等） |
| slug | VARCHAR (UNIQUE, INDEX) | NO | | URL用キー（例：dummy-funabashi-east） |
| address | VARCHAR | YES | | 住所（任意） |
| prefecture | VARCHAR | YES | | 都道府県スラッグ（例：chiba） |
| city | VARCHAR | YES | | 市区町村スラッグ（例：funabashi） |
| official_url | VARCHAR | YES | | 公式ページURL |
| affiliate_url | VARCHAR | YES | | アフィリエイトURL（将来） |
| owner_verified | BOOLEAN | NO | FALSE | オーナー承認済みか |
| last_verified_at_cached | TIMESTAMPTZ | YES | | **ジム単位の最新確認日時（キャッシュ）** |
| created_at | TIMESTAMPTZ | NO | now() | 作成時刻 |
| updated_at | TIMESTAMPTZ | NO | now() | 更新時刻 |

### 制約
- **PK**: `id`
- **UNIQUE**: `slug`

### インデックス
- `ix_gyms_pref_city (prefecture, city)` … エリア検索高速化
- `slug` は UNIQUE + INDEX

### データルール
- `slug` は一意・URL安全な文字列
- `prefecture/city` は文字列のまま（将来正規化予定）
- `last_verified_at_cached` は `gym_equipments.last_verified_at` の最大値を**同期**（API/バッチどちらでも可）

### 例
| id | name | slug | prefecture | city | last_verified_at_cached |
|---|---|---|---|---|---|
| 1 | ダミージム 船橋イースト | dummy-funabashi-east | chiba | funabashi | 2025-09-01T12:00:00Z |

---

## 2) テーブル：equipments（設備マスタ）

### 目的
設備名とカテゴリを**標準化**して検索・比較を容易にする。

### カラム定義
| 列名 | 型 | NULL | 既定値 | 説明 |
|---|---|---|---|---|
| id | INTEGER (PK) | NO | | 主キー |
| name | VARCHAR | NO | | 名称（例：スクワットラック） |
| slug | VARCHAR (UNIQUE) | NO | | URL用キー（例：squat-rack） |
| category | VARCHAR | NO | | `free_weight` / `machine` / `cardio` / `other` |
| description | VARCHAR | YES | | 補足 |
| created_at | TIMESTAMPTZ | NO | now() | 作成時刻 |
| updated_at | TIMESTAMPTZ | NO | now() | 更新時刻 |

### 制約
- **PK**: `id`
- **UNIQUE**: `slug`

### インデックス
- `slug` は UNIQUE + INDEX

### データルール
- カテゴリは固定語彙（UI側辞書でラベル表示）
- 同義語はフロント/収集側でマッピングしてから登録

### 例
| id | name | slug | category |
|---|---|---|---|
| 10 | スクワットラック | squat-rack | free_weight |

---

## 3) テーブル：gym_equipments（ジム×設備）

### 目的
ジムごとの設備有無・台数・最大重量・最終確認・検証状態・出典を保持。**一覧のハイライト/スコア**の材料。

### カラム定義
| 列名 | 型 | NULL | 既定値 | 説明 |
|---|---|---|---|---|
| id | INTEGER (PK) | NO | | 主キー |
| gym_id | INTEGER (FK gyms.id) | NO | | 対象ジム |
| equipment_id | INTEGER (FK equipments.id) | NO | | 対象設備 |
| availability | ENUM | NO | `unknown` | `present` / `absent` / `unknown` |
| count | INTEGER | YES | | 台数（不明は NULL、0 は明示的なゼロ） |
| max_weight_kg | INTEGER | YES | | 最大重量（ダンベル等。不明は NULL） |
| notes | VARCHAR | YES | | 備考 |
| verification_status | ENUM | NO | `unverified` | `unverified` / `user_verified` / `owner_verified` / `admin_verified` |
| last_verified_at | TIMESTAMPTZ | YES | | **このレコード**の最終確認日時 |
| source_id | INTEGER (FK sources.id) | YES | | 直近の確認出典（任意） |
| created_at | TIMESTAMPTZ | NO | now() | 作成 |
| updated_at | TIMESTAMPTZ | NO | now() | 更新 |

### 制約
- **PK**: `id`
- **UNIQUE**: `(gym_id, equipment_id)` … 同じ組み合わせの重複登録を禁止
- **CHECK**:
  - `count IS NULL OR count >= 0`
  - `max_weight_kg IS NULL OR max_weight_kg >= 0`

### インデックス
- `ix_gym_eq_gym (gym_id)`
- `ix_gym_eq_eq (equipment_id)`
- `ix_gym_eq_last_verified (last_verified_at)`
- **部分インデックス**: `ix_gym_eq_present ON gym_equipments (gym_id) WHERE availability='present'`
  - “present だけ見たい”集計/検索の高速化に有効

### データルール
- **不明は NULL**、同時に `availability="unknown"` を返す（APIで表現統一）
- `verification_status` は**証跡の強さ**（`owner_verified` ＞ `user_verified` ＞ `unverified`）
- `last_verified_at` は**行単位**の鮮度（→ `gyms.last_verified_at_cached` はジム全体の最大）

### 例
| gym_id | equipment_id | availability | count | max_weight_kg | verification_status | last_verified_at |
|---|---|---|---|---|---|---|
| 1 | 10 | present | 2 | NULL | user_verified | 2025-09-01T12:00:00Z |
| 1 | 12 | present | 6 | NULL | user_verified | 2025-08-28T08:30:00Z |
| 1 | 3 | present | NULL | 40 | unverified | 2025-08-20T10:00:00Z |
| 2 | 10 | absent | NULL | NULL | unverified | 2025-08-15T09:00:00Z |

---

## 4) テーブル：sources（出典）

### 目的
データの**根拠**を記録し、信頼性のラベル付けや履歴管理に備える。

### カラム定義
| 列名 | 型 | NULL | 既定値 | 説明 |
|---|---|---|---|---|
| id | INTEGER (PK) | NO | | 主キー |
| source_type | ENUM | NO | | `official_site` / `on_site_signage` / `user_submission` / `media` / `sns` / `other` |
| title | VARCHAR | YES | | タイトル（例：公式店舗ページ、ユーザー投稿#123 等） |
| url | VARCHAR | YES | | URL（あれば） |
| captured_at | TIMESTAMPTZ | YES | | 取得/撮影日 |
| created_at | TIMESTAMPTZ | NO | now() | 作成 |

### 制約・インデックス
- **PK**: `id`
- enum 補助インデックスは現状不要（件数少ない想定）

### 例
| id | source_type | title | url | captured_at |
|---|---|---|---|---|
| 1 | user_submission | ダミー投稿（seed） | NULL | 2025-09-01T12:00:00Z |

---

## 5) テーブル：user_submissions（ユーザー投稿）

### 目的
ユーザーの設備情報投稿を受け取り、後で検証・反映して `gym_equipments` を更新。

### カラム定義
| 列名 | 型 | NULL | 既定値 | 説明 |
|---|---|---|---|---|
| id | INTEGER (PK) | NO | | 主キー |
| gym_id | INTEGER (FK gyms.id) | NO | | 投稿対象ジム |
| equipment_id | INTEGER (FK equipments.id) | YES | | 任意（自由記述対応のため NULL 可） |
| payload_json | VARCHAR | YES | | 任意フィールド（後で JSON 型移行可） |
| photo_url | VARCHAR | YES | | 画像URL（任意） |
| visited_at | TIMESTAMPTZ | YES | | 実際に見に行った日時 |
| status | ENUM | NO | `pending` | `pending` / `corroborated` / `approved` / `rejected` |
| created_by_user_id | INTEGER | YES | | 将来のユーザーID（匿名は NULL） |
| created_at | TIMESTAMPTZ | NO | now() | 作成 |
| updated_at | TIMESTAMPTZ | NO | now() | 更新 |

### 制約
- **PK**: `id`
- FK: `gym_id`（CASCADE）、`equipment_id`（SET NULL）

### 運用ルール（例）
- `pending` → （他出典と合致などで）`corroborated` → `approved`  
- `approved` 時に `gym_equipments` を更新し、該当行の `verification_status/last_verified_at/source_id` を上書き

---

## 6) Enum 一覧（現行仕様）

- **Availability**: `present` / `absent` / `unknown`  
  - 不明値は `NULL` を許容 + `availability="unknown"` を返すポリシー
- **VerificationStatus**: `unverified` / `user_verified` / `owner_verified` / `admin_verified`
- **SourceType**: `official_site` / `on_site_signage` / `user_submission` / `media` / `sns` / `other`
- **SubmissionStatus**: `pending` / `corroborated` / `approved` / `rejected`

> 注：PostgreSQL のネイティブ ENUM は変更（値追加）が厳密。将来増やす場合は  
> `TEXT + CHECK` 制約への移行も検討。

---

## 7) インデックス戦略

- **検索キー**：`prefecture, city`（複合）  
- **JOIN頻出**：`gym_equipments.gym_id`, `gym_equipments.equipment_id`  
- **鮮度ソート**：`gym_equipments.last_verified_at`（+ `gyms.last_verified_at_cached` を使用）  
- **部分インデックス**：`availability='present'`（present のみ集計/検索）

---

## 8) データ鮮度（キャッシュ列の使い方）

- **gyms.last_verified_at_cached** は、該当ジムの `gym_equipments.last_verified_at` の **最大値** を保持  
- 更新契機：
  - `gym_equipments` 追加/更新時に API 側で再計算して保存（MVPの簡易運用）
  - 将来は DB トリガ or バッチで自動同期
- 検索 `/gyms/search?sort=freshness` はこの列で並べると軽い

---

## 9) 命名・値の扱い方針

- **スラッグ**：小文字・ハイフン区切り（`dummy-funabashi-east`）  
- **NULL と unknown**：  
  - 台数や最大重量は **不明なら NULL**  
  - 同時に `availability="unknown"` をセットし、APIで明示的に“不明”を表示  
- **ユニーク性**：  
  - `gyms.slug` / `equipments.slug` / `(gym_id, equipment_id)` を **物理制約**で担保

---

## 10) 既知の制約・将来の拡張

- **複数出典の紐づけ**：現在は `gym_equipments.source_id` の単一参照のみ。  
  → 将来：`gym_equipment_sources (gym_equipment_id, source_id)` の中間表で多対多化
- **住所正規化 / ジオ**：`prefecture/city` は文字列。  
  → 将来：`areas` テーブルや座標列（lat/lng）を追加
- **ENUM拡張**：値追加の頻度次第で `TEXT + CHECK` へ移行

---

## 11) 品質基準（守るべきルール）

1. **不明値は NULL**、UI/APIで `unknown` を明示  
2. **出典と最終更新**を常に保持（`last_verified_at` / `source_id`）  
3. **重複不可**：同一ジム×設備は1行のみ  
4. **負の値禁止**：`count` / `max_weight_kg` は 0 以上  
5. **検索性能**：エリア・JOIN・鮮度のインデックスを維持

---

## 12) サンプル問い合わせ（想定）

- 「船橋でスクワットラックが**ある**ジムを新しい順」
  - `prefecture='chiba' AND city='funabashi'` で `gyms` 抽出  
  - `gym_equipments.availability='present' AND equipment.slug='squat-rack'` をJOIN  
  - 並び替えは `gyms.last_verified_at_cached DESC`

---
