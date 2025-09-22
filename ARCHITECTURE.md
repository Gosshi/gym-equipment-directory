# Architecture

## Frontend

The web frontend is built with Next.js (App Router) and leverages a modular feature directory under `src/features`. Shared UI primitives live in `components/ui`, while API access is handled via typed service modules in `src/services` backed by a thin wrapper around `fetch`.

### 地図レイヤ & 近隣検索

`/gyms/nearby` では MapLibre GL JS を用いた地図レイヤと、同一データソースを参照する一覧ビューを並列表示します。`NearbyGymsPage` が検索フォーム・地点取得・ステート管理を担い、`NearbyMap` コンポーネントがピン描画と地図中心の同期、`NearbyList` がリスト⇔ピンのハイライト連動とディープリンク遷移を提供します。API 呼び出しは `fetchNearbyGyms` サービス経由で `/gyms/nearby` エンドポイントを利用し、半径変更や地図操作による再フェッチを扱うカスタムフック `useNearbyGyms` で統合しています。

### 検索層（URL同期/状態管理）

`/gyms` と `/gyms/search` は共通の `useGymSearch` フックを中心に構成され、URL クエリ ⇄ フィルタ状態の相互変換を `lib/searchParams` に切り出しています。フィルタ入力は 300ms デバウンス後に `router.push` でクエリ更新し、ページ番号・件数変更は即時反映します。都道府県と市区町村候補はメモリキャッシュを用いて再利用し、検索 API には `fetchGyms` を通じて正規化済みパラメータ（`q`, `pref`, `city`, `cats`, `sort`, `page`, `per_page` など）を送信します。結果一覧とフィルタ UI は `SearchFilters` / `GymList` コンポーネントに分離され、ローディング・エラー・0件状態を個別に扱えるようになっています。
