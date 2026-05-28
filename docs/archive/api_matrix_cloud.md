# Матрица: сущности MVP → Cloud Public API → `raw_*`

Источник контрактов: [OpenAPI iiko.Transport](https://api-ru.iiko.services/api-docs). База `IIKO_CLOUD_API_BASE_URL` (обычно `https://api-ru.iiko.services`). Все защищённые запросы: `Authorization: Bearer <token>` (токен `POST /api/1/access_token`, тело `{ "apiLogin": "<IIKO_API_LOGIN>" }`).

В колонке **Сырьё** — рекомендуемое имя таблицы/префикса JSON-слоя `raw_*` в PostgreSQL. В каждой строке сохранять метаданные ETL из [etl_raw_schema_conventions.md](etl_raw_schema_conventions.md) (`source_system = cloud`, `ingested_at`, и т.д.).

Сводная матрица Cloud + OLAP методов для полного сбора данных: [full_data_collection_methods.md](full_data_collection_methods.md).

## Auth и оболочка

| MVP слой | Метод | Метод HTTP | Имя raw / примечание |
|----------|-------|-------------|---------------------|
| (все запросы) | `/api/1/access_token` | POST | `raw_cloud_api_meta` или кеш только в приложении |

## Организации (филиалы)

| MVP | Transport | Имя raw |
|-----|-----------|---------|
| `dim_organizations` | `/api/1/organizations` (в спецификации часто POST с телом; в существующих интеграциях встречался GET — держите оба под рукой и проверьте вашу сборку по OpenAPI) | `raw_cloud_organizations` |

## Номенклатура и меню

| MVP | Transport | Имя raw |
|-----|-----------|---------|
| `dim_products`, `dim_categories`, цены | `/api/1/nomenclature` (revision / полный дамп); при необходимости внешних меню — `/api/2/menu`, `/api/2/menu/by_id` | `raw_cloud_nomenclature`, `raw_cloud_external_menu` |

## Стоп-листы

| MVP | Transport | Имя raw |
|-----|-----------|---------|
| `fact_stoplists` | `/api/1/stop_lists` | `raw_cloud_stop_lists` |

## Доставки и заказы (доставочный контур)

| MVP | Transport | Имя raw |
|-----|-----------|---------|
| `fact_deliveries`, частично заголовки `fact_orders` | `/api/1/deliveries/by_delivery_date_and_status` | `raw_cloud_deliveries_by_date_status` |
| Доп. деталь по телефону (см. паттерн kml: OLAP → телефоны → Cloud) | `/api/1/deliveries/by_delivery_date_and_phone` | `raw_cloud_deliveries_by_phone` |
| По id | `/api/1/deliveries/by_id` (если доступен в вашей лицензии) | `raw_cloud_delivery_by_id` |

## Прочее из Cloud для расширения MVP

| MVP | Transport | Имя raw |
|-----|-----------|---------|
| Терминальные группы (привязка к точкам) | `/api/1/terminal_groups` | `raw_cloud_terminal_groups` |
| Заказы в зале / общий контур заказов (если не покрывается только доставкой) | См. OpenAPI группы **Order**, **Reserve**, **Banquet** по вашей лицензии; возможны команды асинхронные (`/api/1/commands/status`) | По факту появления методов в спеке завести `raw_cloud_orders_*` |
| Лояльность и клиент | `/api/1/loyalty/iiko/*` (customer info и др.) | `raw_cloud_loyalty_*` → далее в `dim_customers`, `fact_customer_orders` |

## Замечания по покрытию документа MVP

Раздел «исторический синк» в [datalens_iiko_analytics_mvp_v2.md](../datalens_iiko_analytics_mvp_v2.md) упоминает `orders`, `order_items`, `payments`, `discounts`, `customers`, `refunds`, `cancellations`, `losses`.

- То, что **напрямую** есть в типовом Delivery-фокусном Cloud-слое, перечислено выше.
- Полные **`fact_order_items`**, **`fact_payments`**, **`fact_discounts`** для зала и смешанного канала нужно дополнительно картировать к методам вашей сборки (**Sales**/**Order** по OpenAPI или выгрузкам через **OLAP** — см. [api_matrix_olap_server.md](api_matrix_olap_server.md)).
- Держите TODO в коде синка до полного паритета со спецификацией: при открытии нового endpoint добавляйте строку в этот файл и миграцию `raw_*`.
