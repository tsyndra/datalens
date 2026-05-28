# Матрица: OLAP через iikoServer (`hatimaki-co`) → `raw_*`

Хост синхронизации (объединённый Chain филиалов) фиксируется bootstrap-скриптом: **`IIKO_OLAP_SERVER_URL=https://hatimaki-co.iiko.it:443`**, RESTO-база для legacy API: **`IIKO_RESTO_BASE_URL=https://hatimaki-co.iiko.it:443/resto`**.

Эталон реализации паттерна: проект **`kml`** (`_server_auth`, `_olap_get_phones`).

Сводная матрица Cloud + OLAP методов для полного сбора данных: [full_data_collection_methods.md](full_data_collection_methods.md).

## Авторизация iikoServer (REST API)

| Шаг | URL | Описание | Сырьё |
|-----|-----|----------|-------|
| Вход | `GET {IIKO_OLAP_SERVER_URL}/resto/api/auth?login=<user>&pass=<SHA1_HEX>` | `pass` — SHA1 от пароля строкой UTF-8, hex lower-case как у `hashlib.sha1(...).hexdigest()` | ключ сессии в ответе (plain text); в `raw_*` обычно не кладём, только бизнес-ответы OLAP |
| Выход | `GET .../resto/api/logout?key=<session>` | освободить слот лицензии | — |

Переменные окружения: `IIKO_OLAP_LOGIN`, `IIKO_OLAP_PASSWORD`, `IIKO_OLAP_VERIFY_SSL`.

## OLAP отчёт (v2)

| Назначение MVP | Endpoint | Тело запроса (идея) | Имя raw |
|----------------|----------|---------------------|---------|
| Сверка телефонов доставки + мостик к Cloud (`kml`-пайплайн) | `POST {IIKO_OLAP_SERVER_URL}/resto/api/v2/reports/olap?key=<session>` | `reportType`: например **`DELIVERIES`**; **`filters`**: диапазон дат через `filterType` / `periodType`; **`groupByRowFields`**, **`aggregateFields`** — по задаче; параметры имен полей из env: `IIKO_OLAP_*_FIELD` | `raw_server_olap_deliveries_phones_by_chunk` или единое `raw_server_olap_response` с полем `chunk_from`/`chunk_to` |
| Свод продаж по дням/филиалам (пример для reconcile) | тот же `.../reports/olap` | **`reportType`**: пресет, согласованный с офисом (`SALES` и т.д. — см. вашу конфигурацию OLAP на сервере) | `raw_server_olap_sales_daily` |

Тело должно включать фильтры по датам; для ограничения по подразделениям используйте фильтр на поле вроде `Department.Code` или то, что задано в `IIKO_OLAP_DEPT_CODE_FIELD`.

## Параметры периода и чанков (из ваших конфигов)

| Env | Роль |
|-----|------|
| `IIKO_OLAP_ENABLED` | включить вторую «ногу» |
| `IIKO_OLAP_LOOKBACK_DAYS` | глубина окна истории для инкремента |
| `IIKO_OLAP_CHUNK_DAYS` | размер порции по дате к OLAP (нагрузка на сервер) |
| `IIKO_OLAP_PHONE_FIELD` / `DATE_FIELD` / `DEPT_CODE_FIELD` | имена OLAP-колонок в запросе/ответе |

## Связка с Postgres

Рекомендуется сохранять **полный JSON** ответ OLAP (`columnNames`, `data`) в `jsonb`-колонку скачанного вида до нормализации в `fact_*`.

Для воспроизводимости фиксируйте в метаданных строки: `report_type`, `filters` фрагмент, интервал дат периода, `department_filter`/`dept_codes` — см. конвенцию [etl_raw_schema_conventions.md](etl_raw_schema_conventions.md).
