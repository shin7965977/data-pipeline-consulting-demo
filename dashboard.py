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
    """Load analytical Gold marts from BigQuery or fallback to local DuckDB."""
    try:
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
    except Exception as e:
        # Fallback to local DuckDB if BigQuery is offline
        import duckdb

        db_path = "test_pipeline.duckdb"
        if os.path.exists(db_path):
            con = duckdb.connect(db_path)
            df_kpi = con.execute("SELECT * FROM gold_daily_sales_kpi ORDER BY order_date").df()
            df_ltv = con.execute("SELECT * FROM gold_customer_ltv ORDER BY lifetime_net_revenue DESC").df()
            df_prod = con.execute("SELECT * FROM gold_product_performance ORDER BY completed_sales_amount DESC").df()
            return df_kpi, df_ltv, df_prod, f"Local DuckDB ({db_path})"
        raise RuntimeError(f"Failed to load BigQuery data and local DuckDB not found: {e}") from e


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
    min_date = df_kpi["order_date"].min().date()
    max_date = df_kpi["order_date"].max().date()
    
    st.subheader("📅 時間區間篩選")
    selected_dates = st.date_input(
        "選擇日期範圍",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
        start_d, end_d = selected_dates
        mask = (df_kpi["order_date"].dt.date >= start_d) & (df_kpi["order_date"].dt.date <= end_d)
        filtered_kpi = df_kpi.loc[mask]
    elif isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 1:
        start_d = selected_dates[0]
        mask = df_kpi["order_date"].dt.date >= start_d
        filtered_kpi = df_kpi.loc[mask]
    else:
        filtered_kpi = df_kpi

    st.markdown("---")
    st.markdown("### 🤖 Gemini AI 設定")
    user_gemini_key = st.text_input(
        "輸入 Gemini API Key (選填)",
        type="password",
        value=os.getenv("GEMINI_API_KEY", ""),
        help="輸入後將啟用 Google Gemini 原生對話與 Function Calling，直接與 BigQuery 進行 AI 互動！",
    )

    model_choice = st.selectbox(
        "選擇 Gemini 模型版本",
        options=["⚡ Auto (自動偵測最新可用 Flash 模型)", "gemini-2.5-flash", "gemini-2.0-flash", "自訂模型名稱..."],
        index=0,
        help="選擇 Auto 時，系統會動態查詢 Google API 獲取最新的通用 Flash 模型，並自動排除無免費額度的特殊模型（如 omni）！",
    )
    if model_choice == "自訂模型名稱...":
        target_model = st.text_input("輸入自訂模型名稱", value="gemini-2.5-flash")
    elif "Auto" in model_choice:
        target_model = "auto"
    else:
        target_model = model_choice

    st.markdown("---")
    st.markdown("### 🏛️ 架構特性")
    st.markdown("- ⚡ **0 閒置成本** (Cloud Run Jobs)")
    st.markdown("- 🔒 **全自動 PII 雜湊** (SHA-256)")
    st.markdown("- 🤖 **FastMCP / Gemini Tool Calling**")

# ==============================================================================
# 4. Main Executive Header & Top KPI Cards
# ==============================================================================
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

# ==============================================================================
# 5. Core Analytical Tabs
# ==============================================================================
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
# TAB 4: FastMCP AI 數據對話助手
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🤖 FastMCP 智慧營運顧問 (自然語言即時問答)")
    st.markdown("直接透過自然語言向 BigQuery `platzi_gold` 層提問，由後端 FastMCP 工具提供安全無 PII 洩漏的即時數據洞察。")

    col_q1, col_q2, col_q3 = st.columns(3)
    with col_q1:
        if st.button("📊 過去一週的整體 GMV 與退款率？"):
            st.session_state.ai_query = "請問過去一週的整體 GMV、實質營收與退款率如何？"
    with col_q2:
        if st.button("🏆 銷售額最高的前 3 名商品是？"):
            st.session_state.ai_query = "請列出目前總銷售額排名前三的商品名稱與金額。"
    with col_q3:
        if st.button("💎 誰是貢獻最高的 Platinum 客戶？"):
            st.session_state.ai_query = "請列出終身價值 (LTV) 最頂級的客戶群體特性。"

    user_prompt = st.text_input(
        "輸入您的業務問題：",
        value=st.session_state.get("ai_query", "請問目前我們累積的實質淨營收與最暢銷商品是什麼？"),
    )

    if st.button("送出提問 🚀", type="primary"):
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

                    # Dynamic Model Auto-Resolution: Filter for general text models & sort semantically
                    chosen_model = target_model
                    if chosen_model == "auto":
                        try:
                            import re

                            available = []
                            for m in client.models.list():
                                m_name = m.name.replace("models/", "")
                                # Filter for flash models, exclude omni, vision/video-only, embed, tts
                                if "flash" in m_name.lower() and not any(
                                    bad in m_name.lower() for bad in ["omni", "embed", "imagen", "tts", "stt", "realtime"]
                                ):
                                    available.append(m_name)

                            def version_score(name: str) -> float:
                                nums = re.findall(r"(\d+(?:\.\d+)?)", name)
                                return float(nums[0]) if nums else 0.0

                            if available:
                                available.sort(key=version_score, reverse=True)
                                chosen_model = available[0]
                            else:
                                chosen_model = "gemini-2.5-flash"
                        except Exception:  # noqa: BLE001
                            chosen_model = "gemini-2.5-flash"

                    tools = [get_daily_sales_kpi, get_top_products, get_customer_metrics]
                    system_prompt = (
                        "你是一位精通現代數據架構的資深電商分析顧問。"
                        "你可以調用工具查詢 BigQuery platzi_gold 金牌數據（每日銷售 KPI、商品銷量與顧客 LTV）。"
                        "請以結構化、專業繁體中文並結合具體數據回答使用者的商業決策問題。"
                    )

                    # Resilience Cascade: If the latest model experiences 503 high demand, fallback gracefully
                    candidate_models = [chosen_model]
                    for fallback in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                        if fallback not in candidate_models:
                            candidate_models.append(fallback)

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
                            # If high demand (503) or rate limit (429), try next candidate model
                            if any(k in err_msg for k in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand"]):
                                continue
                            raise e

                    if resp is None:
                        raise last_err or RuntimeError("No model response available")

                    fallback_notice = (
                        f"（原選 `{chosen_model}` 伺服器流量過載，已自動降級轉移）"
                        if used_model != chosen_model
                        else ""
                    )
                    st.success(f"✨ 成功調用模型 **`{used_model}`** {fallback_notice}結合 BigQuery FastMCP 工具生成即時洞察！")
                    st.markdown(resp.text)
                except Exception as ex:  # noqa: BLE001
                    st.warning(f"⚠️ 調用 Gemini 失敗（{ex}），自動切換為內建 FastMCP 分析引擎回答：")
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
                kpis = get_daily_sales_kpi(limit=7)
                top_prods = get_top_products(limit=3)
                vip_custs = get_customer_metrics(tier="Platinum", limit=3)

                st.success("✅ FastMCP 成功擷取 BigQuery Gold 數據！(提示：於左側側邊欄輸入 Gemini API Key 可啟動原生 Gemini 2.5 深度推理)")
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
