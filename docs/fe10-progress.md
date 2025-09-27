# FE10 改善計画の進捗サマリー

ユーザーが共有した実施ステップ一覧をベースに、現状の整備状況をドキュメント化する。今後の PR では本ファイルを参照し、未着手項目の棚卸しとドキュメント更新を行う。

## インフラ / AWS（PR プレビュー）

- ✅ **SSO 設定**: AWS IAM Identity Center に `gym-preview` プロファイルを作成し、ブラウザ認可まで動作確認済み。
- ✅ **SSM トンネル経由のプレビュー**: Public IP は公開せず、`aws ssm start-session ... AWS-StartPortForwardingSession` で `:8000→:8000` のポートフォワードを実施。
- ✅ **GitHub Actions からの EC2 upsert**: PR ごとにインスタンスを増やさず、シングルトン運用でコンテナを起動。
- ✅ **Docker 起動**: `run-instances` + `user-data` で Docker / Compose を配備し、API コンテナを起動。
- ✅ **タグ付与**: EC2 に `Purpose=pr-preview-singleton`, `PR=<番号>` を付与し、運用時の追跡を容易化。
- ✅ **DB 接続**: Secrets 経由の `DATABASE_URL` で外部 PostgreSQL へ接続し、`/health` で疎通確認済み。
- ✅ **自動終了**: EventBridge Scheduler で起動から 2–4h 後に `ec2:TerminateInstances` を実行し、`eventbridge-scheduler-ec2-exec` ロールで権限管理。
- ✅ **SSM からのヘルスチェック**: `AWS-RunShellScript` で `127.0.0.1:8000` への `/readyz`, `/healthz`, `/docs` を確認。
- ✅ **失敗時の診断収集**: SSM で `docker compose ps/logs`, `cloud-init-output.log`, `/tmp/seed.log` を取得し、障害解析を高速化。
- ✅ **不要ジョブの停止**: DB シードの自動投入は運用判断で「後日まとめて投入」とし、PR プレビュー中は実施しない。

## CI/CD

- ✅ **PR Light CI**: バックエンドで Ruff + 軽量 pytest、フロントで lint / typecheck / build を実行。
- ✅ **frontend-smoke**: `npm ci → lint → typecheck → build → npm run start -p 3000 → wait-on → curl /` のシーケンスでアプリ起動を検証。
- ✅ **ワークフロー分離**: PR 用に軽量化したジョブへ集約し、不要なマトリクスや長時間テストは非 PR ジョブへ移管。

## バックエンド（API）

- ✅ **API 起動と疎通**: Uvicorn で `/openapi.json`, `/health`, `/healthz`, `/readyz` を確認済み。
- ✅ **DB 接続異常の切り分け**: `psycopg2` で接続テストを行い、`asyncpg` 依存を除去。
- ✅ **ルート確認**: `/gyms/search`, `/gyms/nearby`, `/equipments`, `/meta/*`, `/admin/reports` を走査済み。
- ✅ **DTO 整備**: 検索レスポンス整形のための DTO を追加し、マージ済み。

## フロントエンド（Next.js）

- ✅ **FE5-E**: 地図・一覧・詳細パネルの完全連動と Zustand を単一ソースに統合、URL 同期完了。
- ✅ **FE5-F**: 詳細は右パネルに集約し、地図は必要時のみモーダル/ポップアップ表示。
- ✅ **主要バグ修正**: ピン選択で詳細が消える現象や、近隣一覧選択時の地図揺れを抑止。
- ✅ **FE8-A**: ページネーションと URL 同期（`page`, `limit`, `q`, `category`, `sort`）を安定化し、`popstate` と `replaceState` を適切に切り替え。
- ✅ **URL 履歴 QA 強化**: 戻る/進む挙動を検証し、回帰を抑止。
- ✅ **FE8-C**: ページネーション UX（フォーカス移動、スクロール復帰、アクセシビリティ）を整備。
- ✅ **ダミーデータ拡充**: 千葉・東京・茨城の住所/緯度経度を整合させ、ページネーション検証を容易化。
- ⏳ **FE8-D**: URL 同期と Zustand ストアの責務分離を調整中。
- ⏳ **FE9**: UI/UX 仕上げ（パディング/コントラスト/フォーカスリング、ローディングスケルトン最適化など）を継続中。

## テスト

- ✅ **フロント**: Vitest（unit/integration）と Playwright（E2E 最小セット）を運用中。
- ✅ **E2E 整理**: `search-history` はフレークのため削除し、代替として unit/integration を強化する方針。
- ✅ **既存 E2E**: Home / Search / Nearby map ×2 が約 4 秒で PASS。
- 🟨 **残タスク**: `/gyms` の履歴×ページング再テスト（E2E → 統合テスト化）、近隣マップのクラスタ閾値・展開ズーム調整テスト。

## ドキュメント

- ✅ **AGENTS.md 整備**: Ruff / pytest / PR 日本語 / CI 緑必須、「アプリが起動できないのに完了にしない」運用を明記。
- ✅ **補助ドキュメント**: `docs/feature-nearby.md`, `docs/frontend-search.md` を更新。
- ⏳ **FE10 ドキュメント**: `docs/roadmap-next.md`, `architecture.md`, `testing-strategy.md`, `performance.md`, `accessibility.md` を継続更新。
- ⏳ **テンプレ整備**: Issue / PR テンプレート、`labels.json` の整備を継続。

## 現在のフォーカス

1. ⏳ **FE8-D**: URL 同期とストア責務分離（回帰なしで完了させる）。
2. ✅ **FE9**: UI/UX 仕上げ（既存を壊さず、小粒な PR を複数に分割）。
3. ⏳ **FE10**: ドキュメント・バックログ整備（アーキ図・方針文章化 & テンプレ追加）。

## 参考リンク

- [短期ロードマップ](./roadmap-next.md)
- [テスト戦略](./testing-strategy.md)
- [バックログ台帳](./backlog.md)
- [パフォーマンス方針](./performance.md)
- [アクセシビリティ指針](./accessibility.md)
- [アーキテクチャ概要](./architecture.md)
