# Storage Strategy

Дата актуализации: 2026-05-26.

Цель: загрузить 3 года данных для DataLens без раздувания PostgreSQL сырыми повторными JSON payload.

## Главный вывод

Не обрезаем аналитику. Обрезаем только бесконечный append raw JSON.

DataLens не должен читать `raw_*`. Для DataLens нужны:

- `dim_*`;
- `fact_*`;
- `mart_*`;
- `dl_preset_*` / `dl_report_*`.

Raw нужен для отладки, аудита и восстановления ошибок, но не как вечное хранилище каждого ответа API.

## Что хранить долго

| Слой | Retention | Зачем |
|---|---:|---|
| `dim_*` | бессрочно | справочники |
| `fact_*` | 3+ года | аналитические события |
| `mart_*` | 3+ года | агрегаты DataLens |
| `dl_preset_*` | view | плоские датасеты DataLens |
| `etl_run_status` | 1+ год | мониторинг загрузок |
| `etl_load_checksums` | 3+ года | сверка чанков |

## Что не хранить бесконечно

| Raw таблица | Новый подход |
|---|---|
| `raw_cloud_deliveries_by_date_status` | dedupe by hash, retention 3-14 дней для успешных payload |
| `raw_server_olap_sales_daily` | не append-ить одинаковые окна; хранить checksum и последний payload только для debug |
| `raw_cloud_stop_lists` | вне текущего scope; не грузить, пока метрика не понадобится |
| `raw_cloud_customer_categories` | справочник: upsert latest + hash |
| `raw_cloud_terminal_groups` | справочник: upsert latest + hash |
| `raw_cloud_external_menus` | справочник: latest by menu id/hash |

## Почему текущая БД стала 20 GB

Топ размера:

| Таблица | Размер |
|---|---:|
| `raw_cloud_deliveries_by_date_status` | 18 GB |
| `raw_server_olap_sales_daily` | 1.3 GB |
| `raw_cloud_customer_categories` | 689 MB |
| `raw_cloud_stop_lists` | 213 MB |

При этом нормализованные факты и витрины занимают десятки мегабайт. Значит, полная 3-летняя БД не обязана быть огромной, если не хранить повторный raw.

## Правила ingestion

### Rule 1. Hash every payload

В raw/meta слой добавить:

```sql
payload_hash text NOT NULL
```

Hash считать по canonical JSON:

```text
sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')))
```

### Rule 2. Upsert instead of append

Для регулярных источников ключ должен включать окно и параметры запроса:

```text
source_system
method
organization_id
terminal_group_id
status
window_from
window_to
payload_hash
```

Если payload уже был, обновляем `last_seen_at` и `seen_count`, а не вставляем новый JSON.

### Rule 3. Normalize first, keep raw short

Пайплайн:

```text
API response
  -> normalize into dim/fact/mart
  -> write etl checksum
  -> keep raw only by retention/debug policy
```

Не наоборот.

### Rule 4. Separate historical and realtime raw

Historical backfill:

- нормализовать и агрегировать;
- хранить checksum;
- successful raw можно удалять после 1-3 дней;
- failed raw хранить до ручного разбора.

Realtime today:

- raw retention 3-14 дней;
- `fact_*` upsert по stable id;
- today marts обновлять часто.

### Rule 5. Keep audit summaries

Вместо вечного JSON для каждого запуска хранить:

```text
source
method
date_from/date_to
organization_id
rows_raw
rows_inserted
rows_updated
orders_count
items_qty
gross_revenue
net_revenue
payload_hash
started_at
finished_at
status
error_message
```

## Новые таблицы

Минимально нужны:

```text
etl_run_status
etl_load_checksums
raw_payload_audit
```

Опционально:

```text
raw_payload_errors
```

## Оценка размера

С текущим append-only raw подходом 3 года могут занять сотни GB или больше.

С нормальным подходом:

- факты + витрины за 3 года: ориентировочно десятки GB;
- raw debug retention: ограниченный хвост;
- итоговая БД ожидаемо ближе к `15-40 GB`, а не к `800 GB+`.

Точную оценку нужно пересчитать после внедрения dedupe/retention и тестового backfill 30 дней.

## Перед новым backfill

Текущий статус реализации:

- raw hash/upsert добавлен для основных `raw_cloud_*` и `raw_server_olap_*` таблиц;
- новые OLAP raw payload за 2026-05-26 заняли килобайты, а не гигабайты;
- старые 20 GB очищены через `TRUNCATE ... RESTART IDENTITY CASCADE`;
- текущая пустая БД занимает около `10 MB`;
- `etl` остановлен;
- на базе временно включен `default_transaction_read_only=on`, потому что внешний live/manual sync продолжал записывать новые строки после очистки.

Перед новым 3-летним backfill:

1. Оставить `etl` остановленным.
2. Снять временный read-only:
   `ALTER DATABASE iiko_analytics SET default_transaction_read_only = off;`
3. Довести checksum таблицы до реального заполнения.
4. Запустить тестовый backfill 7-30 дней.
5. Проверить размер raw/fact/mart.
6. Только после этого запускать 3 года.
