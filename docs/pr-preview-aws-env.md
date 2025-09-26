# PRプレビュー環境構築ドキュメント（AWS / GitHub Actions / EC2 / Docker）

1. 目的
   • GitHub Pull Request 単位で 一時的に EC2 を起動し、Docker Compose で API コンテナを動かす
   • マージ/クローズ時にはインスタンスを削除（コスト削減）
   • ステージング用DBと連携しつつ、将来的にはPRごとにEphemeral DBへ切り替え可能

⸻

2. 初期構築手順

2.1 IAM準備
• GitHub Actions 用に OIDC 連携
• github-oidc-pr-staging IAMロールを作成
• 信頼ポリシーに GitHub OIDC を追加
• 権限ポリシーは以下を付与
• ec2:_ （本番は run-instances, terminate-instances, describe-_ のみに絞る）
• iam:PassRole （EC2にSSMロールを付与するため）

2.2 SSM設定
• EC2インスタンスにアタッチするIAM Role: ec2-pr-preview-ssm
• 権限: AmazonSSMManagedInstanceCore
• SSM Agent は Amazon Linux 2023 にプリインストール済み

2.3 セキュリティグループ
• api-sg
• Inbound: TCP 8000 (0.0.0.0/0) → 初期は開放したが、後に制限予定
• Outbound: All
• db-sg
• Inbound: TCP 5432 → api-sg からのみ許可

2.4 GitHub Actions ワークフロー
• pr-preview.yml を .github/workflows/ に追加
• PR Opened → EC2起動
• PR Closed → EC2削除
• docker-compose.yml を EC2 に配布して api サービス起動

⸻

3. ハマったポイントと対処

3.1 GHCR認証エラー
• 最初は packages: read 権限しかなく unauthorized
• → packages: write を追加し解決

3.2 DB接続不可
• SGの設定確認

aws ec2 describe-security-groups --group-ids <DB_SG_ID> \
 --query 'SecurityGroups[0].IpPermissions'

    •	0.0.0.0/0 が開いていた → セキュリティリスク大
    •	修正: db-sg のInboundは api-sg のみ許可

3.3 SSOログイン詰まり
• aws configure sso で「No AWS accounts available」
• 原因: Identity Centerの初期設定不足
• 対処:
• Identity Center 有効化
• ユーザー作成 → アカウント/ロール割り当て
• aws configure sso 再実行 → 成功

3.4 接続確認
• EC2上でAPI確認

curl -s http://127.0.0.1:8000/docs

    •	外部からの疎通確認

curl -I http://<PUBLIC_IP>:8000/ -m 5

→ Security Groupが閉じていると timeout

3.5 SSMポートフォワード
• 外部に公開せず自分だけ確認したい場合:

aws ssm start-session \
 --target <INSTANCE_ID> \
 --document-name AWS-StartPortForwardingSession \
 --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}' \
 --profile gym-preview --region ap-northeast-1

    •	ローカルから http://127.0.0.1:8000/docs でアクセス可能

⸻

4. 現状の運用フロー1. PR作成
   → GitHub Actions が EC2起動、DockerでAPIデプロイ2. PR上に Preview URL をコメント
   • SGが制限されている場合は SSMポートフォワードで確認3. PRクローズ/マージ
   → EC2自動削除

⸻

5. 今後の改善ポイント
   • DBを Ephemeral に切り替え（docker-compose内でPostgres立てる）
   • SGのIngressをPRごとに /32 で動的に制御
   • TTL付きインスタンス削除（消し忘れ防止）
   • ヘルスチェックの厳格化 (/readyz エンドポイント)

⸻

👉 これで、最初の構築方法からトラブルシューティングまで一通りまとまっています。
