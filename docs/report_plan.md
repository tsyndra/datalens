# Report plan: DataLens dashboards and business metrics

Дата актуализации: 2026-05-26.

Статус источников и пробелов для этих отчетов фиксируется в [data_coverage.md](data_coverage.md). Перед сборкой дашбордов сначала нужно внедрить [storage_strategy.md](storage_strategy.md), потому что старая экспериментальная БД раздувалась raw JSON.

Цель: спланировать отчеты, которые должны появиться поверх полной iiko-базы. Основной DataLens-конструктор строится на `dl_olap_*` views; их список и правила использования описаны в [olap_datasets.md](olap_datasets.md). `dl_preset_*` и `dl_report_*` оставлены как совместимые/готовые витрины для отдельных сценариев. `raw_*` используется для проверки и восстановления, но не как основной слой DataLens.

В DataLens нельзя собирать один большой боевой датасет JOIN-ом продаж, товаров, оплат, скидок и доставок: появится fan-out и неправильные суммы. Вместо этого используем несколько `dl_olap_*` фактов и связываем их на дашборде общими фильтрами.

## Общие правила метрик

Базовые поля:

- дата: `business_date`;
- филиал: `organization_id`, `organization_name`;
- источник заказа: `order_source`;
- товар: `product_id`, `product_name`, `category_name`;
- клиент: `customer_id`;
- доставка: `delivery_status`, `delivery_zone`;
- время обновления: `updated_at`.

Не все mart-таблицы обязаны иметь `business_date`:

- дневные/оперативные факты должны иметь `business_date`;
- `mart_customer_retention` использует `cohort_month` и `order_month`, потому что это месячная когортная витрина;
- `mart_customer_summary` является текущим срезом клиента и использует `first_order_date`, `last_order_date`;
- стоп-листы выведены из текущего scope, `mart_today_stoplists` не строим.

Базовые формулы:

| Метрика | Формула |
|---|---|
| Выручка | `SUM(net_revenue)` |
| Валовая выручка | `SUM(gross_revenue)` |
| Заказы | `SUM(orders_count)` или `COUNT(DISTINCT order_id)` на fact-слое |
| Средний чек | `SUM(net_revenue) / SUM(orders_count)` |
| Скидки | `SUM(discount_sum)` |
| Доля скидки | `SUM(discount_sum) / SUM(gross_revenue)` |
| Возвраты | `SUM(refund_sum)` |
| Количество товаров | `SUM(items_qty)` |
| Средняя цена | `SUM(net_revenue) / SUM(items_qty)` |
| Себестоимость | `SUM(cost_sum)` |
| Валовая прибыль | `SUM(profit_sum)` |
| Food cost | `SUM(cost_sum) / SUM(net_revenue)` |
| Маржа | `SUM(profit_sum) / SUM(net_revenue)` |
| Retention | `SUM(repeat_customers) / SUM(customers_count)` |
| SLA доставки | `1 - SUM(late_orders) / SUM(delivery_orders)` |
| Доля опозданий | `SUM(late_orders) / SUM(delivery_orders)` |
| Доля потерь | `SUM(loss_sum) / SUM(net_revenue)` |

## Dashboard 1. Executive overview

Назначение: ежедневная картина бизнеса для собственника/управляющего.

Основные вопросы:

- сколько выручки сегодня, вчера, за неделю, месяц;
- где рост/падение;
- какие филиалы тянут результат;
- какие источники заказов дают выручку;
- есть ли просадка среднего чека.

Датасеты:

- `dl_preset_kpi_summary`;
- `dl_preset_revenue_by_day`;
- `dl_preset_revenue_by_branch`;
- `dl_preset_revenue_by_source`;
- `mart_branch_kpi`.

Виджеты:

| Виджет | Тип | Датасет | Поля |
|---|---|---|---|
| Выручка | indicator | `dl_preset_kpi_summary` | `SUM(net_revenue)` |
| Заказы | indicator | `dl_preset_kpi_summary` | `SUM(orders_count)` |
| Средний чек | indicator | `dl_preset_kpi_summary` | `SUM(net_revenue) / SUM(orders_count)` |
| Скидка % | indicator | `dl_preset_kpi_summary` | `SUM(discount_sum) / SUM(gross_revenue)` |
| Выручка по дням | line | `dl_preset_revenue_by_day` | X `business_date`, filter `organization_name`, Y `SUM(net_revenue)` |
| Филиалы по выручке | bar | `dl_preset_revenue_by_branch` | filter `business_date`, `organization_name`, `SUM(net_revenue)` |
| Источники заказов | pie/bar | `dl_preset_revenue_by_source` | `order_source`, `SUM(net_revenue)` |
| Health филиалов | table | `mart_branch_kpi` | `organization_name`, revenue, avg_check, discount_share, health_score |

Фильтры:

- период;
- филиал;
- источник заказа.

## Dashboard 2. Revenue and trend analysis

Назначение: анализ динамики выручки, сезонности, недельных паттернов.

Датасеты:

- `mart_daily_sales`;
- будущая витрина `mart_revenue_calendar`;
- будущая витрина `mart_revenue_yoy`.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Выручка по дням | line | `SUM(net_revenue)` |
| Выручка по неделям | line/bar | week date, revenue |
| Выручка по месяцам | line/bar | month, revenue |
| День недели x час | heatmap | revenue, orders_count |
| YoY сравнение | line | текущий период vs тот же период прошлого года |
| План/факт | line/table | revenue fact vs target, если появится таблица планов |
| Вклад филиалов в рост | waterfall/bar | delta revenue by branch |

Нужные доработки:

- календарная таблица `dim_calendar`;
- таблица планов `fact_targets`;
- витрина сравнений `mart_revenue_comparison`.

## Dashboard 3. Branch performance

Назначение: рейтинг и диагностика филиалов.

Датасеты:

- `mart_branch_kpi`;
- `mart_daily_sales`;
- `mart_delivery_sla`;
- `mart_losses`.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Рейтинг филиалов | table | revenue, orders, avg_check, margin, discount_share |
| Динамика филиала | line | revenue by day for selected branch |
| Филиалы с падением | table | revenue delta vs previous period |
| Health score | bar/table | `health_score` |
| Скидки по филиалам | bar | discount_sum, discount_share |
| Потери по филиалам | bar | loss_sum, loss_share |
| SLA филиалов | table | late_rate, avg_delivery_minutes |

Нужные доработки:

- корректный `health_score` после появления полной модели потерь;
- планы по филиалам;
- группировка филиалов по региону/кластеру.

## Dashboard 4. Product and menu analytics

Назначение: понять, какие блюда зарабатывают деньги, какие дают маржу, какие проседают.

Датасеты:

- `mart_product_sales`;
- `dl_preset_top_products`;
- `dl_preset_product_daily`;
- будущие `dim_menu`, `mart_product_margin`, `mart_product_availability`.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Топ блюд по выручке | table | product_name, category_name, revenue, qty |
| Топ блюд по количеству | table | qty, orders_count |
| Маржинальность блюд | table/scatter | revenue, cost_sum, profit_sum, food_cost_percent |
| ABC-анализ | table | share of revenue, cumulative share, ABC class |
| Динамика блюда | line | revenue/qty by day |
| Категории меню | treemap/bar | revenue by category |
| Цена и средняя цена | table | avg_price by product and branch |
Нужные доработки:

- external menu для цен и структуры меню;
- стабильная связь Cloud product id и OLAP DishId;
- расчет ABC/XYZ;

## Dashboard 5. Delivery operations

Назначение: контроль доставки, опозданий, зон, курьеров и статусов.

Датасеты:

- `mart_delivery_sla`;
- `mart_today_delivery`;
- `fact_deliveries` для drill-down;
- будущие `mart_courier_performance`, `mart_delivery_geo`.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Доставки сегодня | indicator | delivery_orders |
| Активные доставки | indicator | active_deliveries |
| Среднее время доставки | indicator/line | avg_delivery_minutes |
| P90/P95 доставки | line | p90_delivery_minutes, p95_delivery_minutes |
| Доля опозданий | line/indicator | late_rate |
| SLA по филиалам | table | branch, SLA, late_orders |
| SLA по зонам | map/table | delivery_zone, late_rate |
| Таймлайн готовки | table | cooking_minutes, courier_waiting_minutes |
| Курьеры | table | courier_name, orders, avg_delivery_minutes, late_rate |

Нужные доработки:

- грузить не только `closed`, но и активные статусы доставок;
- нормализовать курьеров;
- сохранить координаты и зоны;
- добавить гео-отчеты.

## Dashboard 6. Customers, retention, loyalty

Назначение: анализ клиентской базы, повторных заказов, LTV, сегментов.

Датасеты:

- `mart_customer_retention`;
- `mart_customer_summary`;
- `fact_customer_orders`;
- будущие `dim_customer_categories`, `mart_customer_segments`.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Новые клиенты | indicator/line | first orders by date |
| Повторные клиенты | indicator/line | repeat customers |
| Retention cohorts | heatmap | cohort_month x order_month |
| LTV | line/table | ltv by cohort/source |
| RFM-сегменты | table/bar | recency, frequency, monetary |
| Клиенты без повторного заказа | table | days_since_last_order |
| День рождения/пол/сегменты | bar | customer demographics |
| Черный список | table | in_blacklist, blacklist_reason |

Нужные доработки:

- безопасно обогащать клиентов через `loyalty/iiko/customer/info`;
- хранить категории гостей;
- не хранить сырые телефоны, только `phone_hash`, если нет отдельного разрешения.

## Dashboard 7. Discounts and promo

Назначение: контроль скидок, ручных скидок, промо и влияния на выручку.

Датасеты:

- `mart_discount_promo`;
- `fact_discounts`;
- будущая OLAP-витрина скидок.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Скидка сумма | indicator | discount_sum |
| Доля скидки | indicator/line | discount_share |
| Скидки по филиалам | bar | branch, discount_sum/share |
| Скидки по акциям | table | discount_name, revenue, discount_sum |
| Ручные скидки | table | manual_discount_sum, manual_discount_orders |
| Аномальные скидки | table | high discount_share, branch, date |

Нужные доработки:

- проверить OLAP поля скидок и промо;
- добавить сотрудника/причину ручной скидки, если доступно;
- связать скидки с кампаниями.

## Dashboard 8. Payments and finance

Назначение: оплата по типам, сверка наличных/карт/онлайна/агрегаторов.

Датасеты:

- `fact_payments`;
- будущие `mart_payments_daily`, `mart_payments_by_branch`.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Оплаты по типам | bar/pie | payment_type, payment_sum |
| Наличные/карта/онлайн | stacked bar | payment_group |
| Оплаты по филиалам | table | branch x payment type |
| Возвраты оплат | table | refunds by payment type |
| Эквайринг/комиссии | table | commission, net after fees |
| Расхождение оплат и выручки | table | payment_sum - net_revenue |

Нужные доработки:

- добавить OLAP payments by `PayTypes`;
- классифицировать payment types;
- добавить комиссии, если источник доступен.

## Dashboard 9. Losses and anomalies

Назначение: контролировать потери: отмены, возвраты, ручные скидки, удаленные позиции, опоздания.

Датасеты:

- `fact_losses`;
- `mart_losses`;
- `mart_branch_kpi`;

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Общие потери | indicator | loss_sum |
| Потери по типам | bar | loss_type, loss_sum |
| Потери по филиалам | bar/table | branch, loss_sum, loss_share |
| Удаленные позиции | table | product, reason, sum |
| Отмены | line/table | cancel count/sum |
| Возвраты | line/table | refund_sum |
| Опоздания | table | late deliveries as loss signal |
Нужные доработки:

- подтвердить OLAP/Cloud источники удалений и причин;
- добавить сотрудников;
- добавить комментарии причин;
- формализовать loss taxonomy.

## Dashboard 10. Realtime operations

Назначение: экран текущего дня для операционного контроля.

Датасеты:

- `mart_today_sales`;
- `mart_today_delivery`;
- `mart_today_branch_status`;
- future `etl_run_status`.

Виджеты:

| Виджет | Тип | Метрики |
|---|---|---|
| Выручка сегодня по часам | line/bar | hour, net_revenue |
| Заказы сегодня по часам | line/bar | hour, orders_count |
| Активные доставки | indicator/table | active_deliveries |
| Опоздания сейчас | indicator/table | late_orders, late_rate |
| Health филиалов сегодня | table | health_score_today |
| Свежесть ETL | indicator | max(updated_at), last successful run |

Нужные доработки:

- отдельная таблица `etl_run_status`;
- minute scheduler;
- DataLens cache TTL 60-300 seconds;
- алерты при stale data.

## Приоритет внедрения

### P0. Починить основу

1. Защитить `mart_daily_sales` от потери OLAP-истории.
2. Заполнить непрерывный OLAP диапазон за 3 года.
3. Настроить стабильное обновление сегодняшнего дня.
4. Добавить мониторинг свежести и ошибок ETL.

### P1. Бизнес-дашборды

1. Executive overview.
2. Revenue trend.
3. Branch performance.
4. Product analytics.
5. Realtime operations.

### P2. Расширенная аналитика

1. Delivery operations.
2. Customers/retention.
3. Discounts/promo.
4. Payments/finance.
5. Losses/anomalies.

### P3. Продвинутые модели

1. ABC/XYZ товаров.
2. Прогноз выручки.
3. Детектор аномалий по филиалам.
4. Рекомендации по меню.
5. Оценка потерь от опозданий.

## Минимальный набор DataLens страниц

1. `Overview`
2. `Revenue`
3. `Branches`
4. `Products`
5. `Realtime`
6. `Delivery`
7. `Customers`
8. `Discounts`
9. `Payments`
10. `Losses`

## Требования к качеству отчетов

- Каждый график должен иметь понятный источник: `mart_*` или `dl_preset_*`.
- Все суммы должны быть сверены с OLAP за выбранный период.
- В каждом отчете должен быть фильтр периода и филиала.
- Оперативные отчеты должны показывать `updated_at` или отдельную свежесть данных.
- Исторические отчеты должны работать на периоде 3 года без дыр в датах.
- Для метрик с делением обязательно использовать `NULLIF`, чтобы не ломать графики при нулевых заказах.
