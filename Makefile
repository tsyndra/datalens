.PHONY: env up down logs logs-etl db-schema db-marts db-psql sync-iiko update-datalens update-today backfill-range auto-backfill scheduler report-builder

# Собирает ./.env: сливает переменные IIKO_* со всех соседних реп под parent(workdir),
# плюс postgres/DATALENS из ./.credentials.env (см. .credentials.env.example).
env:
	python3 scripts/bootstrap_env.py --verbose

# Пересборка без лишних логов
env-quiet:
	python3 scripts/bootstrap_env.py

up: env-quiet
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f db

logs-etl:
	docker compose logs -f etl

db-schema:
	bash scripts/apply_schema.sh

db-marts:
	docker compose exec -T db psql -U $${POSTGRES_USER:-analytics} -d $${POSTGRES_DB:-iiko_analytics} -c "SELECT refresh_datalens_marts(NULL, NULL); SELECT refresh_datalens_today_marts();"

db-psql:
	docker compose exec db psql -U $${POSTGRES_USER:-analytics} -d $${POSTGRES_DB:-iiko_analytics}

sync-iiko:
	python3 scripts/sync_iiko.py

update-datalens:
	bash scripts/update_datalens.sh

update-today:
	bash scripts/update_today.sh

backfill-range:
	bash scripts/backfill_range.sh $${DATE_FROM:?set DATE_FROM=YYYY-MM-DD} $${DATE_TO:?set DATE_TO=YYYY-MM-DD}

auto-backfill:
	bash scripts/auto_backfill.sh

scheduler:
	bash scripts/run_scheduler.sh

report-builder:
	python3 app/report_builder.py
