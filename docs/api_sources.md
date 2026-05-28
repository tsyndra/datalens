# API Sources

Дата актуализации: 2026-05-26.

Единая матрица источников. Старые подробные матрицы лежат в `docs/archive/` и не являются текущим статусом.

Важно: это две разные документации.

- iikoCloud API / Transport API: методы `https://api-ru.iiko.services/api/...`.
- iikoServer REST/OLAP API: методы `https://<server>/resto/api/...`.

## iikoCloud

Base URL:

```text
https://api-ru.iiko.services
```

Auth:

```text
POST /api/1/access_token
```

| Метод | Статус | Использование |
|---|---|---|
| `GET/POST /api/1/organizations` | работает | `dim_organizations` |
| `POST /api/1/nomenclature` | работает частично | `dim_products`, `dim_categories`; полный список есть не у каждого филиала |
| `POST /api/1/terminal_groups` | работает raw | нужна нормализация terminal group -> филиал |
| `POST /api/1/stop_lists` | работает, но отключено | нормализация проверена; ETL пропускает stop-lists по умолчанию, потому что они не нужны |
| `POST /api/1/deliveries/by_delivery_date_and_status` | работает | `fact_orders`, `fact_order_items`, `fact_payments`, `fact_discounts`, `fact_deliveries`, `dim_customers` |
| `POST /api/1/deliveries/by_id` | контракт подтвержден по Cloud-доке | body использует `organizationId`, `orderIds`; live-тесту нужен order id |
| `POST /api/1/deliveries/by_delivery_date_and_phone` | контракт подтвержден по Cloud-доке | body использует `organizationIds`, `phone`; live-тесту нужен телефон |
| `POST /api/1/loyalty/iiko/customer/info` | контракт подтвержден по Cloud-доке | карточка клиента; тестировать только с явно заданным телефоном |
| `POST /api/1/loyalty/iiko/customer_category` | работает raw | нужна `dim_customer_categories` |
| `POST /api/2/menu` | работает raw best-effort | список external menus и price categories |
| `POST /api/2/menu/by_id` | нормализация добавлена | цены, размеры, `isHidden` availability в `dim_product_prices` / `dim_product_availability` |

## iikoServer OLAP

Host:

```text
https://hatimaki-co.iiko.it:443
```

Auth:

```text
GET /resto/api/auth
POST /resto/api/v2/reports/olap
GET /resto/api/logout
```

| OLAP набор | Статус | Использование |
|---|---|---|
| `SALES_DAILY` | работает | полная выручка, заказы, скидки, возвраты по дню/филиалу/источнику |
| `SALES_PRODUCT` | работает | товары, категории, количество, себестоимость, маржа |
| `GET /v2/reports/olap/columns` | работает | официальный способ получить доступные поля для `SALES`, `TRANSACTIONS`, `DELIVERIES` |
| `SALES` + `PayTypes` | работает | оплаты всех каналов, ETL пишет `mart_payments_daily` |
| `SALES` discounts/promo fields | частично работает | ETL пишет OLAP-скидки в `mart_discount_promo` по доступному полю `OrderDiscount.Type`/аналогам |
| `SALES` staff fields | работает | ETL пишет `mart_staff_sales` по `Cashier`, `WaiterName`, `Delivery.Courier`, если поля доступны |
| iikoServer operation journal/audit | не найдено в текущем clean OLAP файле | нужен источник операций удаления/списания/возврата/отмены и user/employee операции |
| `TRANSACTIONS` writeoffs/deletions | не найдено через keyword discovery | fallback после поиска operation journal; нужен ручной разбор полного `/columns` |
| delivery OLAP report | не подтверждено | возможно для мостика OLAP -> Cloud |

## Порядок добавления нового источника

1. Для iikoCloud сверить endpoint/body/response по Cloud-доке.
2. Для iikoServer сначала получить `/v2/reports/olap/columns`, затем строить запрос только по доступным полям.
3. Проверить маленьким live-запросом в `scripts/discover_iiko_api.py`.
4. Зафиксировать статус в этом файле.
5. Добавить raw/meta таблицу только с hash/upsert политикой.
6. Сразу нормализовать в `dim_*`/`fact_*`.
7. Добавить checksum по окну загрузки.
8. Добавить/обновить `mart_*` или `dl_preset_*`.

## Что не делать

- Не грузить DataLens напрямую из iiko API.
- Не строить полную выручку по Cloud deliveries.
- Не append-ить каждый raw payload без hash и retention.
- Не хранить сырые телефоны без отдельного решения.
