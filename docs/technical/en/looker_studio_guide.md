# Google Looker Studio Dashboard Guide

This guide provides setup instructions for building a production-ready, zero-cost e-commerce revenue dashboard connected to BigQuery Gold marts.

---

## 1. Connecting Data Sources in Looker Studio

1. Navigate to [Google Looker Studio](https://lookerstudio.google.com/) and click **Create** ➔ **Data Source**.
2. Select the **BigQuery** connector:
   - **Project**: Select your GCP Project ID.
   - **Dataset**: Select `platzi_gold`.
   - **Tables to Connect**:
     - Connect `gold_daily_sales_kpi` (Primary Sales Metrics).
     - Connect `gold_customer_ltv` (Customer Retention & Segmentation).
     - Connect `gold_product_performance` (Merchandising Leaderboard).

---

## 2. Dashboard Visual Blueprint

### Page 1: Executive Revenue & Order Trends
* **Top Summary Scorecards**:
  - `GMV` (Gross Merchandise Value)
  - `Net Revenue` (Actual cash intake, completed orders only)
  - `AOV` (Average Order Value)
  - `Completed Orders` vs. `Cancellation Rate` (%)
* **Main Chart (Time-Series Dual Axis)**:
  - **Dimension**: `order_date` (Date)
  - **Metric 1 (Bars)**: `gmv` (Light blue)
  - **Metric 2 (Line)**: `net_revenue` (Dark blue / Green)
  - **Date Range Control**: Last 30 / 60 / 90 Days.

---

### Page 2: Customer Cohorts & Lifetime Value (LTV)
* **Customer Tier Distribution (Donut Chart)**:
  - **Dimension**: `customer_tier` (`Platinum`, `Gold`, `Silver`, `Bronze`)
  - **Metric**: `Record Count` & `lifetime_net_revenue`
* **High-Value Customer Leaderboard (Table)**:
  - **Dimensions**: `customer_id`, `customer_name`, `customer_tier`, `first_order_date`, `last_order_date`
  - **Metrics**: `completed_orders`, `lifetime_net_revenue`
  - *(Note: Sensitive PII such as email/phone is securely masked at the Silver layer)*.

---

### Page 3: Merchandising & Product Performance
* **Top Revenue Generators (Bar Chart)**:
  - **Dimension**: `product_title`
  - **Metric**: `completed_sales_amount` (Sorted Descending)
* **Category Breakdown (Treemap)**:
  - **Dimension**: `category_name`
  - **Metric**: `units_sold`
* **Refund Rate Watchlist (Table)**:
  - Highlights products with disproportionately high `refunded_units`.

---

## 3. Cost & Performance Optimization
- Looker Studio queries against `platzi_gold` benefit from pre-aggregated data, scanning only kilobytes per query.
- Free-tier BigQuery allocations (1 TB query scan per month) easily cover daily executive viewing.
