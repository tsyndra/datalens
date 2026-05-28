#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

import psycopg
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
MSK = dt.timezone(dt.timedelta(hours=3))


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
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


def env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    values = [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]
    return values or default


def parse_date(raw: str) -> dt.date:
    return dt.date.fromisoformat(raw)


def parse_date_value(raw: Any) -> dt.date | None:
    parsed_dt = parse_dt(raw)
    if parsed_dt:
        return parsed_dt.date()
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_dt(raw: Any) -> dt.datetime | None:
    if raw is None:
        return None
    if isinstance(raw, dt.datetime):
        return raw
    if isinstance(raw, (int, float)):
        value = float(raw)
        if abs(value) > 10**12:
            value = value / 1000
        if abs(value) > 10**9:
            return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
        return None
    text = str(raw).strip()
    if not text:
        return None
    if re.fullmatch(r"-?\d+", text):
        return parse_dt(int(text))
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=MSK)
        return parsed
    except ValueError:
        return None


def money(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def as_uuid(value: Any, namespace_seed: str) -> uuid.UUID:
    text = str(value or "").strip()
    if text:
        try:
            return uuid.UUID(text)
        except ValueError:
            if re.fullmatch(r"[0-9a-fA-F]{32}", text):
                return uuid.UUID(hex=text)
    return uuid.uuid5(uuid.NAMESPACE_URL, namespace_seed)


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


def order_wrapper(item: dict[str, Any]) -> dict[str, Any]:
    order = item.get("order")
    if isinstance(order, dict):
        return order
    return item


def json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def payload_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def employee_uuid(source_system: str, role: str, source_employee_id: Any, employee_name: Any) -> uuid.UUID:
    source_id = str(source_employee_id or "").strip()
    if source_id:
        return as_uuid(source_id, f"employee:{source_system}:{role}:{source_id}")
    normalized = normalize_name(employee_name) or "unknown"
    return uuid.uuid5(uuid.NAMESPACE_URL, f"employee:{source_system}:{role}:{normalized}")


def payment_group(payment_type: Any) -> str:
    text = normalize_name(payment_type)
    if not text:
        return "unknown"
    if any(x in text for x in ["нал", "cash"]):
        return "cash"
    if any(x in text for x in ["card", "карт", "visa", "mastercard", "мир"]):
        return "card"
    if any(x in text for x in ["online", "онлайн", "internet", "интернет"]):
        return "online"
    if any(x in text for x in ["yandex", "яндекс", "delivery", "деливери", "aggregator", "агрегатор"]):
        return "aggregator"
    if any(x in text for x in ["bonus", "бонус"]):
        return "bonus"
    return "other"


class IikoCloudSync:
    def __init__(self) -> None:
        load_dotenv(REPO_ROOT / ".env")
        load_dotenv(REPO_ROOT / ".credentials.env")

        self.base_url = os.environ.get("IIKO_CLOUD_API_BASE_URL") or os.environ.get("IIKO_API_BASE_URL") or "https://api-ru.iiko.services"
        self.base_url = self.base_url.rstrip("/")
        self.api_login = os.environ.get("IIKO_API_LOGIN") or os.environ.get("IIKO_API_KEY") or ""
        self.database_url = os.environ.get("DATABASE_URL", "")
        self.timeout = max(10, int(os.environ.get("IIKO_TIMEOUT_SECONDS", "60")))
        self.org_number_from = int(os.environ.get("IIKO_ORG_NUMBER_FROM", "10"))
        self.org_number_to = int(os.environ.get("IIKO_ORG_NUMBER_TO", "24"))
        self.request_chunk_hours = max(1, min(24, int(os.environ.get("IIKO_REQUEST_CHUNK_HOURS", "6"))))
        self.nomenclature_sleep_seconds = max(0.0, float(os.environ.get("IIKO_NOMENCLATURE_SLEEP_SECONDS", "1.0")))
        self.delivery_statuses = env_list("IIKO_DELIVERY_STATUSES", ["closed"])
        self.sync_customer_categories_enabled = env_bool("IIKO_SYNC_CUSTOMER_CATEGORIES", True)
        self.sync_external_menus_enabled = env_bool("IIKO_SYNC_EXTERNAL_MENUS", True)
        self.sync_stoplists_enabled = env_bool("IIKO_SYNC_STOPLISTS", False)
        self.verify_ssl = env_bool("IIKO_VERIFY_SSL", True)
        self.olap_enabled = env_bool("IIKO_OLAP_ENABLED", True)
        self.olap_server_url = os.environ.get("IIKO_OLAP_SERVER_URL", "").rstrip("/")
        self.olap_login = os.environ.get("IIKO_OLAP_LOGIN", "")
        self.olap_password = os.environ.get("IIKO_OLAP_PASSWORD", "")
        self.olap_verify_ssl = env_bool("IIKO_OLAP_VERIFY_SSL", True)
        self.olap_date_field = os.environ.get("IIKO_OLAP_DATE_FIELD", "OpenDate.Typed") or "OpenDate.Typed"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._token: str | None = None

        if not self.api_login:
            raise RuntimeError("IIKO_API_LOGIN is empty")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is empty")

    def insert_raw_payload(
        self,
        cur: psycopg.Cursor[Any],
        table: str,
        payload: Any,
        request_key: str,
        *,
        source_system: str = "cloud",
        org_filter: uuid.UUID | None = None,
        window_from: dt.datetime | None = None,
        window_to: dt.datetime | None = None,
        report_type: str | None = None,
        filters: Any | None = None,
    ) -> str:
        allowed_tables = {
            "raw_cloud_organizations",
            "raw_cloud_nomenclature",
            "raw_cloud_deliveries_by_date_status",
            "raw_cloud_stop_lists",
            "raw_cloud_terminal_groups",
            "raw_cloud_customer_categories",
            "raw_cloud_external_menus",
            "raw_server_olap_sales_daily",
            "raw_server_olap_payments",
            "raw_server_olap_staff",
            "raw_server_olap_writeoffs",
        }
        if table not in allowed_tables:
            raise ValueError(f"Unexpected raw table: {table}")
        digest = payload_hash(payload)
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        if table.startswith("raw_server_olap_"):
            cur.execute(
                f"""
                INSERT INTO {table}(
                    source_system, report_type, filters, window_from, window_to,
                    request_key, payload_hash, payload, ingested_at, first_seen_at, last_seen_at, seen_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now(), now(), 1)
                ON CONFLICT (source_system, request_key, payload_hash)
                WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL
                DO UPDATE SET
                    last_seen_at = now(),
                    seen_count = {table}.seen_count + 1
                """,
                (
                    source_system,
                    report_type,
                    json.dumps(filters, ensure_ascii=False, default=str) if filters is not None else None,
                    window_from,
                    window_to,
                    request_key,
                    digest,
                    payload_json,
                ),
            )
        else:
            cur.execute(
                f"""
                INSERT INTO {table}(
                    source_system, org_filter, window_from, window_to,
                    request_key, payload_hash, payload, ingested_at, first_seen_at, last_seen_at, seen_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now(), now(), 1)
                ON CONFLICT (source_system, request_key, payload_hash)
                WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL
                DO UPDATE SET
                    last_seen_at = now(),
                    seen_count = {table}.seen_count + 1
                """,
                (source_system, org_filter, window_from, window_to, request_key, digest, payload_json),
            )
        return digest

    def upsert_employee(
        self,
        cur: psycopg.Cursor[Any],
        *,
        source_system: str,
        role: str,
        employee_name: Any,
        source_employee_id: Any = None,
        phone_hash: str | None = None,
        source_fields: dict[str, Any] | None = None,
    ) -> uuid.UUID | None:
        name = str(employee_name or "").strip()
        source_id = str(source_employee_id or "").strip()
        if not name and not source_id:
            return None
        if not name:
            name = source_id
        normalized = normalize_name(name)
        if not source_id and normalized in {"unknown", "none", "null", "-"}:
            return None
        emp_id = employee_uuid(source_system, role, source_id, name)
        cur.execute(
            """
            INSERT INTO dim_employees(
                employee_id, source_system, source_employee_id, employee_name, normalized_name,
                role, phone_hash, first_seen_at, last_seen_at, is_active_guess, source_fields, updated_at
            )
            VALUES (%s, %s, NULLIF(%s, ''), %s, %s, %s, %s, now(), now(), true, %s, now())
            ON CONFLICT (employee_id) DO UPDATE SET
                source_employee_id = COALESCE(dim_employees.source_employee_id, EXCLUDED.source_employee_id),
                employee_name = COALESCE(NULLIF(EXCLUDED.employee_name, ''), dim_employees.employee_name),
                normalized_name = COALESCE(NULLIF(EXCLUDED.normalized_name, ''), dim_employees.normalized_name),
                role = EXCLUDED.role,
                phone_hash = COALESCE(dim_employees.phone_hash, EXCLUDED.phone_hash),
                last_seen_at = now(),
                is_active_guess = true,
                source_fields = COALESCE(EXCLUDED.source_fields, dim_employees.source_fields),
                updated_at = now()
            """,
            (
                emp_id,
                source_system,
                source_id,
                name,
                normalized,
                role,
                phone_hash,
                json.dumps(source_fields, ensure_ascii=False, default=str) if source_fields else None,
            ),
        )
        return emp_id

    def token(self) -> str:
        if self._token:
            return self._token
        response = self.session.post(
            f"{self.base_url}/api/1/access_token",
            json={"apiLogin": self.api_login},
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("token") if isinstance(payload, dict) else None
        if not token:
            raise RuntimeError(f"Cannot parse iiko access token response: {payload!r}")
        self._token = str(token)
        return self._token

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"}

    def get_json(self, path: str) -> Any:
        response = self.session.get(f"{self.base_url}{path}", headers=self.headers(), timeout=self.timeout, verify=self.verify_ssl)
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        response = None
        for attempt in range(3):
            response = self.session.post(
                f"{self.base_url}{path}",
                headers=self.headers(),
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            if response.status_code != 429:
                break
            retry_after = response.headers.get("Retry-After")
            sleep_seconds = float(retry_after) if retry_after and retry_after.isdigit() else 2.0 * (attempt + 1)
            print(f"[warn] iiko rate limited {path}; retry in {sleep_seconds:.1f}s", file=sys.stderr, flush=True)
            time.sleep(sleep_seconds)
        assert response is not None
        response.raise_for_status()
        return response.json()

    def organizations(self) -> list[dict[str, Any]]:
        payload = self.get_json("/api/1/organizations")
        if isinstance(payload, dict):
            orgs = payload.get("organizations", [])
        else:
            orgs = payload
        return [o for o in orgs if isinstance(o, dict) and o.get("id")]

    def selected_organizations(self, orgs: list[dict[str, Any]], include_all: bool) -> list[dict[str, Any]]:
        if include_all:
            return orgs
        low, high = sorted((self.org_number_from, self.org_number_to))
        selected: list[dict[str, Any]] = []
        for org in orgs:
            number = self.org_number(org)
            if number is not None and low <= number <= high:
                selected.append(org)
        return selected

    @staticmethod
    def org_number(org: dict[str, Any]) -> int | None:
        for raw in (org.get("name"), org.get("code")):
            match = re.match(r"^\s*(\d+)", str(raw or ""))
            if match:
                return int(match.group(1))
        return None

    def sync_organizations(self, conn: psycopg.Connection[Any], orgs: list[dict[str, Any]]) -> None:
        now = dt.datetime.now(dt.timezone.utc)
        with conn.cursor() as cur:
            for org in orgs:
                org_id = as_uuid(org.get("id"), f"org:{org.get('id')}")
                name = str(org.get("name") or org_id)
                code = str(org.get("code") or self.org_number(org) or "")
                self.insert_raw_payload(
                    cur,
                    "raw_cloud_organizations",
                    org,
                    f"organizations:{org_id}",
                    org_filter=org_id,
                    window_from=now,
                    window_to=now,
                )
                cur.execute(
                    """
                    INSERT INTO dim_organizations(organization_id, organization_name, organization_code, is_active, source_system, updated_at)
                    VALUES (%s, %s, %s, %s, 'cloud', now())
                    ON CONFLICT (organization_id) DO UPDATE SET
                        organization_name = EXCLUDED.organization_name,
                        organization_code = EXCLUDED.organization_code,
                        is_active = EXCLUDED.is_active,
                        updated_at = now()
                    """,
                    (org_id, name, code, not bool(org.get("disabled", False))),
                )

    def sync_nomenclature(self, conn: psycopg.Connection[Any], org: dict[str, Any]) -> int:
        org_id = str(org["id"])
        payload = self.post_json("/api/1/nomenclature", {"organizationId": org_id})
        categories = {
            str(cat.get("id")): str(cat.get("name") or "")
            for cat in payload.get("productCategories", [])
            if isinstance(cat, dict) and cat.get("id")
        } if isinstance(payload, dict) else {}
        products = payload.get("products", []) if isinstance(payload, dict) else []
        with conn.cursor() as cur:
            self.insert_raw_payload(
                cur,
                "raw_cloud_nomenclature",
                payload,
                f"nomenclature:{org_id}",
                org_filter=as_uuid(org_id, f"org:{org_id}"),
            )
            count = 0
            for product in products:
                if not isinstance(product, dict) or not product.get("id"):
                    continue
                product_type = str(product.get("type") or "")
                if product_type != "Dish":
                    continue
                product_id = as_uuid(product.get("id"), f"product:{product.get('id')}")
                category_id_raw = product.get("productCategoryId") or product.get("parentGroup")
                category_id = as_uuid(category_id_raw, f"category:{category_id_raw}") if category_id_raw else None
                category_name = str(product.get("categoryName") or categories.get(str(category_id_raw), "") or "")
                cost_price = money(product.get("cost") or product.get("costPrice"))
                product_code = str(product.get("code") or product.get("num") or "")
                sku = str(product.get("sku") or product.get("article") or "")
                measure_unit = str(nested_get(product, "measureUnit.name", "measureUnit") or "")
                weight = money(product.get("weight")) if product.get("weight") is not None else None
                is_deleted = bool(product.get("isDeleted") or product.get("deleted"))
                if category_id:
                    cur.execute(
                        """
                        INSERT INTO dim_categories(category_id, category_name, source_system, updated_at)
                        VALUES (%s, %s, 'cloud', now())
                        ON CONFLICT (category_id) DO UPDATE SET
                            category_name = COALESCE(NULLIF(EXCLUDED.category_name, ''), dim_categories.category_name),
                            updated_at = now()
                        """,
                        (category_id, category_name or str(category_id_raw)),
                    )
                cur.execute(
                    """
                    INSERT INTO dim_products(
                        product_id, product_name, category_id, category_name, cost_price,
                        product_type, measure_unit, weight, product_code, sku, is_active, is_deleted,
                        source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'cloud', now())
                    ON CONFLICT (product_id) DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        category_id = EXCLUDED.category_id,
                        category_name = EXCLUDED.category_name,
                        cost_price = EXCLUDED.cost_price,
                        product_type = EXCLUDED.product_type,
                        measure_unit = EXCLUDED.measure_unit,
                        weight = EXCLUDED.weight,
                        product_code = COALESCE(NULLIF(EXCLUDED.product_code, ''), dim_products.product_code),
                        sku = COALESCE(NULLIF(EXCLUDED.sku, ''), dim_products.sku),
                        is_active = EXCLUDED.is_active,
                        is_deleted = EXCLUDED.is_deleted,
                        updated_at = now()
                    """,
                    (
                        product_id,
                        str(product.get("name") or product_id),
                        category_id,
                        category_name,
                        cost_price,
                        product_type,
                        measure_unit,
                        weight,
                        product_code,
                        sku,
                        not is_deleted,
                        is_deleted,
                    ),
                )
                price_candidates: list[tuple[str, str, float]] = []
                direct_price = money(product.get("price") or product.get("defaultSalePrice") or product.get("currentPrice"))
                if direct_price:
                    price_candidates.append(("default", "", direct_price))
                for size_price in product.get("sizePrices") or []:
                    if not isinstance(size_price, dict):
                        continue
                    size_name = str(nested_get(size_price, "size.name", "size") or "")
                    price = money(size_price.get("price") or size_price.get("currentPrice"))
                    if price:
                        price_candidates.append(("default", size_name, price))
                for price_category in product.get("priceCategories") or product.get("prices") or []:
                    if not isinstance(price_category, dict):
                        continue
                    category_name_for_price = str(price_category.get("name") or price_category.get("priceCategoryName") or "default")
                    price = money(price_category.get("price") or price_category.get("currentPrice"))
                    size_name = str(nested_get(price_category, "size.name", "size") or "")
                    if price:
                        price_candidates.append((category_name_for_price, size_name, price))
                for price_category, size_name, price in price_candidates:
                    cur.execute(
                        """
                        INSERT INTO dim_product_prices(
                            product_id, organization_id, price_category, size_name, price, source_system, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, 'cloud', now())
                        ON CONFLICT (product_id, organization_id, price_category, size_name) DO UPDATE SET
                            price = EXCLUDED.price,
                            updated_at = now()
                        """,
                        (product_id, as_uuid(org_id, f"org:{org_id}"), price_category, size_name, price),
                    )
                count += 1
        return count

    def sync_nomenclature_all(self, conn: psycopg.Connection[Any], orgs: list[dict[str, Any]]) -> int:
        preferred_org_number = os.environ.get("IIKO_NOMENCLATURE_ORG_NUMBER", "").strip()
        probe_orgs = orgs
        if preferred_org_number:
            probe_orgs = [org for org in orgs if str(self.org_number(org) or "") == preferred_org_number] or orgs
        for index, org in enumerate(probe_orgs, 1):
            try:
                count = self.sync_nomenclature(conn, org)
            except requests.HTTPError as exc:
                print(f"[warn] nomenclature failed org={org.get('name')} index={index}: {exc}", file=sys.stderr, flush=True)
                continue
            print(f"[sync] nomenclature probe {index}/{len(probe_orgs)} {org.get('name')}: dishes={count}", flush=True)
            conn.commit()
            if count > 0:
                print(f"[sync] nomenclature source selected: {org.get('name')}", flush=True)
                return count
            if self.nomenclature_sleep_seconds and index < len(probe_orgs):
                time.sleep(self.nomenclature_sleep_seconds)
        print("[warn] nomenclature returned zero Dish products for every probed organization", file=sys.stderr, flush=True)
        return 0

    def sync_terminal_groups(self, conn: psycopg.Connection[Any], orgs: list[dict[str, Any]]) -> int:
        org_ids = [str(o["id"]) for o in orgs if o.get("id")]
        if not org_ids:
            return 0
        payload = self.post_json("/api/1/terminal_groups", {"organizationIds": org_ids, "includeDisabled": True})
        with conn.cursor() as cur:
            self.insert_raw_payload(
                cur,
                "raw_cloud_terminal_groups",
                payload,
                "terminal_groups:" + ",".join(sorted(org_ids)),
            )
        groups = payload.get("terminalGroups") if isinstance(payload, dict) else None
        if isinstance(groups, list):
            return len(groups)
        organizations = payload.get("terminalGroups") or payload.get("organizations") if isinstance(payload, dict) else None
        if isinstance(organizations, list):
            return len(organizations)
        return 1

    def sync_customer_categories(self, conn: psycopg.Connection[Any], orgs: list[dict[str, Any]]) -> int:
        if not self.sync_customer_categories_enabled:
            return 0
        count = 0
        with conn.cursor() as cur:
            for org in orgs:
                org_id = str(org["id"])
                org_uuid = as_uuid(org_id, f"org:{org_id}")
                try:
                    payload = self.post_json("/api/1/loyalty/iiko/customer_category", {"organizationId": org_id})
                except requests.HTTPError as exc:
                    print(f"[warn] customer categories failed org={org.get('name')}: {exc}", file=sys.stderr, flush=True)
                    continue
                self.insert_raw_payload(
                    cur,
                    "raw_cloud_customer_categories",
                    payload,
                    f"customer_categories:{org_id}",
                    org_filter=org_uuid,
                )
                categories = payload.get("items") or payload.get("categories") if isinstance(payload, dict) else None
                count += len(categories) if isinstance(categories, list) else 1
        return count

    def sync_external_menus(self, conn: psycopg.Connection[Any], orgs: list[dict[str, Any]]) -> int:
        if not self.sync_external_menus_enabled:
            return 0
        org_ids = [str(o["id"]) for o in orgs if o.get("id")]
        if not org_ids:
            return 0
        bodies = [
            {"organizationIds": org_ids},
            {"organizationIds": org_ids, "priceCategoryId": None},
        ]
        with conn.cursor() as cur:
            for body in bodies[:1]:
                try:
                    payload = self.post_json("/api/2/menu", body)
                except requests.HTTPError as exc:
                    print(f"[warn] external menu list failed: {exc}", file=sys.stderr, flush=True)
                    return 0
                self.insert_raw_payload(
                    cur,
                    "raw_cloud_external_menus",
                    payload,
                    "external_menu:list:" + ",".join(sorted(org_ids)),
                )
                menus = payload.get("externalMenus") or payload.get("items") or payload.get("menus") if isinstance(payload, dict) else None
                if not isinstance(menus, list):
                    return 1
                loaded = 1
                for menu in menus[:10]:
                    menu_id = menu.get("id") if isinstance(menu, dict) else None
                    if not menu_id:
                        continue
                    try:
                        detail = self.post_json("/api/2/menu/by_id", {"externalMenuId": str(menu_id), "organizationIds": org_ids})
                    except requests.HTTPError as exc:
                        print(f"[warn] external menu by_id failed menu={menu_id}: {exc}", file=sys.stderr, flush=True)
                        continue
                    self.insert_raw_payload(
                        cur,
                        "raw_cloud_external_menus",
                        detail,
                        f"external_menu:by_id:{menu_id}:" + ",".join(sorted(org_ids)),
                    )
                    self.normalize_external_menu(cur, detail, str(menu_id), org_ids)
                    loaded += 1
                return loaded
        return 0

    def normalize_external_menu(
        self,
        cur: psycopg.Cursor[Any],
        payload: Any,
        menu_id: str,
        org_ids: list[str],
    ) -> int:
        if not isinstance(payload, dict):
            return 0
        categories = {
            str(cat.get("id")): str(cat.get("name") or "")
            for cat in payload.get("productCategories", [])
            if isinstance(cat, dict) and cat.get("id")
        }
        default_orgs = [as_uuid(org_id, f"org:{org_id}") for org_id in org_ids]
        count = 0
        for item_category in payload.get("itemCategories") or []:
            if not isinstance(item_category, dict):
                continue
            for item in item_category.get("items") or []:
                if not isinstance(item, dict):
                    continue
                item_id_raw = item.get("itemId") or item.get("id") or item.get("sku")
                if not item_id_raw:
                    continue
                product_id = as_uuid(item_id_raw, f"product:{item_id_raw}")
                category_id_raw = item.get("productCategoryId") or item_category.get("iikoGroupId")
                category_id = as_uuid(category_id_raw, f"category:{category_id_raw}") if category_id_raw else None
                category_name = categories.get(str(category_id_raw), str(item_category.get("name") or ""))
                product_name = str(item.get("name") or item.get("sku") or product_id)
                is_hidden = flag(item.get("isHidden"))
                is_deleted = flag(item.get("isDeleted"))
                cur.execute(
                    """
                    INSERT INTO dim_products(
                        product_id, product_name, category_id, category_name, product_type,
                        measure_unit, sku, is_active, is_deleted, source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'cloud_menu', now())
                    ON CONFLICT (product_id) DO UPDATE SET
                        product_name = COALESCE(NULLIF(EXCLUDED.product_name, ''), dim_products.product_name),
                        category_id = COALESCE(EXCLUDED.category_id, dim_products.category_id),
                        category_name = COALESCE(NULLIF(EXCLUDED.category_name, ''), dim_products.category_name),
                        product_type = COALESCE(NULLIF(EXCLUDED.product_type, ''), dim_products.product_type),
                        measure_unit = COALESCE(NULLIF(EXCLUDED.measure_unit, ''), dim_products.measure_unit),
                        sku = COALESCE(NULLIF(EXCLUDED.sku, ''), dim_products.sku),
                        is_active = EXCLUDED.is_active,
                        is_deleted = EXCLUDED.is_deleted,
                        updated_at = now()
                    """,
                    (
                        product_id,
                        product_name,
                        category_id,
                        category_name,
                        str(item.get("type") or item.get("orderItemType") or ""),
                        str(item.get("measureUnit") or ""),
                        str(item.get("sku") or ""),
                        not (is_hidden or is_deleted),
                        is_deleted,
                    ),
                )
                sizes = item.get("itemSizes") if isinstance(item.get("itemSizes"), list) else []
                if not sizes:
                    sizes = [{"sizeName": "", "prices": item.get("prices") or [], "isHidden": item.get("isHidden")}]
                for size in sizes:
                    if not isinstance(size, dict):
                        continue
                    size_name = str(size.get("sizeName") or size.get("name") or "")
                    size_hidden = is_hidden or flag(size.get("isHidden"))
                    price_rows = size.get("prices") if isinstance(size.get("prices"), list) else []
                    if not price_rows:
                        price_rows = [{"organizations": org_ids, "price": item.get("price") or size.get("price") or 0}]
                    seen_orgs: set[uuid.UUID] = set()
                    for price_row in price_rows:
                        if not isinstance(price_row, dict):
                            continue
                        price = money(price_row.get("price"))
                        row_orgs_raw = price_row.get("organizations")
                        row_orgs = row_orgs_raw if isinstance(row_orgs_raw, list) and row_orgs_raw else org_ids
                        for org_raw in row_orgs:
                            org_uuid = as_uuid(org_raw, f"org:{org_raw}")
                            seen_orgs.add(org_uuid)
                            if price:
                                cur.execute(
                                    """
                                    INSERT INTO dim_product_prices(
                                        product_id, organization_id, price_category, size_name, price, source_system, updated_at
                                    )
                                    VALUES (%s, %s, %s, %s, %s, 'cloud_menu', now())
                                    ON CONFLICT (product_id, organization_id, price_category, size_name) DO UPDATE SET
                                        price = EXCLUDED.price,
                                        updated_at = now()
                                    """,
                                    (product_id, org_uuid, "external_menu", size_name, price),
                                )
                            cur.execute(
                                """
                                INSERT INTO dim_product_availability(
                                    product_id, organization_id, menu_id, size_name, is_available, source_system, updated_at
                                )
                                VALUES (%s, %s, %s, %s, %s, 'cloud_menu', now())
                                ON CONFLICT (product_id, organization_id, menu_id, size_name) DO UPDATE SET
                                    is_available = EXCLUDED.is_available,
                                    updated_at = now()
                                """,
                                (product_id, org_uuid, menu_id, size_name, not size_hidden),
                            )
                    for org_uuid in default_orgs:
                        if org_uuid in seen_orgs:
                            continue
                        cur.execute(
                            """
                            INSERT INTO dim_product_availability(
                                product_id, organization_id, menu_id, size_name, is_available, source_system, updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, 'cloud_menu', now())
                            ON CONFLICT (product_id, organization_id, menu_id, size_name) DO UPDATE SET
                                is_available = EXCLUDED.is_available,
                                updated_at = now()
                            """,
                            (product_id, org_uuid, menu_id, size_name, not size_hidden),
                        )
                count += 1
        return count

    def day_chunks(self, day: dt.date) -> Iterable[tuple[dt.datetime, dt.datetime]]:
        start = dt.datetime.combine(day, dt.time.min)
        end = dt.datetime.combine(day, dt.time(23, 59, 59, 999000))
        cur = start
        while cur <= end:
            nxt = cur + dt.timedelta(hours=self.request_chunk_hours)
            yield cur, min(end, nxt - dt.timedelta(milliseconds=1))
            cur = nxt

    @staticmethod
    def fmt_iiko_time(value: dt.datetime) -> str:
        return value.isoformat(timespec="milliseconds")

    def deliveries(self, org_id: str, start: dt.datetime, end: dt.datetime) -> tuple[Any, list[dict[str, Any]]]:
        payload = {
            "organizationIds": [org_id],
            "deliveryDateFrom": self.fmt_iiko_time(start),
            "deliveryDateTo": self.fmt_iiko_time(end),
            "statuses": self.delivery_statuses,
        }
        try:
            data = self.post_json("/api/1/deliveries/by_delivery_date_and_status", payload)
        except requests.HTTPError:
            if [x.lower() for x in self.delivery_statuses] == ["closed"]:
                raise
            print(
                f"[warn] delivery statuses rejected for org={org_id}; retry with ['closed']",
                file=sys.stderr,
                flush=True,
            )
            payload["statuses"] = ["closed"]
            data = self.post_json("/api/1/deliveries/by_delivery_date_and_status", payload)
        return data, self.extract_orders(data)

    @staticmethod
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

    def sync_deliveries(self, conn: psycopg.Connection[Any], org: dict[str, Any], date_from: dt.date, date_to: dt.date) -> dict[str, int]:
        org_uuid = as_uuid(org["id"], f"org:{org['id']}")
        day = date_from
        raw_count = orders_count = item_count = payment_count = discount_count = delivery_count = 0
        while day <= date_to:
            for start, end in self.day_chunks(day):
                try:
                    raw_payload, orders = self.deliveries(str(org["id"]), start, end)
                except requests.HTTPError as exc:
                    print(f"[warn] deliveries failed org={org.get('name')} {start}..{end}: {exc}", file=sys.stderr, flush=True)
                    continue
                with conn.cursor() as cur:
                    self.insert_raw_payload(
                        cur,
                        "raw_cloud_deliveries_by_date_status",
                        raw_payload,
                        f"deliveries_by_date_status:{org_uuid}:{start.isoformat()}:{end.isoformat()}:{','.join(self.delivery_statuses)}",
                        org_filter=org_uuid,
                        window_from=start.replace(tzinfo=MSK),
                        window_to=end.replace(tzinfo=MSK),
                    )
                raw_count += 1
                for wrapper in orders:
                    counts = self.upsert_order_tree(conn, org_uuid, wrapper, day)
                    orders_count += counts["orders"]
                    item_count += counts["items"]
                    payment_count += counts["payments"]
                    discount_count += counts["discounts"]
                    delivery_count += counts["deliveries"]
                conn.commit()
            day += dt.timedelta(days=1)
        return {
            "raw_batches": raw_count,
            "orders": orders_count,
            "items": item_count,
            "payments": payment_count,
            "discounts": discount_count,
            "deliveries": delivery_count,
        }

    def upsert_order_tree(self, conn: psycopg.Connection[Any], org_uuid: uuid.UUID, wrapper: dict[str, Any], fallback_day: dt.date) -> dict[str, int]:
        order = order_wrapper(wrapper)
        order_id_raw = nested_get(order, "id", "orderId", "externalNumber") or nested_get(wrapper, "id", "orderId")
        order_id = as_uuid(order_id_raw, f"order:{org_uuid}:{order_id_raw}:{json.dumps(order, sort_keys=True, default=str)[:256]}")
        opened_at = parse_dt(nested_get(order, "whenCreated", "createdAt", "creationStatus.createdAt", "deliveryDate", "completeBefore"))
        closed_at = parse_dt(nested_get(order, "whenClosed", "closedAt", "closeTime", "deliveryDate"))
        confirmed_at = parse_dt(nested_get(order, "whenConfirmed"))
        cooking_started_at = parse_dt(nested_get(order, "cookingStartTime"))
        cooking_completed_at = parse_dt(nested_get(order, "whenCookingCompleted"))
        packed_at = parse_dt(nested_get(order, "whenPacked"))
        sent_at = parse_dt(nested_get(order, "whenSended", "whenSent"))
        delivered_at = parse_dt(nested_get(order, "whenDelivered"))
        received_by_api_at = parse_dt(nested_get(order, "whenReceivedByApi"))
        business_date = (closed_at or opened_at).date() if (closed_at or opened_at) else fallback_day
        status = str(nested_get(order, "status", "deliveryStatus", "creationStatus.status") or "").lower()
        is_cancelled = status in {"cancelled", "canceled", "deleted"} or flag(order.get("isDeleted"))
        items = [x for x in (order.get("items") or []) if isinstance(x, dict)]
        payments = [x for x in (order.get("payments") or []) if isinstance(x, dict)]
        discounts = [x for x in (order.get("discounts") or order.get("discountsInfo") or []) if isinstance(x, dict)]
        gross = money(nested_get(order, "sum", "subtotal", "fullSum", "total"))
        item_total = sum(money(i.get("sum") or i.get("total") or money(i.get("price")) * money(i.get("amount") or i.get("quantity"))) for i in items)
        if not gross and item_total:
            gross = item_total
        discount_sum = abs(money(nested_get(order, "discountsSum", "discountSum", "discountAmount")))
        if not discount_sum:
            discount_sum = sum(abs(money(d.get("sum") or d.get("amount"))) for d in discounts)
        net = money(nested_get(order, "resultSum", "total", "sum"))
        if not net:
            net = max(0.0, gross - discount_sum)
        refund_sum = abs(money(nested_get(order, "refundSum", "refundAmount")))
        order_source = str(nested_get(order, "sourceKey", "source", "orderType.name", "orderServiceType") or "delivery")
        order_type = str(nested_get(order, "orderType.name", "orderType", "orderServiceType") or "")
        external_order_id = str(nested_get(wrapper, "externalNumber") or nested_get(order, "externalNumber") or "")
        order_number = str(nested_get(order, "number") or nested_get(wrapper, "number") or "")
        terminal_group_id = str(nested_get(order, "terminalGroupId") or "")
        marketing_source = str(nested_get(order, "marketingSource.name", "marketingSource") or "")
        operator_name = str(nested_get(order, "operator.name", "operator") or "")
        operator_source_id = nested_get(order, "operator.id", "operator.userId")
        guests_count = int(money(nested_get(order, "guestsInfo.count", "guestsCount"))) or None
        processed_payments_sum = money(nested_get(order, "processedPaymentsSum"))
        tips_sum = money(nested_get(order, "tips.sum", "tips"))
        delivery_status = str(nested_get(order, "deliveryStatus", "status") or "unknown")
        delivery_zone = str(nested_get(order, "deliveryPoint.address.city", "deliveryPoint.address.street.name", "deliveryZone") or "unknown")
        complete_before = parse_dt(nested_get(order, "completeBefore"))
        delivery_minutes = None
        delay_minutes = None
        cooking_minutes = None
        courier_waiting_minutes = None
        if opened_at and closed_at:
            delivery_minutes = max(0.0, (closed_at - opened_at).total_seconds() / 60)
        if closed_at and complete_before:
            delay_minutes = max(0.0, (closed_at - complete_before).total_seconds() / 60)
        if cooking_started_at and cooking_completed_at:
            cooking_minutes = max(0.0, (cooking_completed_at - cooking_started_at).total_seconds() / 60)
        if cooking_completed_at and sent_at:
            courier_waiting_minutes = max(0.0, (sent_at - cooking_completed_at).total_seconds() / 60)
        is_late = bool(delay_minutes and delay_minutes > 0)

        customer_phone = str(nested_get(order, "phone", "customer.phone") or "").strip()
        customer_raw_id = nested_get(order, "customer.id")
        customer_id = None
        phone_hash = None
        if customer_phone:
            phone_hash = hashlib.sha256(customer_phone.encode("utf-8")).hexdigest()
            customer_id = uuid.uuid5(uuid.NAMESPACE_URL, f"customer:{phone_hash}")
        elif customer_raw_id:
            customer_id = as_uuid(customer_raw_id, f"customer:{customer_raw_id}")
        customer_name = str(nested_get(order, "customer.name") or "")
        customer_surname = str(nested_get(order, "customer.surname") or "")
        customer_birthdate = parse_date_value(nested_get(order, "customer.birthdate"))
        customer_gender = str(nested_get(order, "customer.gender") or "")
        customer_type = str(nested_get(order, "customer.type") or "")
        customer_in_blacklist = flag(nested_get(order, "customer.inBlacklist"))
        customer_blacklist_reason = str(nested_get(order, "customer.blacklistReason") or "")
        delivery_address = nested_get(order, "deliveryPoint.address")
        address_text = str(nested_get(order, "deliveryPoint.address.fullAddress", "deliveryPoint.address.street.name", "deliveryPoint.address.city") or "")
        if not address_text and isinstance(delivery_address, dict):
            address_text = json.dumps(delivery_address, ensure_ascii=False)
        latitude = money(nested_get(order, "deliveryPoint.coordinates.latitude", "deliveryPoint.address.latitude")) or None
        longitude = money(nested_get(order, "deliveryPoint.coordinates.longitude", "deliveryPoint.address.longitude")) or None
        courier_name = str(nested_get(order, "courierInfo.name", "courierInfo.courier.name") or "")
        courier_source_id = nested_get(order, "courierInfo.id", "courierInfo.courier.id", "courierInfo.userId")
        courier_phone = str(nested_get(order, "courierInfo.phone", "courierInfo.courier.phone") or "").strip()
        courier_phone_hash = hashlib.sha256(courier_phone.encode("utf-8")).hexdigest() if courier_phone else None
        external_courier_service = str(nested_get(order, "externalCourierService.name", "externalCourierService") or "")
        with conn.cursor() as cur:
            operator_employee_id = self.upsert_employee(
                cur,
                source_system="cloud",
                role="operator",
                employee_name=operator_name,
                source_employee_id=operator_source_id,
                source_fields={"order_path": "operator"},
            )
            courier_employee_id = self.upsert_employee(
                cur,
                source_system="cloud",
                role="courier",
                employee_name=courier_name,
                source_employee_id=courier_source_id,
                phone_hash=courier_phone_hash,
                source_fields={"order_path": "courierInfo"},
            )
            if customer_id:
                cur.execute(
                    """
                    INSERT INTO dim_customers(
                        customer_id, phone_hash, first_order_date, last_order_date,
                        customer_name, customer_surname, birthdate, gender, customer_type,
                        in_blacklist, blacklist_reason, first_order_source, first_organization_id,
                        source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'cloud', now())
                    ON CONFLICT (customer_id) DO UPDATE SET
                        phone_hash = COALESCE(dim_customers.phone_hash, EXCLUDED.phone_hash),
                        first_order_date = CASE
                            WHEN dim_customers.first_order_date IS NULL THEN EXCLUDED.first_order_date
                            WHEN EXCLUDED.first_order_date IS NULL THEN dim_customers.first_order_date
                            ELSE LEAST(dim_customers.first_order_date, EXCLUDED.first_order_date)
                        END,
                        last_order_date = GREATEST(COALESCE(dim_customers.last_order_date, EXCLUDED.last_order_date), EXCLUDED.last_order_date),
                        customer_name = COALESCE(NULLIF(EXCLUDED.customer_name, ''), dim_customers.customer_name),
                        customer_surname = COALESCE(NULLIF(EXCLUDED.customer_surname, ''), dim_customers.customer_surname),
                        birthdate = COALESCE(dim_customers.birthdate, EXCLUDED.birthdate),
                        gender = COALESCE(NULLIF(EXCLUDED.gender, ''), dim_customers.gender),
                        customer_type = COALESCE(NULLIF(EXCLUDED.customer_type, ''), dim_customers.customer_type),
                        in_blacklist = EXCLUDED.in_blacklist,
                        blacklist_reason = COALESCE(NULLIF(EXCLUDED.blacklist_reason, ''), dim_customers.blacklist_reason),
                        first_order_source = COALESCE(dim_customers.first_order_source, EXCLUDED.first_order_source),
                        first_organization_id = COALESCE(dim_customers.first_organization_id, EXCLUDED.first_organization_id),
                        updated_at = now()
                    """,
                    (
                        customer_id,
                        phone_hash,
                        business_date,
                        business_date,
                        customer_name,
                        customer_surname,
                        customer_birthdate,
                        customer_gender,
                        customer_type,
                        customer_in_blacklist,
                        customer_blacklist_reason,
                        order_source,
                        org_uuid,
                    ),
                )
            cur.execute(
                """
                INSERT INTO fact_orders(
                    order_id, business_date, opened_at, closed_at, organization_id, customer_id,
                    order_source, order_type, status, is_delivery, is_cancelled,
                    gross_revenue, discount_sum, net_revenue, refund_sum,
                    external_order_id, order_number, terminal_group_id, marketing_source, operator_name, operator_employee_id,
                    guests_count, processed_payments_sum, tips_sum, source_system, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'cloud', now())
                ON CONFLICT (order_id) DO UPDATE SET
                    business_date = EXCLUDED.business_date,
                    opened_at = EXCLUDED.opened_at,
                    closed_at = EXCLUDED.closed_at,
                    organization_id = EXCLUDED.organization_id,
                    customer_id = EXCLUDED.customer_id,
                    order_source = EXCLUDED.order_source,
                    order_type = EXCLUDED.order_type,
                    status = EXCLUDED.status,
                    is_delivery = EXCLUDED.is_delivery,
                    is_cancelled = EXCLUDED.is_cancelled,
                    gross_revenue = EXCLUDED.gross_revenue,
                    discount_sum = EXCLUDED.discount_sum,
                    net_revenue = EXCLUDED.net_revenue,
                    refund_sum = EXCLUDED.refund_sum,
                    external_order_id = EXCLUDED.external_order_id,
                    order_number = EXCLUDED.order_number,
                    terminal_group_id = EXCLUDED.terminal_group_id,
                    marketing_source = EXCLUDED.marketing_source,
                    operator_name = EXCLUDED.operator_name,
                    operator_employee_id = EXCLUDED.operator_employee_id,
                    guests_count = EXCLUDED.guests_count,
                    processed_payments_sum = EXCLUDED.processed_payments_sum,
                    tips_sum = EXCLUDED.tips_sum,
                    updated_at = now()
                """,
                (
                    order_id,
                    business_date,
                    opened_at,
                    closed_at,
                    org_uuid,
                    customer_id,
                    order_source,
                    order_type,
                    status,
                    is_cancelled,
                    gross,
                    discount_sum,
                    net,
                    refund_sum,
                    external_order_id,
                    order_number,
                    terminal_group_id,
                    marketing_source,
                    operator_name,
                    operator_employee_id,
                    guests_count,
                    processed_payments_sum,
                    tips_sum,
                ),
            )
            delivery_id = as_uuid(nested_get(wrapper, "id") or order_id_raw, f"delivery:{order_id}")
            cur.execute(
                """
                INSERT INTO fact_deliveries(
                    delivery_id, order_id, business_date, organization_id, delivery_zone, delivery_status,
                    delivery_minutes, delay_minutes, cooking_minutes, courier_waiting_minutes,
                    is_late, is_active, address_text, latitude, longitude, courier_name, courier_employee_id, courier_phone_hash,
                    complete_before, when_confirmed, cooking_started_at, cooking_completed_at, when_packed,
                    when_sent, when_delivered, when_received_by_api, external_courier_service,
                    source_system, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'cloud', now())
                ON CONFLICT (delivery_id) DO UPDATE SET
                    order_id = EXCLUDED.order_id,
                    business_date = EXCLUDED.business_date,
                    organization_id = EXCLUDED.organization_id,
                    delivery_zone = EXCLUDED.delivery_zone,
                    delivery_status = EXCLUDED.delivery_status,
                    delivery_minutes = EXCLUDED.delivery_minutes,
                    delay_minutes = EXCLUDED.delay_minutes,
                    cooking_minutes = EXCLUDED.cooking_minutes,
                    courier_waiting_minutes = EXCLUDED.courier_waiting_minutes,
                    is_late = EXCLUDED.is_late,
                    is_active = EXCLUDED.is_active,
                    address_text = EXCLUDED.address_text,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    courier_name = EXCLUDED.courier_name,
                    courier_employee_id = EXCLUDED.courier_employee_id,
                    courier_phone_hash = EXCLUDED.courier_phone_hash,
                    complete_before = EXCLUDED.complete_before,
                    when_confirmed = EXCLUDED.when_confirmed,
                    cooking_started_at = EXCLUDED.cooking_started_at,
                    cooking_completed_at = EXCLUDED.cooking_completed_at,
                    when_packed = EXCLUDED.when_packed,
                    when_sent = EXCLUDED.when_sent,
                    when_delivered = EXCLUDED.when_delivered,
                    when_received_by_api = EXCLUDED.when_received_by_api,
                    external_courier_service = EXCLUDED.external_courier_service,
                    updated_at = now()
                """,
                (
                    delivery_id,
                    order_id,
                    business_date,
                    org_uuid,
                    delivery_zone,
                    delivery_status,
                    delivery_minutes,
                    delay_minutes,
                    cooking_minutes,
                    courier_waiting_minutes,
                    is_late,
                    address_text,
                    latitude,
                    longitude,
                    courier_name,
                    courier_employee_id,
                    courier_phone_hash,
                    complete_before,
                    confirmed_at,
                    cooking_started_at,
                    cooking_completed_at,
                    packed_at,
                    sent_at,
                    delivered_at,
                    received_by_api_at,
                    external_courier_service,
                ),
            )
            deleted_item_losses = 0
            for index, item in enumerate(items):
                product = item.get("product") if isinstance(item.get("product"), dict) else {}
                product_raw = item.get("productId") or item.get("id") or product.get("id") or item.get("positionId")
                product_name = str(item.get("name") or nested_get(item, "product.name") or product_raw or "unknown")
                category_raw = nested_get(item, "product.productCategoryId", "product.category.id")
                category_name = str(nested_get(item, "product.category.name", "product.categoryName") or "")
                category_id = as_uuid(category_raw, f"category:{category_raw}") if category_raw else None
                product_id = as_uuid(product_raw or product_name, f"product:{product_raw or product_name}")
                quantity = money(item.get("amount") or item.get("quantity"))
                price = money(item.get("price"))
                item_net_raw = money(item.get("resultSum"))
                item_gross = money(item.get("sum") or item.get("total"))
                if not item_gross and price and quantity:
                    item_gross = price * quantity
                item_discount = abs(money(item.get("discountSum") or item.get("discountsSum")))
                item_net = item_net_raw if item_net_raw else max(0.0, item_gross - item_discount)
                if not item_discount and item_gross and item_net and item_gross > item_net:
                    item_discount = item_gross - item_net
                cost = money(item.get("cost"))
                item_id = as_uuid(item.get("id") or item.get("positionId"), f"order_item:{order_id}:{product_id}:{index}")
                item_status = str(item.get("status") or "")
                is_deleted_item = flag(item.get("deleted")) or item_status.lower() == "deleted"
                is_modifier = str(item.get("type") or "").lower() == "modifier"
                modifiers_json = json_or_none(item.get("modifiers"))
                combo_json = json_or_none(item.get("comboInformation"))
                size_name = str(nested_get(item, "size.name", "size") or "")
                when_printed = parse_dt(item.get("whenPrinted"))
                tax_percent = money(item.get("taxPercent")) if item.get("taxPercent") is not None else None
                if category_id:
                    cur.execute(
                        """
                        INSERT INTO dim_categories(category_id, category_name, source_system, updated_at)
                        VALUES (%s, %s, 'cloud', now())
                        ON CONFLICT (category_id) DO UPDATE SET
                            category_name = COALESCE(NULLIF(EXCLUDED.category_name, ''), dim_categories.category_name),
                            updated_at = now()
                        """,
                        (category_id, category_name or str(category_raw)),
                    )
                cur.execute(
                    """
                    INSERT INTO dim_products(product_id, product_name, category_id, category_name, cost_price, source_system, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'cloud', now())
                    ON CONFLICT (product_id) DO UPDATE SET
                        product_name = COALESCE(NULLIF(EXCLUDED.product_name, ''), dim_products.product_name),
                        category_id = COALESCE(EXCLUDED.category_id, dim_products.category_id),
                        category_name = COALESCE(NULLIF(EXCLUDED.category_name, ''), dim_products.category_name),
                        cost_price = COALESCE(NULLIF(EXCLUDED.cost_price, 0), dim_products.cost_price),
                        updated_at = now()
                    """,
                    (product_id, product_name, category_id, category_name, cost),
                )
                cur.execute(
                    """
                    INSERT INTO fact_order_items(
                        order_item_id, order_id, business_date, organization_id, product_id,
                        product_name, category_name, quantity, unit_price, gross_revenue, discount_sum,
                        net_revenue, cost_sum, item_status, is_deleted, is_modifier, modifiers_json,
                        combo_json, size_name, when_printed, tax_percent, source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, 'cloud', now())
                    ON CONFLICT (order_item_id) DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        category_name = EXCLUDED.category_name,
                        quantity = EXCLUDED.quantity,
                        unit_price = EXCLUDED.unit_price,
                        gross_revenue = EXCLUDED.gross_revenue,
                        discount_sum = EXCLUDED.discount_sum,
                        net_revenue = EXCLUDED.net_revenue,
                        cost_sum = EXCLUDED.cost_sum,
                        item_status = EXCLUDED.item_status,
                        is_deleted = EXCLUDED.is_deleted,
                        is_modifier = EXCLUDED.is_modifier,
                        modifiers_json = EXCLUDED.modifiers_json,
                        combo_json = EXCLUDED.combo_json,
                        size_name = EXCLUDED.size_name,
                        when_printed = EXCLUDED.when_printed,
                        tax_percent = EXCLUDED.tax_percent,
                        updated_at = now()
                    """,
                    (
                        item_id,
                        order_id,
                        business_date,
                        org_uuid,
                        product_id,
                        product_name,
                        category_name,
                        quantity,
                        price,
                        item_gross,
                        item_discount,
                        item_net,
                        cost,
                        item_status,
                        is_deleted_item,
                        is_modifier,
                        modifiers_json,
                        combo_json,
                        size_name,
                        when_printed,
                        tax_percent,
                    ),
                )
                if is_deleted_item and item_gross:
                    deleted_item_losses += 1
                    loss_key = f"deleted_item:{order_id}:{item_id}"
                    cur.execute(
                        """
                        INSERT INTO fact_losses(
                            loss_id, source_loss_key, business_date, organization_id, order_id, order_item_id,
                            loss_type, loss_reason, loss_sum, source_system, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 'deleted_item', %s, %s, 'cloud', now())
                        ON CONFLICT (source_loss_key) WHERE source_loss_key IS NOT NULL DO UPDATE SET
                            loss_sum = EXCLUDED.loss_sum,
                            loss_reason = EXCLUDED.loss_reason,
                            updated_at = now()
                        """,
                        (as_uuid(loss_key, loss_key), loss_key, business_date, org_uuid, order_id, item_id, item_status or "deleted", item_gross),
                    )
            for index, payment in enumerate(payments):
                payment_id = as_uuid(payment.get("id"), f"payment:{order_id}:{index}")
                payment_type = str(nested_get(payment, "paymentType.name", "type", "kind") or "")
                payment_group = str(nested_get(payment, "paymentType.paymentTypeKind", "paymentType.kind", "group") or "")
                cur.execute(
                    """
                    INSERT INTO fact_payments(
                        payment_id, order_id, business_date, organization_id, payment_type, payment_group,
                        payment_sum, is_fiscalized_externally, is_prepay, is_external,
                        is_processed_externally, source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'cloud', now())
                    ON CONFLICT (payment_id) DO UPDATE SET
                        payment_type = EXCLUDED.payment_type,
                        payment_group = EXCLUDED.payment_group,
                        payment_sum = EXCLUDED.payment_sum,
                        is_fiscalized_externally = EXCLUDED.is_fiscalized_externally,
                        is_prepay = EXCLUDED.is_prepay,
                        is_external = EXCLUDED.is_external,
                        is_processed_externally = EXCLUDED.is_processed_externally,
                        updated_at = now()
                    """,
                    (
                        payment_id,
                        order_id,
                        business_date,
                        org_uuid,
                        payment_type,
                        payment_group,
                        money(payment.get("sum") or payment.get("amount")),
                        flag(payment.get("isFiscalizedExternally")),
                        flag(payment.get("isPrepay")),
                        flag(payment.get("isExternal")),
                        flag(payment.get("isProcessedExternally")),
                    ),
                )
            for index, discount in enumerate(discounts):
                discount_id = as_uuid(discount.get("id"), f"discount:{order_id}:{index}")
                discount_name = str(nested_get(discount, "name", "discountType.name") or "unknown")
                discount_type = str(nested_get(discount, "type", "discountType.type") or "")
                discount_amount = abs(money(discount.get("sum") or discount.get("amount")))
                is_manual_discount = flag(discount.get("isManual")) or "ручн" in discount_name.lower() or "свобод" in discount_name.lower()
                cur.execute(
                    """
                    INSERT INTO fact_discounts(discount_id, order_id, business_date, organization_id, discount_name, discount_type, discount_sum, is_manual, source_system, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'cloud', now())
                    ON CONFLICT (discount_id) DO UPDATE SET
                        discount_name = EXCLUDED.discount_name,
                        discount_type = EXCLUDED.discount_type,
                        discount_sum = EXCLUDED.discount_sum,
                        is_manual = EXCLUDED.is_manual,
                        updated_at = now()
                    """,
                    (
                        discount_id,
                        order_id,
                        business_date,
                        org_uuid,
                        discount_name,
                        discount_type,
                        discount_amount,
                        is_manual_discount,
                    ),
                )
                if is_manual_discount and discount_amount:
                    loss_key = f"manual_discount:{order_id}:{discount_id}"
                    cur.execute(
                        """
                        INSERT INTO fact_losses(
                            loss_id, source_loss_key, business_date, organization_id, order_id,
                            loss_type, loss_reason, loss_sum, source_system, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, 'manual_discount', %s, %s, 'cloud', now())
                        ON CONFLICT (source_loss_key) WHERE source_loss_key IS NOT NULL DO UPDATE SET
                            loss_sum = EXCLUDED.loss_sum,
                            loss_reason = EXCLUDED.loss_reason,
                            updated_at = now()
                        """,
                        (as_uuid(loss_key, loss_key), loss_key, business_date, org_uuid, order_id, discount_name, discount_amount),
                    )
            if is_cancelled and gross:
                loss_key = f"cancel:{order_id}"
                cur.execute(
                    """
                    INSERT INTO fact_losses(
                        loss_id, source_loss_key, business_date, organization_id, order_id,
                        loss_type, loss_reason, loss_sum, source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, 'cancel', %s, %s, 'cloud', now())
                    ON CONFLICT (source_loss_key) WHERE source_loss_key IS NOT NULL DO UPDATE SET
                        loss_sum = EXCLUDED.loss_sum,
                        loss_reason = EXCLUDED.loss_reason,
                        updated_at = now()
                    """,
                    (as_uuid(loss_key, loss_key), loss_key, business_date, org_uuid, order_id, status or "cancelled", gross),
                )
            if refund_sum:
                loss_key = f"refund:{order_id}"
                cur.execute(
                    """
                    INSERT INTO fact_losses(
                        loss_id, source_loss_key, business_date, organization_id, order_id,
                        loss_type, loss_reason, loss_sum, source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, 'refund', 'refund_sum', %s, 'cloud', now())
                    ON CONFLICT (source_loss_key) WHERE source_loss_key IS NOT NULL DO UPDATE SET
                        loss_sum = EXCLUDED.loss_sum,
                        updated_at = now()
                    """,
                    (as_uuid(loss_key, loss_key), loss_key, business_date, org_uuid, order_id, refund_sum),
                )
            if is_late and delay_minutes:
                loss_key = f"delivery_late:{order_id}"
                cur.execute(
                    """
                    INSERT INTO fact_losses(
                        loss_id, source_loss_key, business_date, organization_id, order_id,
                        loss_type, loss_reason, loss_sum, source_system, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, 'delivery_late', %s, 0, 'cloud', now())
                    ON CONFLICT (source_loss_key) WHERE source_loss_key IS NOT NULL DO UPDATE SET
                        loss_reason = EXCLUDED.loss_reason,
                        updated_at = now()
                    """,
                    (as_uuid(loss_key, loss_key), loss_key, business_date, org_uuid, order_id, f"delay_minutes={delay_minutes:.2f}"),
                )
        return {"orders": 1, "items": len(items), "payments": len(payments), "discounts": len(discounts), "deliveries": 1}

    def sync_stoplists(self, conn: psycopg.Connection[Any], orgs: list[dict[str, Any]]) -> int:
        org_ids = [str(o["id"]) for o in orgs]
        if not org_ids:
            return 0
        payload = self.post_json("/api/1/stop_lists", {"organizationIds": org_ids})
        count = 0
        with conn.cursor() as cur:
            self.insert_raw_payload(
                cur,
                "raw_cloud_stop_lists",
                payload,
                "stop_lists:" + ",".join(sorted(org_ids)),
            )
            organizations = payload.get("terminalGroupStopLists") or payload.get("organizations") or []
            if isinstance(organizations, list):
                for group in organizations:
                    if not isinstance(group, dict):
                        continue
                    org_raw = group.get("organizationId") or group.get("organization") or ""
                    org_uuid = as_uuid(org_raw, f"org:{org_raw}") if org_raw else None
                    terminal_groups = group.get("items") or []
                    if not isinstance(terminal_groups, list):
                        continue
                    for terminal_group in terminal_groups:
                        if not isinstance(terminal_group, dict):
                            continue
                        terminal_group_id = str(terminal_group.get("terminalGroupId") or "")
                        items = terminal_group.get("items") or terminal_group.get("stopList") or terminal_group.get("products") or []
                        if not isinstance(items, list):
                            continue
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            product_raw = item.get("productId") or item.get("id")
                            if not product_raw or org_uuid is None:
                                continue
                            product_id = as_uuid(product_raw, f"product:{product_raw}")
                            started_at = parse_dt(item.get("dateAdd") or item.get("startedAt")) or dt.datetime.now(dt.timezone.utc)
                            cur.execute(
                                """
                                INSERT INTO dim_products(product_id, product_name, source_system, updated_at)
                                VALUES (%s, %s, 'cloud', now())
                                ON CONFLICT (product_id) DO NOTHING
                                """,
                                (product_id, str(item.get("sku") or product_raw)),
                            )
                            cur.execute(
                                """
                                INSERT INTO fact_stoplists(organization_id, product_id, started_at, ended_at, source_system, updated_at)
                                SELECT %s, %s, %s, NULL, 'cloud', now()
                                WHERE NOT EXISTS (
                                    SELECT 1
                                    FROM fact_stoplists
                                    WHERE organization_id = %s
                                      AND product_id = %s
                                      AND started_at = %s
                                      AND ended_at IS NULL
                                )
                                """,
                                (org_uuid, product_id, started_at, org_uuid, product_id, started_at),
                            )
                            count += 1
        return count

    def refresh_marts(self, conn: psycopg.Connection[Any], date_from: dt.date, date_to: dt.date) -> None:
        with conn.cursor() as cur:
            cur.execute("SELECT refresh_datalens_marts(%s, %s)", (date_from, date_to))
            cur.execute("SELECT refresh_datalens_today_marts()")

    def olap_auth(self) -> str:
        if not self.olap_server_url or not self.olap_login or not self.olap_password:
            raise RuntimeError("IIKO_OLAP_SERVER_URL / IIKO_OLAP_LOGIN / IIKO_OLAP_PASSWORD are required")
        response = requests.get(
            f"{self.olap_server_url}/resto/api/auth",
            params={"login": self.olap_login, "pass": hashlib.sha1(self.olap_password.encode("utf-8")).hexdigest()},
            verify=self.olap_verify_ssl,
            timeout=self.timeout,
        )
        response.raise_for_status()
        key = response.text.strip()
        if not key:
            raise RuntimeError("Empty iikoServer OLAP session key")
        return key

    def olap_logout(self, key: str) -> None:
        try:
            requests.get(
                f"{self.olap_server_url}/resto/api/logout",
                params={"key": key},
                verify=self.olap_verify_ssl,
                timeout=10,
            )
        except Exception:
            pass

    def olap_report(self, key: str, body: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.olap_server_url}/resto/api/v2/reports/olap",
            params={"key": key},
            json=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            verify=self.olap_verify_ssl,
            timeout=max(self.timeout, 90),
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    def olap_columns(self, key: str, report_type: str) -> dict[str, dict[str, Any]]:
        response = requests.get(
            f"{self.olap_server_url}/resto/api/v2/reports/olap/columns",
            params={"key": key, "reportType": report_type},
            verify=self.olap_verify_ssl,
            timeout=max(self.timeout, 90),
        )
        response.raise_for_status()
        payload = response.json()
        return {str(k): v for k, v in payload.items() if isinstance(v, dict)} if isinstance(payload, dict) else {}

    @staticmethod
    def first_available(columns: dict[str, dict[str, Any]], candidates: list[str], flag_name: str) -> str | None:
        for field in candidates:
            meta = columns.get(field)
            if meta and meta.get(flag_name):
                return field
        return None

    @staticmethod
    def olap_org_id(department_code: Any, department_name: Any) -> uuid.UUID:
        code = str(department_code or "").strip()
        name = str(department_name or "").strip()
        return uuid.uuid5(uuid.NAMESPACE_URL, f"iiko-olap-department:{code}:{name}")

    def sync_olap_sales_marts(self, conn: psycopg.Connection[Any], date_from: dt.date, date_to: dt.date) -> dict[str, int]:
        if not self.olap_enabled:
            return {"daily_sales": 0, "branch_kpi": 0, "product_sales": 0}

        key = self.olap_auth()
        try:
            sales_columns = self.olap_columns(key, "SALES")
            daily_body = {
                "reportType": "SALES",
                "buildSummary": False,
                "groupByRowFields": [self.olap_date_field, "Department.Code", "Department", "OriginName"],
                "aggregateFields": [
                    "UniqOrderId.OrdersCount",
                    "DishAmountInt",
                    "DishSumInt",
                    "DiscountSum",
                    "DishDiscountSumInt",
                    "DishReturnSum",
                ],
                "filters": {
                    self.olap_date_field: {
                        "filterType": "DateRange",
                        "periodType": "CUSTOM",
                        "from": date_from.isoformat(),
                        "to": date_to.isoformat(),
                        "includeLow": True,
                        "includeHigh": True,
                    }
                },
            }
            daily_payload = self.olap_report(key, daily_body)
            daily_rows = [r for r in daily_payload.get("data", []) if isinstance(r, dict)]

            product_body = {
                "reportType": "SALES",
                "buildSummary": False,
                "groupByRowFields": [self.olap_date_field, "Department.Code", "Department", "DishId", "DishName", "DishCategory"],
                "aggregateFields": [
                    "UniqOrderId.OrdersCount",
                    "DishAmountInt",
                    "DishSumInt",
                    "DiscountSum",
                    "DishDiscountSumInt",
                    "ProductCostBase.ProductCost",
                ],
                "filters": daily_body["filters"],
            }
            product_payload = self.olap_report(key, product_body)
            product_rows = [r for r in product_payload.get("data", []) if isinstance(r, dict)]

            payment_field = self.first_available(sales_columns, ["PayTypes", "PayTypes.Group", "PayTypes.GUID"], "groupingAllowed")
            payment_payload: dict[str, Any] = {"data": []}
            if payment_field:
                payment_body = {
                    "reportType": "SALES",
                    "buildSummary": False,
                    "groupByRowFields": [self.olap_date_field, "Department.Code", "Department", payment_field],
                    "aggregateFields": [x for x in ["UniqOrderId.OrdersCount", "DishSumInt"] if x in sales_columns],
                    "filters": daily_body["filters"],
                }
                payment_payload = self.olap_report(key, payment_body)

            discount_field = self.first_available(sales_columns, ["OrderDiscount.Type", "ItemSaleEventDiscountType", "DiscountPercent"], "groupingAllowed")
            discount_payload: dict[str, Any] = {"data": []}
            if discount_field:
                discount_body = {
                    "reportType": "SALES",
                    "buildSummary": False,
                    "groupByRowFields": [self.olap_date_field, "Department.Code", "Department", discount_field],
                    "aggregateFields": [x for x in ["UniqOrderId.OrdersCount", "DiscountSum", "DishDiscountSumInt"] if x in sales_columns],
                    "filters": daily_body["filters"],
                }
                discount_payload = self.olap_report(key, discount_body)

            staff_reports: list[tuple[str, str, dict[str, Any]]] = []
            for role, field in [
                ("cashier", self.first_available(sales_columns, ["Cashier", "Cashier.Id"], "groupingAllowed")),
                ("waiter", self.first_available(sales_columns, ["WaiterName", "OrderWaiter.Name", "WaiterTeam.Name"], "groupingAllowed")),
                ("courier", self.first_available(sales_columns, ["Delivery.Courier", "Delivery.Courier.Id"], "groupingAllowed")),
            ]:
                if not field:
                    continue
                body = {
                    "reportType": "SALES",
                    "buildSummary": False,
                    "groupByRowFields": [self.olap_date_field, "Department.Code", "Department", field],
                    "aggregateFields": [x for x in ["UniqOrderId.OrdersCount", "DishDiscountSumInt"] if x in sales_columns],
                    "filters": daily_body["filters"],
                }
                staff_reports.append((role, field, self.olap_report(key, body)))
        finally:
            self.olap_logout(key)

        with conn.cursor() as cur:
            self.insert_raw_payload(
                cur,
                "raw_server_olap_sales_daily",
                daily_payload,
                f"olap:SALES_DAILY:{date_from.isoformat()}:{date_to.isoformat()}",
                source_system="server_olap",
                report_type="SALES_DAILY",
                filters=daily_body["filters"],
                window_from=dt.datetime.combine(date_from, dt.time.min, tzinfo=MSK),
                window_to=dt.datetime.combine(date_to, dt.time.max, tzinfo=MSK),
            )
            self.insert_raw_payload(
                cur,
                "raw_server_olap_sales_daily",
                product_payload,
                f"olap:SALES_PRODUCT:{date_from.isoformat()}:{date_to.isoformat()}",
                source_system="server_olap",
                report_type="SALES_PRODUCT",
                filters=product_body["filters"],
                window_from=dt.datetime.combine(date_from, dt.time.min, tzinfo=MSK),
                window_to=dt.datetime.combine(date_to, dt.time.max, tzinfo=MSK),
            )
            payment_rows = [r for r in payment_payload.get("data", []) if isinstance(r, dict)]
            if payment_rows:
                self.insert_raw_payload(
                    cur,
                    "raw_server_olap_payments",
                    payment_payload,
                    f"olap:SALES_PAYMENTS:{date_from.isoformat()}:{date_to.isoformat()}",
                    source_system="server_olap",
                    report_type="SALES_PAYMENTS",
                    filters=daily_body["filters"],
                    window_from=dt.datetime.combine(date_from, dt.time.min, tzinfo=MSK),
                    window_to=dt.datetime.combine(date_to, dt.time.max, tzinfo=MSK),
                )
                for row in payment_rows:
                    business_date = dt.date.fromisoformat(str(row[self.olap_date_field])[:10])
                    org_id = self.olap_org_id(row.get("Department.Code"), row.get("Department"))
                    payment_type = str(row.get(payment_field or "") or "unknown")
                    group = payment_group(payment_type)
                    payment_sum = money(row.get("DishSumInt"))
                    orders_count = int(money(row.get("UniqOrderId.OrdersCount")))
                    cur.execute(
                        """
                        INSERT INTO mart_payments_daily(
                            business_date, organization_id, organization_name, payment_type,
                            payment_group, orders_count, payment_sum, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                        ON CONFLICT (business_date, organization_id, payment_type) DO UPDATE SET
                            organization_name = EXCLUDED.organization_name,
                            payment_group = EXCLUDED.payment_group,
                            orders_count = EXCLUDED.orders_count,
                            payment_sum = EXCLUDED.payment_sum,
                            updated_at = now()
                        """,
                        (business_date, org_id, str(row.get("Department") or ""), payment_type, group, orders_count, payment_sum),
                    )
            discount_rows = [r for r in discount_payload.get("data", []) if isinstance(r, dict)]
            if discount_rows:
                self.insert_raw_payload(
                    cur,
                    "raw_server_olap_sales_daily",
                    discount_payload,
                    f"olap:SALES_DISCOUNTS:{date_from.isoformat()}:{date_to.isoformat()}",
                    source_system="server_olap",
                    report_type="SALES_DISCOUNTS",
                    filters=daily_body["filters"],
                    window_from=dt.datetime.combine(date_from, dt.time.min, tzinfo=MSK),
                    window_to=dt.datetime.combine(date_to, dt.time.max, tzinfo=MSK),
                )
                for row in discount_rows:
                    business_date = dt.date.fromisoformat(str(row[self.olap_date_field])[:10])
                    org_id = self.olap_org_id(row.get("Department.Code"), row.get("Department"))
                    discount_name = str(row.get(discount_field or "") or "unknown")
                    discount_sum = money(row.get("DiscountSum"))
                    orders_count = int(money(row.get("UniqOrderId.OrdersCount")))
                    net = money(row.get("DishDiscountSumInt"))
                    cur.execute(
                        """
                        INSERT INTO mart_discount_promo(
                            business_date, organization_id, organization_name, discount_name, discount_type,
                            orders_count, gross_revenue, discount_sum, net_revenue, avg_discount_per_order,
                            discount_share, manual_discount_sum, manual_discount_orders, updated_at
                        )
                        VALUES (%s, %s, %s, %s, 'olap', %s, 0, %s, %s, %s, 0, 0, 0, now())
                        ON CONFLICT (business_date, organization_id, discount_name) DO UPDATE SET
                            organization_name = EXCLUDED.organization_name,
                            discount_type = EXCLUDED.discount_type,
                            orders_count = EXCLUDED.orders_count,
                            discount_sum = EXCLUDED.discount_sum,
                            net_revenue = EXCLUDED.net_revenue,
                            avg_discount_per_order = EXCLUDED.avg_discount_per_order,
                            updated_at = now()
                        """,
                        (
                            business_date,
                            org_id,
                            str(row.get("Department") or ""),
                            discount_name,
                            orders_count,
                            discount_sum,
                            net,
                            (discount_sum / orders_count) if orders_count else 0,
                        ),
                    )
            staff_rows_count = 0
            for role, field, staff_payload in staff_reports:
                staff_rows = [r for r in staff_payload.get("data", []) if isinstance(r, dict)]
                if not staff_rows:
                    continue
                staff_rows_count += len(staff_rows)
                self.insert_raw_payload(
                    cur,
                    "raw_server_olap_staff",
                    staff_payload,
                    f"olap:SALES_STAFF:{role}:{date_from.isoformat()}:{date_to.isoformat()}",
                    source_system="server_olap",
                    report_type=f"SALES_STAFF_{role.upper()}",
                    filters=daily_body["filters"],
                    window_from=dt.datetime.combine(date_from, dt.time.min, tzinfo=MSK),
                    window_to=dt.datetime.combine(date_to, dt.time.max, tzinfo=MSK),
                )
                for row in staff_rows:
                    business_date = dt.date.fromisoformat(str(row[self.olap_date_field])[:10])
                    org_id = self.olap_org_id(row.get("Department.Code"), row.get("Department"))
                    staff_name = str(row.get(field) or "unknown")
                    source_employee_id = None
                    if field.endswith(".Id") or field.endswith(".GUID"):
                        source_employee_id = row.get(field)
                    staff_employee_id = self.upsert_employee(
                        cur,
                        source_system="server_olap",
                        role=role,
                        employee_name=staff_name,
                        source_employee_id=source_employee_id,
                        source_fields={"olap_field": field},
                    )
                    orders_count = int(money(row.get("UniqOrderId.OrdersCount")))
                    net = money(row.get("DishDiscountSumInt"))
                    cur.execute(
                        """
                        INSERT INTO mart_staff_sales(
                            business_date, organization_id, organization_name, employee_id, staff_role, staff_name,
                            orders_count, net_revenue, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                        ON CONFLICT (business_date, organization_id, staff_role, staff_name) DO UPDATE SET
                            organization_name = EXCLUDED.organization_name,
                            employee_id = EXCLUDED.employee_id,
                            orders_count = EXCLUDED.orders_count,
                            net_revenue = EXCLUDED.net_revenue,
                            updated_at = now()
                        """,
                        (business_date, org_id, str(row.get("Department") or ""), staff_employee_id, role, staff_name, orders_count, net),
                    )
            for row in daily_rows:
                business_date = dt.date.fromisoformat(str(row[self.olap_date_field])[:10])
                org_id = self.olap_org_id(row.get("Department.Code"), row.get("Department"))
                org_name = str(row.get("Department") or row.get("Department.Code") or "unknown")
                order_source = str(row.get("OriginName") or "offline")
                orders_count = int(money(row.get("UniqOrderId.OrdersCount")))
                gross = money(row.get("DishSumInt"))
                discount = money(row.get("DiscountSum"))
                net = money(row.get("DishDiscountSumInt"))
                qty = money(row.get("DishAmountInt"))
                refund = money(row.get("DishReturnSum"))
                cur.execute(
                    """
                    INSERT INTO dim_organizations(organization_id, organization_name, organization_code, source_system, updated_at)
                    VALUES (%s, %s, %s, 'server_olap', now())
                    ON CONFLICT (organization_id) DO UPDATE SET
                        organization_name = EXCLUDED.organization_name,
                        organization_code = EXCLUDED.organization_code,
                        updated_at = now()
                    """,
                    (org_id, org_name, str(row.get("Department.Code") or "")),
                )
                cur.execute(
                    """
                    INSERT INTO mart_daily_sales(
                        business_date, organization_id, organization_name, order_source,
                        orders_count, gross_revenue, discount_sum, net_revenue, avg_check,
                        items_qty, cancelled_orders, refund_sum, discount_share, cancel_rate, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, 0, now())
                    ON CONFLICT (business_date, organization_id, order_source) DO UPDATE SET
                        organization_name = EXCLUDED.organization_name,
                        orders_count = EXCLUDED.orders_count,
                        gross_revenue = EXCLUDED.gross_revenue,
                        discount_sum = EXCLUDED.discount_sum,
                        net_revenue = EXCLUDED.net_revenue,
                        avg_check = EXCLUDED.avg_check,
                        items_qty = EXCLUDED.items_qty,
                        refund_sum = EXCLUDED.refund_sum,
                        discount_share = EXCLUDED.discount_share,
                        updated_at = now()
                    """,
                    (
                        business_date,
                        org_id,
                        org_name,
                        order_source,
                        orders_count,
                        gross,
                        discount,
                        net,
                        (net / orders_count) if orders_count else 0,
                        qty,
                        refund,
                        (discount / gross) if gross else 0,
                    ),
                )
            for row in product_rows:
                business_date = dt.date.fromisoformat(str(row[self.olap_date_field])[:10])
                org_id = self.olap_org_id(row.get("Department.Code"), row.get("Department"))
                org_name = str(row.get("Department") or row.get("Department.Code") or "unknown")
                product_raw = row.get("DishId") or row.get("DishName")
                product_id = as_uuid(product_raw, f"olap-product:{product_raw}:{row.get('DishName')}")
                product_name = str(row.get("DishName") or product_raw or "unknown")
                category_name = str(row.get("DishCategory") or "")
                qty = money(row.get("DishAmountInt"))
                gross = money(row.get("DishSumInt"))
                discount = money(row.get("DiscountSum"))
                net = money(row.get("DishDiscountSumInt"))
                cost = money(row.get("ProductCostBase.ProductCost"))
                orders_count = int(money(row.get("UniqOrderId.OrdersCount")))
                cur.execute(
                    """
                    INSERT INTO dim_products(product_id, product_name, category_name, cost_price, source_system, updated_at)
                    VALUES (%s, %s, %s, 0, 'server_olap', now())
                    ON CONFLICT (product_id) DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        category_name = COALESCE(NULLIF(EXCLUDED.category_name, ''), dim_products.category_name),
                        updated_at = now()
                    """,
                    (product_id, product_name, category_name),
                )
                cur.execute(
                    """
                    INSERT INTO mart_product_sales(
                        business_date, organization_id, organization_name, product_id, product_name, category_name,
                        items_qty, gross_revenue, discount_sum, net_revenue, cost_sum, profit_sum,
                        food_cost_percent, avg_price, orders_count, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (business_date, organization_id, product_id) DO UPDATE SET
                        organization_name = EXCLUDED.organization_name,
                        product_name = EXCLUDED.product_name,
                        category_name = EXCLUDED.category_name,
                        items_qty = EXCLUDED.items_qty,
                        gross_revenue = EXCLUDED.gross_revenue,
                        discount_sum = EXCLUDED.discount_sum,
                        net_revenue = EXCLUDED.net_revenue,
                        cost_sum = EXCLUDED.cost_sum,
                        profit_sum = EXCLUDED.profit_sum,
                        food_cost_percent = EXCLUDED.food_cost_percent,
                        avg_price = EXCLUDED.avg_price,
                        orders_count = EXCLUDED.orders_count,
                        updated_at = now()
                    """,
                    (
                        business_date,
                        org_id,
                        org_name,
                        product_id,
                        product_name,
                        category_name,
                        qty,
                        gross,
                        discount,
                        net,
                        cost,
                        net - cost,
                        (cost / net) if net else 0,
                        (net / qty) if qty else 0,
                        orders_count,
                    ),
                )
            cur.execute(
                """
                DELETE FROM mart_branch_kpi
                WHERE business_date BETWEEN %s AND %s
                """,
                (date_from, date_to),
            )
            cur.execute(
                """
                INSERT INTO mart_branch_kpi(
                    business_date, organization_id, organization_name, orders_count, net_revenue, avg_check,
                    discount_sum, discount_share, delivery_orders, late_orders, late_rate, refund_sum,
                    cancel_rate, total_losses, health_score, updated_at
                )
                SELECT
                    business_date,
                    organization_id,
                    max(organization_name),
                    sum(orders_count)::integer,
                    sum(net_revenue),
                    COALESCE(sum(net_revenue) / NULLIF(sum(orders_count), 0), 0)::numeric(14,2),
                    sum(discount_sum),
                    COALESCE(sum(discount_sum) / NULLIF(sum(gross_revenue), 0), 0)::numeric(14,6),
                    0,
                    0,
                    0,
                    sum(refund_sum),
                    0,
                    0,
                    GREATEST(0, 100 - COALESCE(sum(discount_sum) / NULLIF(sum(gross_revenue), 0), 0) * 20)::numeric(14,2),
                    now()
                FROM mart_daily_sales
                WHERE business_date BETWEEN %s AND %s
                GROUP BY business_date, organization_id
                """,
                (date_from, date_to),
            )
        return {
            "daily_sales": len(daily_rows),
            "branch_kpi": len(daily_rows),
            "product_sales": len(product_rows),
            "payment_sales": len(payment_rows) if "payment_rows" in locals() else 0,
            "discount_sales": len(discount_rows) if "discount_rows" in locals() else 0,
            "staff_sales": staff_rows_count if "staff_rows_count" in locals() else 0,
        }

    def run(
        self,
        date_from: dt.date,
        date_to: dt.date,
        include_all_orgs: bool = False,
        skip_nomenclature: bool = False,
        skip_olap: bool = False,
        only_nomenclature: bool = False,
        only_olap: bool = False,
    ) -> dict[str, Any]:
        if only_olap:
            with psycopg.connect(self.database_url) as conn:
                print(f"[sync] OLAP-only SALES marts {date_from}..{date_to}", flush=True)
                olap_counts = self.sync_olap_sales_marts(conn, date_from, date_to)
                conn.commit()
                print(f"[sync] OLAP-only SALES: {olap_counts}", flush=True)
                return {"mode": "only_olap", **olap_counts}

        orgs = self.selected_organizations(self.organizations(), include_all_orgs)
        if not orgs:
            raise RuntimeError("No organizations selected")
        print(f"[sync] organizations selected: {len(orgs)}", flush=True)
        totals = {"orders": 0, "items": 0, "payments": 0, "discounts": 0, "deliveries": 0, "raw_batches": 0}
        with psycopg.connect(self.database_url) as conn:
            self.sync_organizations(conn, orgs)
            conn.commit()
            product_count = 0
            if not skip_nomenclature:
                product_count = self.sync_nomenclature_all(conn, orgs)
                print(f"[sync] products loaded: {product_count}", flush=True)
            if only_nomenclature:
                conn.commit()
                return {"organizations": len(orgs), "products": product_count}
            try:
                terminal_group_count = self.sync_terminal_groups(conn, orgs)
            except requests.HTTPError as exc:
                terminal_group_count = 0
                print(f"[warn] terminal groups failed: {exc}", file=sys.stderr, flush=True)
            conn.commit()
            print(f"[sync] terminal group payloads loaded: {terminal_group_count}", flush=True)
            customer_category_count = self.sync_customer_categories(conn, orgs)
            conn.commit()
            print(f"[sync] customer category payloads loaded: {customer_category_count}", flush=True)
            external_menu_count = self.sync_external_menus(conn, orgs)
            conn.commit()
            print(f"[sync] external menu payloads loaded: {external_menu_count}", flush=True)
            stoplist_count = 0
            if self.sync_stoplists_enabled:
                stoplist_count = self.sync_stoplists(conn, orgs)
                conn.commit()
                print(f"[sync] active stoplist rows loaded: {stoplist_count}", flush=True)
            else:
                print("[sync] stoplists skipped: IIKO_SYNC_STOPLISTS is disabled", flush=True)
            for index, org in enumerate(orgs, 1):
                print(f"[sync] {index}/{len(orgs)} {org.get('name')}: deliveries {date_from}..{date_to}", flush=True)
                counts = self.sync_deliveries(conn, org, date_from, date_to)
                for key, value in counts.items():
                    totals[key] += value
                print(f"[sync] {org.get('name')}: {counts}", flush=True)
            self.refresh_marts(conn, date_from, date_to)
            olap_counts = {"daily_sales": 0, "branch_kpi": 0, "product_sales": 0}
            if not skip_olap:
                print(f"[sync] OLAP SALES marts {date_from}..{date_to}", flush=True)
                olap_counts = self.sync_olap_sales_marts(conn, date_from, date_to)
                print(f"[sync] OLAP SALES: {olap_counts}", flush=True)
            conn.commit()
        return {
            "organizations": len(orgs),
            "products": product_count,
            "terminal_group_payloads": terminal_group_count,
            "customer_category_payloads": customer_category_count,
            "external_menu_payloads": external_menu_count,
            "stoplist_items": stoplist_count,
            **totals,
            **olap_counts,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync iiko Cloud data into PostgreSQL mart pipeline.")
    today = dt.datetime.now(MSK).date()
    parser.add_argument("--date-from", type=parse_date, default=today - dt.timedelta(days=7))
    parser.add_argument("--date-to", type=parse_date, default=today)
    parser.add_argument("--all-orgs", action="store_true", help="Ignore IIKO_ORG_NUMBER_FROM/TO and load every organization.")
    parser.add_argument("--skip-nomenclature", action="store_true")
    parser.add_argument("--skip-olap", action="store_true")
    parser.add_argument("--only-nomenclature", action="store_true", help="Load one complete Cloud nomenclature source and exit.")
    parser.add_argument("--only-olap", action="store_true", help="Load only iikoServer OLAP marts for the date range.")
    args = parser.parse_args()
    try:
        result = IikoCloudSync().run(
            args.date_from,
            args.date_to,
            include_all_orgs=args.all_orgs,
            skip_nomenclature=args.skip_nomenclature,
            skip_olap=args.skip_olap,
            only_nomenclature=args.only_nomenclature,
            only_olap=args.only_olap,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"sync_iiko FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
