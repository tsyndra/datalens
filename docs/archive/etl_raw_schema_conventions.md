# Конвенции `raw_*` и поле источника `source_system`

Каждый приём больших JSON-батчей из внешнего провайдера складывается в слой **`raw_*`**, до нормализации в `stg_*`/`dim_*`/`fact_*`.

## Обязательные метаданные строки загрузки

Рекомендуемые колонки (имена можно адаптировать под DDL, но смысл сохранять):

| Колонка | Тип | Значение |
|---------|-----|----------|
| `source_system` | `text` | Константы: **`cloud`** (HTTPS `api-* .iiko.services`), **`server_olap`** (HTTP к `hatimaki-co` через `/resto/api/v2/reports/olap`), **`resto_legacy`** если появится прямое чтение `/resto/api/...` наравне без OLAP. |
| `ingested_at` | `timestamptz` | Время записи синх-хронизации в целевой БД. |
| `extraction_started_at` | `timestamptz` | При необходимости — когда начался HTTP запрос к провайдеру. |
| `provider_request_id` / `correlation_id` | `text` nullable | Если API вернул идемпотентный id. |
| `payload` | `jsonb` | Сырой ответ или объект с неизменными полями. |
| `org_filter` | `uuid` nullable | Организация, которой задавалось окно синка (если применимо). |
| `window_from` | `timestamptz` nullable | Интервал, которым параметрировался метод. |
| `window_to` | `timestamptz` nullable | — « — |

## Принцип lineage

При любом переходе `raw_* → stg_*` прописывать **те же** имена источников в промежуточных таблицах до тех пор, пока не произойдёт реальное объединение витрины (тогда возможна одна финальная `source_mix` строка только на уровне `mart_*` по правилам согласованности из [reconcile_cloud_vs_olap.md](reconcile_cloud_vs_olap.md)).

Уникальный ключ сырья в Postgres: желательно `hash(payload)` или `jsonb_digest` до дедупа в пределах `source_system` и окна времени.

## Связка с документацией API

Табличные строки см.:

- Cloud: [api_matrix_cloud.md](api_matrix_cloud.md)
- Сервер OLAP: [api_matrix_olap_server.md](api_matrix_olap_server.md)
