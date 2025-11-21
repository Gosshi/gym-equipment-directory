# Render へのデプロイ手順

## 1. 前提
- 本ドキュメントは、gym-equipment-directory を Render に本番デプロイするための手順まとめです。
- backend は FastAPI、frontend は Next.js、DB は Render 管理の PostgreSQL を前提とします。
- ルート直下の `render.yaml` を Blueprint デプロイに利用します。

## 2. Render アカウントと GitHub 連携
1. Render アカウントを作成し、GitHub と連携します。
2. リポジトリ `gym-equipment-directory` の `main` ブランチにアクセスできるようにします。
3. プライベートリポジトリの場合は Render にリポジトリアクセスを付与してください。

## 3. Render PostgreSQL の作成手順
1. Render ダッシュボードで **New -> PostgreSQL** を選択します。
2. **Name** に `gym-postgres` を入力し、**Plan** は `starter` など必要なプランを選択します。
3. 作成後に表示される接続情報から `Internal Database URL` を控えておき、接頭辞 `postgres://` を `postgresql+asyncpg://` に置き換えた値を `DATABASE_URL` として backend の環境変数に設定します。

## 4. render.yaml を使った Blueprint デプロイ手順
1. Render ダッシュボードで **Blueprints** を開き、`New Blueprint Instance` を作成します。
2. GitHub リポジトリとブランチ `main` を指定し、`render.yaml` を選択します。
3. デプロイを開始すると以下が自動で作成されます。
   - `gym-backend`: backend 用 Web Service（Dockerfile.render 使用、ヘルスチェック `/health`）。
   - `gym-frontend`: frontend 用 Web Service（Dockerfile.render 使用）。
   - `gym-postgres`: Render 管理の PostgreSQL。
4. 1 回目のデプロイ後、各サービスの Dashboard から未入力の環境変数（`sync: false` や `generateValue` でないもの）を設定し、再デプロイします。

## 5. 環境変数の設定一覧
Render ダッシュボードで以下を設定してください（空欄は適宜置き換え）。

| 変数 | 用途 | 設定例 |
| --- | --- | --- |
| BACKEND_URL | 公開 API URL | `https://api-xxx.onrender.com` |
| FRONTEND_URL | 公開フロント URL | `https://app-xxx.onrender.com` |
| DATABASE_URL | Render PostgreSQL の接続文字列 | Render の **Internal Database URL** を `postgresql+asyncpg://...` 形式に書き換えた値 |
| SECRET_KEY | アプリのシークレット | `generate` で自動生成 or 手動設定 |
| ADMIN_UI_TOKEN | `/admin` 用アクセストークン | 強固なランダム文字列 |
| OPENCAGE_API_KEY | ジオコーディング API キー | 取得した API キー |
| APP_ENV | 実行環境 | `prod` |
| APP_PORT | backend のポート | `8000` |
| LOG_LEVEL | ログレベル | `INFO` |
| ALLOW_ORIGINS | CORS 許可ドメイン | `https://app-xxx.onrender.com` |
| RATE_LIMIT_ENABLED | レート制限の有効化 | `1` |
| SENTRY_DSN / SENTRY_TRACES_RATE / RELEASE | 監視設定 | 必要に応じて設定 |
| SCORE_W_FRESH / SCORE_W_RICH / FRESHNESS_WINDOW_DAYS | 検索スコア重み | 既定値のまま可 |
| META_CACHE_TTL_SECONDS | メタ情報キャッシュ TTL | `300` など |
| ALEMBIC_STARTUP_* | マイグレーション起動リトライ | 既定値のまま可 |
| NEXT_PUBLIC_BACKEND_URL | frontend からの API 参照先 | `https://api-xxx.onrender.com` |
| NEXT_PUBLIC_API_BASE / NEXT_PUBLIC_API_BASE_URL | フロントの API ベース URL | `https://api-xxx.onrender.com` |
| NEXT_PUBLIC_AUTH_MODE | 認証モード | `stub` など |
| NODE_ENV | Next.js 実行環境 | `production` |

## 6. デプロイ後の確認
1. backend サービスの URL で `GET /health` を実行し、`{"status": "ok"}` が返ることを確認します。
2. frontend サービスの URL にアクセスし、トップページ → 検索ページ → 詳細ページの遷移と API 呼び出しが正常に動くか確認します。
3. `/admin` へアクセスする場合は `ADMIN_UI_TOKEN` を設定した上でログインできることを確認します。

## 7. トラブルシュート
- **health チェックが落ちる**: `DATABASE_URL` が正しいか、PostgreSQL が起動しているか確認。環境変数 `APP_ENV` や `APP_PORT` の設定漏れがないかを見直す。
- **CORS エラー**: `ALLOW_ORIGINS` に frontend の公開 URL が含まれているか確認する。
- **フロントから API が叩けない**: `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_API_BASE_URL` が backend の公開 URL になっているか確認。`BACKEND_URL` も併せて更新。
- **/admin が 307 でリダイレクトされ続ける**: `ADMIN_UI_TOKEN` が設定されているか、クッキー / Authorization ヘッダーのトークンが一致しているかを確認。
- **Sentry に通知が来ない**: `SENTRY_DSN` と `SENTRY_TRACES_RATE` が設定されているか、`RELEASE` がユニークな値になっているかを確認。
