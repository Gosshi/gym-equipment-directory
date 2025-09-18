# PR プレビュー on AWS Handbook (Single EC2 + GHCR + Compose)

最終更新: 2025-09-18

このハンドブックは、GitHub Actions から OIDC で AWS に接続し、PR ごとに単一の EC2 インスタンスを起動して FastAPI を Docker Compose で公開する仕組みの、構築・運用・トラブルシューティングを網羅したものです。既存の docs/pr-preview-aws*.md の内容、および実際の構築・調整で得た知見を統合しています。

---

## 0. 概要

- 目的: プルリクエストごとに一時的なプレビュー環境（単一の EC2）を自動起動し、`http://<PublicIP>:8000` で API を確認できるようにする。
- 主要技術: GitHub Actions, AWS (EC2, IAM OIDC, SSM), Docker, Docker Compose v2, GHCR。
- セキュリティ方針: 原則として最小公開。必要に応じて SG を PR ごとの /32 で出し入れ。DB は同 VPC のプライベート接続を推奨。

---

## 1. アーキテクチャ

- EC2: Amazon Linux 2023 (x86_64) を PR ごとに 1 台（シングルトン）
  - User Data で Docker / Compose v2 を導入
  - GHCR からアプリイメージを pull（失敗時は該当コミットのソース tarball を取得してローカルビルド）
  - DB マイグレーション（`alembic upgrade head`）は one-shot コンテナで実行（リトライと DB 到達待ちあり）
  - その後 `uvicorn` で起動
- GHCR: Actions で `:<sha>` と `:pr-<number>` を push（同一リポ PR のみ）
- DB: 既存の STG DB（EC2 上の PostgreSQL を想定）。同一 VPC 内のプライベート IP で接続するのが安全
- SG: 
  - `api-sg`（環境変数 `SG_ID`）: EC2 に付与。必要に応じて 8000/tcp を PR ごとの Public IP/32 で一時開放
  - `db-sg`（任意, `secrets.DB_SG_ID`）: 5432/tcp を EC2 Public IP/32 で一時開放（原則は `db-sg` のインバウンドを `api-sg` 参照許可）
- SSM: ログ取得/トンネル/手動確認に利用可能

---

## 2. IAM / OIDC 設定

### 2.1 GitHub OIDC ロール（例: `github-oidc-pr-staging`）
- 信頼ポリシー: GitHub OIDC を許可
- 権限（最小化推奨）:
  - `ec2:RunInstances`, `ec2:TerminateInstances`, `ec2:Describe*`, `ec2:AuthorizeSecurityGroupIngress`, `ec2:RevokeSecurityGroupIngress`, `ec2:CreateTags`, `ec2:Wait*`
  - `iam:PassRole`（EC2 起動時にインスタンスプロファイルを付与）
  - `ssm:SendCommand`, `ssm:GetCommandInvocation`（失敗時ログ収集を Actions サマリーへ）

### 2.2 EC2 インスタンスプロファイル（例: `ec2-pr-preview-ssm`）
- 権限: `AmazonSSMManagedInstanceCore` 必須
- 追加で `ec2:DescribeInstances` などが必要な場合は付与

---

## 3. セキュリティグループ（SG）設計

- `api-sg`（`SG_ID`）: EC2 に付与。原則は外部公開しないが、要件により 8000/tcp を PR ごとの Public IP/32 で一時開放
- `db-sg`: DB 側に付与。インバウンド 5432 は `api-sg` の参照許可が推奨（0.0.0.0/0 は不可）
- 自動開閉:
  - Upsert 時: `api-sg` に 8000/tcp の `<EC2 Public IP>/32` を追加（説明: `pr-preview PR <番号>`）
  - 任意: `db-sg` に 5432/tcp の `<EC2 Public IP>/32` を追加（`secrets.DB_SG_ID` がある場合）
  - Destroy（open PR が 0）: `api-sg` の 8000/tcp ルールを説明で特定し revoke（idempotent）

---

## 4. GitHub Actions ワークフロー（.github/workflows/pr-preview.yml）

### 4.1 トリガ
```yaml
on:
  pull_request:
    types: [opened, reopened, synchronize, closed]
```

### 4.2 permissions
```yaml
permissions:
  id-token: write
  contents: read
  packages: write     # GHCR push
  issues: write       # PR へコメント
  pull-requests: write
```

### 4.3 Build & Push（同一リポ PR のみ）
- `docker/setup-buildx-action@v3`
- `docker/login-action@v3`（GHCR）
- `docker/build-push-action@v6`
- リポジトリパスは小文字化（GHCR は小文字必須）

### 4.4 AWS 認証（OIDC）
- `aws-actions/configure-aws-credentials@v4`

### 4.5 Preflight
- AMI/SG/Subnet 整合、`RunInstances --dry-run` で権限を検証（`DryRunOperation` なら OK）

### 4.6 Upsert 本体
- 既存 `Purpose=pr-preview-singleton` を terminate → 新規 `run-instances`
- User Data のポイント:
  - Docker / Compose v2 導入（AL2023 は `docker-compose-plugin` パッケージ無し → GitHub リリースから配置）
  - `usermod -aG docker ec2-user/ssm-user` + ソケット待ち + `chmod 666 /var/run/docker.sock`
  - GHCR ログイン: `echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin`
  - compose 生成: `/srv/app/docker-compose.yml`（API のみ。DB は Secrets からの `DATABASE_URL`）
  - `SENTRY_DSN` は空なら compose から行を削除（空文字渡しで落ちるため）
  - pull リトライ → 失敗時は GitHub API から tarball ダウンロード → ローカルビルド
  - DB 到達待ち（/dev/tcp チェック）→ `alembic upgrade head` を 5 回までリトライ実行
  - `docker compose up -d`
- その後:
  - Public IP を `GITHUB_OUTPUT` へ出力
  - API SG の 8000/tcp を `<Public IP>/32` で authorize（説明: `pr-preview PR <番号>`）
  - 任意で DB SG の 5432 も `<Public IP>/32` で authorize（`secrets.DB_SG_ID` がある場合）
  - 8000/TCP の開放待ち + `/docs` ヘルス
  - PR へ URL コメント（フォークと IP 未取得はスキップ）

### 4.7 Destroy（PR close & open PR = 0）
- `api-sg` の 8000/tcp ルールを説明 `pr-preview PR <番号>` で特定し revoke（見つからなくても継続）
- `Purpose=pr-preview-singleton` を terminate

---

## 5. 必要な Secrets / 変数

- `STG_DATABASE_URL`（必須）: 例 `postgresql://user:pass@172.31.x.x:5432/db`（パスワードは URL エンコード）
- `STG_SENTRY_DSN`（任意）: 空なら自動無効化（compose から除去）。有効にする場合のみ設定
- `GHCR_USERNAME`（任意/推奨）: GHCR 認証用（private pull）
- `GHCR_TOKEN`（任意/推奨）: `read:packages` 付き PAT（パッケージへのアクセス権必須）
- `DB_SG_ID`（任意）: DB SG を /32 で一時開放したいときに使用

環境変数（env:）
- `AWS_REGION`, `AMI_ID`, `INSTANCE_TYPE`, `SG_ID`, `SUBNET_ID`, `INSTANCE_PROFILE`, `INSTANCE_NAME` など

---

## 6. 運用（コンソール/コマンド）

### 6.1 PR プレビューを確認する（外部 IP 経由）
1. Actions のジョブログで `Preview URL: http://<PublicIP>:8000` を確認
2. SG が /32 で開放されていれば外部からアクセス可能

### 6.2 自分だけ確認（SSM ポートフォワード）
```bash
aws ssm start-session \
  --target <INSTANCE_ID> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}' \
  --region ap-northeast-1 --profile <your-sso-profile>
# http://127.0.0.1:8000/docs
```

### 6.3 EC2 での確認コマンド
```bash
docker compose -f /srv/app/docker-compose.yml ps -a
docker compose -f /srv/app/docker-compose.yml logs --tail=200 api
curl -fsS http://127.0.0.1:8000/docs | head
```

---

## 7. トラブルシューティング

以下は実際に遭遇した代表的な事象と対処です。

### 7.1 GHCR `repository name must be lowercase`
- タグのリポジトリ部分は小文字必須。
- 対処: ワークフローで `toLower(github.repository)` を使用。

### 7.2 GHCR `unauthorized`（EC2 側）
- 原因: EC2 で `docker login ghcr.io` 未実施、PAT 権限不足（`read:packages`）またはパッケージアクセス権なし。
- 対処:
  - User Data で `docker login` を実行（空でも続行）。
  - 失敗時はソース tarball をダウンロードして **ローカルビルド** でフォールバック。

### 7.3 `docker-compose-plugin` が見つからない（AL2023）
- DNF にパッケージが無い。
- 対処: Compose v2 を公式リリースから配置（CLI プラグイン）。

### 7.4 Session Manager で `permission denied ... /var/run/docker.sock`
- ユーザーに docker グループが付いていない/即時反映されない。
- 対処: `usermod -aG docker ssm-user` 済み。ソケット生成待ち & `chmod 666` を適用。

### 7.5 cloud-init `scripts-user failed` / ヒアドキュメント終端ずれ
- User Data 中の入れ子 here-doc の終端ズレは典型的な失敗原因。
- 対処: 文字列は `printf/echo` で厳密生成。失敗時は `/var/log/cloud-init-output.log` で箇所特定。

### 7.6 `no configuration file provided: not found`
- `docker compose` を `/srv/app` 以外で実行すると発生。
- 対処: `-f /srv/app/docker-compose.yml` で明示。

### 7.7 `DATABASE_URL` が空/誤り
- 警告: `The "DATABASE_URL" variable is not set.`
- 対処: Upsert のテンプレート置換に `DATABASE_URL` を追加。Secrets 値の URL エンコードも確認。

### 7.8 DB タイムアウト（`psycopg2.OperationalError`）
- 原因: SG 未許可、RDS/EC2 の到達性問題、`pg_hba.conf`/ファイアウォール。
- 対処:
  - 同一 VPC 内なら **db-sg の 5432 を api-sg 参照許可**。
  - 一時的に `<PublicIP>/32` を開放（`DB_SG_ID` 利用）。
  - `listen_addresses='*'`, `pg_hba.conf` に CIDR を追加し再起動。

### 7.9 Sentry BadDsn で即落ち
- 原因: `SENTRY_DSN` が空文字でも環境変数が存在している。
- 対処: DSN が空なら compose から `SENTRY_DSN:` 行を **削除**（未設定扱い）。有効にする時だけ正しい DSN を Secrets に設定。

### 7.10 PR コメント 403 `Resource not accessible by integration`
- 原因: 権限不足、フォーク PR、IP 未取得。
- 対処:
  - `permissions: issues: write, pull-requests: write` を付与
  - フォーク PR/空 IP はスキップ

### 7.11 8000 に繋がらない（外部）
- 確認: Actions ログの `Preview URL`、`api-sg` に 8000/tcp `<PublicIP>/32` があるか
- 対処: Upsert 時の自動開放が入っているか、もしくは手動で一時開放

---

## 8. ベストプラクティス / Tips

- PR ごとの /32 開閉は漏れがち → 説明文字列に `pr-preview PR <番号>` を必ず付与して追跡・自動 revoke を容易にする
- ヘルスチェックは段階的に（TCP → /docs → /readyz → /health/db）
- GHCR private 運用時は **パッケージの可視性/アクセス権** を必ず見直す（PAT 所有者がアクセス権を持つか）
- DB の資格情報は URL エンコード（`@`, `:` など）
- `docker compose` のバイナリ設置は OS に依存しがち → 公式リリースからの配置が安定
- 失敗時は `/var/log/cloud-init-output.log` が最重要ログ

---

## 9. 用語集

- OIDC: OpenID Connect。GitHub Actions から AWS ロールをフェデレーションする標準方式
- GHCR: GitHub Container Registry。`ghcr.io/<owner>/<repo>:<tag>`
- SSM: AWS Systems Manager。セッションマネージャー/リモートコマンド/ポートフォワードに利用
- SG: Security Group。インスタンスや ENI に付与する仮想ファイアウォール
- User Data: EC2 起動時にクラウドイニットで走る初期化スクリプト

---

## 10. 付録: 代表コマンド

### メタデータ
```bash
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id
curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4
```

### SG
```bash
aws ec2 describe-security-groups --group-ids <SG_ID> --query 'SecurityGroups[0].IpPermissions'
```

### Compose/ログ
```bash
docker compose -f /srv/app/docker-compose.yml ps -a
docker compose -f /srv/app/docker-compose.yml logs --tail=200 api
```

---

## 11. 受け入れ基準（抜粋）

1) Upsert 後に `api-sg` に 8000/tcp, CIDR=`<EC2 Public IP>/32` が追加（説明: `pr-preview PR <番号>`）
2) 外部から `http://<PublicIP>:8000/docs` へ到達
3) PR を閉じ、open PR が 0 のとき:
   - インスタンスは terminate（既存仕様）
   - `api-sg` の上記 8000/tcp ルールを revoke（説明マッチで特定）
4) authorize/revoke の既存・不存在はワークフロー失敗としない（継続）

---

このハンドブックはリポジトリの .github/workflows/pr-preview.yml の現状実装と整合しています。更新が入った場合は随時この文書も更新してください。

