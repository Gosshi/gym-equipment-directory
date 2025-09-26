# ロードマップ（2025-09-26 更新）

## 概要

### リポジトリ構成

- **バックエンド**: `app/` 配下に FastAPI アプリケーション、ドメイン別の `routers/`・`services/`・`repositories/` がまとまっており、`main.py` でミドルウェアやルーティングを初期化します。【F:app/main.py†L1-L70】
- **フロントエンド**: `frontend/` に Next.js 14 構成。`src/` 直下へアプリコードを集約しつつ、`components/`（共通 UI / ジム関連 UI）、`features/gyms`（検索・近隣マップ画面）などへ役割別に分割しています。【F:frontend/src/features/gyms/GymsPage.tsx†L1-L148】【F:frontend/src/features/gyms/nearby/NearbyGymsPage.tsx†L1-L200】
- **共通ドキュメント**: `docs/` に機能仕様や運用手順、テスト観点の補助資料を管理します。【F:docs/feature-nearby.md†L1-L34】

### 依存関係・Lint/Format

- バックエンドは Python 3.11 / FastAPI を採用し、Ruff で lint・format を統一しています（`pyproject.toml` で line length=100、double quote 等を指定）。【F:pyproject.toml†L1-L31】
- フロントエンドは Node.js 20 / Next.js 14、状態管理に Zustand、地図描画に MapLibre、フォームは React Hook Form を利用。ESLint（`next/core-web-vitals`）と Prettier（`printWidth: 100`）でスタイルをそろえています。【F:frontend/package.json†L1-L63】【F:frontend/.eslintrc.json†L1-L8】【F:frontend/.prettierrc†L1-L7】
- ルート `package.json` にはフロントエンドの lint/typecheck/test を呼び出すラッパースクリプトを定義し、CI でも流用しています。【F:package.json†L1-L12】

### 画面別コンポーネント & ストア依存

- **検索（一覧＋フィルタ）**: `GymsPage` がフィルタフォーム（`SearchFilters`）と結果一覧（`GymList`）を束ね、`useGymSearch` フックで URL と検索ステート（キーワード・都道府県・距離・現在地）を同期。距離フィルタのフォールバックや位置情報取得の管理もフック内で一括制御します。【F:frontend/src/features/gyms/GymsPage.tsx†L1-L148】【F:frontend/src/hooks/useGymSearch.ts†L1-L220】
- **マップ（近隣ジム）**: `NearbyGymsPage` が `useNearbySearchController`（URL・フォーム同期＋現在地処理）、`useNearbyGyms`（リスト API 呼び出し）、`useVisibleGyms`（表示範囲の追加フェッチ）を連携し、`useMapSelectionStore`（Zustand）でマップ／リスト／URL 間の選択状態を共有します。【F:frontend/src/features/gyms/nearby/NearbyGymsPage.tsx†L1-L200】【F:frontend/src/features/gyms/nearby/useNearbySearchController.ts†L1-L160】【F:frontend/src/hooks/useVisibleGyms.ts†L1-L160】【F:frontend/src/state/mapSelection.ts†L1-L80】
- **詳細パネル**: マップ・一覧の選択に応じて `GymDetailPanel` が API 呼び出しフック `useGymDetail` から詳細データを取得し、モーダル表示版は `GymDetailModal` がラップ。選択解除も `useMapSelectionStore` 経由で統一しています。【F:frontend/src/components/gyms/GymDetailPanel.tsx†L1-L120】【F:frontend/components/gym/GymDetailModal.tsx†L1-L44】【F:frontend/src/hooks/useGymDetail.ts†L1-L80】
- **一覧描画共通部品**: `GymList` や `NearbyList` は仮想スクロール・選択中ジムのフォーカス維持などを担い、検索ストアのページング／選択と連動します。【F:frontend/src/components/gyms/GymList.tsx†L1-L160】【F:frontend/src/features/gyms/nearby/components/NearbyList.tsx†L1-L120】

### テスト & CI

- フロントエンドは Vitest（unit/integration）、Playwright（E2E）構成。`frontend-ci.yml` で lint → typecheck → build を PR 時に実行します。【F:frontend/package.json†L14-L36】【F:.github/workflows/frontend-ci.yml†L1-L26】
- ルートの PR Light CI では Python 側の Ruff / pytest を軽量に回しつつ、バックエンド変更が無い場合はテストをスキップ。PR レビュー前提の高速チェック体制を維持しています。【F:.github/workflows/pr-light.yml†L1-L74】

## 完了済み ✅

- **FE5-E: 地図との完全連動** — マップとリストで同じ選択を共有し、Zustand ストアで URL とも同期する実装が完了済みです。【F:frontend/src/hooks/useSelectedGym.ts†L1-L120】【F:frontend/src/state/mapSelection.ts†L1-L80】
- **FE5-F: ポップアップ詳細表示（右パネル優先）** — 詳細パネル／モーダルが `GymDetailPanel` で統一され、リスト／マップ操作から自動で右パネルへ詳細が表示されるよう仕上がっています。【F:frontend/src/features/gyms/nearby/NearbyGymsPage.tsx†L200-L320】【F:frontend/src/components/gyms/GymDetailPanel.tsx†L1-L200】
- **地図連動バグ修正（ピン詳細の瞬間消失/往復揺れ）** — マップ側で自動パン時の抑制や直前のドラッグ検知を実装済みで、選択が安定しています。【F:frontend/src/features/gyms/nearby/components/NearbyMap.tsx†L320-L480】
- **検索フィルタ改善（都道府県維持・現在地維持・距離スライダー）** — `useGymSearch` が URL 同期と位置情報のフォールバックを扱い、距離スライダー変更時に自動でページングをリセットする挙動を保持しています。【F:frontend/src/hooks/useGymSearch.ts†L180-L320】【F:docs/frontend-search.md†L1-L32】

## 進行中 ⏳

- **近隣ジム検索 UX 拡張** — 緯度経度の手入力のみ対応しており、住所・駅名ジオコーディングやマップクラスタリング最適化などの改善余地が残っています。【F:docs/feature-nearby.md†L17-L34】
- **URL 履歴同期の境界ケース精査** — `useSelectedGym` と検索系フックで push/replace を使い分けているが、ブラウザ戻る／進むの UX 確認とテスト強化が継続課題です。【F:frontend/src/hooks/useSelectedGym.ts†L40-L120】【F:frontend/src/hooks/useGymSearch.ts†L200-L320】

## バグ & ToDo

### P1

- **近隣ジム地図がズームできない**
  - 再現: `/gyms/nearby` でマップをホイール／ピンチ操作しても拡大縮小が反映されない。
  - 期待: ホイールやトラックパッド操作で MapLibre がズームし、一覧の検索範囲も追随する。
  - 仮説: `NearbyMap` 初期化時に `gestureHandling` 相当の設定を入れておらず、`map.easeTo` 連発や `suppressMoveRef` の扱いで `scrollZoom` が無効化されている可能性。`NavigationControl` のみ追加しているため、ホイールイベントが親要素で抑止されていないか（リスト側のスクロール干渉、`pointer-events` 付きオーバーレイ）を含め調査が必要です。【F:frontend/src/features/gyms/nearby/components/NearbyMap.tsx†L200-L360】

### P2

- **URL 戻る/進む時の選択同期** — `useSelectedGym` / `useGymSearch` が同時に URL を書き換えるため、連続操作時の履歴スタック確認とブラウザテストを追加する。
- **ページネーション時のフォーカス・スクロール復帰** — `GymList` / `NearbyList` で `scrollIntoView` を利用しているが、仮想スクロールと相互作用するケースの QA を増やす。【F:frontend/src/components/gyms/GymList.tsx†L80-L160】【F:frontend/src/features/gyms/nearby/components/NearbyList.tsx†L120-L240】
- **近隣マップのクラスタ閾値調整** — ピン密度が高い都市部での cluster 展開ズーム値が急すぎる点を調整し、UX を改善する。【F:frontend/src/features/gyms/nearby/components/NearbyMap.tsx†L200-L320】

## 次のPR計画（小さな粒度での進行）

1. **P1 ズームバグ調査と修正**
   - 変更範囲: `NearbyMap` コンポーネント（MapLibre 初期化とイベント処理）、必要に応じてスタイル。
   - 影響範囲: 近隣ジムマップ全体スクロール抑止や自動パンへの影響を確認。
   - リスク: ズーム/ドラッグハンドリング退行。E2E と実機確認が必要。
   - テスト観点: ホイール・ピンチ操作、ナビゲーションコントロールでのズーム、リスト選択との同期。
2. **URL 履歴挙動の QA 強化**
   - 変更範囲: `useSelectedGym` と `useGymSearch` の履歴制御、Vitest 追加。
   - 影響範囲: 検索結果ページの URL 同期、モーダル開閉。
   - リスク: ブラウザ戻る/進む挙動が変わる可能性。回帰テスト要。
   - テスト観点: vitest でのヒストリー操作シミュレーション、Playwright での戻る/進む操作。
3. **ページネーション UX 安定化**
   - 変更範囲: `GymList`・`NearbyList` のスクロール制御、アクセシビリティ属性。
   - 影響範囲: 検索結果一覧・近隣一覧のページ切り替え。
   - リスク: 仮想スクロールとの競合。スクリーンリーダー挙動への配慮。
   - テスト観点: キーボード操作でのページ移動、フォーカス移動確認、単体テスト更新。

（依存関係）P1 バグ修正を最優先で解消 → URL 履歴 QA → ページネーション UX の順で着手。

## リリースまでのロードマップ

- **M0: 安定化準備（今週）**
  - 成果物: P1 ズームバグ修正 PR、QA チェックリスト更新、リリースノート雛形作成。
  - 判定条件: 近隣マップのズームが全操作で動作し、都道府県フィルタ・現在地取得・距離スライダー・地図⇄一覧⇄詳細の連動に回帰が無いことを QA 済みで確認。
- **M1: UX 精査（+1 週間）**
  - 成果物: URL 履歴 QA 強化 PR、ページネーション UX 安定化 PR。
  - 判定条件: Playwright の戻る/進むテスト追加が CI で緑になり、フォーカス・スクロール挙動がデザインレビューで承認される。
- **M2: リリース候補凍結（+1 週間）**
  - 成果物: 既知 P2 バグの洗い出し完了、必要に応じてホットフィックス PR を小粒度で適用。
  - 判定条件: QA チェックリスト全項目クリア、主要ブラウザ／モバイルでの回帰なし、SSM プレビューで PM の承認取得。
- **M3: リリース（+1〜2 日）**
  - 成果物: バージョンタグ作成、リリースノート公開、運用引き継ぎ（監視・サポート体制）。
  - 判定条件: 本番リリース後 24h で重大障害なし、アクセス解析で主要 KPI が目標レンジ内。

## 次に着手するPR

- **P1 近隣ジム地図ズーム不可の修正**（想定 2–4h）: `NearbyMap` のズーム設定調査／調整と回帰テスト追加。
