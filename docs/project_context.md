# Project Context

Дата актуализации: 2026-05-26.

Главный файл состояния проекта. Читать первым.

## Цель

Собрать PostgreSQL-базу для Yandex DataLens поверх iiko:

- история за 3 года;
- оперативное обновление текущего дня;
- DataLens читает `mart_*` и `dl_preset_*`, а не iiko API и не сырой JSON;
- данные покрывают выручку, товары, филиалы, доставки, клиентов, скидки, оплаты, потери и операционные KPI.
- стоп-листы сейчас не входят в scope загрузки и дашбордов.

## Текущий статус

Проект уже доказал доступность основных источников. Экспериментальная БД, которая раздулась до `20 GB` из-за append-only хранения raw JSON, очищена.

`etl` остановлен вручную, чтобы не продолжать раздувать БД:

```bash
docker compose stop etl
```

PostgreSQL остается запущенным. Текущий размер пустой БД после очистки: около `10 MB`.

## Что было проверено до очистки

До очистки был выполнен контролируемый sync за `2026-05-26`, чтобы проверить новые источники:

| Слой | Строк | Диапазон |
|---|---:|---|
| `fact_orders` | 44 156 | 2026-04-30..2026-05-26 |
| `fact_order_items` | 261 743 | по заказам |
| `fact_payments` | 57 276 | по заказам |
| `fact_discounts` | 42 335 | по заказам |
| `fact_deliveries` | 153 560 | по заказам/статусам |
| `fact_losses` | 107 884 | derived losses |
| `mart_daily_sales` | 5 608 | 2026-05-01..2026-05-26 |
| `mart_product_sales` | 247 095 | 2026-05-01..2026-05-26 |
| `mart_losses` | 27 150 | 2026-05-01..2026-05-26 |

Главные источники уже работают:

- iikoCloud organizations;
- iikoCloud nomenclature;
- iikoCloud deliveries by date/status;
- iikoCloud terminal groups raw;
- iikoCloud customer categories raw;
- iikoCloud external menu raw best-effort;
- iikoServer OLAP `SALES_DAILY`;
- iikoServer OLAP `SALES_PRODUCT`.
- iikoServer OLAP payments by available `PayTypes` field into `mart_payments_daily`;
- iikoServer OLAP staff by available `Cashier`/`WaiterName`/`Delivery.Courier` fields into `mart_staff_sales`;
- iikoServer OLAP discounts by available discount field into `mart_discount_promo`;
- Cloud stop-lists normalization была проверена, но stop-lists отключены как ненужные для текущей аналитики.

Контролируемый тестовый sync за `2026-05-26` прошел успешно:

```text
payment_sales: 178
discount_sales: 182
staff_sales: 276
```

## Текущее состояние БД

Данные очищены через `TRUNCATE ... RESTART IDENTITY CASCADE`.

```text
db_size: около 10 MB
estimated user table rows: 0
etl service: stopped
database default_transaction_read_only: on
```

Схема, views, роли и права сохранены.

Read-only включен временно, потому что внешний live/manual sync продолжал короткими подключениями заливать новые строки после очистки. Перед осознанным новым backfill или live-загрузкой нужно снять:

```bash
docker compose exec -T db psql -U analytics -d postgres -c "ALTER DATABASE iiko_analytics SET default_transaction_read_only = off;"
```

## Главная проблема, которую исправляем

Сырой слой сейчас хранит повторные payload каждого запуска. Это быстро убивает диск.

Старый размер до очистки: `20 GB`.

Основной размер:

| Таблица | Размер | Причина |
|---|---:|---|
| `raw_cloud_deliveries_by_date_status` | 18 GB | повторные JSON payload за одни и те же даты/статусы |
| `raw_server_olap_sales_daily` | 1.3 GB | повторные OLAP payload |
| `raw_cloud_customer_categories` | 689 MB | повторные справочные payload |
| `raw_cloud_stop_lists` | 213 MB | повторные оперативные payload |

Нормализованные факты и витрины занимают десятки мегабайт, а не гигабайты. Значит, проблема не в DataLens-слое, а в raw retention/deduplication.

## Новый принцип хранения

Не режем аналитические данные. Режем только бесконечное хранение повторного raw JSON.

Долго храним:

- `dim_*`;
- `fact_*`;
- `mart_*`;
- `dl_preset_*`;
- `etl_run_status`;
- контрольные суммы загрузок.

Raw JSON:

- дедуплицировать по `payload_hash`;
- для realtime хранить 3-14 дней;
- для справочников хранить последнюю версию и hash истории изменений;
- для исторического backfill сохранять только ошибочные payload или audit summary;
- не append-ить одинаковый ответ при каждом scheduler run.

Подробно: [storage_strategy.md](storage_strategy.md).

## Источники истины

- Полная выручка, заказы всех каналов, товарные продажи, себестоимость и возвраты: iikoServer OLAP `SALES`.
- Доставочные детали, статусы, тайминги, клиентские детали: iikoCloud.
- DataLens: только `dl_preset_*` / будущие `dl_report_*` views.

Cloud deliveries не являются полной выручкой бизнеса. Их нельзя использовать как единственный источник `Revenue by day`.

## Ближайший план

1. Переделать raw storage: hash, upsert, retention.
2. Старые данные уже очищены, БД готова к тестовой новой загрузке.
3. Разделить OLAP и Cloud витрины:
   - `mart_olap_daily_sales`;
   - `mart_cloud_delivery_sales`;
   - финальный `mart_daily_sales` как OLAP-first.
4. Добавить полноценное заполнение `etl_run_status` и checksum-таблицу по каждому окну.
5. Пересоздать БД или очистить raw и запустить backfill заново.
6. Сначала грузить 3 года OLAP `SALES_DAILY` и `SALES_PRODUCT`.
7. Cloud-доставки грузить только в нормализованные факты, с ограниченным raw retention.
8. После базовой истории добрать оставшиеся метрики из [data_coverage.md](data_coverage.md).

## Документы

| Файл | Роль |
|---|---|
| [data_coverage.md](data_coverage.md) | что есть, чего не хватает, где брать и как решать |
| [backlog.md](backlog.md) | P0 backlog по потерям |
| [storage_strategy.md](storage_strategy.md) | как хранить данные без раздувания БД |
| [api_sources.md](api_sources.md) | источники Cloud/OLAP и статус методов |
| [report_plan.md](report_plan.md) | план дашбордов DataLens |
| [archive/](archive/) | старые справочные md, не источник текущего статуса |
