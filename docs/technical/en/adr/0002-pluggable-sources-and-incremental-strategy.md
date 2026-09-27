# 2. Pluggable Source Adapters, Incremental ELT, and AI Security Boundary

Date: 2026-09-16
Status: accepted

## Context
本專案為面向中小企業的商業原型（Prototype）。為達成「未來接案可直接抽換客戶數據來源」並兼顧大數據量下的運算成本控制與資安合規，必須在架構層面解耦資料來源、確立增量處理機制，並界定 AI 查詢工具的安全範疇。

## Decision
1. **可抽換資料來源架構（Pluggable Source Adapter）**：
   - 資料擷取層抽像化為獨立來源適配器（`ingestion/sources/`）。
   - 適配器統一產出規範化中繼標準（Canonical Schema：`raw_orders`, `raw_customers`, `raw_products`）。更換客戶資料源時，只需新增適配器，下游 dbt 模型完全複用。
2. **端到端增量處理（Incremental ELT）**：
   - `dlt` 以 `updated_at` 時間戳記為 Watermark 游標，僅擷取增量變更。
   - `dbt` 在 Silver 與 Gold 層採用 `materialized='incremental'`，以 `order_id` 為主鍵進行 Merge/Upsert，大幅縮短運算時間與 BigQuery 掃描費用。
3. **AI 查詢安全邊界（FastMCP Scope & Governance）**：
   - AI 工具僅開放對 `Gold` 層（去識別化商業聚合寬表）的唯讀權限。
   - 嚴格隔離 PII 個資（姓名、Email 等僅保留於 Bronze/Silver 且不外露給 AI）。
   - FastMCP 內建單次查詢 byte 上限防護，杜絕雲端費用失控。

## Consequences
- **優點**：
  - 極高的顧問專案複用率，大幅縮短商業交付週期。
  - 運算與儲存費用隨時間累積依然保持平穩。
  - 符合企業個資合規要求，消除中小企業對 AI 存取資料庫的安全疑慮。
