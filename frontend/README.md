# Gym Equipment Directory Frontend

Next.js (App Router) + TypeScript + Tailwind CSS の最小構成です。トップページでは API の
`/health` を叩き、レスポンス結果を 3 状態（ロード中 / 成功 / 失敗）で表示します。

## 必要条件

- Node.js 20 系
- npm (同梱)

## セットアップ

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

アプリは `http://127.0.0.1:3000` で起動します。`.env.local` に `NEXT_PUBLIC_API_BASE_URL`
を設定すると、再起動なしでフロントエンドから参照する API が切り替わります。

## 環境変数

| 変数名                     | 既定値                  | 用途                                        |
| -------------------------- | ----------------------- | ------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | API ベース URL。必ず絶対 URL を指定すること |

- 値はクライアント側にも埋め込まれます。秘密情報は入れないでください。
- `.env.example` をベースに `.env.local` を作成してください（コミットしない）。

## SSM トンネル使用時の例

```
# 例: SSM Session Manager で 8000 番ポートをローカルにフォワードした場合
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

- API コンテナ（FastAPI）が `8000` で待ち受けている想定です。
- トンネルを貼り直すごとに再確認してください。

## PR プレビュー環境の指針

- プレビュー用 API のエンドポイントを発行後、同じ URL を
  `NEXT_PUBLIC_API_BASE_URL` に設定してください。
- `.env.local` を用意できない場合は、ホスティング側の環境変数機能で公開変数として
  上記キーをセットします。
- 確認方法: `npm run dev` もしくはプレビュー URL でトップページを開き、ヘルスチェック
  カードが `status: ok` を示すことを確認します。

## 利用可能な npm スクリプト

| コマンド                   | 説明                                                                                      |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| `npm run dev`              | 開発サーバーを起動します                                                                  |
| `npm run build`            | 本番ビルドを生成します                                                                    |
| `npm run start`            | ビルド済みアプリを起動します                                                              |
| `npm run lint`             | ESLint を実行します                                                                       |
| `npm run typecheck`        | TypeScript の型チェックを実行します                                                       |
| `npm run format`           | Prettier で整形します                                                                     |
| `npm run test`             | Vitest による全テスト                                                                     |
| `npm run test:unit`        | 単体テストのみを実行します                                                                |
| `npm run test:integration` | 結合テストのみを実行します                                                                |
| `npm run analyze`          | `ANALYZE=true next build` を実行し、`.next/analyze/*.html` に bundle レポートを出力します |
| `npm run lh:ci`            | `npm run build` → Lighthouse CI を順に実行し、`lighthouse/reports` に結果を保存します     |

## 実装メモ

- UI コンポーネントは shadcn/ui ベース。Tailwind CSS と組み合わせた軽量構成です。
- API クライアントは `NEXT_PUBLIC_API_BASE_URL` を参照し、タイムアウトや HTTP エラーを
  例外としてハンドリングします。
- 375px 程度の幅でも崩れないようコンポーネントを配置しています。

## パフォーマンス計測とレポート

### Bundle Analyzer

- `npm run analyze`
  - `ANALYZE=true next build` が走り、`.next/analyze/client.html` などに結果が出力されます。
  - `maplibre-gl` や `@tanstack/react-virtual` などの重い依存を別チャンク化した状態を確認できます。

### Lighthouse CI

- `npm run lh:ci`
  - プロダクションビルド → `next start`（デフォルトで `127.0.0.1:3010`）→ Lighthouse CLI の順で実行します。
  - 結果は `lighthouse/reports/*.report.json|html` に保存されます。
  - Chrome がインストールされていない環境では `CHROME_PATH` を渡してください。ポート 3010 が使用できない場合は `LH_PORT` を上書き可能です。

### Before / After サマリ

| 計測対象       | 指標                             | Before                 | After                  | 備考                                                                            |
| -------------- | -------------------------------- | ---------------------- | ---------------------- | ------------------------------------------------------------------------------- |
| `/gyms/nearby` | Next.js build: ページバンドル    | 7.91 kB                | 7.12 kB                | `maplibre-gl` を非同期チャンクへ分離                                            |
| `/gyms`        | Next.js build: First Load JS     | 122 kB                 | 123 kB                 | 仮想化グリッドを遅延ロード（初回 chunk は据置、追加 JS はオンデマンド読み込み） |
| `/` & `/gyms`  | Lighthouse Performance (desktop) | 88 / 89                | 94 / 95                | `npm run lh:ci` (Chromium 121, MacBook Pro 2023) の実測値                       |
| `/gyms`        | LCP / CLS / TTI                  | 2.98 s / 0.08 / 3.84 s | 2.21 s / 0.02 / 2.67 s | Skeleton 導入 + リクエスト集約で初動安定化                                      |

> ※ Lighthouse の数値は `npm run lh:ci` をローカルで実行した際のサンプルです。環境（CPU・ネットワーク）によって変動します。
