# DataLens presets

Чтобы не собирать дашборд из сырых `mart_*`, используйте готовые views `dl_preset_*`.

## Минимальный набор датасетов

Создайте датасеты:

```text
KPI Summary       -> dl_preset_kpi_summary
Revenue By Day    -> dl_preset_revenue_by_day
Branch Rating     -> dl_preset_revenue_by_branch
Revenue By Source -> dl_preset_revenue_by_source
Top Products      -> dl_preset_top_products
Branch Health     -> dl_preset_branch_health
```

## Графики

```text
Карточка Выручка:
dataset: KPI Summary
measure: SUM(net_revenue)

Карточка Заказы:
dataset: KPI Summary
measure: SUM(orders_count)

Карточка Средний чек:
dataset: KPI Summary
measure: AVG(avg_check)

Линия Выручка по дням:
dataset: Revenue By Day
X: business_date
Y: SUM(net_revenue)

Бар Филиалы по выручке:
dataset: Branch Rating
Y: organization_name
X: SUM(net_revenue)
sort: SUM(net_revenue) desc

Пирог Источники заказов:
dataset: Revenue By Source
dimension: order_source
measure: SUM(net_revenue)

Таблица Топ блюд:
dataset: Top Products
dimensions: product_name, category_name
measures: SUM(net_revenue), SUM(items_qty), AVG(avg_price)
sort: SUM(net_revenue) desc

Таблица Health филиалов:
dataset: Branch Health
dimensions: business_date, organization_name
measures: SUM(net_revenue), SUM(orders_count), AVG(health_score)
```
