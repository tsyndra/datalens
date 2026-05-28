# Data Coverage And Gaps

Дата актуализации: 2026-05-26.

Этот документ отвечает на три вопроса:

1. Что уже нормально грузится.
2. Чего не хватает для метрик.
3. Где это брать и как решать.

## Текущее покрытие

Текущая БД очищена после экспериментальной загрузки. Ниже указано, что было проверено до очистки и какие источники доступны для новой загрузки.

| Блок | Статус | Источник |
|---|---|---|
| Филиалы | есть | Cloud organizations |
| Товары/категории | есть частично | Cloud nomenclature + OLAP product fields |
| Полная выручка | есть за майский диапазон | OLAP `SALES_DAILY` |
| Товарные продажи | есть за майский диапазон | OLAP `SALES_PRODUCT` |
| Доставочные заказы | есть | Cloud deliveries |
| Позиции доставочных заказов | есть | Cloud deliveries `order.items` |
| Оплаты доставочных заказов | есть | Cloud deliveries `order.payments` |
| Скидки доставочных заказов | есть | Cloud deliveries `order.discounts` |
| Доставка/SLA | есть | Cloud deliveries timings/statuses |
| Клиенты | есть частично | Cloud delivery customer payload |
| Потери | есть частично | derived from Cloud cancellations/refunds/manual discounts/deleted items/late deliveries |
| Стоп-листы | вне текущего scope, не грузим | Cloud stop lists |
| OLAP оплаты всех каналов | есть за тестовый день | iikoServer OLAP `SALES` + `PayTypes` |
| OLAP скидки | есть частично за тестовый день | iikoServer OLAP `SALES` + доступные discount fields |
| OLAP сотрудники | есть за тестовый день | iikoServer OLAP `SALES` + `Cashier`/`WaiterName`/`Delivery.Courier` |
| External menu | raw есть best-effort | Cloud `/api/2/menu` |
| Terminal groups | raw есть | Cloud terminal groups |
| Customer categories | raw есть | Cloud customer categories |

## Фактические объемы

После очистки:

| Показатель | Значение |
|---|---:|
| Размер БД | около 10 MB |
| Строк в user tables | 0 |

Последний проверочный sync до очистки:


| Таблица | Строк | Диапазон |
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
| `mart_payments_daily` | 178 | 2026-05-26 |
| `mart_staff_sales` | 276 | 2026-05-26 |

## Что реально остается не закрытым

После последних правок P1-P4 переведены в реализацию. Реально не закрыты или не подтверждены только эти данные:

| Данные | Статус | Почему не закрыто | Что делать |
|---|---|---|---|
| Журнал операций iikoServer | не закрыто | нужен источник операций: удаление позиции, списание, возврат, отмена, ручная скидка, пользователь/сотрудник операции | P0 backlog: искать в iikoServer operation journal/audit API и полном `/v2/reports/olap/columns` |
| Сотрудник операции | не закрыто для операций | `dim_employees` уже есть, но для операции нужен user/employee из iikoServer journal/OLAP | закрывать вместе с журналом операций iikoServer |
| Полноценный staff directory со stable employee id | частично | сотрудники обновляются из заказов/OLAP по имени/роли; stable id есть только если источник его отдаст | искать iikoServer staff/employee endpoint или id-поля в OLAP/journal |
| Loyalty customer profile bulk enrichment | optional, не блокер | основные клиенты берутся из заказов; `customer/info` нужен только для дополнительных полей loyalty | клиентов брать из заказов, enrichment делать позже при необходимости |
| Availability/menu structure | в реализации | основной источник `/api/1/nomenclature`; дополнительный источник `/api/2/menu` + `/api/2/menu/by_id` | ETL нормализует цены и `isHidden` из external menu в `dim_product_prices` / `dim_product_availability` |
| Комиссии/эквайринг | вне текущего scope | решили пока не делать | оставить только `PayTypes` и сверку оплат с выручкой |

Отдельно: история за 3 года не является проблемой источника. Ее можно грузить после снятия read-only и запуска нового backfill, но сначала нужен тестовый прогон с новым raw dedupe/retention.

## Что не хватает и как решать

### 1. История 3 года

Проблема: сейчас загружен только майский диапазон, а raw JSON уже раздул БД до `20 GB`.

Где брать:

- OLAP `SALES_DAILY`;
- OLAP `SALES_PRODUCT`;
- Cloud deliveries только для доставочных деталей.

Решение:

- сначала поменять raw storage по [storage_strategy.md](storage_strategy.md);
- грузить OLAP историю чанками по 7-31 день;
- Cloud deliveries писать в `fact_*`, raw хранить только dedupe/retention;
- после каждого чанка писать checksum: даты, филиалы, заказы, revenue, позиции.

### 2. Защита полной выручки

Проблема: `refresh_datalens_marts()` может пересобрать `mart_daily_sales` из Cloud/fact-слоя, а потом OLAP накладывается сверху. При неполном запуске можно потерять OLAP-историю.

Где брать:

- полная выручка: OLAP `SALES_DAILY`;
- доставочная детализация: Cloud deliveries.

Решение:

- создать `mart_olap_daily_sales`;
- создать `mart_cloud_delivery_sales`;
- финальный `mart_daily_sales` делать OLAP-first;
- запретить Cloud update затирать OLAP даты.

### 3. Оплаты всех каналов

Статус: тестовая загрузка за `2026-05-26` работает, создана `mart_payments_daily`.

Проблема: `fact_payments` покрывает оплаты из доставочных заказов. Для зала/самовывоза/всех каналов нужна агрегатная OLAP-оплата.

Где брать:

- OLAP `SALES`, `groupByRowFields`: `OpenDate.Typed`, `Department.Code`, `Department`, `PayTypes`;
- Cloud payments оставлять как детализацию доставок.

Решение:

- raw/upsert таблица `raw_server_olap_payments` добавлена;
- `mart_payments_daily` добавлена;
- `mart_payments_by_branch` пока не нужен отдельно, это агрегация `mart_payments_daily`;
- классифицировать `PayTypes` в cash/card/online/aggregator;
- сверять `sum(payment_sum)` с `mart_daily_sales.net_revenue`.

### 4. Скидки и промо всех каналов

Статус: тестовая загрузка за `2026-05-26` работает частично, OLAP-скидки пишутся в `mart_discount_promo`.

Проблема: `fact_discounts` сейчас детальный только по Cloud deliveries. Для полной аналитики нужны OLAP скидки/промо.

Где брать:

- Cloud `order.discounts` для доставочной детализации;
- OLAP `SALES` discount/promo fields, точные поля надо подтвердить discovery.

Решение:

- `scripts/discover_iiko_api.py` теперь получает официальный `/v2/reports/olap/columns`;
- ETL выбирает доступное discount поле из columns, не угадывает имя;
- отдельная `raw_server_olap_discounts` пока не заведена, payload хранится в `raw_server_olap_sales_daily` с `report_type = SALES_DISCOUNTS`;
- `mart_discount_promo` расширяется OLAP-строками;
- отделить ручные скидки, промо и системные скидки.

### 5. Потери

Проблема: `fact_losses` уже наполняется derived signals, но это не журнал операций iikoServer.

Что уже есть:

- отмены;
- возвраты;
- ручные скидки;
- удаленные позиции из Cloud payload;
- опоздания доставки как loss signal.

Чего не хватает не как "причин потерь", а как операционного журнала:

- операции удаления позиции;
- операции списания;
- операции возврата;
- операции отмены;
- операции ручной скидки;
- сотрудник/пользователь, который сделал операцию;
- основание/комментарий операции, если iikoServer его отдает;
- потери от stop-list availability не считаем, потому что стоп-листы выведены из scope.

Где брать:

- в первую очередь iikoServer operation journal/audit API, если он доступен в текущей лицензии/доке;
- iikoServer OLAP `SALES`, `TRANSACTIONS`, `DELIVERIES` как fallback, если там есть нужные поля;
- Cloud `cancelInfo`, `problem`, `items[].deleted`, `items[].status` только для доставочного слоя.

Решение:

- discovery через `/v2/reports/olap/columns` не нашел очевидных writeoff/deletion полей в `TRANSACTIONS` по ключевым словам;
- нужно проверить iikoServer operation journal/audit endpoints и вручную разобрать полный список `TRANSACTIONS` columns, а не угадывать имена;
- добавить `raw_server_olap_writeoffs_or_deletions`;
- расширить `fact_losses` типами `writeoff`, `deletion`, `manual_discount`, `refund`, `cancellation`, `late_delivery`;
- `mart_losses` считать из единой taxonomy.

### 6. Стоп-листы: вне scope

Статус: не нужны для текущих дашбордов и загрузки.

Решение: ETL отключает их по умолчанию (`IIKO_SYNC_STOPLISTS=false`), DataLens-витрины по ним не строим.

Если когда-нибудь понадобятся, источник уже понятен:

- форма подтверждена по Cloud-доке: `terminalGroupStopLists[].items[].items[]`;
- endpoint Cloud `/api/1/stop_lists`;
- terminal groups для связи с филиалом.

### 7. Клиенты, loyalty, retention

Статус: основная модель клиентов реализуется через парсинг всех Cloud delivery orders. Это закрывает клиентов для retention/RFM.

Пояснение по loyalty: это не обязательный источник клиентов. Он нужен только если понадобятся дополнительные атрибуты гостя из программы лояльности: категории, день рождения, blacklist, wallet/bonus info и другие поля, которых нет в заказе.

Где брать:

- в первую очередь парсить все Cloud delivery orders и вытаскивать клиентов из payload заказов;
- Cloud `/api/1/loyalty/iiko/customer/info` использовать как optional enrichment, если хватает безопасного идентификатора для запроса;
- Cloud `/api/1/loyalty/iiko/customer_category` использовать для справочника категорий.

Решение:

- не хранить сырые телефоны без отдельного решения;
- основная загрузка клиентов должна идти из уже загружаемых заказов, а не отдельным перебором телефонов;
- расширить `dim_customers` полями из order customer payload;
- добавить `dim_customer_categories` и `mart_customer_segments`;
- RFM считать из `fact_customer_orders`.

### 8. Сотрудники

Статус: добавлена `dim_employees`, которая обновляется из Cloud `operator`/`courierInfo` и OLAP staff fields при sync.

Ограничение: stable employee id будет только там, где источник реально отдает id. Если id нет, временно используется `role + normalized_name`.

Где брать:

- Cloud `operator`, `courierInfo`;
- OLAP `Cashier`, `WaiterName`, `Delivery.Courier` и другие staff/cashier/waiter fields из `/v2/reports/olap/columns`;
- будущие найденные iikoServer/iikoCloud staff endpoints, если они есть в документации и доступны.

Решение:

- discovery для OLAP staff fields переведен на `/v2/reports/olap/columns`;
- ETL пишет агрегаты по `Cashier`, `WaiterName`, `Delivery.Courier`, если эти поля доступны;
- добавить `dim_employees` как постоянно обновляемый справочник;
- обновлять `dim_employees` из каждого sync: upsert по `source_system + source_employee_id`, если id есть, иначе по `role + normalized_name`;
- хранить роли: `cashier`, `waiter`, `operator`, `courier`, `unknown`;
- хранить `first_seen_at`, `last_seen_at`, `is_active_guess`, `source_fields`;
- добавить поля employee/operator/courier в delivery/order/loss facts;
- строить `mart_staff_performance` после подтверждения источника.

### 9. Меню, цены, availability

Статус: `/api/1/nomenclature` выбран основным источником, добавлены `dim_product_prices`, `dim_product_availability` и расширения `dim_products`.

Дополнительный источник: `/api/2/menu` и `/api/2/menu/by_id`; ETL нормализует external menu prices и `isHidden`.

Где брать:

- в первую очередь Cloud `/api/1/nomenclature`;
- OLAP `DishId`, `DishName`, `DishCategory` только для связи с продажами;
- Cloud `/api/2/menu` и `/api/2/menu/by_id` для цен, размеров и menu availability.

Решение:

- сначала нормализовать `dim_products`, `dim_categories`, `dim_product_prices` из nomenclature;
- external menu нормализовать в `dim_product_prices` и `dim_product_availability`;
- сделать bridge Cloud product id -> OLAP DishId по id/name/category;
- не грузить модификаторы как отдельные товары без явного правила.

### 10. Гео и доставка

Проблема: SLA есть, но гео/курьеры/зоны не полные.

Где брать:

- Cloud `deliveryPoint`;
- Cloud `deliveryZone`;
- Cloud `courierInfo`;
- Cloud `externalCourierService`;
- Cloud timings.

Решение:

- нормализовать адрес/координаты/зону в `fact_deliveries`;
- добавить `dim_delivery_zones`;
- добавить `mart_delivery_geo` и `mart_courier_performance`;
- raw delivery payload хранить только ограниченно.

## Приоритет

P0 backlog: потери

1. Сохранить полный catalog OLAP columns для `SALES`, `TRANSACTIONS`, `DELIVERIES`.
2. Вручную разобрать поля writeoff/deletion/refund/cancel/reason/comment/user/employee.
3. Добавить raw/upsert слой для найденных OLAP loss reports.
4. Расширить `fact_losses`: `writeoff`, `deletion`, `manual_discount`, `refund`, `cancellation`, `late_delivery`.
5. Привязать сотрудника и причину, если поле реально есть в OLAP/Cloud.
6. Пересобрать `mart_losses` из единой taxonomy.

P1 implementation: клиенты

1. Спарсить всех клиентов из всех Cloud delivery orders.
2. Не хранить сырые телефоны; сохранять `phone_hash` и разрешенные атрибуты клиента.
3. Расширить `dim_customers`.
4. Построить `fact_customer_orders`, `mart_customer_retention`, `mart_customer_segments`.
5. Loyalty customer info использовать только как enrichment, если будет понятен безопасный ключ запроса.

P2 implementation: сотрудники

1. Сделать `dim_employees`, которая постоянно обновляется из OLAP и Cloud.
2. Источники: `Cashier`, `WaiterName`, `Delivery.Courier`, Cloud `operator`, Cloud `courierInfo`.
3. Если есть stable employee id, использовать его; если нет, временно матчить по роли и нормализованному имени.
4. Добавить `first_seen_at`, `last_seen_at`, `is_active_guess`.
5. Привязать сотрудников к заказам, доставкам, потерям и staff marts.

P3 implementation: номенклатура

1. Сначала проверить и нормализовать Cloud `/api/1/nomenclature`.
2. Из нее собрать товары, категории, цены, модификаторы и признаки активности, если поля есть.
3. OLAP `DishId` использовать для связи с продажами.
4. `/api/2/menu` трогать только если nomenclature не закрывает нужные поля.

P4 implementation: финансы без эквайринга

1. Эквайринг и комиссии пока не делаем.
2. Оставить OLAP payments by `PayTypes`.
3. Классифицировать типы оплат в `cash/card/online/aggregator/bonus/other`.
4. Делать сверку оплат с выручкой.
