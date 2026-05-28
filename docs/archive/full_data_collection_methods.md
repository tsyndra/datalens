# Full data collection methods

Дата ревизии: 2026-05-22.

Цель документа: зафиксировать полный набор источников и методов, которые нужны для полноценного сбора данных в PostgreSQL/DataLens. Это не список всех методов iiko вообще, а практическая матрица под наши витрины `dim_*`, `fact_*`, `mart_*` и пресеты `dl_preset_*`.

Общий контекст проекта и порядок работ: [project_context.md](project_context.md). План отчетов и метрик: [report_plan.md](report_plan.md).

## Главный вывод

Для полного DataLens нельзя опираться только на iikoCloud `deliveries`.

- Полная выручка, заказы всех каналов, товарные продажи, себестоимость и возвраты должны идти из iikoServer OLAP `SALES`.
- iikoCloud нужен для справочников, номенклатуры, терминальных групп, доставки, стоп-листов и клиентских деталей.
- Cloud `POST /api/1/deliveries/by_delivery_date_and_status` покрывает доставочный контур, но не весь ресторанный оборот. Если строить `Revenue by day` только по Cloud-доставкам, в диапазонах будут дыры.

`Revenue by day` сейчас строится из `dl_preset_revenue_by_day -> mart_daily_sales`. Для полного диапазона дат `mart_daily_sales` должен быть заполнен OLAP-данными за каждую дату периода.

## Обязательный минимум

| Блок | Источник | Метод | Назначение | Текущий статус |
|---|---|---|---|---|
| Авторизация Cloud | iikoCloud | `POST /api/1/access_token` | токен для Cloud API | используется |
| Организации | iikoCloud | `GET /api/1/organizations` | `dim_organizations`, список филиалов | используется |
| Терминальные группы | iikoCloud | `POST /api/1/terminal_groups` | связь филиал -> terminal group, доставка/заказы | сохраняется в raw |
| Номенклатура | iikoCloud | `POST /api/1/nomenclature` | `dim_products`, `dim_categories`, блюда, категории, единицы | используется частично |
| Внешнее меню | iikoCloud | `POST /api/2/menu`, `POST /api/2/menu/by_id` | меню, цены, структура, если Cloud nomenclature неполная | сохраняется в raw best-effort |
| Стоп-листы | iikoCloud | `POST /api/1/stop_lists` | `fact_stoplists`, активные стопы | используется |
| Доставки по дате и статусу | iikoCloud | `POST /api/1/deliveries/by_delivery_date_and_status` | `fact_deliveries`, детали доставочных заказов | используется |
| Доставка по id | iikoCloud | `POST /api/1/deliveries/by_id` | дозагрузка полной карточки конкретной доставки | кандидат на проверку |
| Доставка по телефону и дате | iikoCloud | `POST /api/1/deliveries/by_delivery_date_and_phone` | восстановление деталей клиента/доставки по телефону | кандидат на проверку |
| Клиентская карточка | iikoCloud | `POST /api/1/loyalty/iiko/customer/info` | имя, дата рождения, категории, blacklist | endpoint известен, нужен безопасный тест с телефоном |
| Категории клиентов | iikoCloud | `POST /api/1/loyalty/iiko/customer_category` | сегменты/категории гостей | сохраняется в raw |
| Авторизация OLAP | iikoServer | `GET /resto/api/auth` | ключ сессии OLAP | используется |
| OLAP отчет | iikoServer | `POST /resto/api/v2/reports/olap` | все исторические агрегаты продаж | используется |
| Завершение OLAP-сессии | iikoServer | `GET /resto/api/logout` | освобождение сессии | используется |

## OLAP-наборы, которые нужны для полной аналитики

Все запросы идут в один endpoint:

```text
POST {IIKO_OLAP_SERVER_URL}/resto/api/v2/reports/olap?key=<session>
```

Базовый фильтр по дате:

```json
{
  "OpenDate.Typed": {
    "filterType": "DateRange",
    "periodType": "CUSTOM",
    "from": "YYYY-MM-DD",
    "to": "YYYY-MM-DD",
    "includeLow": true,
    "includeHigh": true
  }
}
```

`OpenDate.Typed` берется из `IIKO_OLAP_DATE_FIELD`.

| Витрина | reportType | groupByRowFields | aggregateFields | Статус |
|---|---|---|---|---|
| `mart_daily_sales` | `SALES` | `OpenDate.Typed`, `Department.Code`, `Department`, `OriginName` | `UniqOrderId.OrdersCount`, `DishAmountInt`, `DishSumInt`, `DiscountSum`, `DishDiscountSumInt`, `DishReturnSum` | используется |
| `mart_product_sales` | `SALES` | `OpenDate.Typed`, `Department.Code`, `Department`, `DishId`, `DishName`, `DishCategory` | `UniqOrderId.OrdersCount`, `DishAmountInt`, `DishSumInt`, `DiscountSum`, `DishDiscountSumInt`, `ProductCostBase.ProductCost` | используется |
| Оплаты по типам | `SALES` | `OpenDate.Typed`, `Department.Code`, `Department`, `PayTypes` | `UniqOrderId.OrdersCount`, `DishSumInt` | проверено discovery, нужно добавить в ETL |
| Возвраты | `SALES` | `OpenDate.Typed`, `Department.Code`, `Department`, `OriginName` | `DishReturnSum` плюс детализация по доступным полям возврата | частично используется агрегатом |
| Скидки/промо | `SALES` | `OpenDate.Typed`, `Department.Code`, `Department`, поле скидки из OLAP-конфигурации | `DiscountSum`, `DishDiscountSumInt`, `UniqOrderId.OrdersCount` | нужно проверить точное поле на сервере |
| Удаления/списания | OLAP-отчет по операциям или продажам, зависит от конфигурации | дата, филиал, причина, сотрудник, блюдо | сумма/количество | нужно проверить на сервере |
| Сотрудники/кассиры | `SALES` или профильный OLAP-отчет | дата, филиал, сотрудник/кассир/официант | заказы, выручка | нужно проверить на сервере |
| Доставки OLAP | `DELIVERIES` или доступный доставочный OLAP-отчет | дата, филиал, телефон/номер/статус | счетчики, суммы | кандидат для мостика OLAP -> Cloud |

Практический порядок: сначала расширить `scripts/discover_iiko_api.py`, чтобы он проверял спорные OLAP-поля на коротком периоде, затем добавлять нормализацию в `scripts/sync_iiko.py`.

## Cloud-наборы, которые нужны для деталей

| Сущность | Метод | Что забираем | Raw-таблица | Нормализация |
|---|---|---|---|---|
| Организации | `GET /api/1/organizations` | id, name, code, disabled | `raw_cloud_organizations` | `dim_organizations` |
| Терминальные группы | `POST /api/1/terminal_groups` | terminal group id, organization id, name, disabled | `raw_cloud_terminal_groups` | добавить `dim_terminal_groups` или поля в `dim_organizations` |
| Номенклатура | `POST /api/1/nomenclature` | products, groups, productCategories, sizes | `raw_cloud_nomenclature` | `dim_products`, `dim_categories` |
| Внешнее меню | `POST /api/2/menu`, `POST /api/2/menu/by_id` | меню, цены, категории, availability | `raw_cloud_external_menu` | расширить `dim_products`, цены по филиалам |
| Доставки | `POST /api/1/deliveries/by_delivery_date_and_status` | order, items, payments, discounts, customer, deliveryPoint, timings | `raw_cloud_deliveries_by_date_status` | `fact_orders`, `fact_order_items`, `fact_payments`, `fact_discounts`, `fact_deliveries`, `dim_customers` |
| Доставка по id | `POST /api/1/deliveries/by_id` | полная карточка одного заказа | `raw_cloud_delivery_by_id` | дозагрузка пропущенных полей |
| Доставка по телефону | `POST /api/1/deliveries/by_delivery_date_and_phone` | история доставок клиента в периоде | `raw_cloud_deliveries_by_phone` | обогащение `dim_customers` и retention |
| Стоп-листы | `POST /api/1/stop_lists` | активные stop list items | `raw_cloud_stop_lists` | `fact_stoplists`, `mart_today_stoplists` |
| Клиент | `POST /api/1/loyalty/iiko/customer/info` | customer id, name, phone, birthdate, categories, blacklist | `raw_cloud_customer_info` | `dim_customers` |
| Категории клиентов | `POST /api/1/loyalty/iiko/customer_category` | категории/сегменты | `raw_cloud_customer_categories` | `dim_customer_categories` |

## Что нужно добавить в ETL

1. Нормализовать сохраненные `terminal_groups`.
2. Проверить полноту external menu и нормализовать цены/структуру, если `nomenclature` не дает полный список/цены.
3. Для `deliveries` грузить не только `closed`, а полный набор статусов, когда строим оперативные витрины:
   - `Unconfirmed`;
   - `WaitCooking`;
   - `ReadyForCooking`;
   - `CookingStarted`;
   - `CookingCompleted`;
   - `Waiting`;
   - `OnWay`;
   - `Delivered`;
   - `Closed`;
   - `Cancelled`, если API принимает этот статус в нашей конфигурации.
4. Добавить OLAP payments mart/fact:
   - `PayTypes`;
   - сумма;
   - количество заказов.
5. Проверить OLAP-поля для скидок, причин удалений, кассиров/официантов и добавить их в discovery.
6. Добавить/наполнить raw-таблицы:
   - `raw_cloud_terminal_groups` — добавлено;
   - `raw_cloud_external_menus` — добавлено;
   - `raw_cloud_delivery_by_id`;
   - `raw_cloud_deliveries_by_phone`;
   - `raw_cloud_customer_info`;
   - `raw_cloud_customer_categories` — добавлено;
   - `raw_server_olap_payments`;
   - `raw_server_olap_discounts`;
   - `raw_server_olap_staff`;
   - `raw_server_olap_writeoffs_or_deletions`.
7. Для исторической выручки запускать OLAP-бэкфилл по всему нужному периоду. Cloud-доставки использовать как детализацию, а не как единственный источник revenue.

## Почему в Revenue by day видна только часть дат

`dl_preset_revenue_by_day` читает `mart_daily_sales`. Если в `mart_daily_sales` за период есть строки только за `2026-05-20` и `2026-05-21`, DataLens физически не может показать `2026-05-13..2026-05-19`.

Правильное исправление не в настройке графика, а в загрузке истории:

```bash
bash scripts/backfill_range.sh 2026-05-13 2026-05-21
```

Этот запуск должен пройти с доступом к сети, потому что он обращается к iikoCloud и iikoServer OLAP.

## Следующий технический шаг

Расширить `scripts/discover_iiko_api.py` так, чтобы он отдельными проверками печатал статус для:

- `terminal_groups`;
- `menu` и `menu/by_id`;
- `deliveries/by_id`;
- `deliveries/by_delivery_date_and_phone`;
- `loyalty/iiko/customer/info`;
- OLAP `SALES` payments;
- OLAP discounts;
- OLAP staff;
- OLAP deletions/writeoffs.

После этого переносить только подтвержденные поля в схему и ETL.
