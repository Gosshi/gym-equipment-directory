#!/usr/bin/env bash
set -euo pipefail

PR_NUM="${1:-}"
PROFILE="${AWS_PROFILE:-gym-preview}"
REGION="${AWS_REGION:-ap-northeast-1}"
LOCAL_PORT="${LOCAL_PORT:-8001}"
REMOTE_PORT="${REMOTE_PORT:-8000}"

if [[ -z "${PR_NUM}" ]]; then
  echo "Usage: $0 <PR_NUMBER> [LOCAL_PORT]"
  exit 1
fi
if [[ $# -ge 2 ]]; then
  LOCAL_PORT="$2"
fi

echo "== Looking for PR #${PR_NUM} preview instance (region=${REGION}, profile=${PROFILE}) =="

# ① タグで検索して、最新(LaunchTime降順)のインスタンスIDを取得
IID=$(
  aws ec2 describe-instances \
    --profile "${PROFILE}" --region "${REGION}" \
    --filters \
      "Name=tag:Purpose,Values=pr-preview-singleton" \
      "Name=tag:PR,Values=${PR_NUM}" \
      "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query 'Reservations[].Instances[].[LaunchTime,InstanceId]' \
    --output text \
  | sort -r \
  | awk 'NR==1{print $2}'
)

# ② 見つからない時は Name タグでもフォールバック
if [[ -z "${IID:-}" || "${IID}" == "None" ]]; then
  IID=$(
    aws ec2 describe-instances \
      --profile "${PROFILE}" --region "${REGION}" \
      --filters \
        "Name=tag:Purpose,Values=pr-preview-singleton" \
        "Name=tag:Name,Values=*pr${PR_NUM}*" \
        "Name=instance-state-name,Values=pending,running,stopped,stopping" \
      --query 'Reservations[].Instances[].[LaunchTime,InstanceId]' \
      --output text \
    | sort -r \
    | awk 'NR==1{print $2}'
  )
fi

if [[ -z "${IID:-}" || "${IID}" == "None" ]]; then
  echo "Not found: instance for PR=${PR_NUM}."
  echo "Check tags {Purpose=pr-preview-singleton, PR=${PR_NUM}} on the instance."
  exit 2
fi

PUB_IP=$(aws ec2 describe-instances --profile "${PROFILE}" --region "${REGION}" \
  --instance-ids "${IID}" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
PRI_IP=$(aws ec2 describe-instances --profile "${PROFILE}" --region "${REGION}" \
  --instance-ids "${IID}" --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)
STATE=$(aws ec2 describe-instances --profile "${PROFILE}" --region "${REGION}" \
  --instance-ids "${IID}" --query 'Reservations[0].Instances[0].State.Name' --output text)

echo "Found instance: ${IID} (state=${STATE}, public=${PUB_IP}, private=${PRI_IP})"
echo "Using local port: ${LOCAL_PORT}"

echo
echo "== Starting SSM port forwarding =="
set -x
aws ssm start-session \
  --target "${IID}" \
  --document-name AWS-StartPortForwardingSession \
  --parameters "{\"portNumber\":[\"${REMOTE_PORT}\"],\"localPortNumber\":[\"${LOCAL_PORT}\"]}" \
  --profile "${PROFILE}" --region "${REGION}"