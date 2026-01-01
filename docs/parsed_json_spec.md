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
| `tags` | string[] | - | 施設タグ (`parking`, `shower` 等) |

---

## categories 配列

施設が対応するカテゴリのリスト。複合施設の場合は複数含む。

| 値 | 説明 | 対応オブジェクト |
|---|---|---|
| `gym` | トレーニング室・ジム | `gym` |
| `pool` | プール | `pool` |
| `court` | コート (テニス、バスケ等) | `court` |
| `field` | グラウンド・野球場 | `field` |
| `hall` | 体育館 | `hall` |
| `studio` | スタジオ | `studio` |
| `archery` | 弓道場 | `archery` |
| `martial_arts` | 武道場 | `martial_arts` |

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

---

### gym オブジェクト

トレーニング室・ジムの情報。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `equipments` | array | - | 設備情報配列 |

#### equipments 配列アイテム

| フィールド | 型 | 説明 |
|---|---|---|
| `slug` | string | 設備の識別子 (`treadmill`, `dumbbell` 等) |
| `count` | int | 台数 |

```json
{
  "equipments": [
    {"slug": "treadmill", "count": 5},
    {"slug": "dumbbell", "count": 10},
    {"slug": "bench_press", "count": 2}
  ]
}
```

**主な設備slug:**
- `treadmill` - トレッドミル
- `bike` - エアロバイク
- `dumbbell` - ダンベル
- `bench_press` - ベンチプレス
- `cable_machine` - ケーブルマシン
- `smith_machine` - スミスマシン
- `leg_press` - レッグプレス
- `rowing_machine` - ローイングマシン

---

### pool オブジェクト

プール施設の情報。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `lanes` | int | - | レーン数 |
| `length_m` | int | - | プールの長さ (メートル) |
| `heated` | boolean | - | 温水プールか |
| `depth_m` | float | - | 水深 (メートル) |
| `type` | string | - | プール種別 (`競泳用`, `子供用`, `流水` 等) |

```json
{
  "lanes": 6,
  "length_m": 25,
  "heated": true,
  "depth_m": 1.2
}
```

**length_m の典型値:**
- `25` - 25mプール (一般的)
- `50` - 50mプール (競泳用)
- `15` - 15mプール (小規模施設)

---

### court オブジェクト

コート施設の情報。テニス、バスケ、バドミントン等の屋外・屋内コートを含む。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `courts` | array | ○ | コートタイプ別の配列 |

#### courts 配列アイテム

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `court_type` | string | ○ | コート種別 |
| `count` | int | ○ | 面数 |
| `surface` | string | - | コート素材 |
| `lighting` | boolean | - | 照明設備の有無 |

```json
{
  "courts": [
    {"court_type": "テニス", "count": 4, "surface": "砂入り人工芝", "lighting": true},
    {"court_type": "バスケットボール", "count": 1, "surface": "床", "lighting": true},
    {"court_type": "バドミントン", "count": 6, "surface": "床", "lighting": true},
    {"court_type": "卓球", "count": 10}
  ]
}
```

**court_type の値:**

| カテゴリ | 値の例 |
|---------|--------|
| テニス系 | `テニス`, `テニスコート`, `庭球`, `硬式テニス`, `軟式テニス`, `ソフトテニス` |
| 球技系 | `バスケットボール`, `バレーボール`, `フットサル`, `ハンドボール` |
| ネット系 | `バドミントン`, `卓球` |
| その他 | `多目的コート`, `テニス・フットサル兼用` |

**surface の値:**

| 種別 | 値 | 主な用途 |
|------|-----|----------|
| 屋外テニス | `砂入り人工芝`, `オムニコート`, `クレー`, `ハードコート` | テニス |
| 屋内 | `床`, `フローリング`, `体育館床面` | バスケ、バレー、バドミントン |
| 屋外多目的 | `人工芝`, `天然芝`, `土` | フットサル等 |

---

### hall オブジェクト

体育館・アリーナの情報。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `sports` | string[] | - | 対応スポーツ一覧 |
| `area_sqm` | int/float | - | 面積 (平方メートル) |
| `capacity` | int | - | 収容人数 |

```json
{
  "sports": ["バスケットボール", "バレーボール", "バドミントン", "卓球", "体操"],
  "area_sqm": 1200
}
```

**sports の値:**
- `バスケットボール`, `バレーボール`, `バドミントン`
- `卓球`, `体操`, `ダンス`, `エアロビクス`
- `柔道`, `剣道`, `空手`
- `フットサル`, `ハンドボール`

---

### field オブジェクト

グラウンド・運動場の情報。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `field_type` | string | - | グラウンド種別 |
| `fields` | int | - | 面数 |
| `lighting` | boolean | - | 照明設備の有無 |
| `surface` | string | - | 表面素材 |

```json
{
  "field_type": "野球場",
  "fields": 2,
  "lighting": true,
  "surface": "人工芝"
}
```

**field_type の値:**
- `野球場`, `軟式野球場`, `ソフトボール場`
- `サッカー場`, `ラグビー場`
- `陸上競技場`, `多目的グラウンド`
- `ゲートボール場`, `グラウンドゴルフ場`

**surface の値:**
- `人工芝`, `天然芝`, `土`, `クレー`, `アンツーカー`

---

### archery オブジェクト

弓道場・アーチェリー場の情報。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `archery_type` | string | - | 弓道場種別 |
| `rooms` | int | - | 室数・射場数 |
| `targets` | int | - | 的の数 |
| `distance_m` | int | - | 射距離 (メートル) |

```json
{
  "archery_type": "近的場",
  "rooms": 1,
  "targets": 6,
  "distance_m": 28
}
```

**archery_type の値:**
- `弓道場` - 一般的な弓道場
- `近的場` - 28m射程の弓道場
- `遠的場` - 60m射程の弓道場
- `アーチェリー場` - 洋弓場

---

### martial_arts オブジェクト

武道場の情報。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `martial_arts_type` | string | - | 武道場種別 |
| `rooms` | int | - | 室数 |
| `tatami_count` | int | - | 畳数 |

```json
{
  "martial_arts_type": "柔剣道場",
  "rooms": 1,
  "tatami_count": 120
}
```

**martial_arts_type の値:**
- `柔道場`, `剣道場`, `柔剣道場`
- `空手道場`, `合気道場`
- `武道場` (多目的)

---

### studio オブジェクト

スタジオ・多目的室の情報。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `rooms` | int | - | 室数 |
| `area_sqm` | int/float | - | 面積 (平方メートル) |
| `mirror` | boolean | - | 鏡の有無 |
| `activities` | string[] | - | 対応アクティビティ |

```json
{
  "rooms": 2,
  "area_sqm": 80,
  "mirror": true,
  "activities": ["ダンス", "ヨガ", "エアロビクス"]
}
```

---

## サンプル (複合施設)

```json
{
  "facility_name": "○○スポーツセンター",
  "address": "東京都○○区△△1-2-3",
  "page_url": "https://example.com/facility",
  "official_url": "https://example.com",
  "categories": ["gym", "pool", "court", "hall"],
  "is_gym": true,
  "tags": ["parking", "shower"],
  "meta": {
    "hours": {"open": 900, "close": 2100},
    "fee": {"adult": 300, "child": 100},
    "is_multi_facility": true
  },
  "gym": {
    "equipments": [
      {"slug": "treadmill", "count": 5},
      {"slug": "bike", "count": 8}
    ]
  },
  "pool": {
    "lanes": 6,
    "length_m": 25,
    "heated": true
  },
  "court": {
    "courts": [
      {"court_type": "テニス", "count": 4, "surface": "砂入り人工芝", "lighting": true},
      {"court_type": "バドミントン", "count": 6, "surface": "床", "lighting": true}
    ]
  },
  "hall": {
    "sports": ["バスケットボール", "バレーボール", "バドミントン"],
    "area_sqm": 1200
  }
}
```

---

## バージョン履歴

| 日付 | 変更内容 |
|---|---|
| 2026-01-01 | court.courts 各要素内に lighting を追加（親レベルから移動）|
| 2026-01-01 | カテゴリオブジェクト詳細仕様追加。court.courts に surface を追加 |
| 2025-12-30 | 初版作成。categories 統一に伴い仕様明文化 |
