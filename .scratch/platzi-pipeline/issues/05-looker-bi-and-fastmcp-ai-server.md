# 05: Downstream BI Dashboard and FastMCP AI Service

**What to build:** The business delivery and AI consumption layers. A Google Looker Studio dashboard template connecting natively to BigQuery Gold marts displaying interactive e-commerce KPIs (revenue trends, customer retention, product leaderboards). A secure FastMCP server exposes BigQuery Gold metrics tools to AI agents, enabling natural language business questioning ("What was Net Revenue last week?") while strictly prohibiting access to raw customer PII and enforcing query byte scan budgets.

**Blocked by:** 04: Docker Packaging and Serverless Orchestration

**Status:** closed

- [x] Looker Studio data source configuration and dashboard blueprint connecting to `gold_daily_sales_kpi`, `gold_customer_ltv`, and `gold_product_performance`.
- [x] Dashboard features interactive filters (date range, product category) and displays GMV, Net Revenue, AOV, and LTV.
- [x] FastMCP server implemented under `mcp_server/` using Python FastMCP SDK.
- [x] AI tools expose analytical functions (e.g., `get_kpi_summary`, `get_top_products`, `get_customer_cohorts`).
- [x] Tool logic strictly restricts querying to the `platzi_gold` dataset; access to Bronze and Silver is blocked.
- [x] Query limits and maximum byte scan budgets are enforced to prevent runaway BigQuery costs.
- [x] Verification script demonstrates successful tool invocation and natural language query response.
