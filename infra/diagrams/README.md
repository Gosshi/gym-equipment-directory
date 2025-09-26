# AWS プレビュー環境ダイアグラム

このディレクトリには mingrammer/diagrams を使って Gym Equipment Directory の PR プレビュー向け
AWS 構成を可視化するスクリプトが含まれています。

## セットアップ

1. Graphviz をローカルにインストールしてください（macOS の場合は `brew install graphviz` など）。
2. 依存関係を仮想環境にインストールします。
   ```bash
   cd infra/diagrams
   make init
   ```

## 図の生成

- PNG 形式を生成: `make png`
- SVG 形式を生成: `make svg`
- 両形式をまとめて生成: `make all`

生成すると `gym-preview-aws.png` および `gym-preview-aws.svg` が作成されます。生成物は `.gitignore`
に含まれているためリポジトリには追加されません。

## 図の内容

- GitHub Actions から OIDC 経由で IAM Role を引き受け、PR Preview 用の EC2 インスタンスを起動する
  フローを描画します。
- VPC 内の Public Subnet (`subnet-xxxx`) に API 用 EC2 (`api-sg`) と DB 用 EC2 (`db-sg`) を配置します。
- API EC2 から DB EC2 への tcp/5432 (Security Group 間) の接続を表現します。
- Internet Gateway と Route Table を点線で描画し、Public モード時のみ利用される経路には
  「SSM運用では未使用」と注記を付けています。
- ユーザーの Mac から AWS Systems Manager のポートフォワーディングを経由して 127.0.0.1:8000 から
  EC2:8000 へアクセスする流れを示します。

## ラベルを環境変数でカスタマイズ

下記の環境変数を設定すると図中のラベルを差し替えられます。設定していない場合は
`aws_arch.py` 内のデフォルト値が使用されます。

- `GH_OIDC_ROLE_ARN`: GitHub Actions から引き受ける IAM Role の表示名
- `PREVIEW_INSTANCE_NAME`: PR Preview 用 EC2 の表示名
- `SUBNET_ID`: Public Subnet の表示名
- `API_SG_ID`: API 用 Security Group の表示名
- `DB_SG_ID`: DB 用 Security Group の表示名
- `VPC_ID`: VPC の表示名

必要に応じて他の値を追加する場合は `aws_arch.py` の `LABEL_DEFAULTS` を編集してください。
