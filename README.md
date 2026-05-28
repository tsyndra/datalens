## DataLens iiko Analytics

PostgreSQL + ETL слой для аналитики iiko в Yandex DataLens.

Текущий статус: основные источники iikoCloud и iikoServer OLAP проверены, но полный backfill остановлен. Перед новой загрузкой за 3 года нужно изменить хранение raw JSON, иначе БД быстро раздувается.

## Документы

Актуальные документы:

| Файл | Назначение |
|---|---|
| [docs/project_context.md](docs/project_context.md) | главный статус проекта, читать первым |
| [docs/data_coverage.md](docs/data_coverage.md) | что загружено, чего не хватает, где брать и как решать |
| [docs/storage_strategy.md](docs/storage_strategy.md) | как хранить данные для DataLens без раздувания raw JSON |
| [docs/api_sources.md](docs/api_sources.md) | единая матрица iikoCloud/iikoServer источников |
| [docs/report_plan.md](docs/report_plan.md) | план DataLens-дашбордов и метрик |
| [docs/olap_datasets.md](docs/olap_datasets.md) | OLAP-датасеты и правила безопасных метрик |

Старые справочные md перенесены в [docs/archive](docs/archive). Они не являются текущим статусом проекта.

## Архитектура

```text
iikoCloud / iikoServer OLAP
        ↓
Python ETL
        ↓
PostgreSQL
        ↓
dim_* / fact_* / mart_* / dl_preset_*
        ↓
Yandex DataLens
```

DataLens должен читать только `mart_*`, `dl_preset_*` или будущие `dl_report_*`. Не читать `raw_*` и не ходить напрямую в iiko API.

## Важное состояние

`etl` остановлен вручную:

```bash
docker compose stop etl
```

Не запускать полный backfill до внедрения [storage_strategy.md](docs/storage_strategy.md).

Текущая экспериментальная БД занимает около `20 GB`, в основном из-за повторного хранения raw JSON:

- `raw_cloud_deliveries_by_date_status`;
- `raw_server_olap_sales_daily`;
- `raw_cloud_customer_categories`;
- `raw_cloud_stop_lists`.

Нормализованные факты и витрины занимают существенно меньше места.

## Подъем PostgreSQL

```bash
cp .credentials.env.example .credentials.env
# отредактируйте пароль и DATABASE_URL

make env
docker compose up -d db
make db-schema
```

Полный `docker compose up -d` поднимет и `etl`. Сейчас это нежелательно, пока не изменен raw storage.

## Команды

Сгенерировать `.env`:

```bash
make env
```

Поднять только PostgreSQL:

```bash
docker compose up -d db
```

Применить схему:

```bash
make db-schema
```

Открыть psql:

```bash
make db-psql
```

Остановить ETL:

```bash
docker compose stop etl
```

Логи ETL:

```bash
make logs-etl
```

Запустить веб-конструктор отчетов:

```bash
make report-builder
# открыть http://127.0.0.1:8088
```

Панель читает `DATABASE_URL` из `.env`/`.credentials.env` и строит SQL только
через whitelist полей в `app/report_builder.py`.

## Перед новой загрузкой

1. Внедрить hash/upsert/retention для raw.
2. Добавить `etl_run_status` и checksum-таблицы.
3. Разделить `mart_olap_daily_sales` и `mart_cloud_delivery_sales`.
4. Очистить или пересоздать экспериментальную БД.
5. Прогнать тестовый backfill 7-30 дней.
6. Проверить размер raw/fact/mart.
7. Только потом запускать 3-летнюю загрузку.
