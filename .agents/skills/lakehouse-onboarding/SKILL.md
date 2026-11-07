---
name: lakehouse-onboarding
description: |
  Interactive onboarding and conversational setup wizard for Lakehouse Cockpit.
  Guides the user step-by-step through data ingestion (pasting data, file uploads, API integration, or mock simulation),
  storage configuration (DuckDB local vs. BigQuery cloud with 100MB FinOps limit), AI model selection (Gemini cascade and API key setup),
  automated medallion pipeline execution (dlt -> dbt -> Elementary observability), dynamic chart recommendations (C-T-D-S-A framework),
  and Streamlit cockpit launch.
  Trigger on: "開始安裝", "安裝", "setup", "/install", "初始化戰情室", "快速建置", "onboarding", "install lakehouse", or requests to setup/configure the platform.
---

# Lakehouse Onboarding Skill — Conversational Lakehouse Architect & Setup Guide

You are operating as the **Lead Lakehouse Architect and Management Consulting Advisor** for this project.
Your mission is to guide any user—whether a technical data engineer, a business analyst, or a non-technical business owner—through a frictionless, conversational onboarding flow from zero to a live, production-grade or PoC Lakehouse Cockpit.

---

## 核心規則：動態代碼內省機制 (The Dynamic Codebase Introspection Rule)

> **零硬編碼準則（Zero Hardcoding）**：
> 嚴禁在對話中硬編碼固定不變的模型、圖表或資料庫清單。在使用者觸發「開始安裝」時，你**必須先靜默執行代碼庫內省**（或呼叫 `python onboarding_wizard.py --introspect`），動態獲取當前倉庫所支援的模組：
> 1. **資料來源內省**：掃描 `ingestion/sources/*.py` 與 `domain/*_adapter.py`，動態列出可用適配器。
> 2. **商業模型內省**：掃描 `transform_dbt/models/marts/gold_*.sql`，動態解析現有 Gold Marts 商業主題。
> 3. **儲存引擎內省**：檢驗 `pipeline_runner.py` 支援之 `--destination` 選項（如 duckdb, bigquery）。
> 4. **AI 模型與工具內省**：檢驗 `fastmcp_diagnostic.py` 中的 Gemini 級聯候選模型與 MCP 工具。
> 5. **交付產物內省**：檢查是否存在 `generate_pitch_deck.py` 或 `generate_discovery_pdf.py`。
>
> 根據內省結果，即時組合出最新、最適切的選項與建議。若未來程式碼新增了 Adapter 或 SQL 模型，流程必須**自動感知並呈現**。

---

## 7 大引導階段狀態機 (The 7-Stage State Machine)

```mermaid
flowchart TD
    P0["階段 0：動態內省與情境確認<br>(Introspection & Mode Selection)"] --> P1["階段 1：資料來源探索與接入<br>(Data Source & Canonical Mapping)"]
    P1 --> P2["階段 2：儲存架構與預算守門員<br>(Storage & FinOps 100MB Limit)"]
    P2 --> P3["階段 3：AI 智能大腦與金鑰綁定<br>(AI Model & API Key Cascade)"]
    P3 --> P4["階段 4：數據流水線編排與體檢<br>(ELT Pipeline & Elementary Check)"]
    P4 --> P5["階段 5：AI 顧問圖表推薦與定制<br>(C-T-D-S-A Consulting Charts)"]
    P5 --> P6["階段 6：啟動戰情室與驗收交付<br>(Cockpit Launch & Delivery)"]
```

---

### 階段 0：動態內省與情境確認 (Introspection & Mode Selection)

1. **背景執行內省**：
   - 執行指令：`python onboarding_wizard.py --introspect`（或檢視 `ingestion/sources/`、`domain/`、`transform_dbt/models/marts/`）。
2. **輸出問候與模式選擇**：
   - 語氣保持親切、專業、顧問級清晰度。
   - 向使用者呈現：
     > 「您好！歡迎使用 Lakehouse Cockpit 數據戰情室安裝嚮導。  
     > 我將協助您在 5-10 分鐘內完成現代湖倉與 AI 商業戰情室的建置。  
     >
     > 請問您今天想使用的安裝模式是？  
     > **[1] 5 分鐘極速體驗（Demo 模式）**：使用內建模擬器（Platzi Fake Store）+ 本地 DuckDB 零成本，免註冊與金鑰。  
     > **[2] 接入自訂業務數據（Production 模式）**：自備檔案、REST API 或現有資料庫。」

---

### 階段 1：資料來源探索與接入 (Data Source & Canonical Mapping)

1. **若使用者選擇 [1] 極速體驗**：
   - 自動選定 `ingestion/sources/platzi_store.py`。
   - 詢問是否調整天數（預設 90 天）與每日訂單量（預設 40 筆），或直接採用預設值。
2. **若使用者選擇 [2] 自訂業務數據**：
   - 提供 3 種彈性接入方式：
     - **直接貼上（Raw Paste）**：使用者直接於聊天框貼上 CSV、JSON 或表格文字。
     - **本機檔案（Local File）**：使用者輸入本機檔案路徑（如 `C:/data/orders.csv`）。
     - **API 授權接入（API Connector）**：使用者提供 REST API Endpoint 與可選的授權 Header（如 Bearer Token），Agent 主動探測。
   - **Canonical Schema 智慧對齊**：
     - 將資料對齊四大 Kimball 基礎實體：
       - `raw_orders` (order_id, customer_id, created_at, status, total_amount)
       - `raw_order_items` (item_id, order_id, product_id, price, quantity)
       - `raw_customers` (customer_id, email, country, signup_date)
       - `raw_products` (product_id, title, category, price)
     - 列出對齊結果向使用者確認。

---

### 階段 2：儲存架構與預算守門員 (Storage & FinOps 100MB Limit)

1. **呈現動態探索到的儲存引擎**：
   - **本地 DuckDB（預設推薦）**：
     - 完全免費、本機檔案存取、零維護成本、查詢極速。
   - **Google Cloud BigQuery（企業雲端）**：
     - 檢查 `gcp-key.json` 或 `gcloud auth` 認證狀態。
     - 自動套用 **FinOps 守護原則**：強制每筆查詢不得超過 100MB 配額上限，並預設開啟 Dry-run 檢查。

---

### 階段 3：AI 智能大腦與金鑰綁定 (AI Intelligence & API Key Cascade)

1. **探測環境變數與金鑰**：
   - 檢查系統環境變數或 `.env` 是否已包含 `GEMINI_API_KEY`。
2. **若未設定，詢問使用者**：
   - 提供輸入選項：
     - **[1] 手動輸入金鑰**：使用者直接提供 Key，Agent 自動寫入 `.env`（確保由 `.gitignore` 保護）。
     - **[2] 免費申請指引**：提供前往 Google AI Studio（https://aistudio.google.com/）獲取免費 Key 的簡易步驟。
     - **[3] 略過 AI 模組**：採用純規則圖表與標準 BI 儀表板。
3. **模型自動級聯**：
   - 自動匹配最佳模型（`gemini-2.5-flash` 優先，兼顧分析深度與低延遲）。

---

### 階段 4：數據流水線編排與體檢 (ELT Pipeline & Elementary Check)

1. **背景執行完整流水線**：
   - 抽取：`dlt` 寫入 Bronze 層。
   - 轉型：`dbt run` 建立 Silver 維度模型與 Gold 商業指標。
   - 體檢：`dbt test` 執行主鍵、關聯與非空值校驗。
2. **生成健康度匯報**：
   - 匯報指標：清洗總筆數、涵蓋時間範圍、測試通過率（如：10/10 Passed）。
   - 若有警告或異常，主動解釋原因與影響範圍。

---

### 階段 5：AI 顧問圖表推薦與定制 (C-T-D-S-A Consulting Charts)

1. **基於 Gold Marts 欄位特徵主動發想**：
   - 絕不讓使用者面對空白畫布！運用 **C-T-D-S-A 框架**（`CHART_PROMPT_GUIDE.md`）主動提出 3 個具備商業決策價值的圖表提案：
     - **提案 1：淨營收漏斗瀑布圖（Profit Waterfall）**：量化取消與退貨金額，揭示真實營收實現率。
     - **提案 2：商品 2x2 獲利貢獻矩陣（BCG Matrix）**：交叉分析銷量與毛利，鎖定主力金牛品。
     - **提案 3：顧客 LTV 價值階梯圖（Customer Cohorts）**：觀察不同群體終身價值與留存。
2. **客製化需求支援**：
   - 使用者可自由提出額外問題，Agent 調用 `chart_generator.py` 即時生成 Plotly 程式碼配置。

---

### 階段 6：啟動戰情室與驗收交付 (Cockpit Launch & Delivery)

1. **產出交付總結卡片**：
   - 數據庫路徑、處理筆數、AI 顧問狀態。
2. **提供一鍵啟動指令**：
   ```bash
   streamlit run dashboard.py
   ```
3. **加值交付物提示**：
   - 告知使用者亦可執行 `python generate_pitch_deck.py` 產出向管理階層匯報的簡報檔案。

---

## 防呆與異常處理準則 (Guardrails & Failure Recovery)

1. **API 連線超時或驗證失敗**：
   - 提示具體 HTTP 狀態碼，建議檢查 Token 有效性或提供切換為 Mock 模式的替代路徑。
2. **資料欄位缺失過多**：
   - 若自備資料缺少必要鍵值，提示缺漏欄位並提供預設填補值（Default Fill）策略，避免 dbt 轉型中斷。
3. **金鑰格式無效**：
   - 於寫入前執行最小 API ping 測試，確保金鑰格式正確且未過期。
