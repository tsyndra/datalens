#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 YYYY-MM-DD YYYY-MM-DD" >&2
  exit 2
fi

date_from="$1"
date_to="$2"
lock_file="/tmp/datalens_iiko_sync.lock"

python3 scripts/bootstrap_env.py >/dev/null
flock -n "$lock_file" python3 scripts/sync_iiko.py \
  --date-from "$date_from" \
  --date-to "$date_to" \
  --skip-nomenclature
