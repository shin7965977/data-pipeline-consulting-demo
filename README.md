# Modern Serverless E-Commerce ELT Data Pipeline & AI-Ready Lakehouse

[![CI Quality Gates](https://github.com/shin7965977/data-pipeline-consulting-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/shin7965977/data-pipeline-consulting-demo/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![dbt Core](https://img.shields.io/badge/dbt--core-1.11+-orange.svg)](https://www.getdbt.com/)
[![dlt Hub](https://img.shields.io/badge/dlt-0.5+-brightgreen.svg)](https://dlthub.com/)
[![FastMCP](https://img.shields.io/badge/FastMCP-AI%20Service-purple.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, production-grade Modern Data Stack (MDS) implementation designed for **e-commerce retail intelligence and SME consulting demos**. Built with a **Serverless-first, near-$0/month idle TCO** architecture, strict **Medallion Data Lakehouse** engineering, **Data Observability**, **Looker Studio BI**, and **FastMCP AI Agent Services**.

---

## 🏛️ Architecture Overview

```
[ Platzi Fake Store REST API ] + [ Python Order Simulator (3-State Lifecycle) ]
                                |
                                v
                [ Canonical Schema Normalizer ]
                                |
                                v
               [ dlt Ingestion Engine (DuckDB / BigQuery) ]
                                |
                                v
               +----------------------------------+
               |  Medallion Architecture (GCP BQ)  |
               |                                  |
               |  [BRONZE] raw_* (Append-only)    |
               |          |                       |
               |          v                       |
               |  [SILVER] stg_* (PII Masking)    |
               |          |                       |
               |          v                       |
               |  [SILVER] dim_*, fct_* (Star)    |
               |          |                       |
               |          v                       |
               |  [GOLD]   gold_* (Marts & KPIs)  |
               +----------------------------------+
                     |                      |
                     v                      v
         [ Looker Studio BI ]     [ FastMCP AI Agent ]
         - Executive Sales KPIs   - Claude / OpenAI Tool Calling
         - Customer LTV & Cohorts - Strict Gold-layer Whitelisting
         - Product Leaderboards   - Auto PII Redaction & Cost Caps
```

### 💼 Key Consulting Highlights
1. **Zero-Idle TCO (Serverless)**: Instead of paying 24/7 for managed Airflow (Composer ~ $300+/mo), orchestration runs on **Google Cloud Scheduler + Cloud Run Jobs** (~ $0/mo idle cost).
2. **Canonical Schema Adapter Pattern**: Upstream e-commerce APIs (Shopify, WooCommerce, Platzi) are mapped into standardized schema contracts, insulating dbt models from source schema drift.
3. **Enterprise PII Governance**: Names and emails are cryptographically salted and SHA-256 hashed at the staging layer; AI agents and Looker Studio never touch raw customer identities.
4. **Data Observability**: Pre-integrated with **Elementary Data** for automated test anomaly detection, schema drift monitoring, and run history auditing.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Infrastructure as Code** | Terraform | BigQuery datasets, Cloud Run Jobs, Cloud Scheduler, IAM & Artifact Registry |
| **Data Ingestion** | `dlt` (data load tool) | Resilient schema evolution, automatic batching & typing |
| **Data Transformation** | `dbt-core` + DuckDB / BigQuery | Medallion staging, Star Schema dimensional modeling & Gold marts |
| **Data Observability** | `elementary-data` + dbt tests | Automated schema test assertions, uniqueness & referential integrity |
| **Containerization** | Docker (Multi-stage) | Lean, reproducible image pre-baked with dbt packages |
| **Orchestration** | Cloud Scheduler + Cloud Run | Serverless cron triggers (`0 2 * * *`) with manual override |
| **BI & Analytics** | Google Looker Studio | Executive dashboards, KPI monitoring & retention curves |
| **AI Consumption** | FastMCP (Model Context Protocol) | LLM tool provider with security whitelisting and query scan budgets |
| **CI / CD Quality Gates** | GitHub Actions + Ruff + SQLFluff | Automated static analysis, SQL linting, and full test suite enforcement |

---

## 🚀 Quick Start (Local Demo)

You can run the entire pipeline locally in under 60 seconds without requiring a Google Cloud account (using local DuckDB).

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Clone & Setup
```bash
git clone https://github.com/shin7965977/data-pipeline-consulting-demo.git
cd data-pipeline-consulting-demo

# Create virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Pipeline Locally
```bash
# Execute end-to-end (Simulator -> Ingestion -> Staging -> Silver -> Gold Marts)
python pipeline_runner.py --target=all --dataset=test_pipeline.duckdb
```

### 4. Run Docker Container
```bash
docker compose run pipeline --target=all
```

---

## 🤖 FastMCP AI Agent Service

The FastMCP server allows LLM assistants (such as Claude Desktop or OpenAI agents) to query e-commerce analytics safely through natural language.

### Security Invariants
- 🔒 **Gold Layer Whitelisting**: The MCP server strictly forbids access to `platzi_bronze` and `platzi_silver`.
- 🛡️ **PII Redaction**: Customer identifiers are permanently masked.
- ⚡ **Byte Scan & Limit Caps**: Queries enforce `MAX_BYTES_BILLED` and max row limits to prevent accidental cloud spend.

### Start the MCP Server
```bash
python mcp_server/server.py
```

### Available AI Tools
- `get_daily_sales_kpi(start_date, end_date, limit)`: GMV, Net Revenue, completed orders, cancellations, and refund rates.
- `get_top_products(metric, limit)`: Top performing products ranked by total revenue or units sold.
- `get_customer_metrics(limit)`: High-value customer LTV percentiles, frequency, and monetary scores.

### 📖 商業顧問與視覺化提問指南 (Management Consultant Prompting Guides)
想要獲得頂級顧問水準的精準策略分析與視覺化產物？請參閱本專案的專屬指南與萬用模板：
- 👉 **[提問框架.md](提問框架.md)**：包含 C-C-T-C-D 5 大核心拼圖、空泛 vs. 顧問級提問對照表、與一鍵複製模板。
- 👉 **[圖表生成指南.md](圖表生成指南.md)**：包含 C-T-D-S-A 圖表規格框架、繪圖負向約束、3 大商業圖表模板（瀑布圖/2x2矩陣/水平長條）。

---

## 📊 Business Intelligence (Looker Studio)

Connect Looker Studio natively to BigQuery Gold Marts:
- **`gold_daily_sales_kpi`**: Trend lines for Daily GMV vs. Net Revenue, cancellation rates.
- **`gold_product_performance`**: Category contribution matrix and unit volume leaderboards.
- **`gold_customer_ltv`**: Customer segmentation tiers, average order value distributions.

Detailed dashboard setup blueprints and formulas are provided in [docs/looker_studio_guide.md](docs/looker_studio_guide.md).

---

## 🛡️ Automated Quality Gates (CI/CD)

Every pull request automatically passes through strict quality gates:
1. **Python Quality**: `ruff check` (linting & import sorting).
2. **SQL Standards**: `sqlfluff lint` against BigQuery/dbt conventions.
3. **Unit & Contract Tests**: `pytest tests/` verifying:
   - Order simulator lifecycle transitions (`completed` -> `cancelled`/`refunded`).
   - Canonical Schema contracts.
   - FastMCP security boundary enforcement.
   - End-to-end dbt run and test assertions.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
