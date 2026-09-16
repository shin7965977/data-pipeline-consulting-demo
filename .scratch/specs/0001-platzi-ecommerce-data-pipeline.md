# Spec 0001: Platzi E-Commerce Cloud Data Pipeline & Analytics Platform

**Status**: ready-for-agent  
**Category**: Greenfield Core Platform  
**Target Delivery**: Prototype & Consulting Demonstration  

---

## Problem Statement

Small and Medium Enterprises (SMEs) face severe challenges when attempting to leverage their operational data for business intelligence and AI insights. Traditional enterprise data stacks (e.g., Snowflake + Fivetran + Managed Airflow / Cloud Composer) are prohibitively expensive ($500~$2000+/month minimum base cost), overly complex to operate, and require dedicated Data Engineering teams to maintain. Conversely, ad-hoc spreadsheet exports and direct database querying lack historical modeling, data quality observability, and scalability.

Furthermore, boutique data consultants require a modular, reusable prototype that can be showcased on GitHub to demonstrate senior-level DataOps practices (IaC, Medallion modeling, automated testing, and AI tool integration) while being easily portable to real-world client data (Shopify, ERP, PostgreSQL) with minimal refactoring.

---

## Solution

Build a modern, serverless, low-TCO (Total Cost of Ownership, ~$0/month idle cost) end-to-end ELT data pipeline deployed on Google Cloud Platform. The solution:
1. Simulates realistic e-commerce purchase behavior with lifecycle state transitions on top of the Platzi Store catalog.
2. Ingests raw data using a pluggable, code-first Python framework (`dlt`) mapped to a canonical schema with incremental watermark tracking.
3. Transforms data in GCP BigQuery across Medallion layers (Bronze raw append -> Silver Star Schema -> Gold KPI Marts) using `dbt-core`.
4. Orchestrates daily batch execution and on-demand manual triggers serverlessly via GCP Cloud Scheduler and Cloud Run Jobs inside an optimized Docker container.
5. Manages all cloud infrastructure declaratively using Terraform.
6. Enforces enterprise data quality and anomaly detection via Elementary Data, validated through automated GitHub Actions CI/CD.
7. Exposes validated metrics to business operators through Google Looker Studio and to AI agents through FastMCP.

---

## User Stories

### Persona: SME Business Owner & Operators
1. As an e-commerce business owner, I want to see a daily-updated executive dashboard of GMV, Net Revenue, and AOV, so that I can monitor financial health without paying expensive software subscriptions.
2. As an e-commerce business owner, I want orders with cancellation and refund statuses properly deducted from Net Revenue, so that my financial reporting reflects true cash intake rather than gross sales volume.
3. As a marketing manager, I want to view Customer Lifetime Value (LTV) cohorts and repurchase intervals, so that I can identify high-value customer segments for targeted retention campaigns.
4. As a merchandising manager, I want to see a leaderboard of top-performing products and categories by sales volume and margin, so that I can optimize inventory replenishment.
5. As a business operator, I want to manually trigger an immediate data pipeline refresh on demand through a simple cloud interface, so that I can see the impact of promotional campaigns without waiting for the overnight scheduled run.
6. As an executive, I want to ask natural language questions about business performance to an AI assistant, so that I can obtain instant data-backed answers without writing SQL queries.

### Persona: Consulting Client & IT Stakeholder
7. As a prospective consulting client, I want all sensitive Customer PII (emails, phone numbers, addresses) masked and excluded from analytical Gold tables and AI query tools, so that our customer privacy complies with regulatory standards.
8. As a client IT manager, I want cloud infrastructure provisioned entirely via Terraform, so that deployment is repeatable, audited, and can be cleanly torn down or replicated across cloud projects.
9. As a client IT manager, I want zero idle compute charges for pipeline scheduling, so that my monthly cloud infrastructure invoice remains predictably near zero dollars.
10. As a client developer, I want to swap the demo data source for our live production data (e.g., Shopify API) by implementing a single source adapter, so that our existing downstream dbt models and Looker dashboards require no structural modifications.

### Persona: Analytics & Data Engineer (Developer)
11. As a data engineer, I want the order generator to produce 90 days of historically distributed orders with realistic weekly seasonal patterns, so that downstream BI charts demonstrate authentic trend lines.
12. As a data engineer, I want data ingestion to utilize incremental watermarks based on `updated_at`, so that only newly modified records are transferred to BigQuery on each execution.
13. As an analytics engineer, I want dbt models organized into distinct staging (Bronze to Silver) and marts (Silver to Gold) layers, so that transformation dependencies are maintainable and DAG lineage is clean.
14. As an analytics engineer, I want automated dbt schema tests (unique, not_null, accepted_values, relationships) and Elementary anomaly monitors to run during every execution, so that data pipeline failures alert before corrupting BI reports.
15. As a developer, I want to run the entire pipeline end-to-end locally using a single `docker compose` command, so that I can iterate and debug without deploying to GCP.
16. As a developer, I want automated CI/CD checks enforcing Python linting (Ruff), SQL linting (SQLFluff), and unit testing (Pytest) on every pull request, so that code quality standards remain high.

---

## Implementation Decisions

### 1. Architectural Topology & Monorepo Organization
The repository will be structured as a unified monorepo with strict separation of responsibilities:
- `terraform/`: Declarative GCP infrastructure definitions.
- `ingestion/`: Ingestion engine and pluggable source adapters.
- `transform_dbt/`: dbt-core transformation project and Elementary packages.
- `mcp_server/`: FastMCP implementation exposing BigQuery Gold mart metrics.
- `docker/`: Dockerfile, container entrypoint scripts, and local compose setup.
- `.github/workflows/`: CI/CD quality assurance pipelines.

### 2. Pluggable Source Adapter & Canonical Schema
- Ingestion logic must decouple source-specific fetching from database loading.
- Every source adapter must conform to a standardized interface yielding Canonical Records:
  - `raw_orders`: `order_id`, `customer_id`, `order_status` (`completed` | `cancelled` | `refunded`), `currency`, `gross_amount`, `discount_amount`, `net_amount`, `created_at`, `updated_at`.
  - `raw_order_items`: `item_id`, `order_id`, `product_id`, `unit_price`, `quantity`, `subtotal`.
  - `raw_customers`: `customer_id`, `email`, `name`, `created_at`, `updated_at`.
  - `raw_products`: `product_id`, `title`, `price`, `category_id`, `category_name`, `updated_at`.
- The reference implementation will provide `platzi_store.py` (fetching catalog data from Platzi Store REST API combined with synthetic realistic order generators).
- Incremental loading will utilize dlt's state cursor tracking against `updated_at`.

### 3. BigQuery Medallion Lakehouse Strategy
- **Bronze (`platzi_bronze`)**: Raw append-only datasets managed by dlt. Preserves nested structures and ingestion metadata (`_dlt_load_id`, `_dlt_id`).
- **Silver (`platzi_silver`)**: Cleaned, deduplicated, and flattened Star Schema managed by dbt.
  - Dimensions: `dim_customers` (PII masked or pseudonymous), `dim_products`, `dim_categories`.
  - Facts: `fct_orders`, `fct_order_items` materialized as `incremental` with `unique_key='order_id'` and `merge` strategy.
- **Gold (`platzi_gold`)**: High-performance business aggregation marts optimized for analytical querying.
  - `gold_daily_sales_kpi`: Aggregated by date, reporting daily GMV, completed order count, Net Revenue, AOV, cancellation rate, refund amount.
  - `gold_customer_ltv`: Aggregated by customer, reporting first/last purchase date, total orders, lifetime Net Revenue, recency, and value tier.
  - `gold_product_performance`: Aggregated by product, reporting units sold, gross revenue, refund count, category share.

### 4. Serverless Orchestration Architecture
- Execution is packaged into a unified container image pushed to GCP Artifact Registry.
- The container entrypoint provides a parameterized CLI:
  - `--target=ingest`: Runs source extraction and Bronze ingestion only.
  - `--target=transform`: Runs dbt models and dbt test validations only.
  - `--target=all`: Sequentially executes ingestion, transformation, and observability tests.
- Deployment target is GCP Cloud Run Jobs:
  - Configured with zero standby instances (0 idle cost).
  - Configured with maximum execution timeout (e.g., 30 minutes) and automatic retry on transient failure.
- Triggered on a schedule via GCP Cloud Scheduler using cron syntax (`0 2 * * *` UTC).
- Manual execution is supported via standard GCP Cloud Console or gcloud CLI invocation.

### 5. AI Interface & Governance Boundary (FastMCP)
- FastMCP server exposes specialized tools to LLMs for querying metrics (e.g., `get_daily_sales_kpi`, `get_top_products`, `get_customer_metrics`).
- Query scope is strictly restricted to the `platzi_gold` dataset.
- Access to `platzi_bronze` and `platzi_silver` is prohibited to prevent PII exposure.
- Queries are parameterized with date ranges and limits to prevent runaway query scan costs.

### 6. Infrastructure-as-Code (Terraform) Scope
Terraform modules manage all foundational cloud resources:
- BigQuery Datasets: Bronze, Silver, Gold with region pinning (`asia-east1` or `us-central1`).
- Artifact Registry Repository: Docker image store.
- Cloud Run Job: Container specification, environment variables, memory/CPU allocation.
- Cloud Scheduler Job: HTTP target calling Cloud Run Job with OAuth Service Account token.
- IAM Service Accounts: Least-privilege roles (`roles/bigquery.dataEditor`, `roles/run.invoker`).

---

## Testing Decisions

### Seam Architecture
We define testing at the highest practical boundaries:

1. **Adapter Transformation Seam (`ingestion.sources`)**:
   - **What to test**: External behavior of the source adapter. Given raw API mock payloads, verify that the returned records strictly comply with the Canonical Schema, that data types are properly cast, and that order lifecycle states validate against canonical enum values.
   - **What NOT to test**: Internal network libraries or third-party dlt mechanics.

2. **Analytics Transformation Seam (`dbt test`)**:
   - **What to test**: External mathematical invariants and relational integrity across Silver and Gold.
     - GMV must always be greater than or equal to Net Revenue.
     - Order item totals must equal parent order gross amounts.
     - Foreign keys between `fct_orders` and `dim_customers` must be referentially valid.
     - Primary keys must be strictly unique and not null.
   - **Tools**: dbt native tests + Elementary data anomaly tests.

3. **Pipeline Orchestrator Seam (`docker/entrypoint.sh`)**:
   - **What to test**: CLI argument parsing and exit codes. Passing `--target=invalid` returns non-zero code; running `--target=all` in local mock mode executes the sequence to completion.

4. **CI/CD Quality Gates (Pre-merge)**:
   - Python code must pass `ruff check .` and `ruff format --check .`.
   - SQL models must pass `sqlfluff lint transform_dbt/models/`.
   - Unit tests must pass `pytest tests/`.

---

## Out of Scope

1. **Sub-second Real-time Streaming**: Real-time Kafka / Apache Flink streaming is explicitly out of scope; daily/hourly micro-batch ELT satisfies SME requirements.
2. **Multi-tenant SaaS Architecture**: The platform is designed as a single-client dedicated cloud footprint, not a multi-tenant SaaS.
3. **Complex Enterprise SSO**: Identity management relies on native GCP IAM and Google Workspace / Google Account authorization rather than custom Okta/SAML integrations.
4. **Credit Card Payment Processing**: The simulator generates synthetic transaction metadata; actual payment gateway integrations (Stripe/PayPal) are simulated.

---

## Further Notes

- **Initial Seed Volume**: First-time initialization populates 90 days of synthetic historical orders (~5,000 - 10,000 transactions) to provide rich time-series visual trends in Looker Studio immediately upon deployment.
- **Cost Estimate**: Under standard SME daily batch frequency, total monthly GCP infrastructure expenditures are projected to remain below $1.00 USD within free-tier allowances.
