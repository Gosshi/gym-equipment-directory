# PR06〜PR12 レビューサマリとロードマップ提案

## A. PR06〜PR12 のレビュー結果

### 1-1. Critical
- `app/schemas/meta.py` に必須 import がなく、起動時に `NameError: BaseModel` で API が落ちる。Meta
  API 全体が参照不可になるため早急な修正が必要。
- `/meta/cities` で `pref` 未指定時に `ValueError` を直接送出しており 500 になる。422 を返す
  仕様と乖離。

### 1-2. Major
- `/gyms/nearby` の `lat`/`lng` に範囲バリデーションがなく、±INF や ±200 などの異常値がそのまま
  DB に渡る。結果件数が 0 になるだけでなく、インデックスを効かせられずフルスキャンになる
  リスク。
- `/gyms/search` offset トークンは base64 文字列のみを前提としており、文字列でない場合の型安全性
  が低い。異常トークン時の 422 は確保されているが、sort 不一致時の早期検知が router ではなく
  utils 側の `ValueError` 依存になっている。
- last_verified_at が存在しないジムを freshness ソートから除外するため、total が UI に提示する
  件数とずれる（freshness 以外のソートでは含まれる）。仕様として明文化・計測されていないため
  フロントで混乱が起きる可能性。

### 1-3. Minor
- `/gyms/search` router（レガシー互換版）と `/api/routers/gyms.py`（新 API）が併存しており、
  OpenAPI 上の説明が二重化している。Frontend では新 API を利用しているが、旧 router にも
  freshness/richness 以外の sort が反映されていないため、メンテ対象を明示するコメントが欲しい。
- Meta API のレスポンススキーマは computed_field で後方互換を担保しているが、docs/README など
  から参照されておらず、移行方針が共有されにくい。簡易表を `docs/` 配下に置くとオンボーディン
  グが楽になる。
- `/gyms/nearby` は page_token あり時は keyset、なし時は offset で件数算出も異なる。仕様上は
  問題ないが、クライアントの無限スクロール実装で has_prev/has_more の意味が揺れやすいので
  ドキュメント補足を推奨。

### 1-4. スコアリング（10 点満点）
- 設計: 7/10 — router/service/repo の分離は概ね良好だが、レガシー router の併存で責務境界が曖昧。
- 実装の堅牢さ: 6/10 — Meta スキーマの import 抜け、cities の 422 漏れなど基本的なバリデーション
  抜けが残存。地理検索の入力制約も不足。
- テスト: 7/10 — 正常系と一部エッジはカバーされているが、異常座標や空 pref/city といった入力系
  バリデーションテストが不足。

## B. 今後のロードマップ

### 2-1. 初回リリースまでに必要なPR一覧

| PR | Priority | Scope | Acceptance Criteria | Layers |
| --- | --- | --- | --- | --- |
| PR-13 | P0 | Meta API 安定化（import 抜け・422 返却・pref/city バリデーション強化） | `/meta/*` が 422/503 を正しく返し、openapi 再生成。| router / schemas / tests |
| PR-14 | P0 | /gyms/nearby 座標バリデーション & rate limit | lat/lng を ge/le で 90/180 に制約し、異常値時に 422。| router / tests |
| PR-15 | P0 | Search token/total の仕様明文化 & docs 反映 | freshness 除外ロジックの仕様を docs と OpenAPI に反映し、UI も説明付きに。| docs / frontend |
| PR-16 | P1 | CI/CD 整備（lint/pytest/next lint/build） | GitHub Actions が lint/format/pytest/next lint/build を実行し緑になる。| infra / backend / frontend |
| PR-17 | P1 | ingest/admin 運用フロー簡略化 | `make ingest` 等で 1 コマンド更新、admin 審査のテスト追加。| scripts / admin / tests |
| PR-18 | P1 | ログ・エラーモニタリング最低限 | structlog 出力整備、Sentry DSN 環境変数で有効化し health check。| backend / infra |

### 2-2. リリース後の改善PR一覧

| PR | Priority | Scope | Acceptance Criteria | Layers |
| --- | --- | --- | --- | --- |
| PR-19 | P2 | パフォーマンス：地理系インデックス/キャッシュ | gyms(lat,lng) への GiST/BRIN 追加、meta キャッシュを Redis 差し替え可能に。| db / infra / services |
| PR-20 | P2 | 機能拡張：レビュー・お気に入り同期 | レビュー投稿 API と一覧取得、favorites の DB 永続化。| backend / frontend / db |
| PR-21 | P2 | スクレイピング差分検知 v2 | ソースごとのハッシュ比較・変更検知アラート、テスト追加。| ingest / tests |
| PR-22 | P3 | 画像アップロード & CDN 連携 | S3 署名付き URL 発行、フロントのアップロード UI 追加。| infra / backend / frontend |
| PR-23 | P3 | DX 改善ドキュメント | 開発環境セットアップ、サンプルリクエスト集、アーキ図更新。| docs |

### 2-3. ざっくりスケジュール（週次、1PR=1〜3日想定）
- Week1: PR-13, PR-14
- Week2: PR-15, PR-16
- Week3: PR-17
- Week4: PR-18, PR-19 (余力があれば着手)
- 短期（〜1ヶ月）マイルストーン: P0/P1 を完了し MVP 公開。
- 中期（〜3ヶ月）マイルストーン: P2 を進め、画像アップロードやレビュー機能の基盤を整備。
