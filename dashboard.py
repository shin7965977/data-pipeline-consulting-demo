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
# 3. Natural Language AI Chart Generation Engine (Text-to-Visualization)
# ==============================================================================
def generate_chart_from_nl(
    prompt: str,
    df_kpi: pd.DataFrame,
    df_prod: pd.DataFrame,
    df_ltv: pd.DataFrame,
    gemini_api_key: str = "",
) -> tuple[go.Figure, str, str, pd.DataFrame]:
    """Analyze natural language prompt and generate an interactive Plotly chart with consulting insights.

    Returns: (fig, title, insight_text, raw_df)
    """
    clean_prompt = prompt.strip().lower()

    # Step 1: Check if Gemini is available for AI-powered visualization reasoning
    gemini_spec = None
    if gemini_api_key:
        try:
            import json
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_api_key)
            system_instruction = (
                "You are an expert Data Visualization and MBB Strategy Consultant. "
                "The user will ask for a chart or business insight in natural language. "
                "Available BigQuery datasets:\n"
                "1. 'kpi' columns: order_date, total_orders, completed_orders, cancelled_orders, refunded_orders, gmv, net_revenue, aov, cancellation_rate, refund_rate\n"
                "2. 'products' columns: product_id, product_title, category_name, completed_sales_amount, units_sold, unit_price\n"
                "3. 'customers' columns: customer_id, customer_name, customer_tier, total_orders, completed_orders, lifetime_net_revenue\n\n"
                "Respond ONLY with a valid JSON object (no markdown quotes, no explanations):\n"
                "{\n"
                '  "dataset": "kpi" | "products" | "customers",\n'
                '  "chart_type": "line" | "bar" | "pie" | "scatter" | "area",\n'
                '  "x": "column_name",\n'
                '  "y": ["col1", "col2"] or "col1",\n'
                '  "color": "col" or null,\n'
                '  "title": "Clear descriptive chart title in Traditional Chinese",\n'
                '  "top_n": 10 or null,\n'
                '  "insight": "1-2 sentences of MBB-level business insight in Traditional Chinese"\n'
                "}"
            )
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            if res and res.text:
                gemini_spec = json.loads(res.text)
        except Exception:
            gemini_spec = None

    # Step 2: If Gemini returned a valid spec, render using that spec
    if gemini_spec and isinstance(gemini_spec, dict) and "dataset" in gemini_spec:
        ds_name = gemini_spec.get("dataset")
        c_type = gemini_spec.get("chart_type", "line")
        x_col = gemini_spec.get("x")
        y_col = gemini_spec.get("y")
        title = gemini_spec.get("title", prompt)
        insight = gemini_spec.get("insight", "AI 已依據您的需求完成動態可視化圖表。")

        if ds_name == "products":
            target_df = df_prod.copy()
            if gemini_spec.get("top_n"):
                sort_col = y_col[0] if isinstance(y_col, list) else y_col
                if sort_col in target_df.columns:
                    target_df = target_df.sort_values(by=sort_col, ascending=False).head(gemini_spec["top_n"])
        elif ds_name == "customers":
            target_df = df_ltv.copy()
        else:
            target_df = df_kpi.copy()

        fig = None
        if c_type == "line":
            fig = px.line(target_df, x=x_col, y=y_col, markers=True, title=title, template="plotly_dark")
        elif c_type == "bar":
            fig = px.bar(target_df, x=x_col, y=y_col, title=title, template="plotly_dark", color=gemini_spec.get("color"))
        elif c_type == "pie":
            fig = px.pie(target_df, names=x_col, values=y_col if isinstance(y_col, str) else y_col[0], hole=0.45, title=title, template="plotly_dark")
        elif c_type == "scatter":
            fig = px.scatter(target_df, x=x_col, y=y_col, color=gemini_spec.get("color"), title=title, template="plotly_dark")
        elif c_type == "area":
            fig = px.area(target_df, x=x_col, y=y_col, title=title, template="plotly_dark")

        if fig:
            fig.update_layout(margin={"l": 20, "r": 20, "t": 40, "b": 20})
            return fig, title, insight, target_df

    # Step 3: Intelligent Deterministic Rule-Based Fallback (Works 100% offline & without API Key)
    # Check Product dataset keywords
    if any(kw in clean_prompt for kw in ["商品", "產品", "品類", "類別", "category", "product", "暢銷", "熱銷", "庫存"]):
        if any(kw in clean_prompt for kw in ["品類", "類別", "category"]):
            cat_df = df_prod.groupby("category_name")[["completed_sales_amount", "units_sold"]].sum().reset_index()
            cat_df = cat_df.sort_values(by="completed_sales_amount", ascending=False)
            if any(kw in clean_prompt for kw in ["圓餅", "佔比", "比例", "分佈", "pie"]):
                fig = px.pie(
                    cat_df,
                    names="category_name",
                    values="completed_sales_amount",
                    title="各商品品類 (Category) 銷售金額分佈佔比",
                    hole=0.45,
                    template="plotly_dark",
                )
                title = "各商品品類銷售佔比圓餅圖"
                insight = f"主力品類為【{cat_df.iloc[0]['category_name']}】，貢獻了全站最高銷售金額 (${cat_df.iloc[0]['completed_sales_amount']:,.2f})。"
            else:
                fig = px.bar(
                    cat_df,
                    x="category_name",
                    y="completed_sales_amount",
                    color="completed_sales_amount",
                    title="各商品品類 (Category) 總營收排行榜",
                    template="plotly_dark",
                    labels={"completed_sales_amount": "銷售總額 ($)", "category_name": "品類名稱"},
                    color_continuous_scale="Purples",
                )
                title = "各商品品類總營收長條圖"
                insight = f"品類營收最高為【{cat_df.iloc[0]['category_name']}】，共售出 {cat_df.iloc[0]['units_sold']} 件商品。"
            return fig, title, insight, cat_df
        else:
            is_units = any(kw in clean_prompt for kw in ["件數", "數量", "銷量", "units"])
            val_col = "units_sold" if is_units else "completed_sales_amount"
            unit_lbl = "銷售件數 (件)" if is_units else "銷售總額 ($)"
            top_df = df_prod.sort_values(by=val_col, ascending=True).tail(10)
            fig = px.bar(
                top_df,
                x=val_col,
                y="product_title",
                orientation="h",
                color="category_name",
                title=f"Top 10 熱銷商品排行榜 ({unit_lbl})",
                labels={val_col: unit_lbl, "product_title": "商品名稱", "category_name": "品類"},
                template="plotly_dark",
            )
            title = f"Top 10 熱銷商品業績排行圖 ({unit_lbl})"
            best_prod = top_df.iloc[-1]
            insight = f"冠軍商品為【{best_prod['product_title']}】，累積貢獻 {best_prod[val_col]:,.0f} {unit_lbl}。"
            return fig, title, insight, top_df

    # Check Customer dataset keywords
    elif any(kw in clean_prompt for kw in ["會員", "客戶", "顧客", "customer", "tier", "白金", "黃金", "platinum", "gold", "silver", "bronze", "ltv", "rfm", "人"]):
        tier_colors = {"Platinum": "#a855f7", "Gold": "#eab308", "Silver": "#94a3b8", "Bronze": "#b45309"}
        if any(kw in clean_prompt for kw in ["圓餅", "佔比", "比例", "分佈", "pie"]):
            tier_summary = df_ltv.groupby("customer_tier")["lifetime_net_revenue"].sum().reset_index()
            fig = px.pie(
                tier_summary,
                names="customer_tier",
                values="lifetime_net_revenue",
                color="customer_tier",
                color_discrete_map=tier_colors,
                title="各會員等級 (Customer Tiers) 營收貢獻分佈",
                hole=0.45,
                template="plotly_dark",
            )
            title = "會員等級營收分佈圓餅圖"
            insight = "Platinum 與 Gold 會員貢獻全站核心營收，符合二八法則 (Pareto 80/20)，建議強化高階會員權益維護。"
            return fig, title, insight, tier_summary
        elif any(kw in clean_prompt for kw in ["散佈", "散點", "關係", "scatter"]):
            fig = px.scatter(
                df_ltv,
                x="total_orders",
                y="lifetime_net_revenue",
                color="customer_tier",
                color_discrete_map=tier_colors,
                title="顧客下單次數 vs. 終生累積貢獻額 (LTV) 散佈圖",
                labels={"total_orders": "累計下單次數", "lifetime_net_revenue": "終生價值 LTV ($)"},
                template="plotly_dark",
            )
            title = "顧客下單次數 vs 終生價值散佈圖"
            insight = "顧客下單次數與終生價值呈現強烈正相關，回購次數超過 5 次的顧客顯著晉升為高價值客群。"
            return fig, title, insight, df_ltv
        else:
            tier_agg = df_ltv.groupby("customer_tier").agg(
                customer_count=("customer_id", "count"),
                total_revenue=("lifetime_net_revenue", "sum"),
                avg_orders=("total_orders", "mean"),
            ).reset_index()
            fig = px.bar(
                tier_agg,
                x="customer_tier",
                y="total_revenue",
                color="customer_tier",
                color_discrete_map=tier_colors,
                title="各會員等級累積淨營收總額 ($)",
                labels={"total_revenue": "累積總營收 ($)", "customer_tier": "會員等級"},
                template="plotly_dark",
            )
            title = "各會員等級累積淨營收長條圖"
            insight = "各等級營收結構分明，建議對 Silver/Bronze 會員推播專屬回購誘因以加速升級。"
            return fig, title, insight, tier_agg

    # Check KPI / Timeseries keywords
    else:
        kpi_df = df_kpi.sort_values(by="order_date").copy()
        if any(kw in clean_prompt for kw in ["退款", "取消", "refund", "cancel", "損耗", "流失"]):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=kpi_df["order_date"], y=kpi_df["refund_rate"] * 100, mode="lines+markers", name="退款率 (%)", line={"color": "#ef4444", "width": 3}))
            fig.add_trace(go.Scatter(x=kpi_df["order_date"], y=kpi_df["cancellation_rate"] * 100, mode="lines+markers", name="取消率 (%)", line={"color": "#f59e0b", "width": 3}))
            fig.update_layout(title="每日訂單取消率 vs. 退款率趨勢監控 (%)", template="plotly_dark", yaxis={"title": "百分比 (%)", "showgrid": True})
            title = "每日退款率與取消率走勢圖"
            avg_ref = kpi_df["refund_rate"].mean() * 100
            avg_can = kpi_df["cancellation_rate"].mean() * 100
            insight = f"期間平均退款率為 {avg_ref:.1f}%，取消率為 {avg_can:.1f}%，走勢平穩無異常劇烈尖峰。"
            return fig, title, insight, kpi_df
        elif any(kw in clean_prompt for kw in ["客單價", "aov", "均額", "單價"]):
            fig = px.line(
                kpi_df,
                x="order_date",
                y="aov",
                markers=True,
                title="歷史平均客單價 (AOV) 走勢分析 ($)",
                template="plotly_dark",
                labels={"aov": "平均客單價 ($)", "order_date": "日期"},
                color_discrete_sequence=["#38bdf8"],
            )
            title = "歷史平均客單價 (AOV) 走勢圖"
            insight = f"平均客單價最高達 ${kpi_df['aov'].max():,.2f}，全期均值為 ${kpi_df['aov'].mean():,.2f}。"
            return fig, title, insight, kpi_df
        elif any(kw in clean_prompt for kw in ["訂單", "單數", "完成", "狀態", "orders"]):
            fig = go.Figure()
            fig.add_trace(go.Bar(x=kpi_df["order_date"], y=kpi_df["completed_orders"], name="已完成訂單", marker_color="#10b981"))
            fig.add_trace(go.Bar(x=kpi_df["order_date"], y=kpi_df["cancelled_orders"], name="已取消訂單", marker_color="#f59e0b"))
            fig.add_trace(go.Bar(x=kpi_df["order_date"], y=kpi_df["refunded_orders"], name="已退款訂單", marker_color="#ef4444"))
            fig.update_layout(barmode="stack", title="每日訂單狀態履約分佈 (堆疊長條圖)", template="plotly_dark")
            title = "每日訂單狀態履約分佈圖"
            insight = f"總訂單量達 {kpi_df['total_orders'].sum():,} 筆，其中完成履約比率達 {kpi_df['completed_orders'].sum()/kpi_df['total_orders'].sum()*100:.1f}%。"
            return fig, title, insight, kpi_df
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=kpi_df["order_date"], y=kpi_df["gmv"], mode="lines+markers", name="GMV 總銷售額 ($)", line={"color": "#6366f1", "width": 3}, fill="tozeroy", fillcolor="rgba(99, 102, 241, 0.1)"))
            fig.add_trace(go.Scatter(x=kpi_df["order_date"], y=kpi_df["net_revenue"], mode="lines+markers", name="Net Revenue 實質淨營收 ($)", line={"color": "#10b981", "width": 3}))
            fig.update_layout(title="每日 GMV 總銷售額 vs. 實質淨營收對比走勢圖 ($)", template="plotly_dark", yaxis={"title": "金額 ($)", "showgrid": True})
            title = "每日 GMV 與實質淨營收對比圖"
            insight = f"全期 GMV 累計達 ${kpi_df['gmv'].sum():,.2f}，淨營收實現率達 {kpi_df['net_revenue'].sum()/kpi_df['gmv'].sum()*100:.1f}%。"
            return fig, title, insight, kpi_df


# ==============================================================================
# 4. FastMCP AI Operations Copilot Component (Embedded in Sidebar)
# ==============================================================================
def render_fastmcp_copilot():
    st.subheader("🤖 FastMCP 智慧營運顧問")
    st.caption("AI Operations Lakehouse Copilot · ⚡ Live")
    st.caption(f"🔒 鎖定 BigQuery `({PROJECT_ID}.platzi_gold)` 脫敏分析")

    # Gemini AI API Key Setting
    st.markdown("##### 🔑 Gemini AI 設定")
    user_gemini_key = st.text_input(
        "輸入 Gemini API Key (選填)",
        type="password",
        value=os.getenv("GEMINI_API_KEY", ""),
        help="輸入後將啟用 Google Gemini 原生對話與 Function Calling，直接與 BigQuery 進行 AI 互動！",
        key="sidebar_gemini_api_key",
    )
    st.caption("⚡ **全自動模型協議**：系統自動偵測並調用 Google API 最新旗艦模型（版本絕不寫死）。")

    st.markdown("##### 💡 快速業務提問")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        if st.button("📊 一週營收退款", key="btn_q1", use_container_width=True):
            st.session_state.ai_query = "請問過去一週的整體 GMV、實質營收與退款率如何？"
        if st.button("💎 Platinum 客戶", key="btn_q3", use_container_width=True):
            st.session_state.ai_query = "請列出終身價值 (LTV) 最頂級的客戶群體特性。"
    with q_col2:
        if st.button("🏆 Top 3 熱銷品", key="btn_q2", use_container_width=True):
            st.session_state.ai_query = "請列出目前總銷售額排名前三的商品名稱與金額。"

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

                    st.success("✅ FastMCP 成功擷取 BigQuery Gold 數據！(提示：於上方輸入 API Key 可啟動原生 Gemini 深度推理)")
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

# ==============================================================================
# 4. Sidebar Navigation & Global Filters
# ==============================================================================
with st.sidebar:
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
    # FastMCP Copilot embedded directly into the Sidebar
    render_fastmcp_copilot()

    st.markdown("---")
    st.markdown("### 🏛️ 架構特性")
    st.markdown("- ⚡ **0 閒置成本** (Cloud Run Jobs)")
    st.markdown("- 🔒 **全自動 PII 雜湊** (SHA-256)")
    st.markdown("- 🤖 **FastMCP / Gemini Tool Calling**")

# ==============================================================================
# 5. Main Workspace: E-Commerce Retail Analytics Dashboard
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

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 營收走勢與轉換漏斗",
    "👥 客戶終身價值 (LTV) 分群",
    "🏆 熱銷商品與類別排行",
    "✨ 自然語言 AI 智能圖表",
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
# TAB 4: 自然語言 AI 智能圖表生成器 (NL-to-Visualization)
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("✨ 自然語言 AI 智能圖表生成器 (Text-to-Chart)")
    st.caption("🤖 支援自然繁體中文輸入任何圖表需求，AI 即時自動選取 BigQuery 金牌資料欄位並繪製互動式 Plotly 圖表")

    gemini_key = st.session_state.get("sidebar_gemini_api_key", os.getenv("GEMINI_API_KEY", ""))

    st.markdown("##### 💡 點擊範例指令立即生圖：")
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    with c_btn1:
        if st.button("📈 GMV 與淨營收對比走勢", key="btn_nl_1", use_container_width=True):
            st.session_state.nl_chart_query = "請幫我畫出每日 GMV 與實質淨營收的對比走勢圖"
        if st.button("🏆 Top 10 熱銷商品排行", key="btn_nl_4", use_container_width=True):
            st.session_state.nl_chart_query = "用長條圖呈現銷售額前 10 大熱銷商品"
    with c_btn2:
        if st.button("⚠️ 退款率與取消率監控", key="btn_nl_2", use_container_width=True):
            st.session_state.nl_chart_query = "畫出每日退款率與取消率的監控走勢圖"
        if st.button("🏷️ 商品品類銷售佔比圓餅圖", key="btn_nl_5", use_container_width=True):
            st.session_state.nl_chart_query = "幫我畫各商品品類 (Category) 銷售金額佔比圓餅圖"
    with c_btn3:
        if st.button("💵 平均客單價 (AOV) 走勢", key="btn_nl_3", use_container_width=True):
            st.session_state.nl_chart_query = "請繪製平均客單價 AOV 的歷史波動走勢圖"
        if st.button("👥 會員等級價值分佈圖", key="btn_nl_6", use_container_width=True):
            st.session_state.nl_chart_query = "用圓餅圖呈現不同會員等級 (Customer Tiers) 的營收貢獻"

    col_input, col_submit = st.columns([4, 1])
    with col_input:
        current_nl = st.text_input(
            "請輸入圖表生成指令：",
            value=st.session_state.get("nl_chart_query", "請幫我畫出每日 GMV 與實質淨營收的對比走勢圖"),
            key="nl_chart_input_field",
            placeholder="例如：畫出前五大商品銷售長條圖、或是每日退款率走勢...",
        )
    with col_submit:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_gen = st.button("生成圖表 🚀", key="btn_trigger_chart", type="primary", use_container_width=True)

    target_query = current_nl if current_nl else "請幫我畫出每日 GMV 與實質淨營收的對比走勢圖"

    with st.spinner("AI 正在解析自然語言意圖並調用 BigQuery 金牌數據繪圖..."):
        fig_nl, chart_title, insight_text, raw_df = generate_chart_from_nl(
            prompt=target_query,
            df_kpi=filtered_kpi,
            df_prod=df_prod,
            df_ltv=df_ltv,
            gemini_api_key=gemini_key,
        )

    st.markdown("---")
    st.subheader(f"📊 {chart_title}")
    st.plotly_chart(fig_nl, use_container_width=True)

    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #6366f1;">
            <div class="metric-label">💡 MBB 顧問商業洞察 (Executive Takeaway)</div>
            <div style="font-size: 1.05rem; font-weight: 500; color: var(--text-color, #0f172a); margin-top: 0.25rem;">
                {insight_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🔍 點擊展開：檢視本圖表底層數據表 (Data Preview)"):
        st.dataframe(raw_df, use_container_width=True, hide_index=True)


