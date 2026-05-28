# Backfill Resume

Дата актуализации: 2026-05-27.

## Текущий статус

OLAP-only backfill завершен.

Фактический диапазон в `mart_daily_sales`:

- `2023-05-27..2026-05-27`
- строк: `137174`
- пропущенных дней: `0`

Read-only защита от внешнего live writer возвращена:

```bash
ALTER DATABASE iiko_analytics SET default_transaction_read_only = on;
```

Перед следующим осознанным backfill/live sync нужно снять:

```bash
docker compose exec -T db psql -U analytics -d postgres -c "ALTER DATABASE iiko_analytics SET default_transaction_read_only = off;"
```

## Что было сделано 2026-05-27

Основной проход к моменту проверки уже дошел до текущей даты `2026-05-27`.

Единственный пропущенный чанк был:

- `2023-07-29..2023-08-28`

Повторный запуск сначала упал в sandbox без доступа к host-сокету Postgres:

```text
connection is bad: no error details available
```

После запуска с разрешенным локальным сетевым доступом чанк завершился успешно:

```bash
python3 scripts/backfill_olap.py --date-from 2023-07-29 --date-to 2023-08-28 --chunk-days 31 --workers 1 --kill-other-db-sessions --summary-path /tmp/olap_backfill_retry_20260527.jsonl
```

Результат:

```text
daily_sales: 2904
branch_kpi: 2904
product_sales: 152892
payment_sales: 6205
discount_sales: 7769
staff_sales: 15884
elapsed: 194.2s
failures: 0
```

## Контрольные проверки

Диапазон:

```bash
docker compose exec -T db psql -U analytics -d iiko_analytics -c "SELECT min(business_date), max(business_date), count(*) FROM mart_daily_sales;"
```

```text
min: 2023-05-27
max: 2026-05-27
count: 137174
```

Дыры:

```bash
docker compose exec -T db psql -U analytics -d iiko_analytics -c "WITH days AS (SELECT generate_series('2023-05-27'::date, (SELECT max(business_date) FROM mart_daily_sales), '1 day')::date d), loaded AS (SELECT DISTINCT business_date d FROM mart_daily_sales) SELECT count(*) AS missing_days, min(days.d) AS first_missing, max(days.d) AS last_missing FROM days LEFT JOIN loaded USING (d) WHERE loaded.d IS NULL;"
```

```text
missing_days: 0
first_missing: null
last_missing: null
```

Повторенный чанк:

```bash
docker compose exec -T db psql -U analytics -d iiko_analytics -c "SELECT min(business_date), max(business_date), count(*) FROM mart_daily_sales WHERE business_date BETWEEN '2023-07-29' AND '2023-08-28';"
```

```text
min: 2023-07-29
max: 2023-08-28
count: 2904
```

## Историческая команда основного прохода

Основной проход выполнялся так:

```bash
python3 scripts/backfill_olap.py --date-from 2023-05-28 --date-to 2026-05-26 --chunk-days 31 --workers 1 --kill-other-db-sessions --summary-path /tmp/olap_backfill_summary.jsonl
```

Причина `workers=1`: параллельные воркеры конфликтовали на upsert в `dim_products` / `dim_employees`, плюс внешний live sync писал в БД тем же пользователем.

## Следующее

Backfill истории OLAP завершен. Дальше по проектному плану:

- сверить DataLens views/presets на полном диапазоне;
- решить, когда запускать live/today sync и тогда временно снять read-only;
- не запускать новый writer без явного снятия `default_transaction_read_only`.
