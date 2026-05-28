#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ROOT_DIR = BASE_DIR.parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(ROOT_DIR / ".credentials.env")
load_env_file(ROOT_DIR / ".env")


def database_url() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    user = os.environ.get("POSTGRES_USER", "analytics")
    password = os.environ.get("POSTGRES_PASSWORD", "changeme_rotate_me")
    host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    port = os.environ.get("POSTGRES_PORT", "54337")
    db = os.environ.get("POSTGRES_DB", "iiko_analytics")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


COMMON_TIME_DIMENSIONS = {
    "business_date": "Business date",
    "week_start": "Week",
    "month_start": "Month",
    "iso_weekday": "Weekday",
}


SUBJECTS: dict[str, dict[str, Any]] = {
    "sales": {
        "label": "Sales",
        "view": "dl_olap_sales",
        "description": "Revenue, orders, avg check by date, branch, source.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "organization_name": "Branch",
            "order_source": "Order source",
        },
        "metrics": {
            "orders": {"label": "Orders", "expr": "sum(orders_count)::integer"},
            "gross_revenue": {"label": "Gross revenue", "expr": "sum(gross_revenue)::numeric(14,2)"},
            "net_revenue": {"label": "Net revenue", "expr": "sum(net_revenue)::numeric(14,2)"},
            "avg_check": {"label": "Avg check", "expr": "(sum(net_revenue) / nullif(sum(orders_count), 0))::numeric(14,2)"},
            "discount_sum": {"label": "Discount", "expr": "sum(discount_sum)::numeric(14,2)"},
            "discount_share": {"label": "Discount share", "expr": "(sum(discount_sum) / nullif(sum(gross_revenue), 0))::numeric(14,6)"},
            "refund_sum": {"label": "Refund", "expr": "sum(refund_sum)::numeric(14,2)"},
            "items_qty": {"label": "Items qty", "expr": "sum(items_qty)::numeric(14,3)"},
        },
        "filters": ["business_date", "organization_name", "order_source"],
    },
    "orders": {
        "label": "Orders",
        "view": "dl_olap_orders",
        "description": "Order-level details without product/payment fan-out.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "open_hour": "Hour",
            "organization_name": "Branch",
            "order_source": "Order source",
            "order_type": "Order type",
            "status": "Status",
            "is_delivery": "Delivery",
            "is_cancelled": "Cancelled",
            "payment_groups": "Payment groups",
            "delivery_status": "Delivery status",
        },
        "metrics": {
            "orders": {"label": "Orders", "expr": "count(distinct order_id)::integer"},
            "customers": {"label": "Customers", "expr": "count(distinct customer_id)::integer"},
            "gross_revenue": {"label": "Gross revenue", "expr": "sum(gross_revenue)::numeric(14,2)"},
            "net_revenue": {"label": "Net revenue", "expr": "sum(net_revenue)::numeric(14,2)"},
            "avg_check": {"label": "Avg check", "expr": "(sum(net_revenue) / nullif(count(distinct order_id), 0))::numeric(14,2)"},
            "payment_sum": {"label": "Payment sum", "expr": "sum(payment_sum)::numeric(14,2)"},
            "discount_sum": {"label": "Discount", "expr": "sum(discount_sum)::numeric(14,2)"},
            "late_orders": {"label": "Late orders", "expr": "count(distinct order_id) filter (where is_late)::integer"},
        },
        "filters": ["business_date", "organization_name", "order_source", "order_type", "status", "is_delivery", "is_cancelled", "payment_groups", "delivery_status", "customer_id", "phone_hash"],
    },
    "products": {
        "label": "Products",
        "view": "dl_olap_products",
        "description": "Order item grain for products, categories, baskets, customer-product questions.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "open_hour": "Hour",
            "organization_name": "Branch",
            "order_source": "Order source",
            "product_name": "Product",
            "category_name": "Category",
            "size_name": "Size",
            "is_delivery": "Delivery",
            "is_modifier": "Modifier",
        },
        "metrics": {
            "item_lines": {"label": "Item lines", "expr": "count(*)::integer"},
            "orders": {"label": "Orders", "expr": "count(distinct order_id)::integer"},
            "customers": {"label": "Customers", "expr": "count(distinct customer_id)::integer"},
            "quantity": {"label": "Quantity", "expr": "sum(quantity)::numeric(14,3)"},
            "gross_revenue": {"label": "Gross revenue", "expr": "sum(gross_revenue)::numeric(14,2)"},
            "net_revenue": {"label": "Net revenue", "expr": "sum(net_revenue)::numeric(14,2)"},
            "avg_price": {"label": "Avg price", "expr": "(sum(net_revenue) / nullif(sum(quantity), 0))::numeric(14,2)"},
            "discount_sum": {"label": "Discount", "expr": "sum(discount_sum)::numeric(14,2)"},
            "cost_sum": {"label": "Cost", "expr": "sum(cost_sum)::numeric(14,2)"},
            "profit_sum": {"label": "Profit", "expr": "sum(profit_sum)::numeric(14,2)"},
            "margin_rate": {"label": "Margin rate", "expr": "(sum(profit_sum) / nullif(sum(net_revenue), 0))::numeric(14,6)"},
        },
        "filters": ["business_date", "organization_name", "order_source", "product_name", "category_name", "size_name", "is_delivery", "is_modifier", "customer_id", "phone_hash"],
    },
    "payments": {
        "label": "Payments",
        "view": "dl_olap_payments",
        "description": "Payment rows by type/group.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "organization_name": "Branch",
            "order_source": "Order source",
            "payment_type": "Payment type",
            "payment_group": "Payment group",
            "is_external": "External",
            "is_prepay": "Prepay",
        },
        "metrics": {
            "payments": {"label": "Payments", "expr": "count(*)::integer"},
            "orders": {"label": "Orders", "expr": "count(distinct order_id)::integer"},
            "payment_sum": {"label": "Payment sum", "expr": "sum(payment_sum)::numeric(14,2)"},
        },
        "filters": ["business_date", "organization_name", "order_source", "payment_type", "payment_group", "is_external", "is_prepay"],
    },
    "discounts": {
        "label": "Discounts",
        "view": "dl_olap_discounts",
        "description": "Discount rows by discount name/type/manual flag.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "organization_name": "Branch",
            "order_source": "Order source",
            "discount_name": "Discount",
            "discount_type": "Discount type",
            "is_manual": "Manual",
        },
        "metrics": {
            "discount_rows": {"label": "Discount rows", "expr": "count(*)::integer"},
            "orders": {"label": "Orders", "expr": "count(distinct order_id)::integer"},
            "discount_sum": {"label": "Discount", "expr": "sum(discount_sum)::numeric(14,2)"},
        },
        "filters": ["business_date", "organization_name", "order_source", "discount_name", "discount_type", "is_manual"],
    },
    "delivery": {
        "label": "Delivery",
        "view": "dl_olap_delivery",
        "description": "Delivery statuses, zones, timings, couriers.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "organization_name": "Branch",
            "order_source": "Order source",
            "delivery_zone": "Delivery zone",
            "delivery_status": "Delivery status",
            "courier_name": "Courier",
            "is_late": "Late",
            "is_active": "Active",
        },
        "metrics": {
            "deliveries": {"label": "Deliveries", "expr": "count(*)::integer"},
            "orders": {"label": "Orders", "expr": "count(distinct order_id)::integer"},
            "late_deliveries": {"label": "Late deliveries", "expr": "count(*) filter (where is_late)::integer"},
            "late_rate": {"label": "Late rate", "expr": "(count(*) filter (where is_late)::numeric / nullif(count(*), 0))::numeric(14,6)"},
            "avg_delivery_minutes": {"label": "Avg delivery min", "expr": "avg(delivery_minutes)::numeric(14,2)"},
            "avg_delay_minutes": {"label": "Avg delay min", "expr": "avg(delay_minutes)::numeric(14,2)"},
            "avg_cooking_minutes": {"label": "Avg cooking min", "expr": "avg(cooking_minutes)::numeric(14,2)"},
        },
        "filters": ["business_date", "organization_name", "order_source", "delivery_zone", "delivery_status", "courier_name", "is_late", "is_active"],
    },
    "customers": {
        "label": "Customers",
        "view": "dl_olap_customers",
        "description": "Customer order rows with lifetime customer metrics.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "organization_name": "Branch",
            "order_source": "Order source",
            "customer_type": "Customer type",
            "gender": "Gender",
            "is_first_order": "First order",
            "is_repeat_order": "Repeat order",
            "is_delivery": "Delivery",
        },
        "metrics": {
            "customers": {"label": "Customers", "expr": "count(distinct customer_id)::integer"},
            "orders": {"label": "Orders", "expr": "count(distinct order_id)::integer"},
            "net_revenue": {"label": "Net revenue", "expr": "sum(net_revenue)::numeric(14,2)"},
            "avg_check": {"label": "Avg check", "expr": "(sum(net_revenue) / nullif(count(distinct order_id), 0))::numeric(14,2)"},
            "new_customers": {"label": "New customers", "expr": "count(distinct customer_id) filter (where is_first_order)::integer"},
            "repeat_customers": {"label": "Repeat customers", "expr": "count(distinct customer_id) filter (where is_repeat_order)::integer"},
            "avg_lifetime_orders": {"label": "Avg lifetime orders", "expr": "avg(customer_orders_lifetime)::numeric(14,2)"},
            "avg_lifetime_revenue": {"label": "Avg lifetime revenue", "expr": "avg(customer_revenue_lifetime)::numeric(14,2)"},
        },
        "filters": ["business_date", "organization_name", "order_source", "customer_type", "gender", "is_first_order", "is_repeat_order", "is_delivery", "customer_id", "phone_hash"],
    },
    "operations": {
        "label": "Operations",
        "view": "dl_olap_operations",
        "description": "Losses/events: cancellations, refunds, manual discount signals, deletions.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "organization_name": "Branch",
            "order_source": "Order source",
            "operation_type": "Operation type",
            "operation_reason": "Reason",
            "employee_name": "Employee",
            "employee_role": "Employee role",
        },
        "metrics": {
            "operations": {"label": "Operations", "expr": "count(*)::integer"},
            "orders": {"label": "Orders", "expr": "count(distinct order_id)::integer"},
            "operation_sum": {"label": "Operation sum", "expr": "sum(operation_sum)::numeric(14,2)"},
        },
        "filters": ["business_date", "organization_name", "order_source", "operation_type", "operation_reason", "employee_name", "employee_role"],
    },
    "staff": {
        "label": "Staff",
        "view": "dl_olap_staff",
        "description": "Staff revenue/order counts from OLAP staff fields.",
        "dimensions": {
            **COMMON_TIME_DIMENSIONS,
            "organization_name": "Branch",
            "staff_role": "Staff role",
            "staff_name": "Staff name",
        },
        "metrics": {
            "orders": {"label": "Orders", "expr": "sum(orders_count)::integer"},
            "net_revenue": {"label": "Net revenue", "expr": "sum(net_revenue)::numeric(14,2)"},
            "avg_check": {"label": "Avg check", "expr": "(sum(net_revenue) / nullif(sum(orders_count), 0))::numeric(14,2)"},
        },
        "filters": ["business_date", "organization_name", "staff_role", "staff_name"],
    },
}

SAVED_REPORTS: list[dict[str, Any]] = [
    {
        "id": "revenue_by_day",
        "name": "Выручка по дням",
        "kind": "Продажи",
        "description": "Динамика выручки и заказов по дням.",
        "config": {"subject": "sales", "dimensions": ["business_date"], "metrics": ["net_revenue", "orders"], "order_by": "business_date", "order_dir": "desc", "limit": 90},
    },
    {
        "id": "revenue_by_branch",
        "name": "Выручка по филиалам",
        "kind": "Продажи",
        "description": "Рейтинг филиалов по выручке и заказам.",
        "config": {"subject": "sales", "dimensions": ["organization_name"], "metrics": ["net_revenue", "orders", "avg_check"], "order_by": "net_revenue", "order_dir": "desc", "limit": 100},
    },
    {
        "id": "top_categories",
        "name": "Категории по выручке",
        "kind": "Товары",
        "description": "Категории меню по выручке, количеству и заказам.",
        "config": {"subject": "products", "dimensions": ["category_name"], "metrics": ["net_revenue", "quantity", "orders"], "order_by": "net_revenue", "order_dir": "desc", "limit": 100},
    },
    {
        "id": "top_products",
        "name": "Товары по выручке",
        "kind": "Товары",
        "description": "Топ товаров с количеством, выручкой и средней ценой.",
        "config": {"subject": "products", "dimensions": ["product_name", "category_name"], "metrics": ["net_revenue", "quantity", "avg_price"], "order_by": "net_revenue", "order_dir": "desc", "limit": 200},
    },
    {
        "id": "payments_by_type",
        "name": "Оплаты по типам",
        "kind": "Финансы",
        "description": "Сумма оплат по типам и группам.",
        "config": {"subject": "payments", "dimensions": ["payment_group", "payment_type"], "metrics": ["payment_sum", "orders"], "order_by": "payment_sum", "order_dir": "desc", "limit": 100},
    },
    {
        "id": "delivery_sla",
        "name": "SLA доставки",
        "kind": "Доставка",
        "description": "Опоздания, среднее время доставки и зоны.",
        "config": {"subject": "delivery", "dimensions": ["organization_name", "delivery_zone"], "metrics": ["deliveries", "late_rate", "avg_delivery_minutes"], "order_by": "late_rate", "order_dir": "desc", "limit": 100},
    },
    {
        "id": "customer_repeat_orders",
        "name": "Повторные клиенты",
        "kind": "Клиенты",
        "description": "Новые и повторные клиенты по дням.",
        "config": {"subject": "customers", "dimensions": ["business_date"], "metrics": ["customers", "new_customers", "repeat_customers", "net_revenue"], "order_by": "business_date", "order_dir": "desc", "limit": 90},
    },
]


OPS = {
    "eq": "=",
    "neq": "<>",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}


def json_default(value: Any) -> str:
    return str(value)


def connect():
    return psycopg.connect(database_url(), row_factory=dict_row)


def subject_schema() -> dict[str, Any]:
    result = {}
    for key, cfg in SUBJECTS.items():
        filter_labels = {
            name: cfg["dimensions"].get(name, name.replace("_", " ").title())
            for name in cfg["filters"]
        }
        result[key] = {
            "label": cfg["label"],
            "description": cfg["description"],
            "dimensions": cfg["dimensions"],
            "metrics": {name: metric["label"] for name, metric in cfg["metrics"].items()},
            "filters": filter_labels,
        }
    return result


def fetch_all(cur: psycopg.Cursor[Any], sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    cur.execute(sql, params or [])
    return list(cur.fetchall())


def fetch_one(cur: psycopg.Cursor[Any], sql: str, params: list[Any] | None = None) -> dict[str, Any]:
    cur.execute(sql, params or [])
    row = cur.fetchone()
    return dict(row or {})


def run_dashboard() -> dict[str, Any]:
    with connect() as conn:
        with conn.cursor() as cur:
            bounds = fetch_one(
                cur,
                """
                SELECT
                    max(business_date)::date AS date_to,
                    (max(business_date)::date - interval '29 day')::date AS date_from
                FROM dl_olap_sales
                """,
            )
            date_from = bounds.get("date_from")
            date_to = bounds.get("date_to")
            if not date_to:
                return {"date_from": None, "date_to": None, "kpis": [], "widgets": []}

            params = [date_from, date_to]
            kpi = fetch_one(
                cur,
                """
                SELECT
                    sum(net_revenue)::numeric(14,2) AS net_revenue,
                    sum(orders_count)::integer AS orders_count,
                    (sum(net_revenue) / nullif(sum(orders_count), 0))::numeric(14,2) AS avg_check,
                    (sum(discount_sum) / nullif(sum(gross_revenue), 0))::numeric(14,6) AS discount_share,
                    sum(refund_sum)::numeric(14,2) AS refund_sum
                FROM dl_olap_sales
                WHERE business_date BETWEEN %s AND %s
                """,
                params,
            )
            trend = fetch_all(
                cur,
                """
                SELECT business_date, sum(net_revenue)::numeric(14,2) AS net_revenue, sum(orders_count)::integer AS orders_count
                FROM dl_olap_sales
                WHERE business_date BETWEEN %s AND %s
                GROUP BY business_date
                ORDER BY business_date
                """,
                params,
            )
            branches = fetch_all(
                cur,
                """
                SELECT organization_name, sum(net_revenue)::numeric(14,2) AS net_revenue, sum(orders_count)::integer AS orders_count
                FROM dl_olap_sales
                WHERE business_date BETWEEN %s AND %s
                GROUP BY organization_name
                ORDER BY net_revenue DESC NULLS LAST
                LIMIT 10
                """,
                params,
            )
            categories = fetch_all(
                cur,
                """
                SELECT COALESCE(NULLIF(category_name, ''), 'Без категории') AS category_name,
                       sum(net_revenue)::numeric(14,2) AS net_revenue,
                       sum(quantity)::numeric(14,3) AS quantity
                FROM dl_olap_products
                WHERE business_date BETWEEN %s AND %s
                GROUP BY COALESCE(NULLIF(category_name, ''), 'Без категории')
                ORDER BY net_revenue DESC NULLS LAST
                LIMIT 10
                """,
                params,
            )
            products = fetch_all(
                cur,
                """
                SELECT product_name, COALESCE(NULLIF(category_name, ''), 'Без категории') AS category_name,
                       sum(net_revenue)::numeric(14,2) AS net_revenue,
                       sum(quantity)::numeric(14,3) AS quantity
                FROM dl_olap_products
                WHERE business_date BETWEEN %s AND %s
                GROUP BY product_name, COALESCE(NULLIF(category_name, ''), 'Без категории')
                ORDER BY net_revenue DESC NULLS LAST
                LIMIT 10
                """,
                params,
            )
            payments = fetch_all(
                cur,
                """
                SELECT COALESCE(NULLIF(payment_group, ''), 'unknown') AS payment_group,
                       sum(payment_sum)::numeric(14,2) AS payment_sum,
                       count(distinct order_id)::integer AS orders_count
                FROM dl_olap_payments
                WHERE business_date BETWEEN %s AND %s
                GROUP BY COALESCE(NULLIF(payment_group, ''), 'unknown')
                ORDER BY payment_sum DESC NULLS LAST
                LIMIT 10
                """,
                params,
            )
            delivery = fetch_all(
                cur,
                """
                SELECT organization_name,
                       count(*)::integer AS deliveries,
                       count(*) FILTER (WHERE is_late)::integer AS late_deliveries,
                       (count(*) FILTER (WHERE is_late)::numeric / nullif(count(*), 0))::numeric(14,6) AS late_rate,
                       avg(delivery_minutes)::numeric(14,2) AS avg_delivery_minutes
                FROM dl_olap_delivery
                WHERE business_date BETWEEN %s AND %s
                GROUP BY organization_name
                ORDER BY late_rate DESC NULLS LAST
                LIMIT 10
                """,
                params,
            )
            customers = fetch_one(
                cur,
                """
                SELECT
                    count(distinct customer_id)::integer AS customers,
                    count(distinct customer_id) FILTER (WHERE is_first_order)::integer AS new_customers,
                    count(distinct customer_id) FILTER (WHERE is_repeat_order)::integer AS repeat_customers
                FROM dl_olap_customers
                WHERE business_date BETWEEN %s AND %s
                """,
                params,
            )

    return {
        "date_from": date_from,
        "date_to": date_to,
        "kpis": [
            {"id": "net_revenue", "label": "Выручка", "value": kpi.get("net_revenue"), "format": "money"},
            {"id": "orders_count", "label": "Заказы", "value": kpi.get("orders_count"), "format": "integer"},
            {"id": "avg_check", "label": "Средний чек", "value": kpi.get("avg_check"), "format": "money"},
            {"id": "discount_share", "label": "Скидка %", "value": kpi.get("discount_share"), "format": "percent"},
            {"id": "refund_sum", "label": "Возвраты", "value": kpi.get("refund_sum"), "format": "money"},
            {"id": "customers", "label": "Клиенты", "value": customers.get("customers"), "format": "integer"},
            {"id": "new_customers", "label": "Новые клиенты", "value": customers.get("new_customers"), "format": "integer"},
            {"id": "repeat_customers", "label": "Повторные клиенты", "value": customers.get("repeat_customers"), "format": "integer"},
        ],
        "widgets": [
            {"id": "trend", "title": "Выручка по дням", "type": "line", "label": "business_date", "metric": "net_revenue", "rows": trend},
            {"id": "branches", "title": "Филиалы по выручке", "type": "table", "rows": branches},
            {"id": "categories", "title": "Категории", "type": "table", "rows": categories},
            {"id": "products", "title": "Товары", "type": "table", "rows": products},
            {"id": "payments", "title": "Оплаты", "type": "table", "rows": payments},
            {"id": "delivery", "title": "Доставка и SLA", "type": "table", "rows": delivery},
        ],
    }


def validate_list(values: Any, allowed: dict[str, Any], default: list[str]) -> list[str]:
    if not isinstance(values, list):
        return default
    clean = [v for v in values if isinstance(v, str) and v in allowed]
    return clean or default


def filter_sql(filters: Any, allowed_fields: set[str], params: list[Any]) -> list[str]:
    clauses: list[str] = []
    if not isinstance(filters, list):
        return clauses
    for item in filters:
        if not isinstance(item, dict):
            continue
        field = item.get("field")
        op = item.get("op")
        value = item.get("value")
        value2 = item.get("value2")
        if field not in allowed_fields or not op:
            continue
        if op in OPS:
            if value in (None, ""):
                continue
            params.append(value)
            clauses.append(f"{field} {OPS[op]} %s")
        elif op == "contains":
            if value in (None, ""):
                continue
            params.append(f"%{value}%")
            clauses.append(f"{field} ILIKE %s")
        elif op == "not_contains":
            if value in (None, ""):
                continue
            params.append(f"%{value}%")
            clauses.append(f"{field} NOT ILIKE %s")
        elif op == "between":
            if value in (None, "") or value2 in (None, ""):
                continue
            params.extend([value, value2])
            clauses.append(f"{field} BETWEEN %s AND %s")
        elif op == "is_null":
            clauses.append(f"{field} IS NULL")
        elif op == "not_null":
            clauses.append(f"{field} IS NOT NULL")
    return clauses


def build_report(payload: dict[str, Any], csv_mode: bool = False) -> tuple[str, list[Any]]:
    subject_key = payload.get("subject", "sales")
    if subject_key not in SUBJECTS:
        raise ValueError("Unknown subject")
    cfg = SUBJECTS[subject_key]
    dimensions = validate_list(payload.get("dimensions"), cfg["dimensions"], ["business_date"] if "business_date" in cfg["dimensions"] else [])
    metrics = validate_list(payload.get("metrics"), cfg["metrics"], [next(iter(cfg["metrics"]))])
    limit = int(payload.get("limit") or 50)
    limit = max(1, min(limit, 10000 if csv_mode else 1000))

    select_parts = [dim for dim in dimensions]
    group_parts = [dim for dim in dimensions]
    for metric in metrics:
        select_parts.append(f"{cfg['metrics'][metric]['expr']} AS {metric}")

    params: list[Any] = []
    allowed_filters = set(cfg["filters"])
    clauses = filter_sql(payload.get("filters"), allowed_filters, params)

    sql = f"SELECT {', '.join(select_parts)} FROM {cfg['view']}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    if group_parts:
        sql += " GROUP BY " + ", ".join(group_parts)

    order_field = payload.get("order_by")
    order_dir = "ASC" if str(payload.get("order_dir", "desc")).lower() == "asc" else "DESC"
    allowed_order = set(dimensions) | set(metrics)
    if isinstance(order_field, str) and order_field in allowed_order:
        sql += f" ORDER BY {order_field} {order_dir} NULLS LAST"
    elif metrics:
        sql += f" ORDER BY {metrics[0]} DESC NULLS LAST"
    sql += f" LIMIT {limit}"
    return sql, params


def run_report(payload: dict[str, Any], csv_mode: bool = False) -> dict[str, Any]:
    sql, params = build_report(payload, csv_mode=csv_mode)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description]
    return {"columns": columns, "rows": rows, "sql": sql}


def run_customer_segment(payload: dict[str, Any]) -> dict[str, Any]:
    mode = payload.get("mode", "product")
    field = "product_name" if mode == "product" else "category_name"
    term = str(payload.get("term") or "").strip()
    if not term:
        raise ValueError("Product/category filter is required")
    lifetime_op = payload.get("lifetime_op", "eq")
    if lifetime_op not in OPS:
        lifetime_op = "eq"
    lifetime_count = int(payload.get("lifetime_count") or 1)
    min_orders = int(payload.get("min_orders") or 1)
    date_from = payload.get("date_from")
    date_to = payload.get("date_to")
    limit = max(1, min(int(payload.get("limit") or 500), 5000))

    clauses = [
        f"{field} ILIKE %s",
        f"product_orders_lifetime {OPS[lifetime_op]} %s",
    ]
    params: list[Any] = [f"%{term}%", lifetime_count]
    if date_from:
        clauses.append("business_date >= %s")
        params.append(date_from)
    if date_to:
        clauses.append("business_date <= %s")
        params.append(date_to)

    params.extend([min_orders, limit])
    sql = f"""
        WITH filtered AS (
            SELECT *
            FROM dl_report_customer_segments
            WHERE {" AND ".join(clauses)}
        ),
        selected AS (
            SELECT
                customer_id,
                max(phone_hash) AS phone_hash,
                count(DISTINCT product_id)::integer AS selected_products_count,
                string_agg(DISTINCT product_name, ', ' ORDER BY product_name) AS selected_products,
                string_agg(DISTINCT COALESCE(category_name, ''), ', ' ORDER BY COALESCE(category_name, '')) AS selected_categories,
                sum(product_orders_lifetime)::integer AS selected_orders_lifetime,
                sum(items_qty_lifetime)::numeric(14,3) AS selected_qty_lifetime,
                sum(product_revenue_lifetime)::numeric(14,2) AS selected_revenue_lifetime,
                max(customer_orders_lifetime)::integer AS customer_orders_lifetime,
                max(customer_revenue_lifetime)::numeric(14,2) AS customer_revenue_lifetime
            FROM (
                SELECT DISTINCT
                    customer_id,
                    phone_hash,
                    product_id,
                    product_name,
                    category_name,
                    product_orders_lifetime,
                    items_qty_lifetime,
                    product_revenue_lifetime,
                    customer_orders_lifetime,
                    customer_revenue_lifetime
                FROM filtered
            ) x
            GROUP BY customer_id
        ),
        period_orders AS (
            SELECT DISTINCT
                customer_id,
                period_order_id,
                period_order_revenue,
                business_date
            FROM filtered
        ),
        period AS (
            SELECT
                customer_id,
                count(period_order_id)::integer AS orders_in_period,
                sum(period_order_revenue)::numeric(14,2) AS revenue_in_period,
                min(business_date) AS first_order_in_period,
                max(business_date) AS last_order_in_period
            FROM period_orders
            GROUP BY customer_id
        )
        SELECT
            s.customer_id,
            s.phone_hash,
            s.selected_products_count,
            s.selected_products,
            s.selected_categories,
            s.selected_orders_lifetime,
            s.selected_qty_lifetime,
            s.selected_revenue_lifetime,
            p.orders_in_period,
            p.revenue_in_period,
            p.first_order_in_period,
            p.last_order_in_period,
            s.customer_orders_lifetime,
            s.customer_revenue_lifetime
        FROM selected s
        JOIN period p ON p.customer_id = s.customer_id
        WHERE p.orders_in_period >= %s
        ORDER BY p.orders_in_period DESC, p.revenue_in_period DESC NULLS LAST
        LIMIT %s
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description]
    return {"columns": columns, "rows": rows, "sql": sql}


class Handler(BaseHTTPRequestHandler):
    server_version = "IikoReportBuilder/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = 400) -> None:
        self.send_json({"error": message}, status=status)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            self.send_json(run_dashboard())
            return
        if path == "/api/schema":
            self.send_json({"subjects": subject_schema()})
            return
        if path == "/api/saved-reports":
            self.send_json({"reports": SAVED_REPORTS})
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path == "/" or path == "/index.html":
            self.serve_static("index.html")
            return
        if path.startswith("/static/"):
            self.serve_static(path.removeprefix("/static/"))
            return
        self.send_error_json("Not found", status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/report":
                self.send_json(run_report(payload))
                return
            if path == "/api/customer-segment":
                self.send_json(run_customer_segment(payload))
                return
            if path == "/api/export.csv":
                data = run_report(payload, csv_mode=True)
                self.send_csv(data["columns"], data["rows"], "report.csv")
                return
            if path == "/api/customer-segment.csv":
                data = run_customer_segment(payload)
                self.send_csv(data["columns"], data["rows"], "customer_segment.csv")
                return
        except Exception as exc:
            self.send_error_json(str(exc), status=400)
            return
        self.send_error_json("Not found", status=404)

    def serve_static(self, name: str) -> None:
        safe_name = Path(name)
        if safe_name.is_absolute() or ".." in safe_name.parts:
            self.send_error_json("Invalid path", status=400)
            return
        path = STATIC_DIR / safe_name
        if not path.exists() or not path.is_file():
            self.send_error_json("Not found", status=404)
            return
        content_type = "text/plain; charset=utf-8"
        if path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_csv(self, columns: list[str], rows: list[dict[str, Any]], filename: str) -> None:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col) for col in columns})
        body = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("REPORT_BUILDER_HOST", "127.0.0.1")
    port = int(os.environ.get("REPORT_BUILDER_PORT", "8088"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Report builder listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
