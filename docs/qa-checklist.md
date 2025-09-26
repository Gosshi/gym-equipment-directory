# QA チェックリスト（2025-09-26 更新）

## 共通

- API ベース URL・地図スタイルなど `.env.local` の必須環境変数を再確認する。【F:docs/feature-nearby.md†L7-L26】
- 主要ページでローディング／エラーハンドリングが崩れていないかスクリーンリーダーとあわせて確認する。

## ジム検索ページ `/gyms`

- 都道府県・市区町村・カテゴリ・距離スライダーの組み合わせを変更し、URL クエリが同期されることを確認する。【F:frontend/src/hooks/useGymSearch.ts†L200-L320】
- 現在地取得（許可／拒否／タイムアウト）とフォールバック地点のトースト表示を確認する。【F:docs/frontend-search.md†L1-L32】
- ページネーション操作時にリスト先頭へスムーズスクロールし、選択中カードのハイライトが維持されることを確認する。【F:frontend/src/components/gyms/GymList.tsx†L80-L160】

## 近隣ジムページ `/gyms/nearby`

- 緯度・経度の手入力／現在地取得／地図ドラッグで中心点が切り替わり、検索結果が再フェッチされることを確認する。【F:frontend/src/features/gyms/nearby/useNearbySearchController.ts†L1-L160】
- マップ上でピン・クラスタを操作し、右パネルまたはモーダルに詳細が表示され続けることを確認する。【F:frontend/src/features/gyms/nearby/components/NearbyMap.tsx†L200-L480】
- マップのズーム（ホイール／ピンチ／ナビゲーションボタン）とリストページングの同期が崩れないことを確認する。【F:frontend/src/features/gyms/nearby/NearbyGymsPage.tsx†L120-L240】

## ジム詳細表示

- リスト・マップから同じジムを選択した際に `GymDetailPanel` の内容が一致し、座標／設備情報が欠落していないか確認する。【F:frontend/src/components/gyms/GymDetailPanel.tsx†L1-L200】
- 詳細パネルの「閉じる」操作や外側クリックで Zustand の選択状態がリセットされることを確認する。【F:frontend/src/hooks/useSelectedGym.ts†L80-L160】

## 回帰観点

- ブラウザの戻る／進む操作で検索条件・選択ジムが正しく復元されるかを Playwright などで回す。【F:frontend/src/hooks/useGymSearch.ts†L200-L320】【F:frontend/src/hooks/useSelectedGym.ts†L40-L120】
- ページリロード後も都道府県・距離設定が保持されることを確認する。【F:frontend/src/hooks/useGymSearch.ts†L120-L200】

## リリース前確認

- QA チェックリストの全項目を SSM プレビュー環境で実行し、ズーム挙動・フィルタ連動に回帰が無いことを記録する。
- P1 バグ修正 PR のテスト結果（Vitest / Playwright / `npm run lint` / `npm run format`）を CI ログで再確認する。
- リリースノート草案と既知の P2 課題を PM と共有し、Go/No-Go 判定を合意する。
