# Report Builder Web Panel

The web panel is a small internal OLAP constructor over the local PostgreSQL
database. It is meant for flexible reports that are awkward to build in
DataLens.

## Run

```bash
make report-builder
```

Open:

```text
http://127.0.0.1:8088
```

Optional environment variables:

| Variable | Default |
|---|---|
| `REPORT_BUILDER_HOST` | `127.0.0.1` |
| `REPORT_BUILDER_PORT` | `8088` |
| `DATABASE_URL` | read from `.env` / `.credentials.env` |

## Screens

### OLAP Builder

Choose a fact family:

- Sales
- Orders
- Products
- Payments
- Discounts
- Delivery
- Customers
- Operations
- Staff

Then choose dimensions, metrics, filters, sorting and row limit. The backend
generates SQL from a whitelist in `app/report_builder.py`; browser input cannot
inject arbitrary SQL identifiers or expressions.

### Customer Segments

Build customer lists with mixed lifetime and selected-period conditions:

- selected product or category contains text;
- selected product/category purchases lifetime equals or compares to N;
- period date range;
- customer orders in period greater than or equal to N;
- export to CSV.

This screen uses `dl_report_customer_segments`. It only works for orders where
the data has the chain `customer_id -> order_id -> order_items`.

## Safety Rules

- Use OLAP Builder for normal grouped reports.
- Use Customer Segments for lifetime + selected-period customer conditions.
- Do not combine order revenue with product/payment rows outside controlled
  query templates, because that can multiply rows and inflate sums.
