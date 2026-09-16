import os
from decimal import Decimal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# 1. Page Configuration & Modern Design System
# ==============================================================================
st.set_page_config(
    page_title="Platzi E-Commerce Executive Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Sleek Dark Glassmorphism Styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Metric Cards - Adaptive to Light and Dark Mode */
    .metric-card {
        background: var(--secondary-background-color, #ffffff);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.18);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-label {
        font-size: 0.825rem;
        font-weight: 600;
        color: var(--text-color, #475569);
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        color: var(--text-color, #0f172a) !important;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }
    .metric-subtext {
        font-size: 0.785rem;
        color: #10b981;
        font-weight: 600;
    }
    .metric-subtext.warning {
        color: #d97706;
    }
    
    /* Header Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.85rem;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 9999px;
        color: #34d399;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .pulse-dot {
        width: 8px;
        height: 8px;
        background: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 10px #10b981;
    }
    
    /* Right Fixed Sidebar Rail (mirrors left sidebar) */
    .right-sidebar-rail {
        position: sticky;
        top: 2.5rem;
        max-height: calc(100vh - 4rem);
        overflow-y: auto;
        background: var(--secondary-background-color, #1e293b);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 16px;
        padding: 1.25rem 1.4rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    .right-sidebar-rail::-webkit-scrollbar {
        width: 6px;
    }
    .right-sidebar-rail::-webkit-scrollbar-thumb {
        background: rgba(128, 128, 128, 0.3);
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. BigQuery Data Loader with Intelligent Fallback
# ==============================================================================
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "de-consulting-508822")
KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.abspath("gcp-key.json"))

if os.path.exists(KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH


@st.cache_data(ttl=300)
def load_gold_data():
    """Load analytical Gold marts strictly and exclusively from Google Cloud BigQuery (platzi_gold)."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)

    df_kpi = client.query(
        f"SELECT * FROM `{PROJECT_ID}.platzi_gold.gold_daily_sales_kpi` ORDER BY order_date"
    ).to_dataframe()
    df_ltv = client.query(
        f"SELECT * FROM `{PROJECT_ID}.platzi_gold.gold_customer_ltv` ORDER BY lifetime_net_revenue DESC"
    ).to_dataframe()
    df_prod = client.query(
        f"SELECT * FROM `{PROJECT_ID}.platzi_gold.gold_product_performance` ORDER BY completed_sales_amount DESC"
    ).to_dataframe()

    # Convert Decimals to float if any
    for df in [df_kpi, df_ltv, df_prod]:
        for col in df.columns:
            if df[col].dtype == object and len(df) > 0 and isinstance(df[col].iloc[0], Decimal):
                df[col] = df[col].astype(float)

    source_info = f"Google Cloud BigQuery ({PROJECT_ID}.platzi_gold)"
    return df_kpi, df_ltv, df_prod, source_info


# Load datasets
with st.spinner("Connecting to Google Cloud BigQuery..."):
    try:
        df_kpi, df_ltv, df_prod, data_source = load_gold_data()
        df_kpi["order_date"] = pd.to_datetime(df_kpi["order_date"])
    except Exception as err:  # noqa: BLE001
        st.error(f"⚠️ 無法載入資料：{err}")
        st.stop()

# ==============================================================================
# 3. Sidebar Navigation & Global Filters
# ==============================================================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=80", use_container_width=True)
    st.title("🛍️ 營運智慧中心")
    st.caption("Serverless ELT Modern Lakehouse")

    st.markdown("---")
    st.markdown(f"**資料來源：**\n`{data_source}`")

    # Date Filter
    import datetime

    min_date = df_kpi["order_date"].min().date()
    max_date = df_kpi["order_date"].max().date()
    
    st.subheader("📅 時間區間篩選")
    calendar_min = min_date - datetime.timedelta(days=90)
    calendar_max = datetime.date.today() + datetime.timedelta(days=1)
    if calendar_max < max_date:
        calendar_max = max_date

    selected_dates = st.date_input(
        "選擇日期範圍",
        value=(min_date, max_date),
        min_value=calendar_min,
        max_value=calendar_max,
        help="目前 BigQuery 資料庫每日銷售記錄區間為 9/12 ~ 9/16（由模擬器最近批次產出之交易流水）。",
    )

    if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
        start_d, end_d = selected_dates
        mask = (df_kpi["order_date"].dt.date >= start_d) & (df_kpi["order_date"].dt.date <= end_d)
        filtered_kpi = df_kpi.loc[mask]
    elif isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 1:
        start_d = selected_dates[0]
        end_d = start_d
        mask = df_kpi["order_date"].dt.date >= start_d
        filtered_kpi = df_kpi.loc[mask]
    else:
        start_d, end_d = min_date, max_date
        filtered_kpi = df_kpi

    # BigQuery Gold Data Export / Download Section
    st.markdown("#### 📥 下載 BigQuery 金牌完整數據")
    export_table = st.selectbox(
        "選擇要下載的 BigQuery 金牌資料表",
        options=[
            "📅 依所選日期區間 (KPI)",
            "📊 完整歷史每日銷售 (全量)",
            "💎 客戶終身價值 LTV (全量)",
            "🏆 熱銷商品業績排行 (全量)",
        ],
    )
    if "所選日期區間" in export_table:
        export_df = filtered_kpi
        file_suffix = f"_{start_d}_to_{end_d}" if "start_d" in locals() and "end_d" in locals() else ""
        dl_filename = f"bigquery_gold_daily_kpi{file_suffix}.csv"
        dl_label = f"下載區間 KPI ({len(export_df)} 筆)"
    elif "完整歷史每日銷售" in export_table:
        export_df = df_kpi
        dl_filename = "bigquery_gold_daily_sales_kpi_full.csv"
        dl_label = f"下載全量每日 KPI ({len(export_df)} 筆)"
    elif "客戶終身價值" in export_table:
        export_df = df_ltv
        dl_filename = "bigquery_gold_customer_ltv_full.csv"
        dl_label = f"下載全量客戶 LTV ({len(export_df)} 筆)"
    else:
        export_df = df_prod
        dl_filename = "bigquery_gold_product_performance_full.csv"
        dl_label = f"下載全量商品排行 ({len(export_df)} 筆)"

    st.download_button(
        label=f"💾 {dl_label} (CSV)",
        data=export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=dl_filename,
        mime="text/csv",
        help=f"完全直接從 Google Cloud BigQuery ({PROJECT_ID}.platzi_gold) 匯出之完整金牌數據",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("### 🤖 Gemini AI 設定")
    user_gemini_key = st.text_input(
        "輸入 Gemini API Key (選填)",
        type="password",
        value=os.getenv("GEMINI_API_KEY", ""),
        help="輸入後將啟用 Google Gemini 原生對話與 Function Calling，直接與 BigQuery 進行 AI 互動！",
    )
    st.caption("⚡ **全自動版本協議**：已鎖定永遠自動調用 Google API 最新旗艦模型（無需手動選取），永不過期。")
    target_model = "auto"

    st.markdown("---")
    st.markdown("### 🖥️ 介面排版設定")
    show_ai_panel = st.toggle("🤖 滿版右側 FastMCP 顧問", value=True, help="於網頁右側展開或收合完整滿版 AI 營運顧問面板")
    if show_ai_panel:
        ai_width = st.select_slider("右側顧問寬度", options=["小 (25%)", "標準 (32%)", "寬闊 (40%)"], value="標準 (32%)")
    else:
        ai_width = "0%"

    st.markdown("---")
    st.markdown("### 🏛️ 架構特性")
    st.markdown("- ⚡ **0 閒置成本** (Cloud Run Jobs)")
    st.markdown("- 🔒 **全自動 PII 雜湊** (SHA-256)")
    st.markdown("- 🤖 **FastMCP / Gemini Tool Calling**")

# ==============================================================================
# 4. Main Two-Column Layout (Left: Analytics Workspace, Right: Full-Height FastMCP Copilot)
# ==============================================================================
if show_ai_panel:
    if ai_width == "小 (25%)":
        col_main, col_ai = st.columns([75, 25], gap="large")
    elif ai_width == "寬闊 (40%)":
        col_main, col_ai = st.columns([60, 40], gap="large")
    else:  # 標準 (32%)
        col_main, col_ai = st.columns([68, 32], gap="large")
else:
    col_main = st.container()
    col_ai = None

with col_main:
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.title("E-Commerce Retail Analytics Dashboard")
        st.markdown("基於 **Platzi Store API + dlt + GCP BigQuery Medallion + dbt-core** 的現代數據湖倉視覺化總覽")
    with header_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: right;">
                <div class="status-badge">
                    <div class="pulse-dot"></div>
                    Live BigQuery Connected
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Aggregate High-Level Metrics
    total_gmv = filtered_kpi["gmv"].sum()
    total_net_rev = filtered_kpi["net_revenue"].sum()
    total_orders = filtered_kpi["total_orders"].sum()
    completed_orders = filtered_kpi["completed_orders"].sum()
    cancelled_orders = filtered_kpi["cancelled_orders"].sum()
    refunded_orders = filtered_kpi["refunded_orders"].sum()
    avg_aov = filtered_kpi["aov"].mean()
    cancel_rate = (cancelled_orders / total_orders * 100) if total_orders > 0 else 0
    refund_rate = (refunded_orders / total_orders * 100) if total_orders > 0 else 0

    # 4 Executive KPI Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">總銷售額 (GMV)</div>
                <div class="metric-value">${total_gmv:,.2f}</div>
                <div class="metric-subtext">累積總銷售訂單金流</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">淨實質營收 (Net Revenue)</div>
                <div class="metric-value">${total_net_rev:,.2f}</div>
                <div class="metric-subtext">已扣除退款與折扣</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">平均客單價 (AOV)</div>
                <div class="metric-value">${avg_aov:,.2f}</div>
                <div class="metric-subtext">成交訂單均額</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">訂單退款率 / 取消率</div>
                <div class="metric-value">{refund_rate:.1f}% <span style="font-size:1rem;color:#94a3b8;">/ {cancel_rate:.1f}%</span></div>
                <div class="metric-subtext warning">退款 {refunded_orders} 單 / 取消 {cancelled_orders} 單</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if show_ai_panel:
        tab1, tab2, tab3 = st.tabs([
            "📈 營收走勢與轉換漏斗",
            "👥 客戶終身價值 (LTV) 分群",
            "🏆 熱銷商品與類別排行",
        ])
        tab4 = None
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 營收走勢與轉換漏斗",
            "👥 客戶終身價值 (LTV) 分群",
            "🏆 熱銷商品與類別排行",
            "🤖 FastMCP AI 數據對話",
        ])

# ------------------------------------------------------------------------------
# TAB 1: 每日營收走勢與轉換漏斗
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("📊 每日 GMV 與實質淨營收趨勢")
    
    fig_rev = go.Figure()
    fig_rev.add_trace(
        go.Scatter(
            x=filtered_kpi["order_date"],
            y=filtered_kpi["gmv"],
            mode="lines+markers",
            name="GMV (總銷售)",
            line={"color": "#6366f1", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.1)",
        )
    )
    fig_rev.add_trace(
        go.Scatter(
            x=filtered_kpi["order_date"],
            y=filtered_kpi["net_revenue"],
            mode="lines+markers",
            name="Net Revenue (實質淨營收)",
            line={"color": "#10b981", "width": 3},
        )
    )
    fig_rev.update_layout(
        template="plotly_dark",
        height=380,
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        xaxis={"showgrid": False},
        yaxis={"showgrid": True, "gridcolor": "rgba(255, 255, 255, 0.08)"},
    )
    st.plotly_chart(fig_rev, use_container_width=True)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("📦 訂單履約與狀態分佈")
        fig_status = go.Figure()
        fig_status.add_trace(go.Bar(x=filtered_kpi["order_date"], y=filtered_kpi["completed_orders"], name="Completed (已完成)", marker_color="#10b981"))
        fig_status.add_trace(go.Bar(x=filtered_kpi["order_date"], y=filtered_kpi["cancelled_orders"], name="Cancelled (已取消)", marker_color="#f59e0b"))
        fig_status.add_trace(go.Bar(x=filtered_kpi["order_date"], y=filtered_kpi["refunded_orders"], name="Refunded (已退款)", marker_color="#ef4444"))
        fig_status.update_layout(
            barmode="stack",
            template="plotly_dark",
            height=320,
            margin={"l": 20, "r": 20, "t": 30, "b": 20},
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            yaxis={"showgrid": True, "gridcolor": "rgba(255, 255, 255, 0.08)"},
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col_t2:
        st.subheader("💵 平均客單價 (AOV) 走勢")
        fig_aov = px.line(
            filtered_kpi,
            x="order_date",
            y="aov",
            template="plotly_dark",
            markers=True,
            color_discrete_sequence=["#38bdf8"],
        )
        fig_aov.update_layout(
            height=320,
            margin={"l": 20, "r": 20, "t": 30, "b": 20},
            yaxis={"showgrid": True, "gridcolor": "rgba(255, 255, 255, 0.08)"},
        )
        st.plotly_chart(fig_aov, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: 客戶終身價值 (LTV) 分群
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("👥 客戶層級 (Customer Tiers) 佔比與價值貢獻")
    col_ltv1, col_ltv2 = st.columns([1, 2])
    
    tier_counts = df_ltv["customer_tier"].value_counts().reset_index()
    tier_counts.columns = ["customer_tier", "count"]
    
    tier_colors = {
        "Platinum": "#a855f7",
        "Gold": "#eab308",
        "Silver": "#94a3b8",
        "Bronze": "#b45309",
    }

    with col_ltv1:
        fig_tier = px.pie(
            tier_counts,
            names="customer_tier",
            values="count",
            hole=0.55,
            color="customer_tier",
            color_discrete_map=tier_colors,
            template="plotly_dark",
        )
        fig_tier.update_layout(height=350, margin={"l": 20, "r": 20, "t": 30, "b": 20})
        st.plotly_chart(fig_tier, use_container_width=True)

    with col_ltv2:
        fig_tier_bar = px.bar(
            df_ltv.groupby("customer_tier")["lifetime_net_revenue"].sum().reset_index(),
            x="customer_tier",
            y="lifetime_net_revenue",
            color="customer_tier",
            color_discrete_map=tier_colors,
            template="plotly_dark",
            title="各級別顧客累積淨貢獻額 ($)",
        )
        fig_tier_bar.update_layout(height=350, margin={"l": 20, "r": 20, "t": 40, "b": 20}, showlegend=False)
        st.plotly_chart(fig_tier_bar, use_container_width=True)

    st.subheader("💎 高價值 VIP 客戶排名 (已套用 PII 加密遮蔽)")
    st.caption("🔒 符合 GDPR/個資規範：姓名首字星號化，電子信箱透過 SHA-256 雜湊")
    st.dataframe(
        df_ltv[["customer_id", "customer_name", "masked_email", "customer_tier", "total_orders", "completed_orders", "lifetime_net_revenue"]],
        use_container_width=True,
        hide_index=True,
    )

# ------------------------------------------------------------------------------
# TAB 3: 熱銷商品與類別排行
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("🏆 商品業績與銷售數量排行榜")
    c_p1, c_p2 = st.columns(2)
    
    with c_p1:
        top_rev_prod = df_prod.sort_values(by="completed_sales_amount", ascending=True).tail(10)
        fig_prod_rev = px.bar(
            top_rev_prod,
            x="completed_sales_amount",
            y="product_title",
            orientation="h",
            color="category_name",
            template="plotly_dark",
            title="Top 10 商品銷售金額排行 ($)",
            labels={"completed_sales_amount": "累積成交金額 ($)", "product_title": "商品名稱"},
        )
        fig_prod_rev.update_layout(height=420, margin={"l": 20, "r": 20, "t": 40, "b": 20})
        st.plotly_chart(fig_prod_rev, use_container_width=True)

    with c_p2:
        top_qty_prod = df_prod.sort_values(by="units_sold", ascending=True).tail(10)
        fig_prod_qty = px.bar(
            top_qty_prod,
            x="units_sold",
            y="product_title",
            orientation="h",
            color="category_name",
            template="plotly_dark",
            title="Top 10 商品銷售件數排行 (件)",
            labels={"units_sold": "累積銷售件數", "product_title": "商品名稱"},
        )
        fig_prod_qty.update_layout(height=420, margin={"l": 20, "r": 20, "t": 40, "b": 20})
        st.plotly_chart(fig_prod_qty, use_container_width=True)

    st.subheader("📋 完整商品業績明細清單")
    st.dataframe(df_prod, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# FastMCP AI Copilot Component (Right-Side Resizable Dock or Full Tab)
# ------------------------------------------------------------------------------
def render_fastmcp_copilot(user_gemini_key: str):
    header_ai1, header_ai2 = st.columns([3, 1])
    with header_ai1:
        st.markdown("## 🤖 FastMCP 顧問")
        st.caption("AI Operations Lakehouse Copilot")
    with header_ai2:
        st.markdown(
            """
            <div style="text-align: right; padding-top: 8px;">
                <span class="status-badge" style="font-size: 0.72rem; padding: 0.2rem 0.6rem;">
                    <span class="pulse-dot"></span> Live
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(f"**分析標的：**\n`{PROJECT_ID}.platzi_gold`")
    st.caption("🔒 全自動 PII 脫敏，支援自然語言即時數據分析與業務安全護欄。")
    st.markdown("---")

    st.markdown("**💡 快速業務提問：**")
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        if st.button("📊 一週營收與退款", key="btn_q1", use_container_width=True):
            st.session_state.ai_query = "請問過去一週的整體 GMV、實質營收與退款率如何？"
    with q_col2:
        if st.button("🏆 Top 3 暢銷商品", key="btn_q2", use_container_width=True):
            st.session_state.ai_query = "請列出目前總銷售額排名前三的商品名稱與金額。"
    with q_col3:
        if st.button("💎 Platinum 客戶群", key="btn_q3", use_container_width=True):
            st.session_state.ai_query = "請列出終身價值 (LTV) 最頂級的客戶群體特性。"

    user_prompt = st.text_area(
        "輸入業務問題：",
        value=st.session_state.get("ai_query", "請問目前我們累積的實質淨營收與最暢銷商品是什麼？"),
        height=85,
        key="ai_user_prompt",
        help="輸入與電商營運、銷售績效、商品或顧客相關的分析問題",
    )

    if st.button("送出提問 🚀", type="primary", use_container_width=True):
        with st.spinner("AI 正在透過 FastMCP 查詢 BigQuery 金牌資料集..."):
            from mcp_server.server import (
                get_customer_metrics,
                get_daily_sales_kpi,
                get_top_products,
            )

            # Option A: Real Google Gemini API with Tool Calling (Function Calling)
            if user_gemini_key:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=user_gemini_key)

                    import re

                    # 1. Dynamically retrieve all active text-capable Flash models for this API key
                    available = []
                    try:
                        for m in client.models.list():
                            m_name = m.name.replace("models/", "")
                            if "flash" in m_name.lower() and not any(
                                bad in m_name.lower()
                                for bad in ["omni", "embed", "imagen", "tts", "stt", "realtime"]
                            ):
                                available.append(m_name)

                        def version_score(name: str) -> float:
                            nums = re.findall(r"(\d+(?:\.\d+)?)", name)
                            return float(nums[0]) if nums else 0.0

                        available.sort(key=version_score, reverse=True)
                    except Exception:  # noqa: BLE001
                        available = []

                    # 2. Build candidate cascade list dynamically (never hardcoding deprecated models)
                    candidate_models = available if available else ["gemini-3.6-flash", "gemini-2.5-flash"]
                    chosen_model = candidate_models[0]

                    tools = [get_daily_sales_kpi, get_top_products, get_customer_metrics]
                    system_prompt = (
                        "你是一位精通現代數據架構的資深電商分析顧問。"
                        "你可以調用工具查詢 BigQuery platzi_gold 金牌數據（每日銷售 KPI、商品銷量與顧客 LTV）。"
                        "請以結構化、專業繁體中文並結合具體數據回答使用者的商業決策問題。\n\n"
                        "【業務範疇約束限制】：\n"
                        "本助手專屬於『Platzi 零售電商營運分析』。"
                        "如果使用者的問題與本電商業務（銷售表現、訂單、營收、GMV、商品、顧客、退款、客單價等數據分析）無關"
                        "（例如政治人物、歷史、演藝娛樂、哲學、生活閒聊或其他非業務領域），你必須直接委婉拒絕回答："
                        "『抱歉，我是 Platzi 電商營運數據分析顧問，僅能回答與本電商營運指標、銷售狀況、熱銷商品或顧客分析相關之業務問題。對於無關範疇的提問無法提供回答，請提出與電商業務數據相關的問題。』"
                        "在判定為無關問題時，絕對不要調用查詢工具，也不要輸出不相干的電商數據！"
                    )

                    resp = None
                    last_err = None
                    used_model = chosen_model

                    for candidate in candidate_models:
                        try:
                            resp = client.models.generate_content(
                                model=candidate,
                                contents=user_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_prompt,
                                    tools=tools,
                                    temperature=0.2,
                                ),
                            )
                            used_model = candidate
                            break
                        except Exception as e:  # noqa: BLE001
                            last_err = e
                            err_msg = str(e)
                            # If transient load error (503), quota (429), or deprecated/not found (404), try next dynamic candidate
                            if any(k in err_msg for k in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand", "404", "NOT_FOUND", "no longer available", "deprecated"]):
                                continue
                            raise e

                    if resp is None:
                        raise last_err or RuntimeError("No model response available")

                    fallback_notice = (
                        f"（原選 `{chosen_model}` 暫不可用，已自動轉移）"
                        if used_model != chosen_model
                        else ""
                    )
                    st.success(f"✨ 成功調用最新模型 **`{used_model}`** {fallback_notice}結合 BigQuery FastMCP 工具生成即時洞察！")
                    st.markdown(resp.text)
                except Exception as ex:  # noqa: BLE001
                    st.warning(f"⚠️ 調用 Gemini 失敗（{ex}），自動切換為內建 FastMCP 分析引擎回答：")
                    
                    # Domain Relevance Guardrail
                    BUSINESS_KEYWORDS = [
                        "銷售", "營收", "gmv", "訂單", "商品", "客戶", "ltv", "業績", "退款",
                        "會員", "暢銷", "買", "賣", "kpi", "vip", "排行", "利潤", "金額",
                        "單價", "aov", "平台", "電商", "庫存", "品類", "tier", "platinum", "gold", "數據", "指標", "概況"
                    ]
                    if not any(kw in user_prompt.lower() for kw in BUSINESS_KEYWORDS):
                        st.info("ℹ️ 業務邊界約束提醒：")
                        st.markdown(
                            f"抱歉，我是專屬的 **Platzi 電商數據分析顧問**。\n\n"
                            f"您輸入的提問 *「{user_prompt}」* 與本電商營運、銷售績效、商品或顧客等業務數據無關，因此無法提供回答。\n\n"
                            "💡 **建議您可以提問與業務數據相關之問題，例如：**\n"
                            "- 📊 *「請問過去一週的整體 GMV 與退款率如何？」*\n"
                            "- 🏆 *「目前總銷售額排名前三的商品名稱與金額是？」*\n"
                            "- 💎 *「誰是終身價值最頂級的 Platinum VIP 客戶？」*"
                        )
                    else:
                        kpis = get_daily_sales_kpi(limit=7)
                        top_prods = get_top_products(limit=3)
                        vip_custs = get_customer_metrics(tier="Platinum", limit=3)
                        st.markdown(
                            f"""
                            ### 🎯 FastMCP 分析引擎洞察回覆：
                            **針對提問：** *「{user_prompt}」*
                            1. **近期財務概況**：GMV 達 **${sum(k['gmv'] for k in kpis):,.2f}**，實質淨營收 **${sum(k['net_revenue'] for k in kpis):,.2f}**，均單價 **${sum(k['aov'] for k in kpis)/len(kpis):,.2f}**。
                            2. **暢銷明星商品**：**{top_prods[0]['product_title']}** 居冠（${top_prods[0]['completed_sales_amount']:,.2f}）。
                            3. **頂級 VIP 群體**：Platinum 客戶平均累積貢獻 **${vip_custs[0]['lifetime_net_revenue']:,.2f}**（{vip_custs[0]['completed_orders']} 次購買）。
                            """
                        )
            else:
                # Domain Relevance Guardrail for non-Gemini mode
                BUSINESS_KEYWORDS = [
                    "銷售", "營收", "gmv", "訂單", "商品", "客戶", "ltv", "業績", "退款",
                    "會員", "暢銷", "買", "賣", "kpi", "vip", "排行", "利潤", "金額",
                    "單價", "aov", "平台", "電商", "庫存", "品類", "tier", "platinum", "gold", "數據", "指標", "概況"
                ]
                if not any(kw in user_prompt.lower() for kw in BUSINESS_KEYWORDS):
                    st.info("ℹ️ 業務邊界約束提醒：")
                    st.markdown(
                        f"抱歉，我是專屬的 **Platzi 電商數據分析顧問**。\n\n"
                        f"您輸入的提問 *「{user_prompt}」* 與本電商營運、銷售績效、商品或顧客等業務數據無關，因此無法提供回答。\n\n"
                        "💡 **建議您可以提問與業務數據相關之問題，例如：**\n"
                        "- 📊 *「請問過去一週的整體 GMV 與退款率如何？」*\n"
                        "- 🏆 *「目前總銷售額排名前三的商品名稱與金額是？」*\n"
                        "- 💎 *「誰是終身價值最頂級的 Platinum VIP 客戶？」*"
                    )
                else:
                    kpis = get_daily_sales_kpi(limit=7)
                    top_prods = get_top_products(limit=3)
                    vip_custs = get_customer_metrics(tier="Platinum", limit=3)

                    st.success("✅ FastMCP 成功擷取 BigQuery Gold 數據！(提示：於左側側邊欄輸入 Gemini API Key 可啟動原生 Gemini 深度推理)")
                    st.markdown(
                        f"""
                        ### 🎯 AI 商業顧問洞察回覆：
                        
                        **針對您的提問：** *「{user_prompt}」*
                        
                        依據 Google Cloud BigQuery 最新金牌分析層數據：
                        1. **財務健康度**：
                           - 近期 GMV 規模達 **${sum(k['gmv'] for k in kpis):,.2f}**，實質扣除退款後淨營收為 **${sum(k['net_revenue'] for k in kpis):,.2f}**。
                           - 平均客單價 (AOV) 落在 **${sum(k['aov'] for k in kpis)/len(kpis):,.2f}** 左右，平均退款率維持在 **{sum(k['refund_rate'] for k in kpis)/len(kpis)*100:.1f}%** 的健康標準範圍。
                        
                        2. **明星主力商品**：
                           - 目前最熱銷冠軍為 **{top_prods[0]['product_title']}**，累積銷售額高達 **${top_prods[0]['completed_sales_amount']:,.2f}**（共售出 {top_prods[0]['units_sold']} 件）。
                           - 緊隨其後的是 **{top_prods[1]['product_title']}**（${top_prods[1]['completed_sales_amount']:,.2f}）。
                        
                        3. **核心顧客群體**：
                           - 頂級 **Platinum** 客戶平均貢獻達 **${vip_custs[0]['lifetime_net_revenue']:,.2f}**，購買頻次高達 {vip_custs[0]['completed_orders']} 次。
                           - 個資保護符合標準：客戶 Email 全數進行 SHA-256 不可逆雜湊，安全合規。
                        """
                    )

# Render FastMCP Copilot in the designated location
if col_ai is not None:
    with col_ai:
        st.markdown('<div class="right-sidebar-rail">', unsafe_allow_html=True)
        render_fastmcp_copilot(user_gemini_key)
        st.markdown('</div>', unsafe_allow_html=True)
elif tab4 is not None:
    with tab4:
        render_fastmcp_copilot(user_gemini_key)
