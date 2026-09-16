# 03: Medallion Transformations and Data Observability via dbt-core

**What to build:** Complete analytics transformation modeling and automated data quality assurance using `dbt-core` and `Elementary Data`. Staging models flatten Bronze JSON records into normalized Silver dimension and fact tables (`dim_customers`, `dim_products`, `fct_orders`, `fct_order_items`) using incremental merge materialization. Mart models aggregate Silver facts into performant Gold analytical tables (`gold_daily_sales_kpi`, `gold_customer_ltv`, `gold_product_performance`) calculating true Net Revenue, GMV, AOV, and LTV cohorts.

**Blocked by:** 02: Order Simulator and Pluggable dlt Ingestion Engine

**Status:** closed

- [x] dbt project is initialized with BigQuery connection profile configured via environment variables.
- [x] Staging models (`models/staging/`) unpack Bronze raw tables into clean Silver dimensional schemas with PII masked or pseudonymous.
- [x] Fact models (`fct_orders`, `fct_order_items`) implement `materialized='incremental'` with `unique_key='order_id'` using `merge` strategy.
- [x] Mart models (`models/marts/`) calculate:
  - `gold_daily_sales_kpi`: Daily GMV, completed order volume, Net Revenue, AOV, cancellation rate.
  - `gold_customer_ltv`: Customer lifetime Net Revenue, order frequency, recency, and value tier.
  - `gold_product_performance`: Units sold, gross sales, refund count, category distribution.
- [x] dbt test suite covers primary key uniqueness, not-null constraints, foreign key referential integrity, and business mathematical invariants ($GMV \ge Net\ Revenue$).
- [x] Elementary Data package is integrated to provide automated anomaly detection on order volume drops and revenue anomalies.
- [x] `dbt run` and `dbt test` execute and pass cleanly against BigQuery.
