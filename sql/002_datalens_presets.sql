\set ON_ERROR_STOP on

CREATE OR REPLACE VIEW dl_preset_kpi_summary AS
SELECT
    min(business_date) AS date_from,
    max(business_date) AS date_to,
    sum(orders_count)::integer AS orders_count,
    sum(net_revenue)::numeric(14,2) AS net_revenue,
    (sum(net_revenue) / NULLIF(sum(orders_count), 0))::numeric(14,2) AS avg_check,
    sum(discount_sum)::numeric(14,2) AS discount_sum,
    (sum(discount_sum) / NULLIF(sum(gross_revenue), 0))::numeric(14,6) AS discount_share,
    sum(refund_sum)::numeric(14,2) AS refund_sum
FROM mart_daily_sales;

CREATE OR REPLACE VIEW dl_preset_revenue_by_day AS
SELECT
    business_date,
    sum(orders_count)::integer AS orders_count,
    sum(net_revenue)::numeric(14,2) AS net_revenue,
    (sum(net_revenue) / NULLIF(sum(orders_count), 0))::numeric(14,2) AS avg_check,
    sum(discount_sum)::numeric(14,2) AS discount_sum,
    (sum(discount_sum) / NULLIF(sum(gross_revenue), 0))::numeric(14,6) AS discount_share,
    organization_name
FROM mart_daily_sales
GROUP BY business_date, organization_name;

CREATE OR REPLACE VIEW dl_preset_revenue_by_branch AS
SELECT
    organization_name,
    sum(orders_count)::integer AS orders_count,
    sum(net_revenue)::numeric(14,2) AS net_revenue,
    (sum(net_revenue) / NULLIF(sum(orders_count), 0))::numeric(14,2) AS avg_check,
    sum(discount_sum)::numeric(14,2) AS discount_sum,
    (sum(discount_sum) / NULLIF(sum(gross_revenue), 0))::numeric(14,6) AS discount_share,
    business_date
FROM mart_daily_sales
GROUP BY business_date, organization_name;

CREATE OR REPLACE VIEW dl_preset_branch_daily AS
SELECT
    business_date,
    organization_name,
    sum(orders_count)::integer AS orders_count,
    sum(net_revenue)::numeric(14,2) AS net_revenue,
    (sum(net_revenue) / NULLIF(sum(orders_count), 0))::numeric(14,2) AS avg_check,
    sum(discount_sum)::numeric(14,2) AS discount_sum,
    (sum(discount_sum) / NULLIF(sum(gross_revenue), 0))::numeric(14,6) AS discount_share
FROM mart_daily_sales
GROUP BY business_date, organization_name;

CREATE OR REPLACE VIEW dl_preset_revenue_by_source AS
SELECT
    COALESCE(NULLIF(order_source, ''), 'unknown') AS order_source,
    sum(orders_count)::integer AS orders_count,
    sum(net_revenue)::numeric(14,2) AS net_revenue,
    (sum(net_revenue) / NULLIF(sum(orders_count), 0))::numeric(14,2) AS avg_check,
    sum(discount_sum)::numeric(14,2) AS discount_sum
FROM mart_daily_sales
GROUP BY COALESCE(NULLIF(order_source, ''), 'unknown');

CREATE OR REPLACE VIEW dl_preset_top_products AS
SELECT
    product_name,
    category_name,
    sum(items_qty)::numeric(14,3) AS items_qty,
    sum(orders_count)::integer AS orders_count,
    sum(net_revenue)::numeric(14,2) AS net_revenue,
    (sum(net_revenue) / NULLIF(sum(items_qty), 0))::numeric(14,2) AS avg_price
FROM mart_product_sales
GROUP BY product_name, category_name;

CREATE OR REPLACE VIEW dl_preset_product_daily AS
SELECT
    business_date,
    product_name,
    category_name,
    sum(items_qty)::numeric(14,3) AS items_qty,
    sum(orders_count)::integer AS orders_count,
    sum(net_revenue)::numeric(14,2) AS net_revenue,
    (sum(net_revenue) / NULLIF(sum(items_qty), 0))::numeric(14,2) AS avg_price
FROM mart_product_sales
GROUP BY business_date, product_name, category_name;

CREATE OR REPLACE VIEW dl_preset_branch_health AS
SELECT
    business_date,
    organization_name,
    orders_count,
    net_revenue,
    avg_check,
    discount_sum,
    discount_share,
    refund_sum,
    health_score
FROM mart_branch_kpi;

CREATE OR REPLACE VIEW dl_report_revenue AS
SELECT
    business_date,
    organization_id,
    organization_name,
    order_source,
    orders_count,
    gross_revenue,
    discount_sum,
    net_revenue,
    avg_check,
    items_qty,
    cancelled_orders,
    refund_sum,
    discount_share,
    cancel_rate,
    updated_at
FROM mart_daily_sales;

CREATE OR REPLACE VIEW dl_report_branch_performance AS
SELECT
    business_date,
    organization_id,
    organization_name,
    orders_count,
    net_revenue,
    avg_check,
    discount_sum,
    discount_share,
    delivery_orders,
    late_orders,
    late_rate,
    (1 - late_rate)::numeric(14,6) AS sla_rate,
    refund_sum,
    cancel_rate,
    total_losses,
    (total_losses / NULLIF(net_revenue, 0))::numeric(14,6) AS loss_share,
    health_score,
    updated_at
FROM mart_branch_kpi;

CREATE OR REPLACE VIEW dl_report_products AS
SELECT
    business_date,
    organization_id,
    organization_name,
    product_id,
    product_name,
    category_name,
    items_qty,
    gross_revenue,
    discount_sum,
    net_revenue,
    cost_sum,
    profit_sum,
    food_cost_percent,
    (profit_sum / NULLIF(net_revenue, 0))::numeric(14,6) AS margin_rate,
    avg_price,
    orders_count,
    updated_at
FROM mart_product_sales;

CREATE OR REPLACE VIEW dl_report_order_detail AS
WITH payments AS (
    SELECT
        order_id,
        sum(payment_sum)::numeric(14,2) AS payment_sum,
        string_agg(DISTINCT COALESCE(payment_type, 'unknown'), ', ' ORDER BY COALESCE(payment_type, 'unknown')) AS payment_types,
        string_agg(DISTINCT COALESCE(payment_group, 'unknown'), ', ' ORDER BY COALESCE(payment_group, 'unknown')) AS payment_groups
    FROM fact_payments
    GROUP BY order_id
),
discounts AS (
    SELECT
        order_id,
        sum(discount_sum)::numeric(14,2) AS item_discount_sum,
        bool_or(is_manual) AS has_manual_discount,
        string_agg(DISTINCT discount_name, ', ' ORDER BY discount_name) AS discount_names
    FROM fact_discounts
    GROUP BY order_id
),
delivery AS (
    SELECT DISTINCT ON (order_id)
        order_id,
        delivery_zone,
        delivery_status,
        delivery_minutes,
        delay_minutes,
        cooking_minutes,
        courier_waiting_minutes,
        is_late,
        is_active,
        courier_name,
        address_text,
        complete_before,
        when_delivered
    FROM fact_deliveries
    WHERE order_id IS NOT NULL
    ORDER BY order_id, updated_at DESC
)
SELECT
    o.order_id,
    o.business_date,
    o.opened_at,
    o.closed_at,
    o.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    o.status,
    o.is_delivery,
    o.is_cancelled,
    o.gross_revenue,
    o.discount_sum,
    o.net_revenue,
    o.refund_sum,
    o.processed_payments_sum,
    o.tips_sum,
    COALESCE(p.payment_sum, 0)::numeric(14,2) AS payment_sum,
    p.payment_types,
    p.payment_groups,
    COALESCE(d.item_discount_sum, 0)::numeric(14,2) AS item_discount_sum,
    COALESCE(d.has_manual_discount, false) AS has_manual_discount,
    d.discount_names,
    del.delivery_zone,
    del.delivery_status,
    del.delivery_minutes,
    del.delay_minutes,
    del.cooking_minutes,
    del.courier_waiting_minutes,
    COALESCE(del.is_late, false) AS is_late,
    COALESCE(del.is_active, false) AS is_active_delivery,
    del.courier_name,
    del.address_text,
    del.complete_before,
    del.when_delivered,
    o.operator_name,
    o.guests_count,
    o.source_system,
    o.updated_at
FROM fact_orders o
LEFT JOIN dim_organizations org ON org.organization_id = o.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
LEFT JOIN payments p ON p.order_id = o.order_id
LEFT JOIN discounts d ON d.order_id = o.order_id
LEFT JOIN delivery del ON del.order_id = o.order_id;

CREATE OR REPLACE VIEW dl_report_order_items AS
SELECT
    i.order_item_id,
    i.order_id,
    i.business_date,
    i.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    o.status AS order_status,
    o.is_delivery,
    i.product_id,
    COALESCE(NULLIF(i.product_name, ''), p.product_name, 'unknown') AS product_name,
    COALESCE(NULLIF(i.category_name, ''), p.category_name) AS category_name,
    i.quantity,
    i.unit_price,
    i.gross_revenue,
    i.discount_sum,
    i.net_revenue,
    i.cost_sum,
    (i.net_revenue - i.cost_sum)::numeric(14,2) AS profit_sum,
    ((i.net_revenue - i.cost_sum) / NULLIF(i.net_revenue, 0))::numeric(14,6) AS margin_rate,
    i.item_status,
    i.is_deleted,
    i.is_modifier,
    i.size_name,
    i.source_system,
    i.updated_at
FROM fact_order_items i
JOIN fact_orders o ON o.order_id = i.order_id
LEFT JOIN dim_organizations org ON org.organization_id = i.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
LEFT JOIN dim_products p ON p.product_id = i.product_id;

CREATE OR REPLACE VIEW dl_report_customers AS
SELECT
    s.customer_id,
    c.phone_hash,
    c.customer_name,
    c.customer_surname,
    c.birthdate,
    c.gender,
    c.customer_type,
    c.in_blacklist,
    c.blacklist_reason,
    s.first_order_date,
    s.last_order_date,
    s.first_order_source,
    s.first_organization_id,
    s.first_organization_name,
    s.orders_count,
    s.repeat_orders,
    s.total_revenue,
    s.avg_check,
    s.days_since_last_order,
    s.updated_at
FROM mart_customer_summary s
LEFT JOIN dim_customers c ON c.customer_id = s.customer_id;

CREATE OR REPLACE VIEW dl_report_customer_orders AS
SELECT
    co.customer_id,
    c.phone_hash,
    co.order_id,
    co.organization_id,
    org.organization_name,
    co.business_date,
    co.order_number_by_customer,
    co.days_since_previous_order,
    co.is_first_order,
    co.is_repeat_order,
    co.net_revenue,
    co.order_source,
    o.order_type,
    o.status,
    o.is_delivery,
    o.is_cancelled,
    o.discount_sum,
    o.refund_sum,
    co.source_system,
    co.updated_at
FROM fact_customer_orders co
JOIN dim_customers c ON c.customer_id = co.customer_id
LEFT JOIN fact_orders o ON o.order_id = co.order_id
LEFT JOIN dim_organizations org ON org.organization_id = co.organization_id;

CREATE OR REPLACE VIEW dl_report_customer_products AS
SELECT
    o.customer_id,
    c.phone_hash,
    i.product_id,
    COALESCE(NULLIF(i.product_name, ''), p.product_name, 'unknown') AS product_name,
    COALESCE(NULLIF(i.category_name, ''), p.category_name) AS category_name,
    count(DISTINCT i.order_id)::integer AS product_orders_lifetime,
    sum(i.quantity)::numeric(14,3) AS items_qty_lifetime,
    sum(i.net_revenue)::numeric(14,2) AS product_revenue_lifetime,
    min(i.business_date) AS first_product_order_date,
    max(i.business_date) AS last_product_order_date,
    max(cust.orders_count)::integer AS customer_orders_lifetime,
    max(cust.total_revenue)::numeric(14,2) AS customer_revenue_lifetime,
    max(cust.last_order_date) AS customer_last_order_date
FROM fact_order_items i
JOIN fact_orders o ON o.order_id = i.order_id
LEFT JOIN dim_products p ON p.product_id = i.product_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
LEFT JOIN mart_customer_summary cust ON cust.customer_id = o.customer_id
WHERE o.customer_id IS NOT NULL
  AND COALESCE(i.is_modifier, false) = false
GROUP BY
    o.customer_id,
    c.phone_hash,
    i.product_id,
    COALESCE(NULLIF(i.product_name, ''), p.product_name, 'unknown'),
    COALESCE(NULLIF(i.category_name, ''), p.category_name);

CREATE OR REPLACE VIEW dl_report_customer_segments AS
WITH customer_products AS (
    SELECT
        o.customer_id,
        i.product_id,
        COALESCE(NULLIF(i.product_name, ''), p.product_name, 'unknown') AS product_name,
        COALESCE(NULLIF(i.category_name, ''), p.category_name) AS category_name,
        count(DISTINCT i.order_id)::integer AS product_orders_lifetime,
        sum(i.quantity)::numeric(14,3) AS items_qty_lifetime,
        sum(i.net_revenue)::numeric(14,2) AS product_revenue_lifetime,
        min(i.business_date) AS first_product_order_date,
        max(i.business_date) AS last_product_order_date
    FROM fact_order_items i
    JOIN fact_orders o ON o.order_id = i.order_id
    LEFT JOIN dim_products p ON p.product_id = i.product_id
    WHERE o.customer_id IS NOT NULL
      AND COALESCE(i.is_modifier, false) = false
    GROUP BY
        o.customer_id,
        i.product_id,
        COALESCE(NULLIF(i.product_name, ''), p.product_name, 'unknown'),
        COALESCE(NULLIF(i.category_name, ''), p.category_name)
)
SELECT
    cp.customer_id,
    c.phone_hash,
    cp.product_id,
    cp.product_name,
    cp.category_name,
    cp.product_orders_lifetime,
    cp.items_qty_lifetime,
    cp.product_revenue_lifetime,
    cp.first_product_order_date,
    cp.last_product_order_date,
    s.orders_count AS customer_orders_lifetime,
    s.total_revenue AS customer_revenue_lifetime,
    s.first_order_date,
    s.last_order_date,
    s.days_since_last_order,
    co.order_id AS period_order_id,
    co.business_date,
    co.organization_id,
    org.organization_name,
    co.order_source,
    co.net_revenue AS period_order_revenue,
    co.is_first_order,
    co.is_repeat_order
FROM customer_products cp
JOIN fact_customer_orders co ON co.customer_id = cp.customer_id
LEFT JOIN mart_customer_summary s ON s.customer_id = cp.customer_id
LEFT JOIN dim_customers c ON c.customer_id = cp.customer_id
LEFT JOIN dim_organizations org ON org.organization_id = co.organization_id;

CREATE OR REPLACE VIEW dl_report_delivery AS
SELECT
    d.delivery_id,
    d.order_id,
    d.business_date,
    d.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    d.delivery_zone,
    d.delivery_status,
    d.delivery_minutes,
    d.delay_minutes,
    d.cooking_minutes,
    d.courier_waiting_minutes,
    d.is_late,
    d.is_active,
    d.address_text,
    d.latitude,
    d.longitude,
    d.courier_name,
    d.complete_before,
    d.when_confirmed,
    d.cooking_started_at,
    d.cooking_completed_at,
    d.when_packed,
    d.when_sent,
    d.when_delivered,
    d.external_courier_service,
    d.source_system,
    d.updated_at
FROM fact_deliveries d
LEFT JOIN fact_orders o ON o.order_id = d.order_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
LEFT JOIN dim_organizations org ON org.organization_id = d.organization_id;

CREATE OR REPLACE VIEW dl_report_payments AS
SELECT
    business_date,
    organization_id,
    organization_name,
    payment_type,
    payment_group,
    orders_count,
    payment_sum,
    updated_at
FROM mart_payments_daily;

CREATE OR REPLACE VIEW dl_report_discounts AS
SELECT
    business_date,
    organization_id,
    organization_name,
    discount_name,
    discount_type,
    orders_count,
    gross_revenue,
    discount_sum,
    net_revenue,
    avg_discount_per_order,
    discount_share,
    manual_discount_sum,
    manual_discount_orders,
    updated_at
FROM mart_discount_promo;

CREATE OR REPLACE VIEW dl_report_losses AS
SELECT
    business_date,
    organization_id,
    organization_name,
    loss_type,
    loss_reason,
    loss_sum,
    orders_affected,
    loss_share,
    updated_at
FROM mart_losses;

CREATE OR REPLACE VIEW dl_report_today AS
SELECT
    s.business_date,
    s.hour,
    s.organization_id,
    s.organization_name,
    s.order_source,
    s.orders_count,
    s.net_revenue,
    s.avg_check,
    s.discount_sum,
    s.last_order_at,
    b.delivery_orders,
    b.late_orders,
    b.late_rate,
    b.active_deliveries,
    b.active_stoplist_items,
    b.health_score_today,
    GREATEST(s.updated_at, COALESCE(b.updated_at, s.updated_at)) AS updated_at
FROM mart_today_sales s
LEFT JOIN mart_today_branch_status b
  ON b.business_date = s.business_date
 AND b.organization_id IS NOT DISTINCT FROM s.organization_id;

CREATE OR REPLACE VIEW dl_olap_sales AS
SELECT
    business_date,
    date_trunc('week', business_date)::date AS week_start,
    date_trunc('month', business_date)::date AS month_start,
    extract(isodow FROM business_date)::integer AS iso_weekday,
    organization_id,
    organization_name,
    order_source,
    orders_count,
    gross_revenue,
    discount_sum,
    net_revenue,
    avg_check,
    items_qty,
    cancelled_orders,
    refund_sum,
    discount_share,
    cancel_rate,
    updated_at
FROM mart_daily_sales;

CREATE OR REPLACE VIEW dl_olap_orders AS
WITH payments AS (
    SELECT
        order_id,
        sum(payment_sum)::numeric(14,2) AS payment_sum,
        string_agg(DISTINCT COALESCE(payment_type, 'unknown'), ', ' ORDER BY COALESCE(payment_type, 'unknown')) AS payment_types,
        string_agg(DISTINCT COALESCE(payment_group, 'unknown'), ', ' ORDER BY COALESCE(payment_group, 'unknown')) AS payment_groups
    FROM fact_payments
    GROUP BY order_id
),
discounts AS (
    SELECT
        order_id,
        sum(discount_sum)::numeric(14,2) AS item_discount_sum,
        bool_or(is_manual) AS has_manual_discount,
        string_agg(DISTINCT discount_name, ', ' ORDER BY discount_name) AS discount_names
    FROM fact_discounts
    GROUP BY order_id
),
delivery AS (
    SELECT DISTINCT ON (order_id)
        order_id,
        delivery_zone,
        delivery_status,
        delivery_minutes,
        delay_minutes,
        cooking_minutes,
        courier_waiting_minutes,
        is_late,
        is_active,
        courier_name,
        complete_before,
        when_delivered
    FROM fact_deliveries
    WHERE order_id IS NOT NULL
    ORDER BY order_id, updated_at DESC
)
SELECT
    o.order_id,
    o.business_date,
    date_trunc('week', o.business_date)::date AS week_start,
    date_trunc('month', o.business_date)::date AS month_start,
    extract(isodow FROM o.business_date)::integer AS iso_weekday,
    extract(hour FROM o.opened_at)::integer AS open_hour,
    o.opened_at,
    o.closed_at,
    o.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    o.status,
    o.is_delivery,
    o.is_cancelled,
    1::integer AS orders_count,
    o.gross_revenue,
    o.discount_sum,
    o.net_revenue,
    o.refund_sum,
    o.processed_payments_sum,
    o.tips_sum,
    COALESCE(p.payment_sum, 0)::numeric(14,2) AS payment_sum,
    p.payment_types,
    p.payment_groups,
    COALESCE(d.item_discount_sum, 0)::numeric(14,2) AS item_discount_sum,
    COALESCE(d.has_manual_discount, false) AS has_manual_discount,
    d.discount_names,
    del.delivery_zone,
    del.delivery_status,
    del.delivery_minutes,
    del.delay_minutes,
    del.cooking_minutes,
    del.courier_waiting_minutes,
    COALESCE(del.is_late, false) AS is_late,
    COALESCE(del.is_active, false) AS is_active_delivery,
    del.courier_name,
    del.complete_before,
    del.when_delivered,
    o.operator_name,
    o.guests_count,
    o.source_system,
    o.updated_at
FROM fact_orders o
LEFT JOIN dim_organizations org ON org.organization_id = o.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
LEFT JOIN payments p ON p.order_id = o.order_id
LEFT JOIN discounts d ON d.order_id = o.order_id
LEFT JOIN delivery del ON del.order_id = o.order_id;

CREATE OR REPLACE VIEW dl_olap_products AS
SELECT
    i.order_item_id,
    i.order_id,
    i.business_date,
    date_trunc('week', i.business_date)::date AS week_start,
    date_trunc('month', i.business_date)::date AS month_start,
    extract(isodow FROM i.business_date)::integer AS iso_weekday,
    extract(hour FROM o.opened_at)::integer AS open_hour,
    i.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    o.status AS order_status,
    o.is_delivery,
    o.is_cancelled,
    i.product_id,
    COALESCE(NULLIF(i.product_name, ''), p.product_name, 'unknown') AS product_name,
    COALESCE(NULLIF(i.category_name, ''), p.category_name) AS category_name,
    i.quantity,
    i.unit_price,
    i.gross_revenue,
    i.discount_sum,
    i.net_revenue,
    i.cost_sum,
    (i.net_revenue - i.cost_sum)::numeric(14,2) AS profit_sum,
    ((i.net_revenue - i.cost_sum) / NULLIF(i.net_revenue, 0))::numeric(14,6) AS margin_rate,
    i.item_status,
    i.is_deleted,
    i.is_modifier,
    i.size_name,
    1::integer AS item_lines_count,
    i.source_system,
    i.updated_at
FROM fact_order_items i
JOIN fact_orders o ON o.order_id = i.order_id
LEFT JOIN dim_organizations org ON org.organization_id = i.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
LEFT JOIN dim_products p ON p.product_id = i.product_id;

CREATE OR REPLACE VIEW dl_olap_payments AS
SELECT
    p.payment_id,
    p.order_id,
    p.business_date,
    date_trunc('week', p.business_date)::date AS week_start,
    date_trunc('month', p.business_date)::date AS month_start,
    extract(isodow FROM p.business_date)::integer AS iso_weekday,
    p.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    o.status AS order_status,
    o.is_delivery,
    p.payment_type,
    p.payment_group,
    p.payment_sum,
    p.is_fiscalized_externally,
    p.is_prepay,
    p.is_external,
    p.is_processed_externally,
    p.source_system,
    p.updated_at
FROM fact_payments p
LEFT JOIN fact_orders o ON o.order_id = p.order_id
LEFT JOIN dim_organizations org ON org.organization_id = p.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id;

CREATE OR REPLACE VIEW dl_olap_discounts AS
SELECT
    d.discount_id,
    d.order_id,
    d.business_date,
    date_trunc('week', d.business_date)::date AS week_start,
    date_trunc('month', d.business_date)::date AS month_start,
    extract(isodow FROM d.business_date)::integer AS iso_weekday,
    d.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    o.status AS order_status,
    o.is_delivery,
    d.discount_name,
    d.discount_type,
    d.discount_sum,
    d.is_manual,
    d.source_system,
    d.updated_at
FROM fact_discounts d
LEFT JOIN fact_orders o ON o.order_id = d.order_id
LEFT JOIN dim_organizations org ON org.organization_id = d.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id;

CREATE OR REPLACE VIEW dl_olap_delivery AS
SELECT
    d.delivery_id,
    d.order_id,
    d.business_date,
    date_trunc('week', d.business_date)::date AS week_start,
    date_trunc('month', d.business_date)::date AS month_start,
    extract(isodow FROM d.business_date)::integer AS iso_weekday,
    d.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    o.status AS order_status,
    d.delivery_zone,
    d.delivery_status,
    d.delivery_minutes,
    d.delay_minutes,
    d.cooking_minutes,
    d.courier_waiting_minutes,
    d.is_late,
    d.is_active,
    d.address_text,
    d.latitude,
    d.longitude,
    d.courier_name,
    d.complete_before,
    d.when_confirmed,
    d.cooking_started_at,
    d.cooking_completed_at,
    d.when_packed,
    d.when_sent,
    d.when_delivered,
    d.external_courier_service,
    d.source_system,
    d.updated_at
FROM fact_deliveries d
LEFT JOIN fact_orders o ON o.order_id = d.order_id
LEFT JOIN dim_organizations org ON org.organization_id = d.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id;

CREATE OR REPLACE VIEW dl_olap_customers AS
SELECT
    co.customer_id,
    c.phone_hash,
    c.customer_name,
    c.customer_surname,
    c.birthdate,
    c.gender,
    c.customer_type,
    c.in_blacklist,
    c.blacklist_reason,
    co.order_id,
    co.business_date,
    date_trunc('week', co.business_date)::date AS week_start,
    date_trunc('month', co.business_date)::date AS month_start,
    extract(isodow FROM co.business_date)::integer AS iso_weekday,
    co.organization_id,
    org.organization_name,
    co.order_number_by_customer,
    co.days_since_previous_order,
    co.is_first_order,
    co.is_repeat_order,
    co.net_revenue,
    co.order_source,
    o.order_type,
    o.status AS order_status,
    o.is_delivery,
    o.is_cancelled,
    s.first_order_date,
    s.last_order_date,
    s.orders_count AS customer_orders_lifetime,
    s.repeat_orders AS customer_repeat_orders_lifetime,
    s.total_revenue AS customer_revenue_lifetime,
    s.avg_check AS customer_avg_check_lifetime,
    s.days_since_last_order,
    co.source_system,
    co.updated_at
FROM fact_customer_orders co
JOIN dim_customers c ON c.customer_id = co.customer_id
LEFT JOIN fact_orders o ON o.order_id = co.order_id
LEFT JOIN mart_customer_summary s ON s.customer_id = co.customer_id
LEFT JOIN dim_organizations org ON org.organization_id = co.organization_id;

CREATE OR REPLACE VIEW dl_olap_operations AS
SELECT
    l.loss_id AS operation_id,
    l.source_loss_key,
    l.order_id,
    l.order_item_id,
    l.business_date,
    date_trunc('week', l.business_date)::date AS week_start,
    date_trunc('month', l.business_date)::date AS month_start,
    extract(isodow FROM l.business_date)::integer AS iso_weekday,
    l.organization_id,
    org.organization_name,
    o.customer_id,
    c.phone_hash,
    o.order_source,
    o.order_type,
    l.loss_type AS operation_type,
    l.loss_reason AS operation_reason,
    l.loss_sum AS operation_sum,
    l.employee_uuid,
    e.employee_name,
    e.role AS employee_role,
    l.comment,
    l.source_system,
    l.updated_at
FROM fact_losses l
LEFT JOIN fact_orders o ON o.order_id = l.order_id
LEFT JOIN dim_organizations org ON org.organization_id = l.organization_id
LEFT JOIN dim_customers c ON c.customer_id = o.customer_id
LEFT JOIN dim_employees e ON e.employee_id = l.employee_uuid;

CREATE OR REPLACE VIEW dl_olap_staff AS
SELECT
    business_date,
    date_trunc('week', business_date)::date AS week_start,
    date_trunc('month', business_date)::date AS month_start,
    extract(isodow FROM business_date)::integer AS iso_weekday,
    organization_id,
    organization_name,
    employee_id,
    staff_role,
    staff_name,
    orders_count,
    net_revenue,
    updated_at
FROM mart_staff_sales;

GRANT SELECT ON
    dl_preset_kpi_summary,
    dl_preset_revenue_by_day,
    dl_preset_revenue_by_branch,
    dl_preset_branch_daily,
    dl_preset_revenue_by_source,
    dl_preset_top_products,
    dl_preset_product_daily,
    dl_preset_branch_health,
    dl_report_revenue,
    dl_report_branch_performance,
    dl_report_products,
    dl_report_order_detail,
    dl_report_order_items,
    dl_report_customers,
    dl_report_customer_orders,
    dl_report_customer_products,
    dl_report_customer_segments,
    dl_report_delivery,
    dl_report_payments,
    dl_report_discounts,
    dl_report_losses,
    dl_report_today,
    dl_olap_sales,
    dl_olap_orders,
    dl_olap_products,
    dl_olap_payments,
    dl_olap_discounts,
    dl_olap_delivery,
    dl_olap_customers,
    dl_olap_operations,
    dl_olap_staff
TO datalens_reader;
