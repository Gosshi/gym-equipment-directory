# デプロイメントガイド

このドキュメントでは、ジム設備ディレクトリ（Gym Equipment Directory）アプリケーションのデプロイ構成と手順について説明します。

## アーキテクチャ

- **バックエンド**: [Render](https://render.com) でホストされています。
    - **サービスタイプ**: Web Service (Docker)
    - **データベース**: PostgreSQL (Render管理 または 外部プロバイダ)
    - **Cronジョブ**: 夜間のデータ収集（Ingestion）を行うバックグラウンドワーカー。
- **フロントエンド**: [Vercel](https://vercel.com) でホストされています。
    - **フレームワーク**: Next.js

## バックエンドのデプロイ (Render)

バックエンドはDockerを使用してコンテナ化されています。

### 設定 (`render.yaml`)
プロジェクトには `render.yaml` ブループリント仕様が含まれています。
- **Web Service**: FastAPIアプリケーション (`uvicorn`) を実行します。
- **Cron Job**: 毎日、データ収集スクリプト (`scripts.ingest.run_nightly`) を実行します。

### Dockerfile
本番用のDockerfileは `backend/Dockerfile.render` にあります。
- **マルチステージビルド**: `builder` ステージと `runner` ステージを使用し、イメージサイズを最小化しています。
- **エントリーポイント**: `backend/entrypoint.sh` を使用して、アプリケーション起動前にデータベースマイグレーション (`alembic upgrade head`) を自動的に実行します。

### 環境変数
Renderで以下の環境変数を設定する必要があります：

| 変数名 | 説明 |
|---|---|
| `DATABASE_URL` | PostgreSQLへの接続文字列。 |
| `OPENAI_API_KEY` | OpenAIのAPIキー（住所のクリーニングや抽出に使用）。 |
| `GOOGLE_MAPS_API_KEY` | Google MapsのAPIキー（ジオコーディングに使用）。 |
| `SENTRY_DSN` | Sentryのエラー追跡用DSN。 |
| `LOG_FORMAT` | 本番ログ用に `json` を設定します。 |
| `DISCORD_WEBHOOK_URL` | コストレポートや通知を送信するためのWebhook URL。 |

## フロントエンドのデプロイ (Vercel)

フロントエンドは `frontend/` ディレクトリにあるNext.jsアプリケーションです。

### 設定
- **フレームワークプリセット**: Next.js
- **ルートディレクトリ**: `frontend`
- **ビルドコマンド**: `npm run build` または `next build`
- **出力ディレクトリ**: `.next`

### 環境変数
| 変数名 | 説明 |
|---|---|
| `NEXT_PUBLIC_API_URL` | バックエンドAPIのURL（例: `https://gym-backend.onrender.com`）。 |

## CI/CD

### GitHub Actions
- **CI (`.github/workflows/ci.yml`)**: `main` へのプッシュおよびプルリクエストごとに実行されます。
    - `ruff` (リンター/フォーマッター) を実行します。
    - `pytest` (ユニットテスト) を実行します。
- **デプロイ**:
    - **Render**: GitHubリポジトリと連携しており、`main` へのプッシュ時に自動的にデプロイされます。
    - **Vercel**: GitHubリポジトリと連携しており、`main` へのプッシュ時に自動的にデプロイされます。
