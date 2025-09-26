# PRプレビュー（Single EC2）AWS運用ランブック

最終更新: 2025-09-18 10:51 UTC

このドキュメントは、**PRごとに単一のEC2でFastAPIアプリを起動してプレビュー**する仕組み（GitHub Actions + EC2 + Docker + GHCR + SSM）の**構築メモ／運用手順／トラブルシュート**を、今回の実作業のログに基づいて詳しくまとめたものです。  
「なぜそうしたか」「どこで詰まったか」「どう直したか」を残しています。

---

## 0. TL;DR（まず使うもの）

### ✅ 自分だけSSM経由でPRプレビューを見る（外部公開なし）

```bash
# 前提: Mac に AWS CLI v2 / session-manager-plugin / SSO プロファイル (例: gym-preview)
aws ssm start-session \
  --target <PREVIEW_EC2_INSTANCE_ID> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}' \
  --profile gym-preview --region ap-northeast-1

# ブラウザで
open http://127.0.0.1:8000/docs
```

### ✅ EC2 上で「アプリは起動中？」（コンテナ/ポート/HTTP）

```bash
docker compose -f /srv/app/docker-compose.yml ps
docker compose -f /srv/app/docker-compose.yml logs --tail=100 api
curl -fsS http://127.0.0.1:8000/docs >/dev/null && echo "APP OK" || echo "APP NG"
```

### ✅ DB 到達性（EC2 → DB EC2:5432）と実接続（コンテナ内）

```bash
# TCP到達（/dev/tcpを使う。ncが無くてもOK）
bash -c 'timeout 3 bash -c "echo > /dev/tcp/<DB_PRIVATE_IP>/5432"' && echo "DB TCP OK" || echo "DB TCP NG"

# コンテナ内部から実接続（psycopg2; +asyncpg を除去）
docker compose -f /srv/app/docker-compose.yml exec -T api python - <<'PY'
import os, psycopg2
url = os.environ["DATABASE_URL"].replace("+asyncpg","")
psycopg2.connect(url).close(); print("DB CONNECT OK")
PY
```

---

## 1. 現状アーキテクチャ

- **Preview EC2（Amazon Linux 2023, x86_64）** を PRごとに 1 台（シングルトン）起動  
  → User Data で Docker/Compose をセットアップし、**GHCR** からアプリイメージを pull & 起動。
- **DB は EC2（db-server）上の PostgreSQL**（RDS ではない）。  
  → **VPC内プライベートIP**（例: `172.31.39.125:5432`）で接続。
- **セキュリティグループ（SG）**
  - `api-sg`（sg-0600751c154b62e0c）… プレビューEC2用
  - `db-sg` … DB EC2 用。**インバウンド 5432 は `api-sg` からのみ許可**（0.0.0.0/0 は撤廃）
- **公開方針**: 8000/TCP は**外に公開しない**。**SSM ポートフォワーディング**で限定的に閲覧。

> メリット：攻撃面の極小化・コスト最小化。デメリット：閲覧者は SSO/SSM が必要。

---

## 2. GitHub Actions（ワークフロー）概要

### トリガ

- `pull_request: [opened, reopened, synchronize, closed]`

### 主要ステップ

1. **Build & Push**（同一リポPRのみ）
   - `docker/build-push-action` で GHCR へ `:<sha>` と `:pr-<number>` を push
   - `permissions: packages: write` が必要（push 用）
2. **AWS 認証（OIDC）**
   - `aws-actions/configure-aws-credentials@v4` で `github-oidc-pr-staging` を Assume
3. **Preflight**
   - AMI/SG/Subnet 整合性、`--dry-run` の `RunInstances` 実行で権限を検証  
     → **`DryRunOperation` が出れば権限OK**
4. **Upsert**
   - 既存の `Purpose=pr-preview-singleton` を terminate（待機）→ 新規 `run-instances`
   - **User Data** で Docker/Compose 設置、`docker login ghcr.io`、`docker compose up -d`
   - **DB マイグレーション** は `docker run --rm ... alembic upgrade head`（リトライ付き）
5. **任意: DB SG の /32 一時開放**
   - `secrets.DB_SG_ID` が設定されていれば、**プレビューEC2の Public IP/32** を 5432 に追加許可
   - ただし原則は **SG参照（api-sg → db-sg）** を推奨
6. **ヘルスチェック**
   - 8000/TCP が開くまで待機 → `/docs` or `/healthz` を軽く Probe
7. **PRへコメント**
   - Public IP をコメント（※今回は基本 SSM で見る運用）
8. **PR Close**
   - Open PR が 0 なら terminate（掃除）

---

## 3. User Data の実装（AL2023 向けポイント）

**課題**: `docker-compose-plugin` が DNF に無い環境がある。  
**対応**: Compose v2 を GitHub リリースから配置。

```bash
dnf -y update
dnf -y install docker git
systemctl enable --now docker

usermod -aG docker ec2-user || true
usermod -aG docker ssm-user || true
for i in {1..30}; do [ -S /var/run/docker.sock ] && break || sleep 1; done
chmod 666 /var/run/docker.sock || true

mkdir -p /usr/local/lib/docker/cli-plugins
curl -fL -o /usr/local/lib/docker/cli-plugins/docker-compose \
  https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version || true
```

- GHCR は **EC2 側でも `docker login`** が必要（PAT）  
  `echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin`
- pull 失敗時は **GitHub API tarball** を落として **ローカルビルド** にフォールバック。
- マイグレーションは別コンテナで実施（`alembic upgrade head`）。

---

## 4. GHCR 認証パターン

- **Actions（ビルド/プッシュ）**: `GITHUB_TOKEN`（`packages: write`）  
  `docker/login-action@v3` で ghcr.io にログイン
- **EC2（Pull）**: `GHCR_USERNAME` + `GHCR_TOKEN`（Classic PAT 推奨、`read:packages`）

**よくあったエラー**

- `unauthorized`（EC2 側）→ EC2 の `docker login ghcr.io` が未実施。PAT の権限不足にも注意。
- Actions 側 push 失敗 → `permissions: packages: write` が無い。

### PAT が失効した場合の復旧フロー

1. **新しい PAT を発行する**
   - GitHub の **Settings → Developer settings → Personal access tokens** から再発行。
   - GHCR の private pull が必要なら `read:packages`、push するワークフローがあるなら `write:packages` も付与。
   - Fine-grained PAT を使う場合は対象リポジトリ/Organization のアクセス権を忘れずに設定。
2. **ローカル（手元マシンなど）で認証情報を入れ替える**
   - 古い資格情報を削除し、新 PAT でログインし直す。
     ```bash
     docker logout ghcr.io
     docker login ghcr.io -u <GitHubユーザー名>
     # パスワードに新しい PAT を入力
     ```
   - `~/.docker/config.json` のクレデンシャルが更新されるので、そのまま `docker pull` / `docker push` を再実行。
3. **CI のシークレットを更新する**
   - GitHub Actions などで GHCR にログインしている場合、使用中のシークレット（例: `GHCR_TOKEN`）を新 PAT に差し替える。
   - 更新後に該当ワークフローを再実行し、`docker/login-action` が成功するかログを確認。
4. **権限・設定を再確認する**
   - PAT のスコープや Fine-grained PAT のリポジトリ対象が正しいか確認。
   - それでも失敗する場合は GHCR の障害情報やネットワーク制限（VPN など）も合わせてチェックする。

---

## 5. DB 接続（EC2 の PostgreSQL）

- 形式: `postgresql+asyncpg://USER:PASSWORD@172.31.39.125:5432/DBNAME`
- **パスワードに記号があるときは URL エンコード必須**（例 `pa/ss` → `pa%2Fss`）  
  エラー例：`invalid integer value "...“ for connection option "port"` は URL のパース崩れが原因になりやすい。

### SG 設計（推奨）

- `db-sg` の 5432 インバウンドは **`api-sg` を参照許可**（**0.0.0.0/0 は撤廃**）
- これによりプレビューEC2の Public IP が変わっても、**VPC 内での到達性は維持**。

### 到達性チェック（EC2 上）

```bash
# TCP
bash -c 'timeout 3 bash -c "echo > /dev/tcp/172.31.39.125/5432"' && echo "DB TCP OK" || echo "DB TCP NG"

# コンテナから実接続
docker compose -f /srv/app/docker-compose.yml exec -T api python - <<'PY'
import os, psycopg2
url = os.environ["DATABASE_URL"].replace("+asyncpg","")
psycopg2.connect(url).close(); print("DB CONNECT OK")
PY
```

---

## 6. 自分だけ見る：SSM ポートフォワーディング手順（Mac）

### 6.1 事前準備

- AWS CLI v2
- Session Manager Plugin（`session-manager-plugin`）
- **IAM Identity Center（SSO）** にユーザー作成・アカウント/ロール割当 → `aws configure sso`
  - Start URL 例: `https://d-xxxxxxxxxx.awsapps.com/start`
  - SSO Region: `ap-northeast-1`
  - プロファイル名例: `gym-preview`

### 6.2 トンネル開始

```bash
aws ssm start-session \
  --target <PREVIEW_EC2_INSTANCE_ID> \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}' \
  --profile gym-preview --region ap-northeast-1
```

- ブラウザで `http://127.0.0.1:8000/docs`
- 終了は `Ctrl+C`

### 6.3 便利スクリプト（任意）

```bash
#!/usr/bin/env bash
# preview-tunnel.sh: PR番号だけでトンネル
set -euo pipefail
PR="${1:?usage: preview-tunnel.sh <pr-number>}"
REGION="ap-northeast-1"
PROFILE="gym-preview"

IID=$(aws ec2 describe-instances \
  --filters "Name=tag:Purpose,Values=pr-preview-singleton" \
           "Name=tag:PR,Values=${PR}" \
           "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' \
  --output text --profile "$PROFILE" --region "$REGION")

test -n "$IID" && [ "$IID" != "None" ] || { echo "no running instance for PR ${PR}"; exit 1; }

aws ssm start-session \
  --target "$IID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}' \
  --profile "$PROFILE" --region "$REGION"
```

---

## 7. よく詰まったポイントと解決

| 症状/ログ                                                 | 原因                                       | 対応                                                            |
| --------------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------- |
| `No match for argument: docker-compose-plugin`            | AL2023にパッケージが無い                   | Compose v2 を GitHub リリースから手動配置                       |
| `sh: docker: command not found`                           | Docker未導入/サービス停止                  | `dnf install docker` → `systemctl enable --now docker`          |
| GHCR `unauthorized`                                       | EC2側の `docker login` 未実施、PAT権限不足 | `read:packages` 付き PAT で `docker login ghcr.io`              |
| BuildでGHCR Push失敗                                      | Actions の権限不足                         | `permissions: packages: write` を付与                           |
| `cloud-init ... scripts-user failed`                      | User Data の途中失敗                       | `/var/log/cloud-init-output.log` で失敗箇所特定、手動再現で修正 |
| 外から 8000 に繋がらない                                  | 今回は意図的に外公開なし                   | **SSM ポートフォワーディング** でアクセス                       |
| DB タイムアウト                                           | SG 未許可（db-sg に api-sg 許可なし）      | **db-sg に api-sg を参照許可**（5432）                          |
| `invalid integer value ... for connection option "port"`  | `DATABASE_URL` の記号未エンコード          | パスワードを URL エンコード → Secrets 更新 → Actions 再実行     |
| `UnauthorizedOperation ... DescribeInstances/RouteTables` | ロール/プロファイルの権限不足              | 対象ロールへ `ec2:Describe*` / `iam:PassRole` 等を追加          |
| `No AWS accounts are available to you.`（SSO設定）        | ユーザーにアカウント/ロール未割当          | Identity Center で割当後に再 `aws configure sso`                |

---

## 8. 確認コマンド集（チートシート）

### EC2内のメタデータ

```bash
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id
curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4
```

### SG/サブネット/ルート

```bash
aws ec2 describe-instances --instance-ids <IID> --query 'Reservations[0].Instances[0].SecurityGroups'
aws ec2 describe-security-groups --group-ids <SG_ID> --query 'SecurityGroups[0].IpPermissions'
aws ec2 describe-subnets --subnet-ids <SUBNET_ID> --query 'Subnets[0].{PublicIpOnLaunch:MapPublicIpOnLaunch,RouteTableAssociations:Associations}'
aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=<SUBNET_ID>"
```

### コンテナ/ポート/HTTP

```bash
docker compose -f /srv/app/docker-compose.yml ps -a
docker compose -f /srv/app/docker-compose.yml logs --tail=200 api
ss -ltnp | grep :8000 || sudo lsof -iTCP:8000 -sTCP:LISTEN
curl -sS http://127.0.0.1:8000/docs | head
```

### OpenAPI からルート確認

```bash
curl -s http://127.0.0.1:8000/openapi.json | jq -r '.paths | keys[]' | sed -n '1,50p'
```

---

## 9. クリーニングとログ採取

### PR close で自動Terminate

- ワークフロー内で **open PR=0** なら `Purpose=pr-preview-singleton` を terminate。

### 手動クリーンアップ

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Purpose,Values=pr-preview-singleton" \
           "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text \
| xargs -r aws ec2 terminate-instances --instance-ids
```

### SSMでログ採取（起動失敗時）

```bash
aws ssm send-command \
  --instance-ids <IID> \
  --document-name "AWS-RunShellScript" \
  --parameters commands='["docker compose -f /srv/app/docker-compose.yml ps -a","docker compose -f /srv/app/docker-compose.yml logs --tail=200 api || true","systemctl status docker --no-pager || true"]'
```

---

## 10. 参考（現在の主要リソース）

- **Region**: `ap-northeast-1`
- **AMI**: `ami-08a59875ad2a26a5f` (Amazon Linux 2023, x86_64)
- **Preview EC2 SG**: `api-sg` = `sg-0600751c154b62e0c`
- **Subnet**: `subnet-0312f79d1cf5c6bdc`
- **Instance Profile**: `ec2-pr-preview-ssm`
- **DB (EC2) Private IP**: 例 `172.31.39.125:5432`
- **GHCR**: `ghcr.io/<owner>/<repo>:<sha>` / `:pr-<number>`

---

## 11. 将来の改善（メモ）

- **PRごとのEphemeral DB（Docker/Postgres）**：`db:` サービス追加、PR close でボリューム削除。
- **TTL 自動終了**：起動時に `shutdown-at` タグ → Lambda/SSM Automation でTerminate。
- **/healthz / readyz** の整備とワークフローのHTTPヘルスプローブ連携。
- **Route 53 + Aレコード（社内向け）**：SSM経由のみ or VPN 内のみ到達など。

---

### 変更履歴（抜粋）

- AL2023でのCompose導入を**手動配置**に変更（`docker-compose-plugin` 未提供対策）
- GHCR Pull のため **EC2で `docker login ghcr.io`（PAT）** を追加
- DBは**EC2**で運用（RDSではない）。`db-sg` は **`api-sg` 参照のみ許可**へ是正
- **SSM ポートフォワーディング**により、8000/TCP の外部公開を不要化
- `DATABASE_URL` の**URLエンコード問題**（記号を含むパスワード）を整理
- Preflight で **DryRunOperation** による権限健全性チェックを実装
