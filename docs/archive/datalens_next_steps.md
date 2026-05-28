# Что сделать в DataLens

После применения `make db-schema` DataLens должен подключаться только к роли `datalens_reader`.

## Подключение

Создайте подключение:

```text
Name: iiko_analytics_postgres
Type: PostgreSQL
Host: <публичный хост PostgreSQL>
Port: <порт PostgreSQL>
Database: iiko_analytics
Username: datalens_reader
Password: значение DATALENS_READER_PASSWORD из .credentials.env
Cache TTL: 300
```

Если база не в Yandex Managed PostgreSQL, откройте доступ только с IP-диапазонов DataLens и включите нормальный SSL-сертификат.

Локальный `127.0.0.1:54337` работает только с этой машины. Облачный DataLens не сможет достучаться до него, пока база не вынесена в доступную сеть.

## Датасеты

Предпочтительно создавайте датасеты на готовых `dl_preset_*` views из [datalens_presets.md](datalens_presets.md). Они плоские и не требуют JOIN внутри DataLens.

Если в DataLens объединять несколько `mart_*` таблиц руками, появятся поля с суффиксами `(1)`, `(2)`: например `organization_name`, `net_revenue`, `updated_at` есть сразу в нескольких таблицах. Это не ошибка PostgreSQL, а следствие одинаковых названий колонок в joined dataset. Для боевых графиков используйте `dl_preset_*` или отдельные SQL views с уникальными алиасами.

Технические датасеты на `mart_*` можно создать для отладки:

```text
DS Daily Sales              -> mart_daily_sales
DS Branch KPI               -> mart_branch_kpi
DS Product Sales            -> mart_product_sales
DS Delivery SLA             -> mart_delivery_sla
DS Discounts Promo          -> mart_discount_promo
DS Customer Retention       -> mart_customer_retention
DS Losses                   -> mart_losses
DS Today Sales              -> mart_today_sales
DS Today Delivery           -> mart_today_delivery
DS Today Stoplists          -> mart_today_stoplists
DS Today Branch Status      -> mart_today_branch_status
```

Основные графики строятся только на `mart_*`. Таблицы `fact_*` можно открыть только для технического анализа.

## Вычисляемые поля

```text
Средний чек: SUM([net_revenue]) / SUM([orders_count])
Доля скидки: SUM([discount_sum]) / SUM([gross_revenue])
Доля опозданий: SUM([late_orders]) / SUM([delivery_orders])
SLA доставки: 1 - SUM([late_orders]) / SUM([delivery_orders])
Доля потерь: SUM([loss_sum]) / SUM([net_revenue])
Маржа: SUM([profit_sum]) / SUM([net_revenue])
Retention: SUM([repeat_customers]) / SUM([customers_count])
```
