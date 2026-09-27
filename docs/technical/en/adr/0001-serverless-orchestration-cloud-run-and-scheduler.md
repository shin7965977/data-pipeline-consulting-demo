# 1. Serverless Orchestration via Cloud Scheduler and Cloud Run Jobs

Date: 2026-09-16
Status: accepted

## Context
本專案為面向中小企業（SME）的商業數據管線原型與顧問展示。傳統企業常用 Apache Airflow 作為調度中心，但 Airflow 需要長駐伺服器（VM 或 Cloud Composer），月維護成本高（$30~500+/月），且需要專人維護底層 PostgreSQL 與作業系統健康狀態。中小企業的營運需求以每日批次更新（Daily Batch）與偶發性手動重整為主。

## Decision
我們決定採用 **GCP Cloud Scheduler + Cloud Run Jobs** 作為管線的工作流調度架構，取代常駐的 Apache Airflow：
1. 將 `dlt` 資料擷取與 `dbt` 轉換模型統一打包進 Docker 映像檔，儲存於 GCP Artifact Registry。
2. 以 Cloud Run Jobs 執行批次運算，由 Cloud Scheduler 設定 Cron 定時喚醒。
3. 容器支援 CLI 參數化（`--target=all|ingest|transform`），兼顧日常自動排程與手動單獨觸發。

## Consequences
- **優點**：
  - 極低擁有成本（TCO）：基礎設施月費接近 $0（符合 Cloud Scheduler 與 Cloud Run 免費額度）。
  - 零伺服器維運（NoOps）：無主機當機、硬碟耗盡或需修補 OS 漏洞的風險。
  - 一鍵可重現性：全套基礎設施（包含 Cloud Scheduler 與 Cloud Run Jobs）完全由 Terraform 程式化管理。
- **限制與權衡**：
  - 缺乏 Airflow 原生複雜跨 DAG 依賴視覺化看板；但對中小企業單一端到端批次管線而言，此取捨完全符合經濟效益。
