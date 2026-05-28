#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
MSK = dt.timezone(dt.timedelta(hours=3))


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1].replace('\\"', '"')
        os.environ.setdefault(key, value)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def top_shape(value: Any, depth: int = 2) -> Any:
    if depth <= 0:
        if isinstance(value, dict):
            return "{...}"
        if isinstance(value, list):
            return f"[{len(value)}]"
        return type(value).__name__
    if isinstance(value, dict):
        return {str(k): top_shape(v, depth - 1) for k, v in list(value.items())[:40]}
    if isinstance(value, list):
        return [top_shape(value[0], depth - 1)] if value else []
    return type(value).__name__


def print_result(name: str, ok: bool, detail: dict[str, Any]) -> None:
    print(json.dumps({"check": name, "ok": ok, **detail}, ensure_ascii=False, indent=2))


def nested_get(data: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        cur: Any = data
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None:
            return cur
    return None


def extract_orders(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    groups = payload.get("ordersByOrganizations")
    if isinstance(groups, list):
        out: list[dict[str, Any]] = []
        for group in groups:
            if isinstance(group, dict) and isinstance(group.get("orders"), list):
                out.extend(x for x in group["orders"] if isinstance(x, dict))
        return out
    for key in ("orders", "deliveries", "items"):
        if isinstance(payload.get(key), list):
            return [x for x in payload[key] if isinstance(x, dict)]
    return []


class Discover:
    def __init__(self) -> None:
        load_dotenv(REPO_ROOT / ".env")
        load_dotenv(REPO_ROOT / ".credentials.env")
        self.cloud_base = (os.environ.get("IIKO_CLOUD_API_BASE_URL") or os.environ.get("IIKO_API_BASE_URL") or "https://api-ru.iiko.services").rstrip("/")
        self.api_login = os.environ.get("IIKO_API_LOGIN") or os.environ.get("IIKO_API_KEY") or ""
        self.timeout = max(10, int(os.environ.get("IIKO_TIMEOUT_SECONDS", "60")))
        self.verify_ssl = env_bool("IIKO_VERIFY_SSL", True)
        self.olap_base = os.environ.get("IIKO_OLAP_SERVER_URL", "").rstrip("/")
        self.olap_login = os.environ.get("IIKO_OLAP_LOGIN", "")
        self.olap_password = os.environ.get("IIKO_OLAP_PASSWORD", "")
        self.olap_verify_ssl = env_bool("IIKO_OLAP_VERIFY_SSL", True)
        self.olap_date_field = os.environ.get("IIKO_OLAP_DATE_FIELD", "OpenDate.Typed") or "OpenDate.Typed"
        self.session = requests.Session()
        self.token_value = ""

    def cloud_token(self) -> str:
        if self.token_value:
            return self.token_value
        response = self.session.post(
            f"{self.cloud_base}/api/1/access_token",
            json={"apiLogin": self.api_login},
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        payload = response.json()
        self.token_value = str(payload["token"])
        return self.token_value

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.cloud_token()}", "Content-Type": "application/json"}

    def cloud_get(self, name: str, path: str) -> Any:
        response = self.session.get(f"{self.cloud_base}{path}", headers=self.headers(), timeout=self.timeout, verify=self.verify_ssl)
        detail: dict[str, Any] = {"status": response.status_code}
        try:
            payload = response.json()
            detail["shape"] = top_shape(payload)
        except Exception:
            payload = response.text[:500]
            detail["text_prefix"] = payload
        print_result(name, response.ok, detail)
        response.raise_for_status()
        return payload

    def cloud_post(self, name: str, path: str, body: dict[str, Any], raise_error: bool = False) -> Any:
        response = self.session.post(f"{self.cloud_base}{path}", headers=self.headers(), json=body, timeout=self.timeout, verify=self.verify_ssl)
        detail: dict[str, Any] = {"status": response.status_code}
        try:
            payload = response.json()
            detail["shape"] = top_shape(payload)
        except Exception:
            payload = response.text[:500]
            detail["text_prefix"] = payload
        print_result(name, response.ok, detail)
        if raise_error:
            response.raise_for_status()
        return payload

    @staticmethod
    def org_number(org: dict[str, Any]) -> int | None:
        for raw in (org.get("name"), org.get("code")):
            match = re.match(r"^\s*(\d+)", str(raw or ""))
            if match:
                return int(match.group(1))
        return None

    def olap_auth(self) -> str:
        response = requests.get(
            f"{self.olap_base}/resto/api/auth",
            params={"login": self.olap_login, "pass": hashlib.sha1(self.olap_password.encode("utf-8")).hexdigest()},
            timeout=self.timeout,
            verify=self.olap_verify_ssl,
        )
        print_result("olap_auth", response.ok, {"status": response.status_code})
        response.raise_for_status()
        return response.text.strip()

    def olap_logout(self, key: str) -> None:
        try:
            requests.get(f"{self.olap_base}/resto/api/logout", params={"key": key}, timeout=10, verify=self.olap_verify_ssl)
        except Exception:
            pass

    def olap_report(self, key: str, name: str, body: dict[str, Any]) -> Any:
        response = requests.post(
            f"{self.olap_base}/resto/api/v2/reports/olap",
            params={"key": key},
            json=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=max(self.timeout, 90),
            verify=self.olap_verify_ssl,
        )
        detail: dict[str, Any] = {"status": response.status_code}
        try:
            payload = response.json()
            detail["shape"] = top_shape(payload)
            rows = payload.get("data") if isinstance(payload, dict) else None
            if isinstance(rows, list) and rows:
                detail["first_row_keys"] = sorted(str(k) for k in rows[0].keys())
                detail["rows"] = len(rows)
            elif isinstance(rows, list):
                detail["rows"] = 0
        except Exception:
            payload = response.text[:500]
            detail["text_prefix"] = payload
        print_result(name, response.ok, detail)
        return payload

    def olap_columns(self, key: str, report_type: str) -> dict[str, dict[str, Any]]:
        response = requests.get(
            f"{self.olap_base}/resto/api/v2/reports/olap/columns",
            params={"key": key, "reportType": report_type},
            timeout=max(self.timeout, 90),
            verify=self.olap_verify_ssl,
        )
        detail: dict[str, Any] = {"status": response.status_code, "reportType": report_type}
        payload: Any
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail["fields_count"] = len(payload)
                detail["sample_fields"] = sorted(payload.keys())[:20]
        except Exception:
            payload = response.text[:500]
            detail["text_prefix"] = payload
        print_result(f"olap_columns_{report_type.lower()}", response.ok, detail)
        response.raise_for_status()
        return {str(k): v for k, v in payload.items() if isinstance(v, dict)} if isinstance(payload, dict) else {}

    @staticmethod
    def pick_fields(columns: dict[str, dict[str, Any]], patterns: list[str], *, grouping: bool = False, aggregation: bool = False) -> list[str]:
        out: list[str] = []
        lowered = [(field, (field + " " + str(meta.get("name") or "")).lower(), meta) for field, meta in columns.items()]
        for pattern in patterns:
            rx = re.compile(pattern, re.I)
            for field, haystack, meta in lowered:
                if field in out or not rx.search(haystack):
                    continue
                if grouping and not meta.get("groupingAllowed"):
                    continue
                if aggregation and not meta.get("aggregationAllowed"):
                    continue
                out.append(field)
        return out

    def run(self) -> int:
        if not self.api_login:
            raise RuntimeError("IIKO_API_LOGIN is empty")
        org_payload = self.cloud_get("cloud_organizations", "/api/1/organizations")
        orgs = org_payload.get("organizations") if isinstance(org_payload, dict) else org_payload
        orgs = [x for x in orgs or [] if isinstance(x, dict) and x.get("id")]
        if not orgs:
            raise RuntimeError("No organizations returned from iikoCloud")
        numbered_orgs = [org for org in orgs if self.org_number(org) is not None]
        probe_orgs = numbered_orgs[:5] or orgs[:5]
        org_id = str(probe_orgs[0]["id"])
        today = dt.datetime.now(MSK).date()
        start = dt.datetime.combine(today, dt.time(0, 0, 0)).isoformat(timespec="milliseconds")
        end = dt.datetime.combine(today, dt.time(23, 59, 59)).isoformat(timespec="milliseconds")

        for index, org in enumerate(probe_orgs, 1):
            payload = self.cloud_post(f"cloud_nomenclature_probe_{index}", "/api/1/nomenclature", {"organizationId": str(org["id"])})
            if isinstance(payload, dict):
                print_result(
                    f"cloud_nomenclature_counts_{index}",
                    True,
                    {
                        "org_name": str(org.get("name") or ""),
                        "groups": len(payload.get("groups") or []),
                        "productCategories": len(payload.get("productCategories") or []),
                        "products": len(payload.get("products") or []),
                        "sizes": len(payload.get("sizes") or []),
                    },
                )
        self.cloud_post("cloud_terminal_groups", "/api/1/terminal_groups", {"organizationIds": [org_id], "includeDisabled": True})
        self.cloud_post("cloud_stop_lists", "/api/1/stop_lists", {"organizationIds": [org_id]})
        self.cloud_post(
            "cloud_deliveries_today_closed",
            "/api/1/deliveries/by_delivery_date_and_status",
            {"organizationIds": [org_id], "deliveryDateFrom": start, "deliveryDateTo": end, "statuses": ["closed"]},
        )
        delivery_payload = self.cloud_post(
            "cloud_deliveries_today_all_statuses",
            "/api/1/deliveries/by_delivery_date_and_status",
            {
                "organizationIds": [org_id],
                "deliveryDateFrom": start,
                "deliveryDateTo": end,
                "statuses": ["Unconfirmed", "WaitCooking", "ReadyForCooking", "CookingStarted", "CookingCompleted", "Waiting", "OnWay", "Delivered", "Closed", "Cancelled", "closed"],
            },
        )
        orders = extract_orders(delivery_payload)
        first_order = orders[0] if orders else {}
        order = first_order.get("order") if isinstance(first_order.get("order"), dict) else first_order
        order_id = nested_get(order, "id", "orderId") or nested_get(first_order, "id", "orderId")
        if order_id:
            self.cloud_post(
                "cloud_delivery_by_id",
                "/api/1/deliveries/by_id",
                {"organizationId": org_id, "orderIds": [str(order_id)]},
            )
        else:
            print_result("cloud_delivery_by_id", False, {"reason": "no order id found in today's delivery probe"})

        customer_phone = os.environ.get("IIKO_DISCOVERY_CUSTOMER_PHONE", "").strip()
        if not customer_phone:
            customer_phone = str(nested_get(order, "phone", "customer.phone", "customer.phoneNumber") or "").strip()
            if customer_phone:
                print_result("cloud_customer_phone_probe", True, {"source": "delivery payload", "phone_masked": True})
            else:
                print_result("cloud_customer_phone_probe", False, {"reason": "no phone found in delivery payload"})
        if customer_phone:
            self.cloud_post(
                "cloud_loyalty_customer_info_by_phone",
                "/api/1/loyalty/iiko/customer/info",
                {"type": "phone", "phone": customer_phone, "organizationId": org_id},
            )
            self.cloud_post(
                "cloud_deliveries_by_delivery_date_and_phone",
                "/api/1/deliveries/by_delivery_date_and_phone",
                {"organizationIds": [org_id], "deliveryDateFrom": start, "deliveryDateTo": end, "phone": customer_phone},
            )
        else:
            print_result(
                "cloud_loyalty_customer_info_by_phone",
                False,
                {"reason": "set IIKO_DISCOVERY_CUSTOMER_PHONE or use an order payload with phone"},
            )
        self.cloud_post("cloud_loyalty_customer_categories", "/api/1/loyalty/iiko/customer_category", {"organizationId": org_id})

        if self.olap_base and self.olap_login and self.olap_password:
            key = self.olap_auth()
            try:
                sales_columns = self.olap_columns(key, "SALES")
                transactions_columns = self.olap_columns(key, "TRANSACTIONS")
                deliveries_columns = self.olap_columns(key, "DELIVERIES")
                for name, columns, patterns in [
                    ("olap_sales_payment_field_candidates", sales_columns, [r"PayTypes?", r"payment|оплат"]),
                    ("olap_sales_discount_field_candidates", sales_columns, [r"Discount|скид|promo|акци"]),
                    ("olap_sales_staff_field_candidates", sales_columns, [r"Cashier|Waiter|Employee|Courier|касс|офици|сотруд|курьер"]),
                    ("olap_transactions_writeoff_field_candidates", transactions_columns, [r"Writeoff|списан|Deletion|Removal|удален|причин"]),
                    ("olap_deliveries_field_candidates", deliveries_columns, [r"Delivery|Courier|Phone|Status|достав|курьер|телефон|статус"]),
                ]:
                    candidates = self.pick_fields(columns, patterns, grouping=True)[:40]
                    print_result(name, bool(candidates), {"fields": candidates})

                date_from = (today - dt.timedelta(days=1)).isoformat()
                date_to = today.isoformat()
                base_filter = {
                    self.olap_date_field: {
                        "filterType": "DateRange",
                        "periodType": "CUSTOM",
                        "from": date_from,
                        "to": date_to,
                        "includeLow": True,
                        "includeHigh": True,
                    }
                }
                reports: list[tuple[str, str, list[str], list[str], dict[str, Any]]] = [
                    (
                        "SALES",
                        "olap_sales_daily_probe",
                        [self.olap_date_field, "Department.Code", "Department", "OriginName"],
                        [x for x in ["UniqOrderId.OrdersCount", "DishAmountInt", "DishSumInt", "DiscountSum", "DishDiscountSumInt", "DishReturnSum"] if x in sales_columns],
                        base_filter,
                    ),
                    (
                        "SALES",
                        "olap_sales_product_probe",
                        [self.olap_date_field, "Department.Code", "Department", "DishId", "DishName", "DishCategory"],
                        [x for x in ["UniqOrderId.OrdersCount", "DishAmountInt", "DishSumInt", "DiscountSum", "DishDiscountSumInt", "ProductCostBase.ProductCost"] if x in sales_columns],
                        base_filter,
                    ),
                ]
                for payment_field in self.pick_fields(sales_columns, [r"^PayTypes?$", r"payment|оплат"], grouping=True)[:1]:
                    reports.append(("SALES", "olap_sales_payment_probe", [self.olap_date_field, "Department.Code", "Department", payment_field], [x for x in ["UniqOrderId.OrdersCount", "DishSumInt"] if x in sales_columns], base_filter))
                for discount_field in self.pick_fields(sales_columns, [r"Discount|скид|promo|акци"], grouping=True)[:3]:
                    reports.append(("SALES", "olap_sales_discount_probe_" + discount_field, [self.olap_date_field, "Department.Code", "Department", discount_field], [x for x in ["UniqOrderId.OrdersCount", "DiscountSum", "DishDiscountSumInt"] if x in sales_columns], base_filter))
                for staff_field in self.pick_fields(sales_columns, [r"Cashier|Waiter|Employee|касс|офици|сотруд"], grouping=True)[:3]:
                    reports.append(("SALES", "olap_sales_staff_probe_" + staff_field, [self.olap_date_field, "Department.Code", "Department", staff_field], [x for x in ["UniqOrderId.OrdersCount", "DishDiscountSumInt"] if x in sales_columns], base_filter))
                trx_date_fields = self.pick_fields(transactions_columns, [r"date|time|дата"], grouping=True, aggregation=False)
                trx_date_field = self.olap_date_field if self.olap_date_field in transactions_columns else (trx_date_fields[0] if trx_date_fields else "")
                trx_filter = {
                    trx_date_field: {
                        "filterType": "DateRange",
                        "periodType": "CUSTOM",
                        "from": date_from,
                        "to": date_to,
                        "includeLow": True,
                        "includeHigh": True,
                    }
                } if trx_date_field else {}
                for writeoff_field in self.pick_fields(transactions_columns, [r"Writeoff|списан|Deletion|Removal|удален|причин"], grouping=True)[:3]:
                    aggs = self.pick_fields(transactions_columns, [r"sum|amount|quantity|cost|сумм|кол"], aggregation=True)[:3]
                    if trx_date_field and aggs:
                        reports.append(("TRANSACTIONS", "olap_transactions_writeoff_probe_" + writeoff_field, [trx_date_field, writeoff_field], aggs, trx_filter))

                for report_type, name, group_fields, aggregate_fields, filters in reports:
                    if not group_fields or not aggregate_fields:
                        print_result(name, False, {"reason": "no documented/available fields for this report"})
                        continue
                    report_columns = sales_columns if report_type == "SALES" else transactions_columns if report_type == "TRANSACTIONS" else deliveries_columns
                    missing_group = [field for field in group_fields if field not in report_columns]
                    if missing_group:
                        print_result(name, False, {"reason": "group fields not available", "fields": missing_group})
                        continue
                    self.olap_report(
                        key,
                        name,
                        {
                            "reportType": report_type,
                            "buildSummary": False,
                            "groupByRowFields": group_fields,
                            "aggregateFields": aggregate_fields,
                            "filters": filters,
                        },
                    )
            finally:
                self.olap_logout(key)
        else:
            print_result("olap_skipped", False, {"reason": "OLAP env is incomplete"})
        return 0


def main() -> int:
    try:
        return Discover().run()
    except Exception as exc:
        print_result("discover_failed", False, {"error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
