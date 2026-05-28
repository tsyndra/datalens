# DataLens OLAP Datasets

Use these datasets as the primary DataLens constructor layer. They are split by
fact grain, similar to iiko OLAP report families. Do not join them into one
physical dataset unless the join cardinality is known and controlled.

## Datasets

| Dataset | Grain | Use for |
|---|---|---|
| `dl_olap_sales` | `business_date + organization + order_source` | revenue, orders, avg check, discounts, refunds, branch/source trends |
| `dl_olap_orders` | `order_id` | order-level ad-hoc reports, statuses, customers, delivery flags, payment/discount summaries |
| `dl_olap_products` | `order_item_id` | product/category analysis, baskets, customer-product questions |
| `dl_olap_payments` | `payment_id` | payment type/group reports and payment reconciliation |
| `dl_olap_discounts` | `discount_id` | discounts, promos, manual discounts |
| `dl_olap_delivery` | `delivery_id` | delivery statuses, zones, delays, courier fields, SLA |
| `dl_olap_customers` | `customer_id + order_id` | customer orders, repeat orders, retention/RFM inputs |
| `dl_olap_operations` | `operation_id` from losses/events | cancellations, refunds, manual discounts, derived losses |
| `dl_olap_staff` | `business_date + organization + staff role/name` | staff revenue and order counts |

## Shared Filter Fields

Most datasets expose these fields where the source can support them:

- `business_date`
- `week_start`
- `month_start`
- `iso_weekday`
- `organization_id`
- `organization_name`
- `order_source`
- `customer_id`
- `phone_hash`

In DataLens, use dashboard-level selectors on shared fields to filter charts
from different OLAP datasets together.

## Metric Safety

Use the dataset that matches the fact you want to sum:

- revenue totals: `dl_olap_sales` or `dl_olap_orders`;
- product revenue/quantity: `dl_olap_products`;
- payment sums: `dl_olap_payments`;
- discount sums: `dl_olap_discounts`;
- delivery counts/timings: `dl_olap_delivery`;
- customer order counts: `dl_olap_customers`.

Avoid summing order-level revenue after joining it to product/payment/discount
rows. That creates fan-out and wrong totals.

## Customer/Product Questions

Questions like "customers who bought a selected product/category once lifetime
and made more than N orders in a period" should use:

- `dl_olap_products` for the selected product/category history;
- `dl_olap_customers` for period order counts;
- or a dedicated SQL view if the condition combines lifetime and selected-period
  logic in one chart.

This works only for orders where the source data contains the chain:

`customer_id -> order_id -> order_items`

Aggregated OLAP sales without customer identity can still be used for revenue
and product totals, but not for customer-product segmentation.
