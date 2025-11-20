# Codex 向けプロンプト: PR-12 Frontend検索/詳細/近隣API接続仕上げ

以下の指示を Codex に与え、PR-12（Next.js 側の検索・詳細・近隣マップ接続仕上げ）を実装させる。日本語で説明するが、コード・識別子は既存スタイルに合わせて英語で記述すること。

## スコープ（PR-12）
- `/gyms/search` の **無限スクロール/ページング** と URL パラメータ復元を実装する（q/pref/city/cats/sort/page_size 等）。
- `/gyms/{slug}` 詳細ページで画像/設備/鮮度フィールドを表示し、ローディング・エラーをハンドリングする。
- `/gyms/nearby` を利用した **近隣マップ表示**（ピン+リスト連動）と距離表示を整備する。
- 共通の API クライアント/フック/キャッシュ戦略（SWR/React Query 等）を整理し、エラートースト/リトライ方針を統一する。
- 管理者向け簡易 UI から Admin API の候補承認/却下ができるように接続する（最低限の操作フローで可）。

## 受入基準
- 検索ページ: フィルタ変更・無限スクロールで API が正しく呼ばれ、URL 共有で状態復元できる。
- 詳細ページ: 画像ギャラリー、設備タブ、last_verified_at_cached を表示し、欠損時も UI が崩れない。
- 近隣ページ: lat/lng/radius 指定で API 結果が表示され、リストとマップが同期する。
- Admin 簡易 UI で候補の承認/却下（単体/バルク）が動作し、結果が画面に反映される。
- ESLint/Prettier/FE unit or interaction tests（主要フロー）が通る。

## コードベースの位置
- フロントエンド: `frontend/`（Next.js）
- API クライアント/フック: `frontend/src/lib/`, `frontend/src/hooks/`, `frontend/src/services/`
- ページ/コンポーネント: `frontend/src/pages/`, `frontend/src/components/`

## 実装手順
1. **API クライアント/型定義**
   - `/gyms/search`, `/gyms/{slug}`, `/gyms/nearby`, メタ API, Admin API の型とクライアントを整備する。
   - エラーハンドリングとリトライ/キャッシュ設定を共通化する。
2. **検索ページ**
   - クエリパラメータを URL と状態に同期し、無限スクロールで has_more/page を利用する。
   - フィルタ UI（pref/city/cats/sort）をメタ API と連動させる。
3. **詳細ページ**
   - 画像ギャラリー、設備表示、last_verified_at_cached を組み込み、ローディング/エラー UI を追加する。
4. **近隣ページ/マップ**
   - `/gyms/nearby` を使い、地図ピンとリスト連動、距離表示を実装する。
5. **Admin 簡易 UI**
   - 候補一覧/詳細取得と承認・却下（単体/バルク）操作を接続し、結果を即時反映する。
6. **テスト/品質**
   - ESLint/Prettier、主要フローの FE unit or interaction tests を追加し、CI が通ることを確認する。

## 非機能ガイドライン
- TypeScript/React で既存のコードスタイルに従う（ESLint/Prettier 準拠）。
- 変更は PR-12 に必要な最小限に留め、環境変数や API ベース URL を明示的に扱う。
