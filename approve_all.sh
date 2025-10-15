#!/usr/bin/env bash
API_BASE="http://localhost:8000"
SOURCES=("koto" "sumida" "edogawa")  # 空にすると全ソース
LIMIT=80
SLEEP=2.5            # 429対策
MAX_RETRY=3

approve_one() {
  local id="$1" retry=0
  while :; do
    # --fail-with-body で非2xxをエラー扱い、HTTPコードも出す
    RESP=$(curl -sS --write-out " HTTPSTATUS:%{http_code}" \
      -X POST "$API_BASE/admin/candidates/$id/approve" \
      -H "Content-Type: application/json" -d '{}' )
    BODY="${RESP% HTTPSTATUS:*}"
    CODE="${RESP##*HTTPSTATUS:}"
    if [[ "$CODE" == "200" ]]; then
      printf "."
      return 0
    fi
    retry=$((retry+1))
    if [[ "$CODE" == "429" || "$CODE" =~ ^5 ]]; then
      sleep $SLEEP
      [[ $retry -lt $MAX_RETRY ]] && continue
    fi
    echo ""
    echo "[ERR] approve id=$id code=$CODE body=$(echo "$BODY" | tr -d '\n' | cut -c1-200)"
    return 1
  done
}

approve_source() {
  local src="$1"
  local cursor=""
  local page=1
  while :; do
    URL="$API_BASE/admin/candidates?status=new&limit=$LIMIT"
    [[ -n "$src" ]] && URL="$URL&source=$src"
    [[ -n "$cursor" ]] && URL="$URL&cursor=$cursor"

    RESP=$(curl -sS --fail "$URL") || { echo "[ERR] fetch list failed: $URL"; break; }
    IDS=$(echo "$RESP" | jq -r '(.items // [])[] | .id') || { echo "[ERR] jq parse failed"; break; }
    cursor=$(echo "$RESP" | jq -r '.next_cursor // empty')

    if [[ -z "$IDS" ]]; then
      [[ $page -eq 1 ]] && echo "[$src] no new candidates"
      break
    fi

    echo "[$src] page $page approving $(printf "%s\n" $IDS | wc -l | tr -d ' ') items..."
    # 1つずつ承認（進行記号を出す）
    while IFS= read -r id; do
      approve_one "$id" || true
      sleep $SLEEP
    done <<< "$IDS"
    echo ""  # 改行
    [[ -z "$cursor" ]] && break
    page=$((page+1))
  done
}

# 実行
if [[ ${#SOURCES[@]} -eq 0 ]]; then
  approve_source ""  # 全ソース
else
  for s in "${SOURCES[@]}"; do approve_source "$s"; done
fi

echo "done."
