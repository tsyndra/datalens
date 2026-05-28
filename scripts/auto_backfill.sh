#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p data

state_file="data/auto_backfill_cursor"
lock_file="/tmp/datalens_iiko_sync.lock"
start_date="${DATALENS_BACKFILL_START:-2023-01-01}"
end_date="${DATALENS_BACKFILL_END:-$(date +%F)}"
chunk_days="${DATALENS_BACKFILL_CHUNK_DAYS:-31}"

if [[ -f "$state_file" ]]; then
  cursor="$(<"$state_file")"
else
  cursor="$start_date"
fi

if [[ "$cursor" > "$end_date" ]]; then
  echo "auto_backfill: complete cursor=$cursor end=$end_date"
  exit 0
fi

chunk_to="$(date -d "$cursor + $((chunk_days - 1)) days" +%F)"
if [[ "$chunk_to" > "$end_date" ]]; then
  chunk_to="$end_date"
fi

next_cursor="$(date -d "$chunk_to + 1 day" +%F)"

python3 scripts/bootstrap_env.py >/dev/null

echo "auto_backfill: loading $cursor .. $chunk_to"
flock -n "$lock_file" python3 scripts/sync_iiko.py \
  --date-from "$cursor" \
  --date-to "$chunk_to" \
  --skip-nomenclature

echo "$next_cursor" > "$state_file"
echo "auto_backfill: next cursor $next_cursor"
