# 02: Order Simulator and Pluggable dlt Ingestion Engine

**What to build:** An end-to-end data generation and ingestion pipeline. A Python-based simulator retrieves catalog data from the Platzi Fake Store API and synthesizes 90 days of realistic historical e-commerce orders, modeling a three-state transition lifecycle (`completed`, `cancelled`, `refunded`) with discount amounts and payment methods. A modular source adapter maps records to the Canonical Schema (`raw_orders`, `raw_order_items`, `raw_customers`, `raw_products`) and loads them into BigQuery Bronze using `dlt` with incremental watermark tracking.

**Blocked by:** 01: Terraform GCP Infrastructure Baseline

**Status:** closed

- [x] Pluggable source adapter `ingestion/sources/platzi_store.py` decouples API extraction from the pipeline core.
- [x] Simulator produces 90 days of synthetic historical orders with weekly cyclicality and realistic cancellation/refund ratios.
- [x] Output data conforms strictly to Canonical Schema (`raw_orders`, `raw_order_items`, `raw_customers`, `raw_products`).
- [x] `dlt` pipeline writes raw append-only tables into `platzi_bronze` preserving nested fields and load IDs.
- [x] Ingestion implements state cursor tracking on `updated_at` to support incremental daily runs.
- [x] Running `python ingestion/run_ingest.py` populates BigQuery Bronze tables successfully.
