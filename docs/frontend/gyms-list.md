# ジム一覧ページ (/gyms)

## 概要
- 既存 API `/gyms/search` に接続し、検索フォーム・結果一覧・ページングを提供します。
- URL クエリ（`q`, `prefecture`, `city`, `page`）と状態が同期し、リロード・共有時も条件を再現します。
- フロントエンドからは `process.env.NEXT_PUBLIC_API_BASE_URL` を通じて API ベースURLを切り替えます。

## 環境変数
```
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```
- ルートの `.env.example` に追記済み。開発時は `frontend/.env.local` などに設定してください。
- 値は絶対URL（プロトコル必須）で指定します。末尾の `/` は自動的に除去されます。

## 主な構成コンポーネント
```
GymsPage (src/features/gyms/GymsPage.tsx)
├─ SearchForm              // 検索条件の入力フォーム
├─ GymCard                 // 単一ジムの表示カード
├─ GymsSkeleton            // ローディング用スケルトン
├─ PaginationControls      // 前/次ページ遷移ボタン
└─ NearbyPlaceholder       // /gyms/nearby 連携予定のプレースホルダ
```
- いずれも `GymsPage` 内で定義しており、将来的に分離しやすい構造です。
- `/app/gyms/page.tsx` から `GymsPage` を読み込み、App Router のクライアントコンポーネントとして動作します。

## API インターフェース
- `GET /gyms/search`
  - クエリ: `pref`（都道府県スラッグ）、`city`（市区町村スラッグ）、`q`（任意キーワード）、`page`、`per_page`、`equipment_match` など。
  - レスポンス: `items`（配列）、`total`、`has_next`、`page_token`。
  - フロントでは DTO 正規化を `src/services/gyms.ts` で行い、`GymSummary` 型へ変換して UI に渡します。
- 近隣検索 `GET /gyms/nearby` は UI のみ配置しており、API 呼び出しは今後のステップで実装予定です。

## 既知の制限 / TODO
- `nearby` 機能はプレースホルダ。位置情報許可や API 呼び出しは未実装です。
- ページングは単純な前/次操作のみ。総ページ数表示やジャンプ機能は未対応です。
- ジムのサムネイルが無い場合はプレースホルダ表示のみ。今後のデザイン調整で改善予定です。
- テストを実行する前に `npm install` を実行し、新しいテスト関連依存関係を取得してください。
