# Platzi E-Commerce Analytics Platform

提供中小企業現代化雲端數據中台（ELT + BI + AI）的原型與示範架構，兼具極低維運成本與商業擴充性。

## Language

**Customer**:
在平台上註冊並進行消費的終端顧客（對應數據來源的 User 實體）。
_Avoid_: Client, Account, Buyer

**Product**:
電商平台上架銷售的商品實體，隸屬於特定 Category。
_Avoid_: Item, SKU (除非特指商品庫存單元代碼)

**Order**:
由 Customer 發起的一筆完整購物交易記錄，包含一或多個 Order Items。
狀態嚴格遵循生命週期狀態機：`completed`（已完成）、`cancelled`（已取消）、`refunded`（已退款）。
_Avoid_: Transaction, Purchase

**GMV (Gross Merchandise Value)**:
商品交易總額。計算所有成功建立的訂單原始標價總合（未扣除取消、退款與折扣）。
_Avoid_: Total Sales

**Net Revenue**:
實際淨營收。僅計算狀態為 `completed` 的訂單金額，並扣除折扣與退款金額。
_Avoid_: Revenue, Sales (語意模糊，未指明毛或淨)

**AOV (Average Order Value)**:
平均客單價。特定時間窗內的 Net Revenue 除以 Completed Orders 數量。
_Avoid_: Basket Size, Average Basket

**LTV (Customer Lifetime Value)**:
顧客終身價值。單一 Customer 自首購以來到目前為止所貢獻的累計 Net Revenue。
_Avoid_: Customer Value

**Canonical Schema**:
所有資料來源（Platzi API、未來 Shopify 或 ERP）經由適配器（Adapter）轉換後的統一中繼標準結構（`raw_orders`, `raw_customers`, `raw_products`），供下游 dbt 模型無縫複用。

**Watermark (Cursor)**:
用於增量數據擷取的時間戳記（`updated_at`），僅抓取大於等於游標時間的新增或異動資料。
_Avoid_: Checkpoint, Bookmark

**PII (Personally Identifiable Information)**:
顧客個人身分識別資訊（真實姓名、Email、電話、收貨地址）。此類欄位嚴格隔離於 Silver 以下層級，嚴禁流入 Gold 聚合層與 AI 查詢介面。

**Medallion Layers**:
- **Bronze**: 原始資料層。由 `dlt` 自動寫入，保留 API / Simulator 的原始巢狀 JSON，採 Append-only 記錄歷史。
- **Silver**: 清洗與標準化層。由 `dbt` 轉換，將巢狀結構展平為符合 Kimball 標準的維度表（`dim_*`）與事實表（`fct_*`）。
- **Gold**: 商業指標與聚合層。由 `dbt` 產出面向下游 Looker Studio 與 FastMCP 的高效能聚合表（`gold_*`）。

## Architecture & Orchestration

- **Data Flow**: Ingestion (`dlt`) -> Transformation (`dbt run`) -> Quality Assurance (`dbt test` + Elementary Data).
- **Serverless Orchestration**:
  - **Scheduler**: Google Cloud Scheduler (Cron `0 2 * * *`)
  - **Visual DAG**: Google Cloud Workflows (`platzi-pipeline-orchestrator`), providing step-by-step visual monitoring in GCP Console without server overhead.
  - **Compute**: Google Cloud Run Jobs (`platzi-pipeline-job`), executing containerized steps (`--target=ingest|transform|test`) on demand.
- **Architecture Decision Records (ADRs)**:
  - [`docs/adr/0001-serverless-orchestration-cloud-run-and-scheduler.md`](docs/adr/0001-serverless-orchestration-cloud-run-and-scheduler.md)
  - [`docs/adr/0002-pluggable-sources-and-incremental-strategy.md`](docs/adr/0002-pluggable-sources-and-incremental-strategy.md)
  - [`docs/adr/0003-serverless-dag-orchestration-with-cloud-workflows.md`](docs/adr/0003-serverless-dag-orchestration-with-cloud-workflows.md)

