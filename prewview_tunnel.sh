#!/usr/bin/env bash
# preview-tunnel.sh
# PR番号のEC2プレビューに SSM ポートフォワーディングで接続する
# 使い方: ./preview-tunnel.sh 58 [LOCAL_PORT] [AWS_PROFILE] [AWS_REGION]

set -euo pipefail

PR_NUMBER="${1:-}"
if [[ -z "${PR_NUMBER}" ]]; then
  echo "Usage: $0 <PR_NUMBER> [LOCAL_PORT] [AWS_PROFILE] [AWS_REGION]" >&2
  exit 1
fi

# 引数/デフォルト
LOCAL_PORT="${2:-8000}"
AWS_PROFILE="${3:-${AWS_PROFILE:-gym-preview}}"
AWS_REGION="${4:-${AWS_REGION:-ap-northeast-1}}"

purpose="pr-preview-singleton"

echo "== Looking for PR #${PR_NUMBER} preview instance (region=${AWS_REGION}, profile=${AWS_PROFILE}) =="

# 該当インスタンス取得（runningのみ）
read -r IID PUBIP PRIVIP <<<"$(aws ec2 describe-instances \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}" \
  --filters \
    "Name=tag:Purpose,Values=${purpose}" \
    "Name=tag:PR,Values=${PR_NUMBER}" \
    "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[].[*].[InstanceId,PublicIpAddress,PrivateIpAddress]" \
  --output text | head -n1 || true)"

if [[ -z "${IID:-}" ]]; then
  echo "ERROR: Running instance for PR #${PR_NUMBER} not found."
  echo " - PRのActions（PR Preview）ジョブが成功しているか確認してください。"
  echo " - 起動直後は数十秒かかることがあります。"
  exit 2
fi

echo "Found instance: ${IID} (public=${PUBIP:-N/A}, private=${PRIVIP:-N/A})"

# ローカルポートが空くまでインクリメント（8000, 8001, …）
pick_port() {
  local p="$1"
  while lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; do
    p=$((p+1))
    if (( p > 65530 )); then
      echo "ERROR: no free local port found" >&2
      exit 3
    fi
  done
  echo "$p"
}

LOCAL_PORT="$(pick_port "${LOCAL_PORT}")"
echo "Using local port: ${LOCAL_PORT}"

echo
echo "== Starting SSM port forwarding =="
echo "aws ssm start-session --target ${IID} --document-name AWS-StartPortForwardingSession \\"
echo "  --parameters '{\"portNumber\":[\"8000\"],\"localPortNumber\":[\"${LOCAL_PORT}\"]}' \\"
echo "  --profile ${AWS_PROFILE} --region ${AWS_REGION}"
echo

aws ssm start-session \
  --target "${IID}" \
  --document-name "AWS-StartPortForwardingSession" \
  --parameters "{\"portNumber\":[\"8000\"],\"localPortNumber\":[\"${LOCAL_PORT}\"]}" \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}"

# ここから先はセッション終了後に表示される
echo
echo "Session ended."
echo "次回はブラウザで http://127.0.0.1:${LOCAL_PORT}/docs を開けばPRアプリが見られます。"