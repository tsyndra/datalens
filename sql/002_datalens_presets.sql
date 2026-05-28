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
    (sum(discount_sum) / NULLIF(sum(gross_revenue), 0))::numeric(14,6) AS discount_share
FROM mart_daily_sales
GROUP BY business_date;

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

GRANT SELECT ON
    dl_preset_kpi_summary,
    dl_preset_revenue_by_day,
    dl_preset_revenue_by_branch,
    dl_preset_branch_daily,
    dl_preset_revenue_by_source,
    dl_preset_top_products,
    dl_preset_product_daily,
    dl_preset_branch_health
TO datalens_reader;
