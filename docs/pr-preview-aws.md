# PR プレビュー環境構築メモ (AWS EC2)

## 概要

GitHub Actions から OIDC 経由で AWS にアクセスし、  
プルリクごとに **単一の EC2 インスタンス**を起動して API サーバを Docker Compose で立ち上げる仕組みを構築した。  
最終的に PR にコメントとして Preview URL (`http://<IP>:8000`) を付与するところまで動作確認。

---

## 手順とトラブルシューティング記録

### 1. IAM / OIDC 設定

- GitHub OIDC を利用するため IAM Role `github-oidc-pr-staging` を作成。
  - アタッチポリシー: `ec2:* (RunInstances, TerminateInstances, Describe*, AuthorizeSecurityGroupIngress, Wait)`
  - `iam:PassRole` を許可（EC2 にアタッチする SSM 用インスタンスプロファイルを渡すため）。
- EC2 側で利用するインスタンスプロファイル `ec2-pr-preview-ssm` を作成。
  - SSM 経由でログ収集を行うために `AmazonSSMManagedInstanceCore` を付与。
  - 追加で `ec2:DescribeInstances` を許可しないと `describe-instances` が失敗する → ポリシー追加で解決。

---

### 2. セキュリティグループ

- API 用 SG `sg-0600751c154b62e0c`
  - インバウンド: `TCP/8000` → `0.0.0.0/0` (初期は全開放、後で制限予定)。
- RDS 用 SG
  - 当初 `0.0.0.0/0` がついていた → **セキュリティリスク**なので削除。
  - 代わりに **API SG からのアクセスだけ許可** に変更。  
    これで EC2 経由でのみ DB に接続可能。

---

### 3. 初期トラブル

1. **GHCR pull unauthorized**
   - 原因: GitHub Actions の権限不足 (`packages: write` が必要)。
   - 対応: workflow yaml に `permissions: packages: write` を追加。
   - また、`GHCR_USERNAME` と `GHCR_TOKEN` を Secrets に追加し、EC2 起動時に `docker login ghcr.io` を実行。

2. **DB 接続失敗 (timeout)**
   - 原因: RDS SG が `0.0.0.0/0` で一見開いていたが、EC2 からの到達性がなく失敗。
   - 解決: **EC2 SG → RDS SG** の許可ルールを設定。

3. **`ec2:DescribeInstances` Unauthorized**
   - 原因: SSM 経由の IAM Role に Describe 系権限がなかった。
   - 解決: `ec2:DescribeInstances` を `ec2-pr-preview-ssm` に追加。

4. **docker compose not found**
   - Amazon Linux 2023 には `docker compose` パッケージが無い。
   - 解決: UserData で公式リリースからバイナリを配置。
     ```bash
     mkdir -p /usr/local/lib/docker/cli-plugins
     curl -fL -o /usr/local/lib/docker/cli-plugins/docker-compose \
       https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64
     chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
     ```

---

### 4. 現在の動作

- PR を開くと:
  1. GHCR にイメージを build & push
  2. EC2 を起動 (既存があれば terminate → 再作成)
  3. UserData で `docker compose up -d` 実行 → API 起動
  4. Health check (`/docs`, `/health/db`) を確認
  5. PR に `Preview URL: http://<ip>:8000` をコメント

- PR を close すると:
  - **他に open PR が無ければ** EC2 インスタンスを terminate。

---

## 今後の改善予定

- **Secrets を SSM Parameter Store に移行**（GitHub Secrets から除去）。
- **EC2 → RDS の SG 制御をさらに厳格化**（PR 番号付きで動的にルール付与）。
- **TTL タグ付き自動掃除**（24h で自動削除してコスト抑制）。
- **ephemeral DB を docker で立てる**（共有 RDS を使わず PR ごとに消える DB）。

---

## まとめ

- 最低限「PR ごとに EC2 でアプリが起動してプレビューできる」状態は完成。
- セキュリティやコスト面は別タスクで改善予定。
- 本ドキュメントを見返すことで、トラブル対応の履歴をたどれるようになった。
