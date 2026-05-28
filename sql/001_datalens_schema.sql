\set ON_ERROR_STOP on

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS raw_cloud_organizations (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'cloud',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    provider_request_id text,
    correlation_id text,
    org_filter uuid,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_cloud_nomenclature (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'cloud',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    provider_request_id text,
    correlation_id text,
    org_filter uuid,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_cloud_deliveries_by_date_status (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'cloud',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    provider_request_id text,
    correlation_id text,
    org_filter uuid,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_cloud_stop_lists (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'cloud',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    provider_request_id text,
    correlation_id text,
    org_filter uuid,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_cloud_terminal_groups (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'cloud',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    provider_request_id text,
    correlation_id text,
    org_filter uuid,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_cloud_customer_categories (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'cloud',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    provider_request_id text,
    correlation_id text,
    org_filter uuid,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_cloud_external_menus (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'cloud',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    provider_request_id text,
    correlation_id text,
    org_filter uuid,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_server_olap_sales_daily (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'server_olap',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    report_type text,
    filters jsonb,
    department_filter text,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_server_olap_payments (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'server_olap',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    report_type text,
    filters jsonb,
    department_filter text,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_server_olap_staff (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'server_olap',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    report_type text,
    filters jsonb,
    department_filter text,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_server_olap_writeoffs (
    id bigserial PRIMARY KEY,
    source_system text NOT NULL DEFAULT 'server_olap',
    ingested_at timestamptz NOT NULL DEFAULT now(),
    extraction_started_at timestamptz,
    report_type text,
    filters jsonb,
    department_filter text,
    window_from timestamptz,
    window_to timestamptz,
    payload jsonb NOT NULL
);

ALTER TABLE raw_cloud_organizations ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_cloud_organizations ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_cloud_organizations ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_organizations ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_organizations ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_cloud_nomenclature ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_cloud_nomenclature ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_cloud_nomenclature ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_nomenclature ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_nomenclature ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_cloud_deliveries_by_date_status ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_cloud_deliveries_by_date_status ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_cloud_deliveries_by_date_status ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_deliveries_by_date_status ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_deliveries_by_date_status ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_cloud_stop_lists ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_cloud_stop_lists ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_cloud_stop_lists ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_stop_lists ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_stop_lists ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_cloud_terminal_groups ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_cloud_terminal_groups ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_cloud_terminal_groups ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_terminal_groups ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_terminal_groups ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_cloud_customer_categories ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_cloud_customer_categories ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_cloud_customer_categories ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_customer_categories ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_customer_categories ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_cloud_external_menus ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_cloud_external_menus ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_cloud_external_menus ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_external_menus ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_cloud_external_menus ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_server_olap_sales_daily ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_server_olap_sales_daily ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_server_olap_sales_daily ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_sales_daily ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_sales_daily ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_server_olap_payments ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_server_olap_payments ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_server_olap_payments ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_payments ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_payments ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_server_olap_staff ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_server_olap_staff ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_server_olap_staff ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_staff ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_staff ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

ALTER TABLE raw_server_olap_writeoffs ADD COLUMN IF NOT EXISTS request_key text;
ALTER TABLE raw_server_olap_writeoffs ADD COLUMN IF NOT EXISTS payload_hash text;
ALTER TABLE raw_server_olap_writeoffs ADD COLUMN IF NOT EXISTS first_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_writeoffs ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE raw_server_olap_writeoffs ADD COLUMN IF NOT EXISTS seen_count integer NOT NULL DEFAULT 1;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_cloud_organizations_request_hash
ON raw_cloud_organizations (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_cloud_nomenclature_request_hash
ON raw_cloud_nomenclature (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_cloud_deliveries_request_hash
ON raw_cloud_deliveries_by_date_status (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_cloud_stop_lists_request_hash
ON raw_cloud_stop_lists (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_cloud_terminal_groups_request_hash
ON raw_cloud_terminal_groups (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_cloud_customer_categories_request_hash
ON raw_cloud_customer_categories (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_cloud_external_menus_request_hash
ON raw_cloud_external_menus (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_server_olap_sales_request_hash
ON raw_server_olap_sales_daily (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_server_olap_payments_request_hash
ON raw_server_olap_payments (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_server_olap_staff_request_hash
ON raw_server_olap_staff (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_server_olap_writeoffs_request_hash
ON raw_server_olap_writeoffs (source_system, request_key, payload_hash)
WHERE request_key IS NOT NULL AND payload_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS etl_run_status (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name text NOT NULL,
    date_from date,
    date_to date,
    status text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    error_message text,
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS etl_load_checksums (
    source_system text NOT NULL,
    dataset_name text NOT NULL,
    business_date date NOT NULL,
    organization_id uuid,
    rows_count integer NOT NULL DEFAULT 0,
    orders_count integer NOT NULL DEFAULT 0,
    items_qty numeric(14,3) NOT NULL DEFAULT 0,
    gross_revenue numeric(14,2) NOT NULL DEFAULT 0,
    net_revenue numeric(14,2) NOT NULL DEFAULT 0,
    payload_hash text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_system, dataset_name, business_date, organization_id)
);

CREATE TABLE IF NOT EXISTS dim_organizations (
    organization_id uuid PRIMARY KEY,
    organization_name text NOT NULL,
    organization_code text,
    is_active boolean NOT NULL DEFAULT true,
    source_system text NOT NULL DEFAULT 'cloud',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id uuid PRIMARY KEY,
    product_name text NOT NULL,
    category_id uuid,
    category_name text,
    cost_price numeric(14,2),
    is_active boolean NOT NULL DEFAULT true,
    source_system text NOT NULL DEFAULT 'cloud',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_categories (
    category_id uuid PRIMARY KEY,
    category_name text NOT NULL,
    parent_category_id uuid REFERENCES dim_categories(category_id),
    parent_category_name text,
    source_system text NOT NULL DEFAULT 'cloud',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id uuid PRIMARY KEY,
    phone_hash text,
    first_order_date date,
    source_system text NOT NULL DEFAULT 'cloud',
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS customer_name text;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS customer_surname text;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS birthdate date;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS gender text;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS customer_type text;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS in_blacklist boolean NOT NULL DEFAULT false;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS blacklist_reason text;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS last_order_date date;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS orders_count integer NOT NULL DEFAULT 0;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS total_revenue numeric(14,2) NOT NULL DEFAULT 0;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS avg_check numeric(14,2) NOT NULL DEFAULT 0;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS first_order_source text;
ALTER TABLE dim_customers ADD COLUMN IF NOT EXISTS first_organization_id uuid REFERENCES dim_organizations(organization_id);

ALTER TABLE dim_products ADD COLUMN IF NOT EXISTS product_type text;
ALTER TABLE dim_products ADD COLUMN IF NOT EXISTS measure_unit text;
ALTER TABLE dim_products ADD COLUMN IF NOT EXISTS weight numeric(14,3);
ALTER TABLE dim_products ADD COLUMN IF NOT EXISTS product_code text;
ALTER TABLE dim_products ADD COLUMN IF NOT EXISTS sku text;
ALTER TABLE dim_products ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS dim_product_prices (
    product_id uuid NOT NULL REFERENCES dim_products(product_id),
    organization_id uuid REFERENCES dim_organizations(organization_id),
    price_category text NOT NULL DEFAULT 'default',
    size_name text NOT NULL DEFAULT '',
    price numeric(14,2) NOT NULL DEFAULT 0,
    source_system text NOT NULL DEFAULT 'cloud',
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (product_id, organization_id, price_category, size_name)
);

CREATE TABLE IF NOT EXISTS dim_product_availability (
    product_id uuid NOT NULL REFERENCES dim_products(product_id),
    organization_id uuid REFERENCES dim_organizations(organization_id),
    menu_id text NOT NULL DEFAULT '',
    size_name text NOT NULL DEFAULT '',
    is_available boolean NOT NULL DEFAULT true,
    source_system text NOT NULL DEFAULT 'cloud_menu',
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (product_id, organization_id, menu_id, size_name)
);

CREATE TABLE IF NOT EXISTS dim_employees (
    employee_id uuid PRIMARY KEY,
    source_system text NOT NULL,
    source_employee_id text,
    employee_name text NOT NULL,
    normalized_name text NOT NULL,
    role text NOT NULL,
    phone_hash text,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    is_active_guess boolean NOT NULL DEFAULT true,
    source_fields jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_employees_source_role_source_id
ON dim_employees (source_system, role, source_employee_id)
WHERE source_employee_id IS NOT NULL AND source_employee_id <> '';

CREATE INDEX IF NOT EXISTS idx_dim_employees_role_name
ON dim_employees (role, normalized_name);

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id uuid PRIMARY KEY,
    business_date date NOT NULL,
    opened_at timestamptz,
    closed_at timestamptz,
    organization_id uuid REFERENCES dim_organizations(organization_id),
    customer_id uuid REFERENCES dim_customers(customer_id),
    order_source text NOT NULL DEFAULT 'unknown',
    order_type text,
    status text,
    is_delivery boolean NOT NULL DEFAULT false,
    is_cancelled boolean NOT NULL DEFAULT false,
    gross_revenue numeric(14,2) NOT NULL DEFAULT 0,
    discount_sum numeric(14,2) NOT NULL DEFAULT 0,
    net_revenue numeric(14,2) NOT NULL DEFAULT 0,
    refund_sum numeric(14,2) NOT NULL DEFAULT 0,
    source_system text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS external_order_id text;
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS order_number text;
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS terminal_group_id text;
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS marketing_source text;
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS operator_name text;
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS operator_employee_id uuid REFERENCES dim_employees(employee_id);
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS guests_count integer;
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS processed_payments_sum numeric(14,2) NOT NULL DEFAULT 0;
ALTER TABLE fact_orders ADD COLUMN IF NOT EXISTS tips_sum numeric(14,2) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS fact_order_items (
    order_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES fact_orders(order_id) ON DELETE CASCADE,
    business_date date NOT NULL,
    organization_id uuid REFERENCES dim_organizations(organization_id),
    product_id uuid REFERENCES dim_products(product_id),
    quantity numeric(14,3) NOT NULL DEFAULT 0,
    gross_revenue numeric(14,2) NOT NULL DEFAULT 0,
    discount_sum numeric(14,2) NOT NULL DEFAULT 0,
    net_revenue numeric(14,2) NOT NULL DEFAULT 0,
    cost_sum numeric(14,2) NOT NULL DEFAULT 0,
    source_system text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS product_name text;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS category_name text;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS unit_price numeric(14,2) NOT NULL DEFAULT 0;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS item_status text;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS is_modifier boolean NOT NULL DEFAULT false;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS parent_item_id uuid;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS modifiers_json jsonb;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS combo_json jsonb;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS size_name text;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS when_printed timestamptz;
ALTER TABLE fact_order_items ADD COLUMN IF NOT EXISTS tax_percent numeric(8,4);

CREATE TABLE IF NOT EXISTS fact_payments (
    payment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES fact_orders(order_id) ON DELETE CASCADE,
    business_date date NOT NULL,
    organization_id uuid REFERENCES dim_organizations(organization_id),
    payment_type text,
    payment_sum numeric(14,2) NOT NULL DEFAULT 0,
    source_system text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE fact_payments ADD COLUMN IF NOT EXISTS payment_group text;
ALTER TABLE fact_payments ADD COLUMN IF NOT EXISTS is_fiscalized_externally boolean NOT NULL DEFAULT false;
ALTER TABLE fact_payments ADD COLUMN IF NOT EXISTS is_prepay boolean NOT NULL DEFAULT false;
ALTER TABLE fact_payments ADD COLUMN IF NOT EXISTS is_external boolean NOT NULL DEFAULT false;
ALTER TABLE fact_payments ADD COLUMN IF NOT EXISTS is_processed_externally boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS fact_discounts (
    discount_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES fact_orders(order_id) ON DELETE CASCADE,
    business_date date NOT NULL,
    organization_id uuid REFERENCES dim_organizations(organization_id),
    discount_name text NOT NULL DEFAULT 'unknown',
    discount_type text,
    discount_sum numeric(14,2) NOT NULL DEFAULT 0,
    is_manual boolean NOT NULL DEFAULT false,
    source_system text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fact_deliveries (
    delivery_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid REFERENCES fact_orders(order_id) ON DELETE SET NULL,
    business_date date NOT NULL,
    organization_id uuid REFERENCES dim_organizations(organization_id),
    delivery_zone text NOT NULL DEFAULT 'unknown',
    delivery_status text NOT NULL DEFAULT 'unknown',
    delivery_minutes numeric(14,2),
    delay_minutes numeric(14,2),
    cooking_minutes numeric(14,2),
    courier_waiting_minutes numeric(14,2),
    is_late boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT false,
    source_system text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS address_text text;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS latitude numeric(12,8);
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS longitude numeric(12,8);
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS courier_name text;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS courier_employee_id uuid REFERENCES dim_employees(employee_id);
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS courier_phone_hash text;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS complete_before timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS when_confirmed timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS cooking_started_at timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS cooking_completed_at timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS when_packed timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS when_sent timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS when_delivered timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS when_received_by_api timestamptz;
ALTER TABLE fact_deliveries ADD COLUMN IF NOT EXISTS external_courier_service text;

CREATE TABLE IF NOT EXISTS fact_stoplists (
    stoplist_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid REFERENCES dim_organizations(organization_id),
    product_id uuid REFERENCES dim_products(product_id),
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    avg_revenue_per_hour numeric(14,2) NOT NULL DEFAULT 0,
    source_system text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fact_losses (
    loss_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_date date NOT NULL,
    organization_id uuid REFERENCES dim_organizations(organization_id),
    order_id uuid REFERENCES fact_orders(order_id) ON DELETE SET NULL,
    loss_type text NOT NULL,
    loss_reason text,
    loss_sum numeric(14,2) NOT NULL DEFAULT 0,
    source_system text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE fact_losses ADD COLUMN IF NOT EXISTS source_loss_key text;
ALTER TABLE fact_losses ADD COLUMN IF NOT EXISTS order_item_id uuid;
ALTER TABLE fact_losses ADD COLUMN IF NOT EXISTS employee_id text;
ALTER TABLE fact_losses ADD COLUMN IF NOT EXISTS employee_uuid uuid REFERENCES dim_employees(employee_id);
ALTER TABLE fact_losses ADD COLUMN IF NOT EXISTS comment text;

CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_losses_source_loss_key
ON fact_losses (source_loss_key)
WHERE source_loss_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS fact_customer_orders (
    customer_id uuid NOT NULL REFERENCES dim_customers(customer_id),
    order_id uuid NOT NULL REFERENCES fact_orders(order_id) ON DELETE CASCADE,
    organization_id uuid REFERENCES dim_organizations(organization_id),
    business_date date NOT NULL,
    order_number_by_customer integer NOT NULL,
    days_since_previous_order integer,
    is_first_order boolean NOT NULL DEFAULT false,
    is_repeat_order boolean NOT NULL DEFAULT false,
    net_revenue numeric(14,2) NOT NULL DEFAULT 0,
    order_source text NOT NULL DEFAULT 'unknown',
    source_system text NOT NULL DEFAULT 'cloud',
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (customer_id, order_id)
);

CREATE TABLE IF NOT EXISTS mart_daily_sales (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    order_source text NOT NULL,
    orders_count integer NOT NULL,
    gross_revenue numeric(14,2) NOT NULL,
    discount_sum numeric(14,2) NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    avg_check numeric(14,2) NOT NULL,
    items_qty numeric(14,3) NOT NULL,
    cancelled_orders integer NOT NULL,
    refund_sum numeric(14,2) NOT NULL,
    discount_share numeric(14,6) NOT NULL,
    cancel_rate numeric(14,6) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, order_source)
);

CREATE TABLE IF NOT EXISTS mart_branch_kpi (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    orders_count integer NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    avg_check numeric(14,2) NOT NULL,
    discount_sum numeric(14,2) NOT NULL,
    discount_share numeric(14,6) NOT NULL,
    delivery_orders integer NOT NULL,
    late_orders integer NOT NULL,
    late_rate numeric(14,6) NOT NULL,
    refund_sum numeric(14,2) NOT NULL,
    cancel_rate numeric(14,6) NOT NULL,
    total_losses numeric(14,2) NOT NULL,
    health_score numeric(14,2) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id)
);

CREATE TABLE IF NOT EXISTS mart_product_sales (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    product_id uuid,
    product_name text,
    category_name text,
    items_qty numeric(14,3) NOT NULL,
    gross_revenue numeric(14,2) NOT NULL,
    discount_sum numeric(14,2) NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    cost_sum numeric(14,2) NOT NULL,
    profit_sum numeric(14,2) NOT NULL,
    food_cost_percent numeric(14,6) NOT NULL,
    avg_price numeric(14,2) NOT NULL,
    orders_count integer NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, product_id)
);

CREATE TABLE IF NOT EXISTS mart_delivery_sla (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    delivery_zone text NOT NULL,
    delivery_orders integer NOT NULL,
    avg_delivery_minutes numeric(14,2),
    p90_delivery_minutes numeric(14,2),
    p95_delivery_minutes numeric(14,2),
    late_orders integer NOT NULL,
    late_rate numeric(14,6) NOT NULL,
    avg_delay_minutes numeric(14,2),
    sla_rate numeric(14,6) NOT NULL,
    avg_cooking_minutes numeric(14,2),
    avg_courier_waiting_minutes numeric(14,2),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, delivery_zone)
);

CREATE TABLE IF NOT EXISTS mart_discount_promo (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    discount_name text NOT NULL,
    discount_type text,
    orders_count integer NOT NULL,
    gross_revenue numeric(14,2) NOT NULL,
    discount_sum numeric(14,2) NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    avg_discount_per_order numeric(14,2) NOT NULL,
    discount_share numeric(14,6) NOT NULL,
    manual_discount_sum numeric(14,2) NOT NULL,
    manual_discount_orders integer NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, discount_name)
);

CREATE TABLE IF NOT EXISTS mart_customer_retention (
    cohort_month date NOT NULL,
    order_month date NOT NULL,
    months_since_first_order integer NOT NULL,
    order_source text NOT NULL,
    customers_count integer NOT NULL,
    repeat_customers integer NOT NULL,
    orders_count integer NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    avg_check numeric(14,2) NOT NULL,
    ltv numeric(14,2) NOT NULL,
    retention_rate numeric(14,6) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (cohort_month, order_month, order_source)
);

CREATE TABLE IF NOT EXISTS mart_customer_summary (
    customer_id uuid PRIMARY KEY,
    first_order_date date,
    last_order_date date,
    first_order_source text,
    first_organization_id uuid,
    first_organization_name text,
    orders_count integer NOT NULL,
    repeat_orders integer NOT NULL,
    total_revenue numeric(14,2) NOT NULL,
    avg_check numeric(14,2) NOT NULL,
    days_since_last_order integer,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mart_losses (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    loss_type text NOT NULL,
    loss_reason text,
    loss_sum numeric(14,2) NOT NULL,
    orders_affected integer NOT NULL,
    loss_share numeric(14,6) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, loss_type, loss_reason)
);

CREATE TABLE IF NOT EXISTS mart_payments_daily (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    payment_type text NOT NULL,
    payment_group text,
    orders_count integer NOT NULL,
    payment_sum numeric(14,2) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, payment_type)
);

CREATE TABLE IF NOT EXISTS mart_staff_sales (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    employee_id uuid REFERENCES dim_employees(employee_id),
    staff_role text NOT NULL,
    staff_name text NOT NULL,
    orders_count integer NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, staff_role, staff_name)
);

ALTER TABLE mart_staff_sales ADD COLUMN IF NOT EXISTS employee_id uuid REFERENCES dim_employees(employee_id);

CREATE TABLE IF NOT EXISTS mart_today_sales (
    business_date date NOT NULL,
    hour integer NOT NULL,
    organization_id uuid,
    organization_name text,
    order_source text NOT NULL,
    orders_count integer NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    avg_check numeric(14,2) NOT NULL,
    discount_sum numeric(14,2) NOT NULL,
    last_order_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, hour, organization_id, order_source)
);

CREATE TABLE IF NOT EXISTS mart_today_delivery (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    delivery_status text NOT NULL,
    delivery_orders integer NOT NULL,
    late_orders integer NOT NULL,
    late_rate numeric(14,6) NOT NULL,
    avg_delivery_minutes numeric(14,2),
    p90_delivery_minutes numeric(14,2),
    active_deliveries integer NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, delivery_status)
);

CREATE TABLE IF NOT EXISTS mart_today_stoplists (
    business_date date NOT NULL DEFAULT current_date,
    organization_id uuid,
    organization_name text,
    product_id uuid,
    product_name text,
    category_name text,
    started_at timestamptz NOT NULL,
    duration_minutes numeric(14,2) NOT NULL,
    avg_revenue_per_hour numeric(14,2) NOT NULL,
    lost_revenue_estimate numeric(14,2) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id, product_id, started_at)
);

ALTER TABLE mart_today_stoplists ADD COLUMN IF NOT EXISTS business_date date NOT NULL DEFAULT current_date;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'mart_today_stoplists_pkey'
          AND conrelid = 'mart_today_stoplists'::regclass
    ) THEN
        ALTER TABLE mart_today_stoplists DROP CONSTRAINT mart_today_stoplists_pkey;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'mart_today_stoplists_pkey'
          AND conrelid = 'mart_today_stoplists'::regclass
    ) THEN
        ALTER TABLE mart_today_stoplists
        ADD CONSTRAINT mart_today_stoplists_pkey PRIMARY KEY (business_date, organization_id, product_id, started_at);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS mart_today_branch_status (
    business_date date NOT NULL,
    organization_id uuid,
    organization_name text,
    orders_count integer NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    avg_check numeric(14,2) NOT NULL,
    delivery_orders integer NOT NULL,
    late_orders integer NOT NULL,
    late_rate numeric(14,6) NOT NULL,
    active_deliveries integer NOT NULL,
    active_stoplist_items integer NOT NULL,
    health_score_today numeric(14,2) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (business_date, organization_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_orders_date_org ON fact_orders (business_date, organization_id);
CREATE INDEX IF NOT EXISTS idx_fact_order_items_date_org ON fact_order_items (business_date, organization_id);
CREATE INDEX IF NOT EXISTS idx_fact_deliveries_date_org ON fact_deliveries (business_date, organization_id);
CREATE INDEX IF NOT EXISTS idx_fact_discounts_date_org ON fact_discounts (business_date, organization_id);
CREATE INDEX IF NOT EXISTS idx_fact_losses_date_org ON fact_losses (business_date, organization_id);
CREATE INDEX IF NOT EXISTS idx_fact_customer_orders_date_org ON fact_customer_orders (business_date, organization_id);
CREATE INDEX IF NOT EXISTS idx_fact_customer_orders_customer ON fact_customer_orders (customer_id, business_date);

CREATE OR REPLACE FUNCTION refresh_datalens_marts(p_date_from date DEFAULT NULL, p_date_to date DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    TRUNCATE TABLE fact_customer_orders;

    INSERT INTO fact_customer_orders(
        customer_id, order_id, organization_id, business_date, order_number_by_customer,
        days_since_previous_order, is_first_order, is_repeat_order, net_revenue, order_source,
        source_system, updated_at
    )
    WITH customer_orders AS (
        SELECT
            o.customer_id,
            o.order_id,
            o.organization_id,
            o.business_date,
            o.net_revenue,
            o.order_source,
            o.source_system,
            row_number() OVER (
                PARTITION BY o.customer_id
                ORDER BY o.business_date, COALESCE(o.closed_at, o.opened_at, o.updated_at), o.order_id
            )::integer AS order_number_by_customer,
            lag(o.business_date) OVER (
                PARTITION BY o.customer_id
                ORDER BY o.business_date, COALESCE(o.closed_at, o.opened_at, o.updated_at), o.order_id
            ) AS previous_business_date
        FROM fact_orders o
        WHERE o.customer_id IS NOT NULL
    )
    SELECT
        customer_id,
        order_id,
        organization_id,
        business_date,
        order_number_by_customer,
        CASE
            WHEN previous_business_date IS NULL THEN NULL
            ELSE business_date - previous_business_date
        END,
        order_number_by_customer = 1,
        order_number_by_customer > 1,
        net_revenue,
        order_source,
        source_system,
        now()
    FROM customer_orders;

    WITH first_orders AS (
        SELECT DISTINCT ON (customer_id)
            customer_id,
            business_date AS first_order_date,
            order_source AS first_order_source,
            organization_id AS first_organization_id
        FROM fact_customer_orders
        ORDER BY customer_id, order_number_by_customer
    ),
    customer_agg AS (
        SELECT
            customer_id,
            min(business_date) AS first_order_date,
            max(business_date) AS last_order_date,
            count(*)::integer AS orders_count,
            sum(net_revenue)::numeric(14,2) AS total_revenue,
            COALESCE(sum(net_revenue) / NULLIF(count(*), 0), 0)::numeric(14,2) AS avg_check
        FROM fact_customer_orders
        GROUP BY customer_id
    )
    UPDATE dim_customers c
    SET
        first_order_date = COALESCE(LEAST(c.first_order_date, a.first_order_date), a.first_order_date, c.first_order_date),
        last_order_date = a.last_order_date,
        orders_count = a.orders_count,
        total_revenue = a.total_revenue,
        avg_check = a.avg_check,
        first_order_source = COALESCE(c.first_order_source, f.first_order_source),
        first_organization_id = COALESCE(c.first_organization_id, f.first_organization_id),
        updated_at = now()
    FROM customer_agg a
    LEFT JOIN first_orders f ON f.customer_id = a.customer_id
    WHERE c.customer_id = a.customer_id;

    DELETE FROM mart_daily_sales
    WHERE (p_date_from IS NULL OR business_date >= p_date_from)
      AND (p_date_to IS NULL OR business_date <= p_date_to);

    INSERT INTO mart_daily_sales
    SELECT
        o.business_date,
        o.organization_id,
        COALESCE(org.organization_name, 'unknown') AS organization_name,
        o.order_source,
        count(*)::integer AS orders_count,
        sum(o.gross_revenue) AS gross_revenue,
        sum(o.discount_sum) AS discount_sum,
        sum(o.net_revenue) AS net_revenue,
        COALESCE(sum(o.net_revenue) / NULLIF(count(*), 0), 0)::numeric(14,2) AS avg_check,
        COALESCE(sum(i.quantity), 0)::numeric(14,3) AS items_qty,
        count(*) FILTER (WHERE o.is_cancelled)::integer AS cancelled_orders,
        sum(o.refund_sum) AS refund_sum,
        COALESCE(sum(o.discount_sum) / NULLIF(sum(o.gross_revenue), 0), 0)::numeric(14,6) AS discount_share,
        COALESCE((count(*) FILTER (WHERE o.is_cancelled))::numeric / NULLIF(count(*), 0), 0)::numeric(14,6) AS cancel_rate,
        now()
    FROM fact_orders o
    LEFT JOIN dim_organizations org ON org.organization_id = o.organization_id
    LEFT JOIN (
        SELECT order_id, sum(quantity) AS quantity
        FROM fact_order_items
        GROUP BY order_id
    ) i ON i.order_id = o.order_id
    WHERE (p_date_from IS NULL OR o.business_date >= p_date_from)
      AND (p_date_to IS NULL OR o.business_date <= p_date_to)
    GROUP BY o.business_date, o.organization_id, org.organization_name, o.order_source;

    DELETE FROM mart_branch_kpi
    WHERE (p_date_from IS NULL OR business_date >= p_date_from)
      AND (p_date_to IS NULL OR business_date <= p_date_to);

    INSERT INTO mart_branch_kpi
    WITH order_agg AS (
        SELECT
            o.business_date,
            o.organization_id,
            count(*)::integer AS orders_count,
            sum(o.net_revenue) AS net_revenue,
            COALESCE(sum(o.net_revenue) / NULLIF(count(*), 0), 0)::numeric(14,2) AS avg_check,
            sum(o.discount_sum) AS discount_sum,
            COALESCE(sum(o.discount_sum) / NULLIF(sum(o.gross_revenue), 0), 0)::numeric(14,6) AS discount_share,
            sum(o.refund_sum) AS refund_sum,
            COALESCE((count(*) FILTER (WHERE o.is_cancelled))::numeric / NULLIF(count(*), 0), 0)::numeric(14,6) AS cancel_rate
        FROM fact_orders o
        WHERE (p_date_from IS NULL OR o.business_date >= p_date_from)
          AND (p_date_to IS NULL OR o.business_date <= p_date_to)
        GROUP BY o.business_date, o.organization_id
    ),
    delivery_agg AS (
        SELECT
            d.business_date,
            d.organization_id,
            count(*)::integer AS delivery_orders,
            count(*) FILTER (WHERE d.is_late)::integer AS late_orders,
            COALESCE((count(*) FILTER (WHERE d.is_late))::numeric / NULLIF(count(*), 0), 0)::numeric(14,6) AS late_rate
        FROM fact_deliveries d
        WHERE (p_date_from IS NULL OR d.business_date >= p_date_from)
          AND (p_date_to IS NULL OR d.business_date <= p_date_to)
        GROUP BY d.business_date, d.organization_id
    ),
    loss_agg AS (
        SELECT business_date, organization_id, sum(loss_sum) AS total_losses
        FROM fact_losses
        WHERE (p_date_from IS NULL OR business_date >= p_date_from)
          AND (p_date_to IS NULL OR business_date <= p_date_to)
        GROUP BY business_date, organization_id
    )
    SELECT
        a.business_date,
        a.organization_id,
        COALESCE(org.organization_name, 'unknown') AS organization_name,
        a.orders_count,
        a.net_revenue,
        a.avg_check,
        a.discount_sum,
        a.discount_share,
        COALESCE(d.delivery_orders, 0),
        COALESCE(d.late_orders, 0),
        COALESCE(d.late_rate, 0),
        a.refund_sum,
        a.cancel_rate,
        COALESCE(l.total_losses, 0),
        GREATEST(
            0,
            100
            - COALESCE(d.late_rate, 0) * 30
            - a.cancel_rate * 30
            - a.discount_share * 20
            - COALESCE(a.refund_sum / NULLIF(a.net_revenue, 0), 0) * 20
        )::numeric(14,2) AS health_score,
        now()
    FROM order_agg a
    LEFT JOIN delivery_agg d ON d.business_date = a.business_date AND d.organization_id = a.organization_id
    LEFT JOIN loss_agg l ON l.business_date = a.business_date AND l.organization_id = a.organization_id
    LEFT JOIN dim_organizations org ON org.organization_id = a.organization_id;

    DELETE FROM mart_product_sales
    WHERE (p_date_from IS NULL OR business_date >= p_date_from)
      AND (p_date_to IS NULL OR business_date <= p_date_to);

    INSERT INTO mart_product_sales
    SELECT
        i.business_date,
        i.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        i.product_id,
        COALESCE(p.product_name, 'unknown'),
        p.category_name,
        sum(i.quantity)::numeric(14,3),
        sum(i.gross_revenue),
        sum(i.discount_sum),
        sum(i.net_revenue),
        sum(i.cost_sum),
        (sum(i.net_revenue) - sum(i.cost_sum))::numeric(14,2),
        COALESCE(sum(i.cost_sum) / NULLIF(sum(i.net_revenue), 0), 0)::numeric(14,6),
        COALESCE(sum(i.net_revenue) / NULLIF(sum(i.quantity), 0), 0)::numeric(14,2),
        count(DISTINCT i.order_id)::integer,
        now()
    FROM fact_order_items i
    LEFT JOIN dim_organizations org ON org.organization_id = i.organization_id
    LEFT JOIN dim_products p ON p.product_id = i.product_id
    WHERE (p_date_from IS NULL OR i.business_date >= p_date_from)
      AND (p_date_to IS NULL OR i.business_date <= p_date_to)
    GROUP BY i.business_date, i.organization_id, org.organization_name, i.product_id, p.product_name, p.category_name;

    DELETE FROM mart_delivery_sla
    WHERE (p_date_from IS NULL OR business_date >= p_date_from)
      AND (p_date_to IS NULL OR business_date <= p_date_to);

    INSERT INTO mart_delivery_sla
    SELECT
        d.business_date,
        d.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        d.delivery_zone,
        count(*)::integer,
        avg(d.delivery_minutes)::numeric(14,2),
        percentile_cont(0.90) WITHIN GROUP (ORDER BY d.delivery_minutes)::numeric(14,2),
        percentile_cont(0.95) WITHIN GROUP (ORDER BY d.delivery_minutes)::numeric(14,2),
        count(*) FILTER (WHERE d.is_late)::integer,
        COALESCE((count(*) FILTER (WHERE d.is_late))::numeric / NULLIF(count(*), 0), 0)::numeric(14,6),
        avg(d.delay_minutes)::numeric(14,2),
        (1 - COALESCE((count(*) FILTER (WHERE d.is_late))::numeric / NULLIF(count(*), 0), 0))::numeric(14,6),
        avg(d.cooking_minutes)::numeric(14,2),
        avg(d.courier_waiting_minutes)::numeric(14,2),
        now()
    FROM fact_deliveries d
    LEFT JOIN dim_organizations org ON org.organization_id = d.organization_id
    WHERE (p_date_from IS NULL OR d.business_date >= p_date_from)
      AND (p_date_to IS NULL OR d.business_date <= p_date_to)
    GROUP BY d.business_date, d.organization_id, org.organization_name, d.delivery_zone;

    DELETE FROM mart_discount_promo
    WHERE (p_date_from IS NULL OR business_date >= p_date_from)
      AND (p_date_to IS NULL OR business_date <= p_date_to);

    INSERT INTO mart_discount_promo
    SELECT
        d.business_date,
        d.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        d.discount_name,
        d.discount_type,
        count(DISTINCT d.order_id)::integer,
        COALESCE(sum(o.gross_revenue), 0),
        sum(d.discount_sum),
        COALESCE(sum(o.net_revenue), 0),
        COALESCE(sum(d.discount_sum) / NULLIF(count(DISTINCT d.order_id), 0), 0)::numeric(14,2),
        COALESCE(sum(d.discount_sum) / NULLIF(sum(o.gross_revenue), 0), 0)::numeric(14,6),
        COALESCE(sum(d.discount_sum) FILTER (WHERE d.is_manual), 0),
        count(DISTINCT d.order_id) FILTER (WHERE d.is_manual)::integer,
        now()
    FROM fact_discounts d
    LEFT JOIN fact_orders o ON o.order_id = d.order_id
    LEFT JOIN dim_organizations org ON org.organization_id = d.organization_id
    WHERE (p_date_from IS NULL OR d.business_date >= p_date_from)
      AND (p_date_to IS NULL OR d.business_date <= p_date_to)
    GROUP BY d.business_date, d.organization_id, org.organization_name, d.discount_name, d.discount_type;

    DELETE FROM mart_customer_retention
    WHERE (p_date_from IS NULL OR order_month >= date_trunc('month', p_date_from)::date)
      AND (p_date_to IS NULL OR order_month <= date_trunc('month', p_date_to)::date);

    INSERT INTO mart_customer_retention
    SELECT
        date_trunc('month', c.first_order_date)::date AS cohort_month,
        date_trunc('month', o.business_date)::date AS order_month,
        (
            extract(year FROM age(date_trunc('month', o.business_date), date_trunc('month', c.first_order_date))) * 12
            + extract(month FROM age(date_trunc('month', o.business_date), date_trunc('month', c.first_order_date)))
        )::integer AS months_since_first_order,
        o.order_source,
        count(DISTINCT o.customer_id)::integer AS customers_count,
        count(DISTINCT o.customer_id) FILTER (WHERE o.business_date > c.first_order_date)::integer AS repeat_customers,
        count(*)::integer AS orders_count,
        sum(o.net_revenue) AS net_revenue,
        COALESCE(sum(o.net_revenue) / NULLIF(count(*), 0), 0)::numeric(14,2) AS avg_check,
        COALESCE(sum(o.net_revenue) / NULLIF(count(DISTINCT o.customer_id), 0), 0)::numeric(14,2) AS ltv,
        COALESCE(
            (count(DISTINCT o.customer_id) FILTER (WHERE o.business_date > c.first_order_date))::numeric
            / NULLIF(count(DISTINCT o.customer_id), 0),
            0
        )::numeric(14,6) AS retention_rate,
        now()
    FROM fact_orders o
    JOIN dim_customers c ON c.customer_id = o.customer_id
    WHERE c.first_order_date IS NOT NULL
      AND (p_date_from IS NULL OR o.business_date >= p_date_from)
      AND (p_date_to IS NULL OR o.business_date <= p_date_to)
    GROUP BY cohort_month, order_month, months_since_first_order, o.order_source;

    TRUNCATE TABLE mart_customer_summary;

    INSERT INTO mart_customer_summary
    SELECT
        c.customer_id,
        c.first_order_date,
        c.last_order_date,
        c.first_order_source,
        c.first_organization_id,
        org.organization_name,
        c.orders_count,
        GREATEST(c.orders_count - 1, 0)::integer AS repeat_orders,
        c.total_revenue,
        c.avg_check,
        CASE
            WHEN c.last_order_date IS NULL THEN NULL
            ELSE current_date - c.last_order_date
        END AS days_since_last_order,
        now()
    FROM dim_customers c
    LEFT JOIN dim_organizations org ON org.organization_id = c.first_organization_id
    WHERE c.orders_count > 0;

    DELETE FROM mart_losses
    WHERE (p_date_from IS NULL OR business_date >= p_date_from)
      AND (p_date_to IS NULL OR business_date <= p_date_to);

    INSERT INTO mart_losses
    SELECT
        l.business_date,
        l.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        l.loss_type,
        l.loss_reason,
        sum(l.loss_sum),
        count(DISTINCT l.order_id)::integer,
        COALESCE(sum(l.loss_sum) / NULLIF(sum(o.net_revenue), 0), 0)::numeric(14,6),
        now()
    FROM fact_losses l
    LEFT JOIN fact_orders o ON o.order_id = l.order_id
    LEFT JOIN dim_organizations org ON org.organization_id = l.organization_id
    WHERE (p_date_from IS NULL OR l.business_date >= p_date_from)
      AND (p_date_to IS NULL OR l.business_date <= p_date_to)
    GROUP BY l.business_date, l.organization_id, org.organization_name, l.loss_type, l.loss_reason;
END;
$$;

CREATE OR REPLACE FUNCTION refresh_datalens_today_marts()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    today date := current_date;
BEGIN
    DELETE FROM mart_today_sales WHERE business_date = today;

    INSERT INTO mart_today_sales
    SELECT
        o.business_date,
        extract(hour FROM COALESCE(o.closed_at, o.opened_at, o.updated_at))::integer AS hour,
        o.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        o.order_source,
        count(*)::integer,
        sum(o.net_revenue),
        COALESCE(sum(o.net_revenue) / NULLIF(count(*), 0), 0)::numeric(14,2),
        sum(o.discount_sum),
        max(COALESCE(o.closed_at, o.opened_at, o.updated_at)),
        now()
    FROM fact_orders o
    LEFT JOIN dim_organizations org ON org.organization_id = o.organization_id
    WHERE o.business_date = today
    GROUP BY o.business_date, hour, o.organization_id, org.organization_name, o.order_source;

    DELETE FROM mart_today_delivery WHERE business_date = today;

    INSERT INTO mart_today_delivery
    SELECT
        d.business_date,
        d.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        d.delivery_status,
        count(*)::integer,
        count(*) FILTER (WHERE d.is_late)::integer,
        COALESCE((count(*) FILTER (WHERE d.is_late))::numeric / NULLIF(count(*), 0), 0)::numeric(14,6),
        avg(d.delivery_minutes)::numeric(14,2),
        percentile_cont(0.90) WITHIN GROUP (ORDER BY d.delivery_minutes)::numeric(14,2),
        count(*) FILTER (WHERE d.is_active)::integer,
        now()
    FROM fact_deliveries d
    LEFT JOIN dim_organizations org ON org.organization_id = d.organization_id
    WHERE d.business_date = today
    GROUP BY d.business_date, d.organization_id, org.organization_name, d.delivery_status;

    TRUNCATE TABLE mart_today_stoplists;

    INSERT INTO mart_today_stoplists(
        business_date, organization_id, organization_name, product_id, product_name, category_name,
        started_at, duration_minutes, avg_revenue_per_hour, lost_revenue_estimate, updated_at
    )
    SELECT
        today,
        x.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        x.product_id,
        COALESCE(p.product_name, 'unknown'),
        p.category_name,
        x.started_at,
        (extract(epoch FROM (COALESCE(x.ended_at, now()) - x.started_at)) / 60)::numeric(14,2),
        x.avg_revenue_per_hour,
        (x.avg_revenue_per_hour * extract(epoch FROM (COALESCE(x.ended_at, now()) - x.started_at)) / 3600)::numeric(14,2),
        now()
    FROM (
        SELECT DISTINCT ON (organization_id, product_id, started_at)
            organization_id, product_id, started_at, ended_at, avg_revenue_per_hour
        FROM fact_stoplists
        WHERE ended_at IS NULL OR ended_at::date = today
        ORDER BY organization_id, product_id, started_at, updated_at DESC
    ) x
    LEFT JOIN dim_organizations org ON org.organization_id = x.organization_id
    LEFT JOIN dim_products p ON p.product_id = x.product_id;

    DELETE FROM mart_today_branch_status WHERE business_date = today;

    INSERT INTO mart_today_branch_status
    WITH orders AS (
        SELECT
            business_date,
            organization_id,
            count(*)::integer AS orders_count,
            sum(net_revenue) AS net_revenue,
            COALESCE(sum(net_revenue) / NULLIF(count(*), 0), 0)::numeric(14,2) AS avg_check
        FROM fact_orders
        WHERE business_date = today
        GROUP BY business_date, organization_id
    ),
    deliveries AS (
        SELECT
            business_date,
            organization_id,
            count(*)::integer AS delivery_orders,
            count(*) FILTER (WHERE is_late)::integer AS late_orders,
            COALESCE((count(*) FILTER (WHERE is_late))::numeric / NULLIF(count(*), 0), 0)::numeric(14,6) AS late_rate,
            count(*) FILTER (WHERE is_active)::integer AS active_deliveries
        FROM fact_deliveries
        WHERE business_date = today
        GROUP BY business_date, organization_id
    ),
    stops AS (
        SELECT organization_id, count(*)::integer AS active_stoplist_items
        FROM fact_stoplists
        WHERE ended_at IS NULL
        GROUP BY organization_id
    )
    SELECT
        o.business_date,
        o.organization_id,
        COALESCE(org.organization_name, 'unknown'),
        o.orders_count,
        o.net_revenue,
        o.avg_check,
        COALESCE(d.delivery_orders, 0),
        COALESCE(d.late_orders, 0),
        COALESCE(d.late_rate, 0),
        COALESCE(d.active_deliveries, 0),
        COALESCE(s.active_stoplist_items, 0),
        GREATEST(0, 100 - COALESCE(d.late_rate, 0) * 40 - COALESCE(s.active_stoplist_items, 0) * 2)::numeric(14,2),
        now()
    FROM orders o
    LEFT JOIN deliveries d ON d.business_date = o.business_date AND d.organization_id = o.organization_id
    LEFT JOIN stops s ON s.organization_id = o.organization_id
    LEFT JOIN dim_organizations org ON org.organization_id = o.organization_id;
END;
$$;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'datalens_reader')
        THEN format('ALTER ROLE datalens_reader LOGIN PASSWORD %L', :'datalens_reader_password')
    ELSE format('CREATE ROLE datalens_reader LOGIN PASSWORD %L', :'datalens_reader_password')
END
\gexec

GRANT CONNECT ON DATABASE iiko_analytics TO datalens_reader;
GRANT USAGE ON SCHEMA public TO datalens_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datalens_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO datalens_reader;
