# DataLens + iiko Analytics MVP

## Главная идея

DataLens не должен напрямую ходить в iiko API.

Правильная схема:

```text
iiko API / OLAP / iikoFront / iikoServer
        ↓
Python sync service
        ↓
PostgreSQL
        ↓
fact_* / dim_* / mart_*
        ↓
Yandex DataLens
```

## Что такое mart_*

`mart_*` — это готовые аналитические таблицы или materialized views в PostgreSQL.

DataLens подключается к ним как к обычным таблицам.

Пример:

```text
mart_daily_sales
mart_branch_kpi
mart_product_sales
mart_delivery_sla
```

`mart_*` не нужно "пихать" в DataLens как файл.

Нужно:

```text
1. Создать mart_* в PostgreSQL
2. Создать подключение DataLens к PostgreSQL
3. Создать Dataset на основе mart_*
4. Создать Chart
5. Собрать Dashboard
```

---

# 1. Архитектура

## Поток данных

```text
iiko API / OLAP
        ↓
raw_* tables
        ↓
stg_* tables
        ↓
dim_* and fact_* tables
        ↓
mart_* tables / materialized views
        ↓
DataLens datasets
        ↓
DataLens dashboards
```

## Слои БД

```text
raw_*   — сырые ответы API / OLAP, почти без изменений
stg_*   — очищенные промежуточные таблицы
dim_*   — справочники: филиалы, блюда, категории, клиенты, сотрудники
fact_*  — события и факты: заказы, позиции, оплаты, скидки, доставки
mart_*  — готовые витрины для DataLens
```

## Главное правило

DataLens читает только:

```text
mart_*
```

Для аналитика можно дополнительно открыть:

```text
fact_*
dim_*
```

Но основные дашборды строить только на `mart_*`.

---

# 2. Режимы загрузки данных

Нужно сделать два режима:

```text
1. Historical sync — история и стабильная аналитика
2. Realtime sync — текущий день почти в моменте
```

---

## 2.1 Historical sync

Назначение:

```text
Стабильная аналитика за прошлые дни, недели, месяцы.
```

Что грузить:

```text
orders
order_items
payments
discounts
deliveries
customers
products
categories
organizations
stoplists
refunds
cancellations
losses
```

Расписание:

```text
Каждый день в 05:00
```

Важное правило:

```text
Каждый день пересобирать последние 7 дней.
```

Почему:

```text
Заказы, возвраты, отмены, оплаты и доставки могут измениться задним числом.
```

Команды:

```bash
python manage.py sync_iiko_historical --date-from YYYY-MM-DD --date-to YYYY-MM-DD
python manage.py rebuild_marts --date-from YYYY-MM-DD --date-to YYYY-MM-DD
```

---

## 2.2 Realtime sync

Назначение:

```text
Оперативная аналитика текущего дня.
```

Что грузить каждые 1–5 минут:

```text
new orders
changed orders
order items
payments
discounts
delivery statuses
active stop-lists
current delivery delays
current branch revenue
```

Расписание:

```text
Каждые 1–5 минут
```

Команды:

```bash
python manage.py sync_iiko_realtime
python manage.py rebuild_today_marts
```

Целевые таблицы:

```text
fact_orders
fact_order_items
fact_payments
fact_discounts
fact_deliveries
fact_stoplists
```

Витрины текущего дня:

```text
mart_today_sales
mart_today_delivery
mart_today_stoplists
mart_today_branch_status
```

---

# 3. Почему не делать прямой запрос DataLens → iiko API

Не делать так:

```text
DataLens → iiko API
```

Причины:

```text
1. iiko API может быть медленным
2. iiko API имеет лимиты
3. DataLens делает много запросов при фильтрах
4. Дашборды будут тормозить
5. Сложно склеивать разные endpoint'ы
6. Нет нормального кеша истории
7. Сложно дебажить расхождения
8. Можно получить разные цифры при повторном открытии отчёта
9. Нельзя нормально строить retention, LTV, SLA, потери и прогнозы
```

Правильно делать так:

```text
iiko API → PostgreSQL → DataLens
```

Для “почти в моменте” использовать `realtime sync`, а не прямые запросы из DataLens.

---

# 4. Что собрать из iiko

## 4.1 Филиалы

Таблица:

```sql
dim_organizations
```

Поля:

```text
organization_id
organization_name
city
address
is_active
created_at
updated_at
```

Использование:

```text
Фильтры по филиалам
Сравнение филиалов
Рейтинг филиалов
```

---

## 4.2 Заказы

Таблица:

```sql
fact_orders
```

Поля:

```text
order_id
external_order_id
order_number
organization_id
business_date
created_at
closed_at
order_type
order_source
status
customer_id
waiter_id
cashier_id
guests_count
gross_revenue
discount_sum
net_revenue
delivery_sum
service_sum
items_count
payment_sum
is_delivery
is_cancelled
is_refund
created_at_etl
updated_at_etl
```

Метрики:

```text
orders_count
gross_revenue
net_revenue
discount_sum
avg_check
discount_share
cancel_rate
refund_rate
```

---

## 4.3 Позиции заказа

Таблица:

```sql
fact_order_items
```

Поля:

```text
order_item_id
order_id
organization_id
business_date
product_id
product_name
category_id
category_name
amount
price
gross_sum
discount_sum
net_sum
cost_sum
profit_sum
is_modifier
parent_item_id
course
created_at_etl
```

Метрики:

```text
items_qty
item_revenue
item_discount
avg_item_price
product_share
category_share
profit_margin
food_cost_percent
```

---

## 4.4 Блюда и категории

Таблицы:

```sql
dim_products
dim_categories
```

Поля `dim_products`:

```text
product_id
product_name
category_id
category_name
group_name
measure_unit
is_active
default_price
current_price
cost_price
food_cost_percent
```

Поля `dim_categories`:

```text
category_id
category_name
parent_category_name
```

Использование:

```text
Топ блюд
Топ категорий
Menu engineering
Анализ цены
Анализ маржи
```

---

## 4.5 Оплаты

Таблица:

```sql
fact_payments
```

Поля:

```text
payment_id
order_id
organization_id
business_date
payment_type
payment_group
payment_sum
is_fiscal
is_refund
created_at
```

Метрики:

```text
card_revenue
cash_revenue
online_revenue
aggregator_revenue
refund_sum
refund_rate
```

---

## 4.6 Скидки и акции

Таблица:

```sql
fact_discounts
```

Поля:

```text
discount_id
order_id
order_item_id
organization_id
business_date
discount_name
discount_type
discount_sum
discount_percent
is_manual
employee_id
promo_id
```

Метрики:

```text
discount_sum
discount_share
manual_discount_sum
manual_discount_orders
promo_orders_count
avg_discount_per_order
```

---

## 4.7 Доставка

Таблица:

```sql
fact_deliveries
```

Поля:

```text
delivery_id
order_id
organization_id
business_date
delivery_status
delivery_type
delivery_zone
address
latitude
longitude
courier_id
created_at
confirmed_at
cooking_started_at
cooking_completed_at
courier_assigned_at
sent_at
delivered_at
closed_at
planned_delivery_at
actual_delivery_minutes
cooking_minutes
courier_waiting_minutes
delivery_minutes
delay_minutes
is_late
```

Метрики:

```text
delivery_orders_count
avg_delivery_minutes
p90_delivery_minutes
p95_delivery_minutes
late_orders_count
late_rate
avg_delay_minutes
sla_rate
```

---

## 4.8 Клиенты

Таблица:

```sql
dim_customers
```

Поля:

```text
customer_id
phone_hash
name
first_order_date
last_order_date
orders_count
total_revenue
avg_check
favorite_category
favorite_product
```

Таблица:

```sql
fact_customer_orders
```

Поля:

```text
customer_id
order_id
organization_id
business_date
order_number_by_customer
days_since_previous_order
is_first_order
is_repeat_order
net_revenue
order_source
```

Метрики:

```text
new_customers
repeat_customers
repeat_rate
retention_7d
retention_14d
retention_30d
ltv
avg_days_between_orders
time_to_second_order
```

---

## 4.9 Стоп-листы

Таблица:

```sql
fact_stoplists
```

Поля:

```text
stoplist_id
organization_id
product_id
product_name
category_name
started_at
ended_at
duration_minutes
business_date
is_active
```

Метрики:

```text
stoplist_hours
popular_products_in_stop
lost_revenue_estimate
```

Формула:

```text
lost_revenue_estimate = avg_product_revenue_per_hour * stoplist_hours
```

---

## 4.10 Потери

Таблица:

```sql
fact_losses
```

Поля:

```text
loss_id
organization_id
order_id
business_date
loss_type
loss_reason
loss_sum
employee_id
created_at
comment
```

Типы потерь:

```text
cancel
refund
writeoff
manual_discount
deleted_item
delivery_late
stoplist_lost_sales
```

Метрики:

```text
total_losses
losses_by_type
loss_share
refund_sum
cancelled_revenue
manual_discount_losses
```

---

# 5. Витрины mart_* для DataLens

## 5.1 mart_daily_sales

Назначение:

```text
Основной отчёт по продажам.
```

Гранулярность:

```text
business_date + organization_id + order_source
```

Поля:

```text
business_date
organization_id
organization_name
order_source
orders_count
gross_revenue
discount_sum
net_revenue
avg_check
items_qty
cancelled_orders
refund_sum
discount_share
cancel_rate
```

---

## 5.2 mart_branch_kpi

Назначение:

```text
Рейтинг и сравнение филиалов.
```

Гранулярность:

```text
business_date + organization_id
```

Поля:

```text
business_date
organization_id
organization_name
orders_count
net_revenue
avg_check
discount_sum
discount_share
delivery_orders
late_orders
late_rate
refund_sum
cancel_rate
total_losses
health_score
```

Формула:

```text
health_score =
100
- late_rate * 30
- cancel_rate * 30
- discount_share * 20
- refund_rate * 20
```

---

## 5.3 mart_product_sales

Назначение:

```text
Аналитика блюд и категорий.
```

Гранулярность:

```text
business_date + organization_id + product_id
```

Поля:

```text
business_date
organization_id
organization_name
product_id
product_name
category_name
items_qty
gross_revenue
discount_sum
net_revenue
cost_sum
profit_sum
food_cost_percent
avg_price
orders_count
```

---

## 5.4 mart_delivery_sla

Назначение:

```text
Аналитика доставки, SLA и зон.
```

Гранулярность:

```text
business_date + organization_id + delivery_zone
```

Поля:

```text
business_date
organization_id
organization_name
delivery_zone
delivery_orders
avg_delivery_minutes
p90_delivery_minutes
p95_delivery_minutes
late_orders
late_rate
avg_delay_minutes
sla_rate
avg_cooking_minutes
avg_courier_waiting_minutes
```

---

## 5.5 mart_discount_promo

Назначение:

```text
Скидки, акции, ручные скидки.
```

Гранулярность:

```text
business_date + organization_id + discount_name
```

Поля:

```text
business_date
organization_id
organization_name
discount_name
discount_type
orders_count
gross_revenue
discount_sum
net_revenue
avg_discount_per_order
discount_share
manual_discount_sum
manual_discount_orders
```

---

## 5.6 mart_customer_retention

Назначение:

```text
Продуктовая аналитика клиентов.
```

Гранулярность:

```text
cohort_month + order_month + order_source
```

Поля:

```text
cohort_month
order_month
months_since_first_order
order_source
customers_count
repeat_customers
orders_count
net_revenue
avg_check
ltv
retention_rate
```

---

## 5.7 mart_losses

Назначение:

```text
Дерево потерь.
```

Гранулярность:

```text
business_date + organization_id + loss_type
```

Поля:

```text
business_date
organization_id
organization_name
loss_type
loss_reason
loss_sum
orders_affected
loss_share
```

---

## 5.8 mart_today_sales

Назначение:

```text
Оперативная выручка текущего дня.
```

Гранулярность:

```text
business_date + hour + organization_id + order_source
```

Поля:

```text
business_date
hour
organization_id
organization_name
order_source
orders_count
net_revenue
avg_check
discount_sum
last_order_at
updated_at
```

---

## 5.9 mart_today_delivery

Назначение:

```text
Оперативный контроль доставки текущего дня.
```

Гранулярность:

```text
business_date + organization_id + delivery_status
```

Поля:

```text
business_date
organization_id
organization_name
delivery_status
delivery_orders
late_orders
late_rate
avg_delivery_minutes
p90_delivery_minutes
active_deliveries
updated_at
```

---

## 5.10 mart_today_stoplists

Назначение:

```text
Активные стоп-листы текущего дня.
```

Гранулярность:

```text
organization_id + product_id
```

Поля:

```text
organization_id
organization_name
product_id
product_name
category_name
started_at
duration_minutes
avg_revenue_per_hour
lost_revenue_estimate
updated_at
```

---

## 5.11 mart_today_branch_status

Назначение:

```text
Сводка по филиалам в моменте.
```

Гранулярность:

```text
business_date + organization_id
```

Поля:

```text
business_date
organization_id
organization_name
orders_count
net_revenue
avg_check
delivery_orders
late_orders
late_rate
active_deliveries
active_stoplist_items
health_score_today
updated_at
```

---

# 6. Как создавать mart_*

Для MVP использовать обычные таблицы `mart_*`, которые пересобираются ETL-скриптом.

Пример логики:

```sql
TRUNCATE TABLE mart_daily_sales;

INSERT INTO mart_daily_sales (...)
SELECT ...
FROM fact_orders
GROUP BY ...;
```

Для тяжёлых отчётов можно позже заменить на `MATERIALIZED VIEW`.

Не использовать обычные `VIEW` для тяжёлых отчётов, если данных много.

---

# 7. ETL-команды

Сделать команды:

```bash
python manage.py sync_iiko_historical --date-from YYYY-MM-DD --date-to YYYY-MM-DD
python manage.py sync_iiko_realtime
python manage.py rebuild_marts --date-from YYYY-MM-DD --date-to YYYY-MM-DD
python manage.py rebuild_today_marts
python manage.py load_organizations
python manage.py load_products
python manage.py load_customers --date-from YYYY-MM-DD --date-to YYYY-MM-DD
python manage.py load_stoplists --date-from YYYY-MM-DD --date-to YYYY-MM-DD
```

---

# 8. Расписание

## 8.1 Historical sync

Cron:

```bash
0 5 * * * /app/scripts/sync_historical_yesterday.sh
```

Скрипт:

```text
1. Загружает вчерашние данные
2. Перезагружает последние 7 дней
3. Обновляет справочники
4. Пересобирает все обычные mart_*
```

---

## 8.2 Realtime sync

Cron:

```bash
*/5 * * * * /app/scripts/sync_realtime.sh
```

Скрипт:

```text
1. Загружает новые и изменённые заказы текущего дня
2. Загружает статусы доставок
3. Загружает оплаты и скидки
4. Загружает активные стоп-листы
5. Пересобирает mart_today_*
```

---

# 9. Логи ETL

Таблица:

```sql
etl_runs
```

Поля:

```text
run_id
job_name
started_at
finished_at
status
date_from
date_to
rows_loaded
error_message
```

Требования:

```text
Каждый запуск ETL должен писать лог
Ошибки не должны скрываться
Повторный запуск не должен создавать дубли
```

---

# 10. DataLens: подключение

Создать подключение:

```text
iiko_analytics_postgres
```

Источник:

```text
PostgreSQL
```

Использовать read-only пользователя.

SQL:

```sql
CREATE USER datalens_reader WITH PASSWORD 'strong_password';

GRANT CONNECT ON DATABASE iiko_analytics TO datalens_reader;
GRANT USAGE ON SCHEMA public TO datalens_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datalens_reader;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO datalens_reader;
```

Cache TTL:

```text
Обычные дашборды: 300 секунд или больше
Оперативные дашборды: 60–300 секунд, если база выдерживает
```

---

# 11. DataLens: датасеты

Создать датасеты:

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

Для аналитика можно создать дополнительные датасеты:

```text
DS Fact Orders              -> fact_orders
DS Fact Order Items         -> fact_order_items
DS Fact Payments            -> fact_payments
DS Fact Discounts           -> fact_discounts
DS Fact Deliveries          -> fact_deliveries
```

Но основные дашборды строить на `mart_*`.

---

# 12. DataLens: вычисляемые поля

## Средний чек

```text
SUM([net_revenue]) / SUM([orders_count])
```

## Доля скидки

```text
SUM([discount_sum]) / SUM([gross_revenue])
```

## Доля опозданий

```text
SUM([late_orders]) / SUM([delivery_orders])
```

## SLA доставки

```text
1 - SUM([late_orders]) / SUM([delivery_orders])
```

## Доля потерь

```text
SUM([loss_sum]) / SUM([net_revenue])
```

## Маржа

```text
SUM([profit_sum]) / SUM([net_revenue])
```

## Retention

```text
SUM([repeat_customers]) / SUM([customers_count])
```

---

# 13. DataLens: дашборды

## 13.1 Сеть / CEO

Название:

```text
Сеть — основные показатели
```

Фильтры:

```text
Период
Филиал
Источник заказа
Тип заказа
```

Карточки:

```text
Выручка
Заказы
Средний чек
Скидки
Доля скидок
Опоздания
Потери
Health Score
```

Графики:

```text
Выручка по дням
Заказы по дням
Средний чек по дням
Выручка по филиалам
Рейтинг филиалов по Health Score
Потери по типам
```

---

## 13.2 Оперативный дашборд текущего дня

Название:

```text
Сегодня — оперативный контроль
```

Датасеты:

```text
DS Today Sales
DS Today Delivery
DS Today Stoplists
DS Today Branch Status
```

Фильтры:

```text
Филиал
Источник заказа
Статус доставки
```

Карточки:

```text
Выручка сегодня
Заказы сегодня
Средний чек сегодня
Активные доставки
Опоздания сейчас
Активные стоп-листы
```

Графики:

```text
Выручка по часам сегодня
Заказы по часам сегодня
Филиалы: план/факт текущего дня
Опоздания по филиалам
Активные стоп-листы
Проблемные филиалы
```

---

## 13.3 Филиалы

Название:

```text
Филиалы — сравнение
```

Фильтры:

```text
Период
Филиал
Источник
```

Графики:

```text
Таблица KPI по филиалам
Выручка по филиалам
Средний чек по филиалам
Доля скидок по филиалам
Cancel rate по филиалам
Late rate по филиалам
Потери по филиалам
```

Таблица KPI:

```text
Филиал
Выручка
Заказы
Средний чек
Скидки %
Опоздания %
Отмены %
Возвраты
Потери
Health Score
```

---

## 13.4 Меню / Блюда

Название:

```text
Меню — продажи и маржа
```

Фильтры:

```text
Период
Филиал
Категория
Блюдо
```

Графики:

```text
Топ блюд по выручке
Топ блюд по количеству
Топ категорий
Блюда с высокой скидкой
Блюда с низкой маржой
Динамика продаж блюда
```

Таблица:

```text
Блюдо
Категория
Кол-во
Выручка
Скидка
Средняя цена
Себестоимость
Маржа
Food cost %
```

---

## 13.5 Доставка

Название:

```text
Доставка — SLA и зоны
```

Фильтры:

```text
Период
Филиал
Зона доставки
Курьер
```

Карточки:

```text
Доставок
SLA %
Среднее время доставки
P90 доставки
Опозданий
Среднее опоздание
```

Графики:

```text
SLA по дням
SLA по филиалам
Опоздания по зонам
Среднее время доставки по часам
P90/P95 доставки
Таблица проблемных зон
```

---

## 13.6 Скидки / Акции

Название:

```text
Скидки и акции
```

Фильтры:

```text
Период
Филиал
Акция
Тип скидки
```

Графики:

```text
Сумма скидок по дням
Доля скидок по филиалам
Топ акций по выручке
Топ акций по сумме скидки
Ручные скидки по сотрудникам
```

Таблица:

```text
Акция
Заказов
Валовая выручка
Скидка
Чистая выручка
Средняя скидка
Доля скидки
```

---

## 13.7 Клиенты / Retention

Название:

```text
Клиенты — повторность и LTV
```

Фильтры:

```text
Когорта
Источник первого заказа
Филиал
```

Графики:

```text
Новые клиенты по месяцам
Повторные клиенты по месяцам
Retention cohort table
LTV по когортам
LTV по источникам
Среднее время до второго заказа
```

Таблица когорт:

```text
Когорта
Клиентов
Повтор 7 дней
Повтор 14 дней
Повтор 30 дней
LTV
```

---

## 13.8 Потери

Название:

```text
Потери — loss tree
```

Фильтры:

```text
Период
Филиал
Тип потери
Причина
```

Графики:

```text
Потери по типам
Потери по филиалам
Потери по дням
Топ причин потерь
Топ сотрудников по ручным потерям
```

Таблица:

```text
Дата
Филиал
Тип потери
Причина
Сумма
Заказов затронуто
Доля от выручки
```

---

# 14. Product Analytics MVP

## 14.1 Retention

Метрики:

```text
retention_7d
retention_14d
retention_30d
repeat_rate
time_to_second_order
```

Цель:

```text
Понять, возвращаются ли клиенты после первого заказа.
```

---

## 14.2 LTV

Метрики:

```text
ltv_30d
ltv_60d
ltv_90d
avg_ltv_by_source
avg_ltv_by_branch
```

Цель:

```text
Понять, какие каналы приводят ценных клиентов.
```

---

## 14.3 Promo effectiveness

Метрики:

```text
promo_orders
promo_revenue
promo_discount
promo_net_revenue
repeat_after_promo
```

Цель:

```text
Понять, акции дают новых нормальных клиентов или просто сжигают скидку.
```

---

## 14.4 Menu engineering

Метрики:

```text
product_revenue
product_qty
product_profit
product_margin
product_share
category_share
```

Цель:

```text
Понять, какие блюда продвигать, какие пересматривать, какие убирать.
```

---

## 14.5 Delivery impact on repeat

Метрика:

```text
repeat_rate_by_delivery_time_bucket
```

Бакеты:

```text
0-45 min
45-60 min
60-90 min
90+ min
```

Цель:

```text
Понять, после какого времени доставки клиент перестает возвращаться.
```

---

# 15. Telegram-алерты потом

После MVP добавить алерты:

```text
Выручка к текущему часу ниже нормы на 25%
Late rate выше 20%
P90 доставки выше 75 минут
Скидки выше нормы на 30%
Филиал резко просел по заказам
Популярное блюдо в стопе больше 1 часа
Возвраты выше нормы
Средний чек упал ниже нормы
```

---

# 16. Acceptance Criteria

## База

- [ ] PostgreSQL поднят
- [ ] Созданы таблицы `raw_*`, `stg_*`, `dim_*`, `fact_*`, `mart_*`
- [ ] Есть read-only пользователь для DataLens
- [ ] ETL пишет логи в `etl_runs`
- [ ] Повторный запуск ETL не создаёт дубли
- [ ] Есть historical sync
- [ ] Есть realtime sync
- [ ] Есть пересборка обычных `mart_*`
- [ ] Есть пересборка `mart_today_*`

## Данные

- [ ] Загружаются организации
- [ ] Загружаются заказы
- [ ] Загружаются позиции заказов
- [ ] Загружаются оплаты
- [ ] Загружаются скидки
- [ ] Загружаются доставки
- [ ] Загружаются клиенты, если доступны
- [ ] Загружаются стоп-листы, если доступны
- [ ] Загружаются отмены/возвраты/потери, если доступны

## Витрины

- [ ] `mart_daily_sales`
- [ ] `mart_branch_kpi`
- [ ] `mart_product_sales`
- [ ] `mart_delivery_sla`
- [ ] `mart_discount_promo`
- [ ] `mart_customer_retention`
- [ ] `mart_losses`
- [ ] `mart_today_sales`
- [ ] `mart_today_delivery`
- [ ] `mart_today_stoplists`
- [ ] `mart_today_branch_status`

## DataLens

- [ ] Создано подключение к PostgreSQL
- [ ] У DataLens только read-only доступ
- [ ] Созданы датасеты на `mart_*`
- [ ] Созданы датасеты на `mart_today_*`
- [ ] Созданы вычисляемые поля
- [ ] Собран CEO dashboard
- [ ] Собран Today dashboard
- [ ] Собран Branch dashboard
- [ ] Собран Product dashboard
- [ ] Собран Delivery dashboard
- [ ] Собран Discounts dashboard
- [ ] Собран Retention dashboard
- [ ] Собран Losses dashboard

## Проверка цифр

- [ ] Выручка за день сходится с iiko
- [ ] Количество заказов сходится с iiko
- [ ] Скидки сходятся с iiko
- [ ] Оплаты сходятся с iiko
- [ ] Доставка сходится с iiko
- [ ] Нет дублей по `order_id`
- [ ] Нет дублей по `order_item_id`
- [ ] Realtime dashboard обновляется не реже чем раз в 5 минут
- [ ] Historical dashboard стабильно показывает одинаковые цифры при повторном открытии

## Запрещено

- [ ] Не делать DataLens → iiko API напрямую
- [ ] Не строить основные дашборды на `raw_*`
- [ ] Не давать DataLens write-доступ к базе
- [ ] Не делать тяжёлые расчёты внутри графиков DataLens, если их можно вынести в `mart_*`
