#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

today="$(date +%F)"
lock_file="/tmp/datalens_iiko_sync.lock"

python3 scripts/bootstrap_env.py >/dev/null
flock -n "$lock_file" python3 scripts/sync_iiko.py --date-from "$today" --date-to "$today" --skip-nomenclature
