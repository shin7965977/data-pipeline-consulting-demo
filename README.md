# Modern Serverless E-Commerce ELT Data Pipeline, Lakehouse & AI Strategy Cockpit

[![CI Quality Gates](https://github.com/shin7965977/data-pipeline-consulting-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/shin7965977/data-pipeline-consulting-demo/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![dbt Core](https://img.shields.io/badge/dbt--core-1.11+-orange.svg)](https://www.getdbt.com/)
[![dlt Hub](https://img.shields.io/badge/dlt-0.5+-brightgreen.svg)](https://dlthub.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Executive%20App-FF4B4B.svg)](https://streamlit.io/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%202.5%2F3.6-4285F4.svg)](https://ai.google.dev/)
[![FastMCP](https://img.shields.io/badge/FastMCP-AI%20Service-purple.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, enterprise-grade Modern Data Stack (MDS) implementation designed for **e-commerce retail intelligence and C-Level management consulting demos**. Built with a **Serverless-first, near-$0/month idle TCO** architecture, strict **Medallion Data Lakehouse** engineering, **Data Observability**, **Interactive Streamlit Executive Cockpit**, **Looker Studio BI**, and an **MBB-Level AI Operations Copilot** powered by FastMCP and Google Gemini.

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
                     |             |            |
                     v             v            v
    [ Streamlit Strategy Cockpit ] |  [ FastMCP AI Agent Service ]
    - Tab 1: Sales & P&L KPIs      |  - Gemini 2.5/3.6 Flash Tool Calling
    - Tab 2: Pareto 80/20 SKU      |  - Strict Gold-layer Whitelist
    - Tab 3: Customer LTV & RFM    |  - MBB Management Consultant Skill
    - Tab 4: AI Natural Language   |    (Pyramid Principle, MECE Tree)
             Chart Generator       v
                        [ Looker Studio BI ]
                        - Executive Sales Overview
                        - Cohort & Retention Analysis
```

### 💼 Key Consulting Highlights
1. **Near-$0/mo Idle TCO (Serverless Visual DAG)**: Instead of paying 24/7 for managed Airflow (Cloud Composer ~ $300+/mo), orchestration is driven by a hybrid serverless DAG: **Google Cloud Scheduler + Google Cloud Workflows + Cloud Run Jobs** (~ $0/mo idle cost; monthly 5,000 steps free tier, documented in [ADR-0003](docs/adr/0003-serverless-dag-orchestration-with-cloud-workflows.md)).
2. **Visual Step-by-Step DAG Pipeline**: Cloud Workflows (`platzi-pipeline-orchestrator`) coordinates 3 sequential stages with automated long-polling and retry policies:
   - **Step 1**: Ingest (`dlt` from API to BigQuery Bronze)
   - **Step 2**: Transform (`dbt run` for Silver dimensional models & Gold marts)
   - **Step 3**: Data Observability & Tests (`dbt test` + Elementary anomaly checks)
3. **Canonical Schema Adapter Pattern**: Upstream e-commerce APIs (Shopify, WooCommerce, Platzi) are mapped into standardized schema contracts, insulating dbt models from source schema drift.
4. **Enterprise PII Governance**: Names and emails are cryptographically salted and SHA-256 hashed at the staging layer; AI agents and BI dashboards never touch raw customer identities.
5. **Data Observability**: Pre-integrated with **Elementary Data** for automated test anomaly detection, schema drift monitoring, and run history auditing.
6. **Interactive Streamlit Executive Cockpit (`dashboard.py`)**: Real-time KPI monitoring, Plotly data visualizations, RFM customer segmentation, and an AI-driven natural language chart generator.
7. **MBB Management Consultant AI Skill (`claude-skill-management-consultant-B1`)**: 129 consulting modules enforcing the **Pyramid Principle (Action Titles)**, **MECE Issue Trees**, **Net Realization Rate** calculations, and **30-60-90 Day Tactical Roadmaps**.
8. **Domain Relevance AI Guardrails**: Intelligent prompt filtering that strictly defends the assistant against off-topic queries (e.g., politics, entertainment) to ensure professional focus.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Infrastructure as Code** | Terraform | BigQuery datasets, Cloud Run Jobs, Cloud Workflows, Cloud Scheduler & IAM |
| **Data Ingestion** | `dlt` (data load tool) | Resilient schema evolution, automatic batching, typing & incremental loading |
| **Data Transformation** | `dbt-core` + DuckDB / BigQuery | Medallion staging, Star Schema dimensional modeling & Gold marts |
| **Data Observability** | `elementary-data` + dbt tests | Automated schema test assertions, uniqueness & referential integrity |
| **Orchestration & DAG** | Cloud Scheduler + Cloud Workflows + Cloud Run | Serverless visual DAG (`Ingest -> Transform -> Test`) with $0 idle cost |
| **Executive Cockpit** | Streamlit + Plotly | Interactive analytics dashboard with P&L, Pareto SKU, and RFM tiers |
| **AI Chart Generation** | Google GenAI SDK (Gemini Flash) | Text-to-Chart engine with instant Plotly rendering & domain guardrail |
| **AI Strategy Consulting** | FastMCP + MBB Consultant Skill | Tool calling over BigQuery Gold marts with structured strategic advisory |
| **Containerization** | Docker (Multi-stage) | Lean, reproducible image pre-baked with dbt packages and dependencies |
| **BI & Analytics** | Google Looker Studio | Executive dashboards, KPI monitoring & customer cohort retention |
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

### 4. Launch Interactive Streamlit Executive Dashboard
```bash
streamlit run dashboard.py
```
* **Tab 1: 📊 營收與營運關鍵指標** — 每日 GMV、Net Revenue 淨營收走勢、訂單取消與退款率監控。
* **Tab 2: 🏆 商品銷售與貢獻分析** — Top SKU 銷售排行榜、類別貢獻與 Pareto 80/20 累積集中度分析。
* **Tab 3: 💎 顧客終身價值 (LTV) 與分層** — RFM 價值分級（Platinum VIP / Gold / Silver / Bronze）與客單價分佈。
* **Tab 4: 📈 AI 自然語言圖表生成器** — 透過自然語言即時生成專業 Plotly 圖表，內建商業範疇防護攔截無效提問。
* **側邊欄: 🤖 FastMCP 智慧營運顧問** — 整合 Gemini 最新 Flash 模型進行 BigQuery Tool Calling，輸出頂級顧問診斷報告。

### 5. Run Docker Container
```bash
docker compose run pipeline --target=all
```

---

## 🤖 FastMCP AI Agent & Strategy Consulting

The FastMCP server allows LLM assistants (such as Claude Desktop, OpenAI agents, or Gemini Copilot) to query e-commerce analytics safely through natural language.

### Security Invariants
- 🔒 **Gold Layer Whitelisting**: The MCP server strictly forbids access to `platzi_bronze` and `platzi_silver` to prevent PII leaks.
- 🛡️ **PII Redaction**: Customer identifiers (names, emails) are permanently cryptographic-hashed.
- ⚡ **Byte Scan & Limit Caps**: Queries enforce `MAX_BYTES_BILLED` (100MB cap) and row limits to eliminate unexpected cloud spend.

### Start the MCP Server
```bash
python mcp_server/server.py
```

### Available AI Tools
- `get_daily_sales_kpi(start_date, end_date, limit)`: GMV, Net Revenue, completed orders, cancellations, and refund rates.
- `get_top_products(metric, limit)`: Top performing products ranked by total revenue or units sold.
- `get_customer_metrics(limit)`: High-value customer LTV percentiles, frequency, and monetary scores.

---

## 📖 商業顧問與視覺化提問指南 (Management Consultant Prompting Guides)

本專案將麥肯錫（McKinsey）、貝恩（Bain）、BCG（MBB）與 IBM 的頂級顧問方法論深度固化為實用指南，助您在向 AI 提問時獲取最頂級的策略產出：

- 👉 **[提問框架.md](提問框架.md)**：
  - **C-C-T-C-D 5 大核心拼圖**：Context（商業背景）、Complication（現狀異常）、Target（量化目標）、Constraints（邊界約束）、Deliverables（指定產物）。
  - **空泛提問 vs. 顧問級提問對照表**（涵蓋利潤衰退、新市場拓展、AI 數位轉型實戰案例）。
  - **隨選即用萬用提問模板** 與「反客為主」需求深掘技巧。
- 👉 **[圖表生成指南.md](圖表生成指南.md)**：
  - **C-T-D-S-A 圖表規格框架**：Tool（指定引擎）、Type（圖型選型）、Data（座標與排序）、Styling（灰階高亮對比）、Action Title（結論先行標題）。
  - **繪圖負向約束清單**：過濾立體陰影、彩虹配色與擁擠圓餅圖。
  - **3 大高頻商業圖表模板**：策略優先級 2x2 矩陣（Mermaid）、利潤變動瀑布圖（Plotly）、高亮對比長條圖（Seaborn）。

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
