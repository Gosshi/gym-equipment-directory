# parsed_json 仕様書

`gyms` および `gym_candidates` テーブルの `parsed_json` カラムに保存されるJSONオブジェクトの仕様書。

---

## 概要

`parsed_json` はスクレイピング・解析処理で抽出された施設情報を格納するJSONBフィールドです。  
正規化されたカラムに収まらない詳細情報や、カテゴリ固有のメタデータを保持します。

---

## トップレベルフィールド

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `facility_name` | string | ○ | 施設名 |
| `address` | string | - | 住所 |
| `page_url` | string | - | 情報取得元ページURL |
| `official_url` | string | - | 施設公式サイトURL |
| `categories` | string[] | ○ | 施設カテゴリ配列 |
| `is_gym` | boolean | - | トレーニング室があるか |
| `equipments` | string[] | - | 設備名リスト |
| `page_type` | string | - | ページ種別 (`intro`, `detail`, `list` 等) |
| `center_no` | string | - | 施設番号 (自治体管理用) |
| `meta` | object | - | メタ情報オブジェクト |

---

## categories 配列

施設が対応するカテゴリのリスト。複合施設の場合は複数含む。

| 値 | 説明 |
|---|---|
| `gym` | トレーニング室・ジム |
| `pool` | プール |
| `court` | コート (テニス、バスケ等) |
| `field` | グラウンド・野球場 |
| `hall` | 体育館 |
| `studio` | スタジオ |
| `archery` | 弓道場 |
| `martial_arts` | 武道場 |

---

## meta オブジェクト

解析時のメタ情報。

| フィールド | 型 | 説明 |
|---|---|---|
| `category` | string | 主カテゴリ (legacy, `categories[0]` と同等) |
| `categories` | string[] | カテゴリ配列のコピー |
| `page_url` | string | 情報取得元URL |
| `create_gym` | boolean | Gym レコード作成対象か |
| `is_multi_facility` | boolean | 複合施設か |
| `hours` | object | 営業時間 |
| `fee` | object/int | 利用料金 |

### hours オブジェクト

```json
{
  "open": 900,   // 開始時刻 (HHMM形式、例: 9:00)
  "close": 2100  // 終了時刻 (HHMM形式、例: 21:00)
}
```

### fee オブジェクト

```json
{
  "adult": 300,    // 大人料金
  "child": 50,     // 子供料金
  "senior": 200,   // シニア料金
  "per_hour": 500, // 1時間あたり
  "monthly": 5000  // 月額
}
```

---

## カテゴリ固有オブジェクト

`categories` に含まれるカテゴリに応じて、対応するオブジェクトが含まれる。

### gym オブジェクト

```json
{
  "equipments": ["トレッドミル", "ダンベル", "ベンチプレス"]
}
```

### pool オブジェクト

| フィールド | 型 | 説明 |
|---|---|---|
| `lanes` | int | レーン数 |
| `length_m` | int | 長さ (メートル) |
| `heated` | boolean | 温水プールか |

```json
{
  "lanes": 6,
  "length_m": 25,
  "heated": true
}
```

### court オブジェクト

| フィールド | 型 | 説明 |
|---|---|---|
| `court_type` | string | コート種別 (庭球場、バスケットコート等) |
| `courts` | int | 面数 |
| `surface` | string | 表面素材 (クレー、人工芝等) |
| `lighting` | boolean | 照明設備有無 |

```json
{
  "court_type": "庭球場",
  "courts": 4,
  "surface": "クレー",
  "lighting": true
}
```

### field オブジェクト

| フィールド | 型 | 説明 |
|---|---|---|
| `field_type` | string | グラウンド種別 (野球場、サッカー場等) |
| `fields` | int | 面数 |
| `lighting` | boolean | 照明設備有無 |

```json
{
  "field_type": "野球場",
  "fields": 2,
  "lighting": true
}
```

### hall オブジェクト

| フィールド | 型 | 説明 |
|---|---|---|
| `sports` | string[] | 対応スポーツ |
| `area_sqm` | int | 面積 (平方メートル) |

```json
{
  "sports": ["バスケットボール", "バレーボール", "バドミントン"],
  "area_sqm": 1200
}
```

### archery オブジェクト

| フィールド | 型 | 説明 |
|---|---|---|
| `archery_type` | string | 弓道場種別 |
| `rooms` | int | 室数 |

```json
{
  "archery_type": "弓道場",
  "rooms": 1
}
```

---

## サンプル (複合施設)

```json
{
  "facility_name": "上高田運動施設(野球場・庭球場)",
  "address": "東京都中野区上高田五丁目6番1号",
  "page_url": "https://example.com/facility",
  "official_url": "https://example.com",
  "categories": ["field", "court", "archery"],
  "is_gym": false,
  "meta": {
    "hours": { "open": 900, "close": 2100 },
    "category": "field",
    "categories": ["field", "court", "archery"],
    "is_multi_facility": true
  },
  "field": {
    "field_type": "野球場",
    "fields": 2,
    "lighting": true
  },
  "court": {
    "court_type": "庭球場",
    "courts": 4,
    "surface": null,
    "lighting": false
  },
  "archery": {
    "archery_type": "弓道場",
    "rooms": 1
  }
}
```

---

## バージョン履歴

| 日付 | 変更内容 |
|---|---|
| 2025-12-30 | 初版作成。categories 統一に伴い仕様明文化 |
