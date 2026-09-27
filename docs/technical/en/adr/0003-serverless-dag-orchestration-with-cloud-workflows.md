# 3. Serverless Visual DAG Orchestration with Cloud Workflows and Cloud Run Jobs

Date: 2026-09-17
Status: accepted

## Context
在 ADR 0001 中，我們採用了 Cloud Scheduler 直接觸發單一 Cloud Run Job 的極簡無伺服器架構。雖然成功實現了零閒置成本（$0 Idle Cost）與 NoOps，但隨著管線擴展至包含資料品質測試與 Elementary Data 可觀測性（Observability），我們面臨以下挑戰：
1. **黑盒子單一容器**：單一 Job 內部連續執行 Ingest、Transform、Test，一旦中間某個步驟失敗，難以在 GCP Console 直觀看出是哪一階段中斷。
2. **缺乏流程圖視覺化（Visual DAG）**：使用者與維運人員高度依賴類似 Apache Airflow 的 DAG 流程圖來監控各階段執行狀態、執行耗時與依賴關係。
3. **Apache Airflow / Cloud Composer 成本過高**：傳統 Airflow 需長駐 VM 或 Kubernetes 集群（Cloud Composer 最低約 $300+/月），違反中小企業輕量化架構的經濟原則。

## Decision
我們決定將調度層升級為 **Google Cloud Scheduler + Google Cloud Workflows + Cloud Run Jobs** 的混合無伺服器架構：
1. **解耦管線執行階段**：
   - 透過 `pipeline_runner.py --target=ingest|transform|test` 支援單一步驟獨立執行。
2. **採用 Cloud Workflows 作為無伺服器 DAG 調度中心**：
   - 使用 YAML 定義宣告式狀態機（`platzi-pipeline-orchestrator`）。
   - Workflows 呼叫官方 Cloud Run Admin API Connector（`googleapis.run.v2.projects.locations.jobs.run`），依序執行：
     - **Step 1: `run_ingest_step`**（`dlt` 擷取寫入 BigQuery Bronze）
     - **Step 2: `run_transform_step`**（`dbt run` 建立 Silver 與 Gold 星型模型）
     - **Step 3: `run_test_step`**（`dbt test` 驗證 32 項資料品質規則與 Elementary 收集）
   - Workflows Connector 自動處理長輪詢與失敗重試，完全無需人工作業。
3. **Cloud Scheduler 觸發 Workflows**：
   - Cloud Scheduler 每日定時向 Cloud Workflows Executions API 發送 HTTP POST 請求喚醒整個 DAG。
4. **Terraform 完全自動化**：
   - 在 `terraform/workflows.tf` 中宣告 Workflows 與 IAM 權限，納入 IaC 統一控管。

## Consequences
- **優點**：
  - **原生 Visual DAG**：在 Google Cloud Console 中直接提供與 Airflow 相同水準的 step-by-step 流程圖視覺化，每個步驟的即時進度、耗時、輸入輸出清楚可見。
  - **維持零閒置成本（$0 Idle Cost）**：Cloud Workflows 每月前 5,000 個 step 完全免費，非執行時無任何 VM 或 Container 佔用計費，月費依然為 $0。
  - **模組化與可維護性**：任一步驟（如測試失敗）不會影響前期成功的 Ingestion，亦可手動在 Workflows 介面或 CLI 重新執行特定步驟。
  - **無縫整合 Elementary Data**：測試步驟獨立為 DAG 的終端節點，產出品質告警與 Data Lineage 報告。
- **限制與權衡**：
  - Cloud Workflows 採用 YAML / JSON 宣告式語法，相較於 Airflow 的純 Python DSL，自定義複雜動態邏輯的彈性稍低；但對於現代 ELT 數據管線（Ingest -> Transform -> Test）而言，Cloud Workflows 的結構清晰且足夠強大。
