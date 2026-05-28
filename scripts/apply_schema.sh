#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -f .credentials.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .credentials.env
  set +a
fi

: "${POSTGRES_USER:=analytics}"
: "${POSTGRES_DB:=iiko_analytics}"
: "${DATALENS_READER_PASSWORD:?Set DATALENS_READER_PASSWORD in .credentials.env}"

for sql_file in sql/*.sql; do
  docker compose exec -T db psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -v datalens_reader_password="$DATALENS_READER_PASSWORD" \
    -f /dev/stdin < "$sql_file"
done
