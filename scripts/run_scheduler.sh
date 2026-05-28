#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p data logs

lock_file="${DATALENS_SYNC_LOCK_FILE:-/tmp/datalens_iiko_sync.lock}"
realtime_interval="${DATALENS_REALTIME_INTERVAL_SECONDS:-60}"
olap_today_interval="${DATALENS_OLAP_TODAY_INTERVAL_SECONDS:-600}"
backfill_interval="${DATALENS_BACKFILL_INTERVAL_SECONDS:-1800}"
reconcile_interval="${DATALENS_RECONCILE_INTERVAL_SECONDS:-3600}"
reconcile_days="${DATALENS_RECONCILE_DAYS:-7}"

last_realtime=0
last_olap_today=0
last_backfill=0
last_reconcile=0

log() {
  printf '%s %s\n' "$(date -Iseconds)" "$*"
}

run_locked() {
  local name="$1"
  shift

  log "start ${name}: $*"
  if flock -n "$lock_file" "$@"; then
    log "done ${name}"
  else
    local code=$?
    if [[ "$code" -eq 1 ]]; then
      log "skip ${name}: another sync is running"
    else
      log "failed ${name}: exit=${code}"
    fi
  fi
}

today_msk() {
  TZ=Europe/Moscow date +%F
}

date_msk_days_ago() {
  TZ=Europe/Moscow date -d "$1 days ago" +%F
}

log "scheduler boot realtime=${realtime_interval}s olap_today=${olap_today_interval}s backfill=${backfill_interval}s reconcile=${reconcile_interval}s"

while true; do
  now="$(date +%s)"
  today="$(today_msk)"

  if (( now - last_realtime >= realtime_interval )); then
    last_realtime="$now"
    run_locked "realtime-cloud-today" \
      env IIKO_DELIVERY_STATUSES="${IIKO_REALTIME_DELIVERY_STATUSES:-Unconfirmed,WaitCooking,ReadyForCooking,CookingStarted,CookingCompleted,Waiting,OnWay,Delivered,Closed,Cancelled,closed}" \
      python3 scripts/sync_iiko.py \
        --date-from "$today" \
        --date-to "$today" \
        --skip-nomenclature \
        --skip-olap
  fi

  if (( now - last_olap_today >= olap_today_interval )); then
    last_olap_today="$now"
    run_locked "olap-today" \
      python3 scripts/sync_iiko.py \
        --date-from "$today" \
        --date-to "$today" \
        --skip-nomenclature
  fi

  if (( now - last_reconcile >= reconcile_interval )); then
    last_reconcile="$now"
    from_date="$(date_msk_days_ago "$reconcile_days")"
    run_locked "reconcile-recent" \
      python3 scripts/sync_iiko.py \
        --date-from "$from_date" \
        --date-to "$today" \
        --skip-nomenclature
  fi

  if (( now - last_backfill >= backfill_interval )); then
    last_backfill="$now"
    if [[ "${DATALENS_BACKFILL_ENABLED:-1}" == "1" ]]; then
      run_locked "auto-backfill" bash scripts/auto_backfill.sh
    else
      log "skip auto-backfill: DATALENS_BACKFILL_ENABLED!=1"
    fi
  fi

  sleep 5
done
