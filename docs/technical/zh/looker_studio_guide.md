# Google Looker Studio BI 商業儀表板建置指南

[繁體中文](looker_studio_guide.md) | [English](../en/looker_studio_guide.md)

本指南說明如何連線至 BigQuery Gold 商業資料市集，打造企業級、零伺服器授權費用的現代電商營收監控儀表板。

---

## 1. 在 Looker Studio 中連線 BigQuery 資料源

1. 前往 [Google Looker Studio](https://lookerstudio.google.com/)，點擊 **建立 (Create)** ➔ **資料來源 (Data Source)**。
2. 選擇 **BigQuery** 連接器：
   - **專案 (Project)**：選擇您的 GCP Project ID（例如 `de-consulting-508822`）。
   - **資料集 (Dataset)**：選擇 `platzi_gold`。
   - **建議連線的三張商業市集表**：
     - `gold_daily_sales_kpi`（核心營收與訂單轉換指標）。
     - `gold_customer_ltv`（顧客終身價值與會員分群）。
     - `gold_product_performance`（商品銷量與退貨率排行榜）。

---

## 2. 儀表板頁面視覺化藍圖

### 第一頁：高階管理層營收與訂單趨勢 (Executive Revenue & Order Trends)
* **頂部 KPI 摘要卡 (Scorecards)**：
  - `GMV`（總交易額 Gross Merchandise Value）
  - `Net Revenue`（淨營收，僅計入 Completed 已完成訂單）
  - `AOV`（平均客單價 Average Order Value）
  - `Completed Orders`（成交訂單數） vs. `Cancellation Rate`（取消率 %）
* **核心雙軸時間序列圖 (Time-Series Dual Axis)**：
  - **時間維度**：`order_date`（訂單日期）
  - **柱狀圖指標 (Bars)**：`gmv`（淺藍色）
  - **折線圖指標 (Line)**：`net_revenue`（深藍 / 翠綠色）
  - **日期篩選器**：預設過去 30 / 60 / 90 天切換。

---

### 第二頁：顧客分群與終身價值 (Customer Cohorts & LTV)
* **顧客等級分佈環形圖 (Donut Chart)**：
  - **分群維度**：`customer_tier`（`Platinum`, `Gold`, `Silver`, `Bronze`）
  - **數值指標**：顧客數 (Record Count) 與 `lifetime_net_revenue`（各級貢獻營收）
* **高價值 VIP 顧客排行榜 (Table)**：
  - **維度**：`customer_id`, `customer_name`, `customer_tier`, `first_order_date`, `last_order_date`
  - **指標**：`completed_orders`, `lifetime_net_revenue`
  - *(注意：電話、Email 等敏感個資已在 Silver 層完成去識別化與遮罩)*。

---

### 第三頁：商品品類與退貨率分析 (Merchandising & Product Performance)
* **熱銷商品排行柱狀圖 (Bar Chart)**：
  - **維度**：`product_title`
  - **指標**：`completed_sales_amount`（降冪排序）
* **商品類別矩形樹狀圖 (Treemap)**：
  - **維度**：`category_name`
  - **指標**：`units_sold`（總銷售件數）
* **高退貨率警戒表 (Table)**：
  - 標示 `refunded_units` 與退款率異常偏高的商品，作為供應鏈與品管預警指標。

---

## 3. 成本與查詢效能最佳化 (Cost & Performance)
- Looker Studio 直接查詢 `platzi_gold` 預先彙總（Pre-aggregated）後的寬表，每次查詢僅需掃描數 KB 至數 MB 資料量。
- 完全在 Google BigQuery 每月提供的 **1 TB 免費查詢額度** 之內，達到 0 元授權、0 元主機開銷的現代 BI 體驗。
