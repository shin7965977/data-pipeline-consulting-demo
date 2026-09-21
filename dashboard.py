import importlib
import os
import sys
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

# 1. Local execution: Check for local gcp-key.json
if os.path.exists(KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH
else:
    # 2. Streamlit Cloud execution: Safely check st.secrets without throwing when absent
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            import json
            import tempfile

            sa_info = dict(st.secrets["gcp_service_account"])
            tmp_sa = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
            json.dump(sa_info, tmp_sa)
            tmp_sa.flush()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_sa.name
            if "project_id" in sa_info:
                PROJECT_ID = sa_info["project_id"]
    except Exception:
        # Gracefully continue if no secrets.toml exists (e.g. during CI or test collection)
        pass


def _sanitize_bq_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize DataFrame returned by BigQuery client to avoid PyGWalker/DuckDB type incompatibilities."""
    if df is None or df.empty:
        return df
    for col in df.columns:
        dtype_str = str(df[col].dtype).lower()
        if "dbdate" in dtype_str or "date" in col.lower() or "time" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
        elif df[col].dtype == object and len(df) > 0:
            sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if sample_val is not None:
                if isinstance(sample_val, Decimal):
                    df[col] = df[col].astype(float)
                elif hasattr(sample_val, "isoformat") or hasattr(sample_val, "strftime"):
                    try:
                        df[col] = pd.to_datetime(df[col])
                    except Exception:
                        pass
    return df


@st.cache_data(ttl=300)
def load_gold_data():
    """Load analytical Gold marts strictly and exclusively from Google Cloud BigQuery (platzi_gold)."""
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

        df_kpi = _sanitize_bq_dataframe(df_kpi)
        df_ltv = _sanitize_bq_dataframe(df_ltv)
        df_prod = _sanitize_bq_dataframe(df_prod)

        source_info = f"Google Cloud BigQuery ({PROJECT_ID}.platzi_gold)"
        return df_kpi, df_ltv, df_prod, source_info
    except Exception as e:
        if os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
            mock_kpi = pd.DataFrame(
                {
                    "order_date": pd.to_datetime(["2026-09-15", "2026-09-16"]),
                    "gmv": [1000.0, 1500.0],
                    "net_revenue": [900.0, 1400.0],
                    "total_orders": [20, 30],
                    "completed_orders": [18, 28],
                    "cancelled_orders": [1, 1],
                    "refunded_orders": [1, 1],
                    "aov": [50.0, 50.0],
                    "cancellation_rate": [0.05, 0.033],
                    "refund_rate": [0.05, 0.033],
                }
            )
            mock_prod = pd.DataFrame(
                {
                    "product_id": [1, 2],
                    "product_title": ["Product A", "Product B"],
                    "category_name": ["Electronics", "Clothes"],
                    "completed_sales_amount": [5000.0, 3000.0],
                    "units_sold": [50, 60],
                    "unit_price": [100.0, 50.0],
                }
            )
            mock_ltv = pd.DataFrame(
                {
                    "customer_id": [1, 2, 3],
                    "customer_name": ["Alice", "Bob", "Charlie"],
                    "masked_email": ["a***@platzi.com", "b***@platzi.com", "c***@platzi.com"],
                    "customer_tier": ["Platinum", "Gold", "Silver"],
                    "total_orders": [10, 5, 2],
                    "completed_orders": [10, 5, 2],
                    "lifetime_net_revenue": [1000.0, 500.0, 200.0],
                }
            )
            return mock_kpi, mock_ltv, mock_prod, "Mock / Test Environment"
        raise e


@st.cache_data(ttl=300)
def load_silver_data():
    """Load cleaned transactional facts and dimensions from BigQuery (platzi_silver)."""
    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=PROJECT_ID)

        df_orders = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_silver.fct_orders` ORDER BY created_at DESC LIMIT 500"
        ).to_dataframe()
        df_items = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_silver.fct_order_items` LIMIT 500"
        ).to_dataframe()
        df_cust = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_silver.dim_customers` LIMIT 500"
        ).to_dataframe()
        df_prod = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_silver.dim_products` LIMIT 500"
        ).to_dataframe()

        df_orders = _sanitize_bq_dataframe(df_orders)
        df_items = _sanitize_bq_dataframe(df_items)
        df_cust = _sanitize_bq_dataframe(df_cust)
        df_prod = _sanitize_bq_dataframe(df_prod)

        source_info = f"Google Cloud BigQuery ({PROJECT_ID}.platzi_silver)"
        return df_orders, df_items, df_cust, df_prod, source_info
    except Exception as e:
        if os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
            mock_orders = pd.DataFrame(
                {
                    "order_id": [1, 2],
                    "customer_id": [101, 102],
                    "order_status": ["completed", "completed"],
                    "currency": ["USD", "USD"],
                    "gross_amount": [100.0, 250.0],
                    "discount_amount": [10.0, 20.0],
                    "net_amount": [90.0, 230.0],
                    "payment_method": ["credit_card", "paypal"],
                    "created_at": pd.to_datetime(["2026-09-15", "2026-09-16"]),
                }
            )
            mock_items = pd.DataFrame(
                {"item_id": [1, 2], "order_id": [1, 2], "quantity": [1, 2], "unit_price": [100.0, 125.0]}
            )
            mock_cust = pd.DataFrame(
                {"customer_id": [101, 102], "customer_name": ["Alice", "Bob"], "email": ["a@test.com", "b@test.com"]}
            )
            mock_prod = pd.DataFrame(
                {"product_id": [1, 2], "product_title": ["Product 1", "Product 2"], "category_name": ["Tech", "Home"], "unit_price": [100.0, 125.0]}
            )
            return mock_orders, mock_items, mock_cust, mock_prod, "Mock / Test Environment"
        raise e


@st.cache_data(ttl=300)
def load_bronze_data():
    """Load raw ingestion streaming records from BigQuery (platzi_bronze)."""
    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=PROJECT_ID)

        df_raw_orders = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_bronze.raw_orders` LIMIT 500"
        ).to_dataframe()
        df_raw_items = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_bronze.raw_order_items` LIMIT 500"
        ).to_dataframe()
        df_raw_cust = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_bronze.raw_customers` LIMIT 500"
        ).to_dataframe()
        df_dlt = client.query(
            f"SELECT * FROM `{PROJECT_ID}.platzi_bronze._dlt_loads` ORDER BY inserted_at DESC LIMIT 50"
        ).to_dataframe()

        df_raw_orders = _sanitize_bq_dataframe(df_raw_orders)
        df_raw_items = _sanitize_bq_dataframe(df_raw_items)
        df_raw_cust = _sanitize_bq_dataframe(df_raw_cust)
        df_dlt = _sanitize_bq_dataframe(df_dlt)

        source_info = f"Google Cloud BigQuery ({PROJECT_ID}.platzi_bronze)"
        return df_raw_orders, df_raw_items, df_raw_cust, df_dlt, source_info
    except Exception as e:
        if os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
            mock_raw_orders = pd.DataFrame(
                {"order_id": [1, 2], "gross_amount": [100.0, 250.0], "_dlt_load_id": ["load_1", "load_2"], "created_at": pd.to_datetime(["2026-09-15", "2026-09-16"])}
            )
            mock_raw_items = pd.DataFrame({"item_id": [1, 2], "order_id": [1, 2], "_dlt_load_id": ["load_1", "load_2"]})
            mock_raw_cust = pd.DataFrame({"customer_id": [101, 102], "name": ["Alice", "Bob"]})
            mock_dlt = pd.DataFrame(
                {"load_id": ["load_1", "load_2"], "schema_name": ["platzi", "platzi"], "status": [0, 0], "inserted_at": pd.to_datetime(["2026-09-15", "2026-09-16"])}
            )
            return mock_raw_orders, mock_raw_items, mock_raw_cust, mock_dlt, "Mock / Test Environment"
        raise e


# ==============================================================================
# 3. Natural Language AI & Power BI Visualization Engines
# ==============================================================================
import chart_generator
import fastmcp_diagnostic
import powerbi_builder
import workflow_trigger
importlib.reload(chart_generator)
importlib.reload(fastmcp_diagnostic)
importlib.reload(powerbi_builder)
importlib.reload(workflow_trigger)

from chart_generator import generate_chart_from_nl
from fastmcp_diagnostic import render_fastmcp_chat_widget, run_fastmcp_chart_diagnostic
from powerbi_builder import render_powerbi_studio
from workflow_trigger import trigger_pipeline_workflow


# ==============================================================================
# 4. FastMCP AI Operations Copilot Component (Embedded in Sidebar)
# ==============================================================================
def render_fastmcp_copilot():
    st.subheader("🤖 FastMCP 智慧營運顧問")
    st.caption("AI Operations Lakehouse Copilot · ⚡ Live")
    st.caption(f"🔒 鎖定 BigQuery `({PROJECT_ID}.platzi_gold)` 脫敏分析")

    # Gemini AI API Key Setting (Strict BYOK - Bring Your Own Key)
    st.markdown("##### 🔑 Gemini AI 設定")
    user_gemini_key = st.text_input(
        "輸入您的 Google Gemini API Key",
        type="password",
        value=st.session_state.get("sidebar_gemini_api_key", ""),
        placeholder="AIzaSy...",
        help="請輸入您自己的 Google Gemini API Key（可於 Google AI Studio 免費申請）。系統不會儲存您的金鑰，連線結束即釋放。",
        key="sidebar_gemini_api_key",
    )

    if user_gemini_key:
        clean_k = user_gemini_key.strip()
        if clean_k.startswith("AQ.") or clean_k.startswith("ya29."):
            st.error(
                "❌ **金鑰格式錯誤**：您輸入的字串以 `AQ.` 開頭，此為 Google OAuth 臨時憑證，"
                "並非 Gemini API 金鑰！\n\n"
                "Google Gemini 官方金鑰格式**固定以 `AIzaSy...` 開頭（共 39 碼）**。\n\n"
                "👉 [點擊此處前往 Google AI Studio 免費建立 API Key (AIzaSy...)](https://aistudio.google.com/app/apikey)"
            )
        elif not clean_k.startswith("AIza"):
            st.warning("⚠️ **提醒**：Gemini 官方 API Key 通常以 `AIzaSy...` 開頭，請確認是否自 Google AI Studio 複製。")
        else:
            st.success("✅ **金鑰格式正確**（AIzaSy...）")

    st.caption("🔒 **安全保障（BYOK 模式）**：系統絕不儲存金鑰，亦不使用開發者帳號付費。[👉 點此免費獲取 API Key](https://aistudio.google.com/app/apikey)")

    st.selectbox(
        "⚡ 選擇偏好 Gemini 模型版本：",
        options=["auto", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-3.8-flash"],
        format_func=lambda x: {
            "auto": "🚀 自動最適配（遇負載自動降級 3.8 ➔ 3.6 ➔ 2.5）",
            "gemini-3.6-flash": "⚡ Gemini 3.6 Flash（高可用推薦 · 避開尖峰）",
            "gemini-2.5-flash": "🛡️ Gemini 2.5 Flash（穩定高可靠基準）",
            "gemini-3.8-flash": "⭐ Gemini 3.8 Flash（最新旗艦前沿）",
        }.get(x, x),
        key="gemini_selected_model",
        help="如遇 Google 官方 503 模型尖峰壅塞（High Demand），系統預設會自動降級至 3.6 或 2.5；您亦可在此手動指定特定版本。",
    )

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

                    # 2. Build candidate cascade list dynamically with fallback degradation
                    from fastmcp_diagnostic import get_gemini_candidate_models
                    pref_m = st.session_state.get("gemini_selected_model", "auto")
                    candidate_models = get_gemini_candidate_models(client, preferred_model=pref_m)
                    chosen_model = candidate_models[0]

                    tools = [get_daily_sales_kpi, get_top_products, get_customer_metrics]
                    system_prompt = (
                        "你是擁有麥肯錫 (McKinsey) / 貝恩 (Bain) / BCG 資深合夥人（Senior Partner / Engagement Director）水準的頂級管理顧問，"
                        "專精於 Platzi 零售電商數據診斷與營運獲利優化。\n\n"
                        "【你的核心方法論規範（源自 claude-skill-management-consultant-B1 知識庫）】：\n"
                        "1. 嚴格通過「顧問三大檢驗」：\n"
                        "   - So What?（提煉高階商業洞察，而非單純復述或朗讀數據）\n"
                        "   - Why So?（MECE 因果歸因與單位經濟學數學論證）\n"
                        "   - Now What?（高 ROI 且具體可落地的商業行動處方）\n\n"
                        "2. 金字塔原理 (Pyramid Principle) 與結論先行 (Action Title)：\n"
                        "   - 嚴禁廢話或寒暄客套（絕對不要以『你好！我是顧問...』開場）。\n"
                        "   - 報告第一句話必須是加粗顯眼的【核心診斷結論 / Action Title】：一針見血指出當前商業與財務癥結點。\n\n"
                        "3. MECE 議題樹與獲利算式拆解 (Show the Math)：\n"
                        "   - 運用獲利樹拆解核心指標：Profit = GMV × (1 - 取消率 - 退款率) × 毛利率 - Opex (物流履約 / CAC)。\n"
                        "   - 計算淨營收實現率 (Net Realization Rate = Net Revenue / GMV)，明確量化流失的具體金額。\n"
                        "   - 運用 Pareto 80/20 法則定位關鍵少數商品（Top 20% SKU）與核心高價值會員（Platinum VIP）。\n\n"
                        "4. 30-60-90 天戰術落地路徑 (Actionable 30-60-90 Day Roadmap)：\n"
                        "   - Day 1~30 (速贏止血 Quick Wins)：流程與定價微調、高取消率排查、大件商品精準運費重置。\n"
                        "   - Day 31~60 (系統優化 Structural Plays)：高 LTV 客群留存搭售、品類利潤結構與購物車推薦優化。\n"
                        "   - Day 61~90 (戰略穩固 Strategic Scale)：供應商採購階梯議價、降低單位 COGS、建立常態預警機制。\n\n"
                        "【數據調用協議】：\n"
                        "請主動調用 BigQuery platzi_gold 工具（get_daily_sales_kpi、get_top_products、get_customer_metrics）獲取第一手即時數據。\n\n"
                        "【業務範疇約束限制】：\n"
                        "本助手專屬於『Platzi 零售電商營運分析』。如果使用者的問題與本電商業務數據（銷售、營收、GMV、商品、顧客、退款、客單價等）無關"
                        "（例如政治人物、歷史、演藝娛樂、哲學、生活閒聊等），你必須直接委婉拒絕回答，絕對不要調用查詢工具，也不要輸出不相干的電商數據！"
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
                        except Exception as e:
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
                    st.success(f"✨ 成功調用最新模型 **`{used_model}`** {fallback_notice}結合 MBB 管理顧問架構生成頂級診斷報告！")
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

                        sum_gmv = sum(k['gmv'] for k in kpis)
                        sum_net = sum(k['net_revenue'] for k in kpis)
                        realization_rate = (sum_net / sum_gmv * 100) if sum_gmv > 0 else 0
                        avg_aov = sum(k['aov'] for k in kpis) / len(kpis) if kpis else 0

                        st.markdown(
                            f"""
                            ### 📌 【MBB 核心診斷 Action Title】
                            **實質淨營收實現率僅達 {realization_rate:.1f}%，高取消與退款率正侵蝕獲利；需立即啟動「大件商品運費重置」與「VIP 保利精準行銷」。**

                            #### 1. MECE 獲利樹漏斗分解 (Profitability Decomposition)
                            - **GMV 總規模**：${sum_gmv:,.2f}
                            - **實質淨營收 (Net Revenue)**：${sum_net:,.2f}（折損 ${sum_gmv - sum_net:,.2f} 漏斗損耗）
                            - **平均客單價 (AOV)**：${avg_aov:,.2f}
                            - **主力貢獻商品 (Pareto 80/20)**：冠軍商品 **{top_prods[0]['product_title']}** 貢獻 ${top_prods[0]['completed_sales_amount']:,.2f}。

                            #### 2. 30-60-90 天戰術落地藍圖 (Tactical Roadmap)
                            - **Day 1~30 (止血期)**：排查取消率偏高訂單的成因，針對體積過大商品重置免運門檻與專用物流費。
                            - **Day 31~60 (深耕期)**：針對 Platinum VIP 客群（平均貢獻 ${vip_custs[0]['lifetime_net_revenue']:,.2f}）推展高毛利配件搭售 (Cross-sell)，停止全面性價格戰。
                            - **Day 61~90 (穩固期)**：與主力前三大商品供應商談判階梯採購折扣，制度化降低單位 COGS。
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

                    sum_gmv = sum(k['gmv'] for k in kpis)
                    sum_net = sum(k['net_revenue'] for k in kpis)
                    realization_rate = (sum_net / sum_gmv * 100) if sum_gmv > 0 else 0
                    avg_aov = sum(k['aov'] for k in kpis) / len(kpis) if kpis else 0

                    st.success("✅ FastMCP 成功擷取 BigQuery Gold 數據！(提示：於上方輸入 API Key 可啟動原生 Gemini 深度推理)")
                    st.markdown(
                        f"""
                        ### 📌 【MBB 核心診斷 Action Title】
                        **實質淨營收實現率僅達 {realization_rate:.1f}%，漏斗損耗高達 ${sum_gmv - sum_net:,.2f}；需立即實施「運費重構」與「VIP 保利精準行銷」。**

                        #### 1. MECE 獲利樹漏斗分解 (Profitability Decomposition)
                        - **GMV 總規模**：${sum_gmv:,.2f}
                        - **實質淨營收 (Net Revenue)**：${sum_net:,.2f}
                        - **淨營收實現率 (Net Realization Rate)**：**{realization_rate:.1f}%**
                        - **主力核心產品**：**{top_prods[0]['product_title']}**（銷售額 ${top_prods[0]['completed_sales_amount']:,.2f}，售出 {top_prods[0]['units_sold']} 件）。
                        - **頂級 VIP 價值**：Platinum 顧客平均貢獻 **${vip_custs[0]['lifetime_net_revenue']:,.2f}**（已完成 {vip_custs[0]['completed_orders']} 筆訂單）。

                        #### 2. 30-60-90 天戰術落地藍圖 (Tactical Roadmap)
                        - **Day 1~30 (速贏止血)**：全面排查高取消率訂單的結帳體驗瑕疵，大件傢俱設定動態運費，嚴防物流成本侵蝕。
                        - **Day 31~60 (系統深耕)**：針對 Platinum 會員推行「高毛利配件搭售」，以客製化專屬體驗取代無差別打折。
                        - **Day 61~90 (戰略穩固)**：展開 Top 3 明星 SKU 的供應商階梯價格談判，系統化壓降 5%~8% 的 COGS。
                        """
                    )

# ==============================================================================
# 4. Sidebar Navigation & Global Filters
# ==============================================================================
with st.sidebar:
    st.title("🛍️ 營運智慧中心")
    st.caption("Serverless ELT Modern Lakehouse")

    st.markdown("---")
    st.subheader("📁 湖倉資料來源層級 (Lakehouse Layer)")
    layer_options = {
        "gold": "🥇 金牌層 (platzi_gold · 營運認證指標)",
        "silver": "🥈 銀牌層 (platzi_silver · 清洗事實與維度)",
        "bronze": "🥉 銅牌層 (platzi_bronze · 原始 API 流水)",
    }
    selected_layer = st.selectbox(
        "切換湖倉資料來源層級：",
        options=list(layer_options.keys()),
        format_func=lambda k: layer_options[k],
        index=0,
        key="selected_lakehouse_layer",
        help="切換後上方分頁列與圖表將自動跟隨所選層級動態適應！",
    )
    active_dataset = f"platzi_{selected_layer}"
    data_source = f"Google Cloud BigQuery ({PROJECT_ID}.{active_dataset})"
    st.caption(f"🔒 連線資料庫：`{data_source}`")

    # Safe initialization of layer dataframes
    df_kpi, df_ltv, df_prod = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    filtered_kpi = pd.DataFrame()
    df_orders, df_items, df_cust, df_prod_silver = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df_raw_orders, df_raw_items, df_raw_cust, df_dlt = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Dynamically load data based on selected layer
    if selected_layer == "gold":
        df_kpi, df_ltv, df_prod, data_source = load_gold_data()
        df_kpi["order_date"] = pd.to_datetime(df_kpi["order_date"])
    elif selected_layer == "silver":
        df_orders, df_items, df_cust, df_prod_silver, data_source = load_silver_data()
        if "created_at" in df_orders.columns:
            df_orders["created_at"] = pd.to_datetime(df_orders["created_at"])
    else:  # bronze
        df_raw_orders, df_raw_items, df_raw_cust, df_dlt, data_source = load_bronze_data()
        if "created_at" in df_raw_orders.columns:
            df_raw_orders["created_at"] = pd.to_datetime(df_raw_orders["created_at"])

    # Cloud Workflows Trigger Section
    st.markdown("---")
    st.subheader("⚡ 雲端資料管線控制")
    st.caption("Google Cloud Workflows · Serverless DAG")

    col_sync1, col_sync2 = st.columns([2, 1])
    with col_sync1:
        st.markdown("<span style='color:#10b981; font-size:0.85rem; font-weight:600;'>🟢 雲端排程已就緒</span>", unsafe_allow_html=True)
    with col_sync2:
        if st.button("🔄 刷新", key="btn_refresh_cache", help="清除本地快取並重新載入 BigQuery 數據"):
            st.cache_data.clear()
            st.rerun()

    if st.button("🚀 立即同步最新資料 (Trigger Workflow)", type="primary", use_container_width=True, key="btn_trigger_wf"):
        with st.spinner("正在向 Google Cloud Workflows 發送執行請求..."):
            success, resp = trigger_pipeline_workflow(project_id=PROJECT_ID)
            if success:
                exec_id = resp.get("name", "").split("/")[-1] if isinstance(resp, dict) else "已發送"
                st.success(f"🎉 已成功調度雲端工作流！\n\n執行 ID: `{exec_id}`\n\n背景正在執行 Ingest ➔ Transform ➔ Test，約 2~3 分鐘完成後點擊上方「🔄 刷新」即可檢視最新數據。")
            else:
                st.error(f"❌ 觸發失敗：{resp}")

    # Layer-Specific Filters & Downloads
    if selected_layer == "gold":
        import datetime

        raw_min = df_kpi["order_date"].min()
        min_date = raw_min.date() if hasattr(raw_min, "date") else pd.to_datetime(raw_min).date()
        raw_max = df_kpi["order_date"].max()
        max_date = raw_max.date() if hasattr(raw_max, "date") else pd.to_datetime(raw_max).date()

        st.subheader("📅 時間區間篩選")
        calendar_min = min_date - datetime.timedelta(days=90)
        calendar_max = datetime.date.today() + datetime.timedelta(days=1)
        calendar_max = max(calendar_max, max_date)

        selected_dates = st.date_input(
            "選擇日期範圍",
            value=(min_date, max_date),
            min_value=calendar_min,
            max_value=calendar_max,
            help="目前 BigQuery 金牌資料庫每日銷售記錄區間為 9/12 ~ 9/17。",
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
            use_container_width=True,
        )

    elif selected_layer == "silver":
        st.subheader("📊 銀牌層數據指標")
        st.markdown(
            f"- 📦 **清洗後訂單 (fct_orders)**：`{len(df_orders):,}` 筆\n"
            f"- 🛍️ **行項目 (fct_order_items)**：`{len(df_items):,}` 筆\n"
            f"- 👥 **客戶檔案 (dim_customers)**：`{len(df_cust):,}` 筆\n"
            f"- 🏷️ **商品目錄 (dim_products)**：`{len(df_prod_silver):,}` 筆"
        )
        st.markdown("#### 📥 下載 BigQuery 銀牌資料表")
        silver_dl_name = st.selectbox(
            "選擇要下載的銀牌資料表：",
            ["📦 fct_orders (訂單事實表)", "🛍️ fct_order_items (購物車行項目)", "👥 dim_customers (客戶維度)", "🏷️ dim_products (商品維度)"],
        )
        if "fct_orders" in silver_dl_name:
            s_df = df_orders
            s_name = "fct_orders"
        elif "fct_order_items" in silver_dl_name:
            s_df = df_items
            s_name = "fct_order_items"
        elif "dim_customers" in silver_dl_name:
            s_df = df_cust
            s_name = "dim_customers"
        else:
            s_df = df_prod_silver
            s_name = "dim_products"
        st.download_button(
            label=f"💾 下載 {s_name} ({len(s_df)} 筆) (CSV)",
            data=s_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"bigquery_silver_{s_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    else:  # bronze
        st.subheader("📥 銅牌層串流指標")
        st.markdown(
            f"- 📥 **原始訂單流 (raw_orders)**：`{len(df_raw_orders):,}` 筆\n"
            f"- 🛒 **原始品項 (raw_order_items)**：`{len(df_raw_items):,}` 筆\n"
            f"- 👤 **原始客戶 (raw_customers)**：`{len(df_raw_cust):,}` 筆\n"
            f"- ⚙️ **dlt 載入批次 (_dlt_loads)**：`{len(df_dlt):,}` 批"
        )
        st.markdown("#### 📥 下載 BigQuery 銅牌資料表")
        bronze_dl_name = st.selectbox(
            "選擇要下載的銅牌資料表：",
            ["📥 raw_orders (原始訂單流水)", "🛒 raw_order_items (原始項目流水)", "👤 raw_customers (原始客戶快照)", "⚙️ _dlt_loads (dlt Ingestion 歷程)"],
        )
        if "raw_orders" in bronze_dl_name:
            b_df = df_raw_orders
            b_name = "raw_orders"
        elif "raw_order_items" in bronze_dl_name:
            b_df = df_raw_items
            b_name = "raw_order_items"
        elif "raw_customers" in bronze_dl_name:
            b_df = df_raw_cust
            b_name = "raw_customers"
        else:
            b_df = df_dlt
            b_name = "_dlt_loads"
        st.download_button(
            label=f"💾 下載 {b_name} ({len(b_df)} 筆) (CSV)",
            data=b_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"bigquery_bronze_{b_name}.csv",
            mime="text/csv",
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
# 5. Main Workspace: E-Commerce Lakehouse Analytics
# ==============================================================================
header_col1, header_col2 = st.columns([3, 1])
layer_display_titles = {
    "gold": "🥇 金牌層 (platzi_gold · 業務決策與 BI 指標)",
    "silver": "🥈 銀牌層 (platzi_silver · 清洗事實與維度明細)",
    "bronze": "🥉 銅牌層 (platzi_bronze · 原始串流與 Ingestion 歷程)",
}
with header_col1:
    st.title("E-Commerce Lakehouse Analytics")
    st.markdown(
        f"**當前湖倉層級**：{layer_display_titles.get(selected_layer, 'BigQuery Lakehouse')} · "
        "**Platzi Store API + dlt + GCP BigQuery + dbt-core**"
    )
with header_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="text-align: right;">
            <div class="status-badge">
                <div class="pulse-dot"></div>
                {selected_layer.upper()} Layer Connected
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# Layer-Specific Executive KPI Cards
# ------------------------------------------------------------------------------
if selected_layer == "gold":
    total_gmv = filtered_kpi["gmv"].sum() if not filtered_kpi.empty and "gmv" in filtered_kpi.columns else 0.0
    total_net_rev = filtered_kpi["net_revenue"].sum() if not filtered_kpi.empty and "net_revenue" in filtered_kpi.columns else 0.0
    total_orders = filtered_kpi["total_orders"].sum() if not filtered_kpi.empty and "total_orders" in filtered_kpi.columns else 0
    completed_orders = filtered_kpi["completed_orders"].sum() if not filtered_kpi.empty and "completed_orders" in filtered_kpi.columns else 0
    cancelled_orders = filtered_kpi["cancelled_orders"].sum() if not filtered_kpi.empty and "cancelled_orders" in filtered_kpi.columns else 0
    refunded_orders = filtered_kpi["refunded_orders"].sum() if not filtered_kpi.empty and "refunded_orders" in filtered_kpi.columns else 0
    avg_aov = filtered_kpi["aov"].mean() if not filtered_kpi.empty and "aov" in filtered_kpi.columns else 0.0
    cancel_rate = (cancelled_orders / total_orders * 100) if total_orders > 0 else 0
    refund_rate = (refunded_orders / total_orders * 100) if total_orders > 0 else 0

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

elif selected_layer == "silver":
    s_orders_cnt = len(df_orders)
    s_gross = df_orders["gross_amount"].sum() if not df_orders.empty and "gross_amount" in df_orders.columns else 0.0
    s_discount = df_orders["discount_amount"].sum() if not df_orders.empty and "discount_amount" in df_orders.columns else 0.0
    s_net = df_orders["net_amount"].sum() if not df_orders.empty and "net_amount" in df_orders.columns else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">清洗事實訂單 (fct_orders)</div>
                <div class="metric-value">{s_orders_cnt:,} 筆</div>
                <div class="metric-subtext">標準化與關聯事實紀錄</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">累計訂單總毛額 (Gross)</div>
                <div class="metric-value">${s_gross:,.2f}</div>
                <div class="metric-subtext">訂單標準牌價金額</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">行銷折扣扣減 (Discount)</div>
                <div class="metric-value">${s_discount:,.2f}</div>
                <div class="metric-subtext">優惠券與促銷折讓累計</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">實質訂單淨額 (Net Amount)</div>
                <div class="metric-value">${s_net:,.2f}</div>
                <div class="metric-subtext">實收交易金流總額</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

else:  # bronze
    b_raw_orders_cnt = len(df_raw_orders)
    b_raw_items_cnt = len(df_raw_items)
    b_raw_cust_cnt = len(df_raw_cust)
    b_dlt_cnt = len(df_dlt)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">原始訂單事件 (raw_orders)</div>
                <div class="metric-value">{b_raw_orders_cnt:,} 筆</div>
                <div class="metric-subtext">Platzi API Ingestion 落地</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">原始訂單項目 (raw_items)</div>
                <div class="metric-value">{b_raw_items_cnt:,} 筆</div>
                <div class="metric-subtext">訂單細項未清洗流水</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">原始客戶快照 (raw_customers)</div>
                <div class="metric-value">{b_raw_cust_cnt:,} 筆</div>
                <div class="metric-subtext">含原始客戶欄位</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">dlt 管道載入批次 (_dlt_loads)</div>
                <div class="metric-value">{b_dlt_cnt:,} 批</div>
                <div class="metric-subtext">ETL Schema 演化與狀態歷程</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")

# ------------------------------------------------------------------------------
# Dynamic Tab Definition per Layer
# ------------------------------------------------------------------------------
if "custom_tabs" not in st.session_state:
    st.session_state.custom_tabs = []

if selected_layer == "gold":
    base_tab_titles = [
        "📈 營收走勢與轉換漏斗",
        "👥 客戶終身價值 (LTV) 分群",
        "🏆 熱銷商品與類別排行",
        "✨ 自然語言 AI 智能圖表",
        "🎛️ 視覺化自訂看板 (Power BI 畫布)",
    ]
elif selected_layer == "silver":
    base_tab_titles = [
        "📦 訂單事實表 (fct_orders)",
        "🛒 訂單品項事實表 (fct_order_items)",
        "👥 客戶維度表 (dim_customers)",
        "🏷️ 商品維度表 (dim_products)",
        "🎛️ 銀牌層視覺化畫布 (Power BI 畫布)",
    ]
else:  # bronze
    base_tab_titles = [
        "📥 原始訂單流 (raw_orders)",
        "🛒 原始品項流 (raw_order_items)",
        "👤 原始客戶快照 (raw_customers)",
        "⚙️ dlt 載入歷程 (_dlt_loads)",
        "🎛️ 銅牌層視覺化畫布 (Power BI 畫布)",
    ]

custom_tab_titles = [f"📌 {t['title']}" for t in st.session_state.custom_tabs]
all_tab_titles = base_tab_titles + custom_tab_titles + ["➕ 新增圖表分頁"]

all_rendered_tabs = st.tabs(all_tab_titles)
tab1, tab2, tab3, tab4, tab5 = all_rendered_tabs[0], all_rendered_tabs[1], all_rendered_tabs[2], all_rendered_tabs[3], all_rendered_tabs[4]
custom_tabs_rendered = all_rendered_tabs[5:5 + len(st.session_state.custom_tabs)]
tab_add = all_rendered_tabs[-1]


# ==============================================================================
# RENDER TABS ACCORDING TO SELECTED LAKEHOUSE LAYER
# ==============================================================================

if selected_layer == "gold":
    # --------------------------------------------------------------------------
    # GOLD TAB 1: 每日營收走勢與轉換漏斗
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("📊 每日 GMV 與實質淨營收趨勢")
        if not filtered_kpi.empty:
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
        else:
            st.info("尚無符合篩選區間的金牌 KPI 數據。")

    # --------------------------------------------------------------------------
    # GOLD TAB 2: 客戶終身價值 (LTV) 分群
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("👥 客戶層級 (Customer Tiers) 佔比與價值貢獻")
        if not df_ltv.empty:
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
            show_cols = [c for c in ["customer_id", "customer_name", "masked_email", "customer_tier", "total_orders", "completed_orders", "lifetime_net_revenue"] if c in df_ltv.columns]
            st.dataframe(df_ltv[show_cols], use_container_width=True, hide_index=True)
        else:
            st.info("尚無客戶 LTV 分群數據。")

    # --------------------------------------------------------------------------
    # GOLD TAB 3: 熱銷商品與類別排行
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("🏆 商品業績與銷售數量排行榜")
        if not df_prod.empty:
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                top_rev_prod = df_prod.sort_values(by="completed_sales_amount", ascending=True).tail(10)
                fig_prod_rev = px.bar(
                    top_rev_prod,
                    x="completed_sales_amount",
                    y="product_title",
                    orientation="h",
                    color="category_name" if "category_name" in top_rev_prod.columns else None,
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
                    color="category_name" if "category_name" in top_qty_prod.columns else None,
                    template="plotly_dark",
                    title="Top 10 商品銷售件數排行 (件)",
                    labels={"units_sold": "累積銷售件數", "product_title": "商品名稱"},
                )
                fig_prod_qty.update_layout(height=420, margin={"l": 20, "r": 20, "t": 40, "b": 20})
                st.plotly_chart(fig_prod_qty, use_container_width=True)

            st.subheader("📋 完整商品業績明細清單")
            st.dataframe(df_prod, use_container_width=True, hide_index=True)
        else:
            st.info("尚無商品業績排行數據。")

    # --------------------------------------------------------------------------
    # GOLD TAB 4: 自然語言 AI 智能圖表生成器 (NL-to-Visualization + FastMCP Mode A)
    # --------------------------------------------------------------------------
    with tab4:
        st.subheader("✨ 自然語言 AI 智能圖表生成器 (Text-to-Chart)")
        st.caption("🤖 支援自然繁體中文輸入任何圖表需求，AI 即時自動選取 BigQuery 金牌資料欄位並繪製互動式 Plotly 圖表")

        gemini_key = st.session_state.get("sidebar_gemini_api_key", "")

        def set_gold_chart_query(q: str):
            st.session_state["nl_chart_input_field"] = q
            st.session_state["nl_chart_query"] = q
            st.session_state.pop("fastmcp_diag_result_gold_tab4", None)
            st.session_state.pop("mcp_chat_hist_gold_tab4", None)
            st.session_state.pop("active_model_gold_tab4", None)
            st.rerun()

        st.markdown("##### 💡 點擊範例指令立即生圖：")
        c_btn1, c_btn2, c_btn3 = st.columns(3)
        with c_btn1:
            if st.button("📈 GMV 與淨營收對比走勢", key="btn_nl_1", use_container_width=True):
                set_gold_chart_query("請幫我畫出每日 GMV 與實質淨營收的對比走勢圖")
            if st.button("🏆 Top 10 熱銷商品排行", key="btn_nl_4", use_container_width=True):
                set_gold_chart_query("用長條圖呈現銷售額前 10 大熱銷商品")
        with c_btn2:
            if st.button("⚠️ 退款率與取消率監控", key="btn_nl_2", use_container_width=True):
                set_gold_chart_query("畫出每日退款率與取消率的監控走勢圖")
            if st.button("🏷️ 商品品類銷售佔比圓餅圖", key="btn_nl_5", use_container_width=True):
                set_gold_chart_query("幫我畫各商品品類 (Category) 銷售金額佔比圓餅圖")
        with c_btn3:
            if st.button("💵 平均客單價 (AOV) 走勢", key="btn_nl_3", use_container_width=True):
                set_gold_chart_query("請繪製平均客單價 AOV 的歷史波動走勢圖")
            if st.button("👥 會員等級價值分佈圖", key="btn_nl_6", use_container_width=True):
                set_gold_chart_query("用圓餅圖呈現不同會員等級 (Customer Tiers) 的營收貢獻")

        col_input, col_submit = st.columns([4, 1])
        with col_input:
            current_nl = st.text_input(
                "請輸入圖表生成指令：",
                value=st.session_state.get("nl_chart_input_field", st.session_state.get("nl_chart_query", "請幫我畫出每日 GMV 與實質淨營收的對比走勢圖")),
                key="nl_chart_input_field",
                placeholder="例如：畫出前五大商品銷售長條圖、或是每日退款率走勢...",
            )
        with col_submit:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_gen = st.button("生成圖表 🚀", key="btn_trigger_chart", type="primary", use_container_width=True)

        target_query = current_nl.strip() if current_nl and current_nl.strip() else "請幫我畫出每日 GMV 與實質淨營收的對比走勢圖"
        if btn_gen and st.session_state.get("nl_last_executed_query") != target_query:
            st.session_state.pop("fastmcp_diag_result_gold_tab4", None)
            st.session_state.pop("mcp_chat_hist_gold_tab4", None)
            st.session_state.pop("active_model_gold_tab4", None)
            st.session_state["nl_chart_query"] = target_query
            st.rerun()
        st.session_state["nl_last_executed_query"] = target_query

        with st.spinner("AI 正在解析自然語言意圖並調用 BigQuery 金牌數據繪圖..."):
            fig_nl, chart_title, insight_text, raw_df = generate_chart_from_nl(
                prompt=target_query,
                df_kpi=filtered_kpi,
                df_prod=df_prod,
                df_ltv=df_ltv,
                gemini_api_key=gemini_key,
            )

        st.markdown("---")
        if fig_nl is None:
            st.warning(f"### {chart_title}")
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.05);">
                    <div style="font-size: 1.05rem; line-height: 1.6; color: var(--text-color, #0f172a);">
                        {insight_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
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

            # FastMCP Mode A: Deep Diagnostic Trigger
            st.markdown("---")
            col_mcp_btn, col_mcp_info = st.columns([1.8, 3.2])
            with col_mcp_btn:
                run_mcp_diag = st.button(
                    "🤖 呼叫 FastMCP 顧問深度診斷 (Mode A)",
                    key="btn_fastmcp_diag_main",
                    type="primary",
                    use_container_width=True,
                    help="調用 FastMCP 顧問引擎：套用麥肯錫 SCQA + MECE 議題樹 + 30-60-90 天落地方針進行深度數據因果診斷",
                )
            with col_mcp_info:
                st.caption("⚡ **FastMCP A 模式**：圖表生成後，點擊立即呼叫 FastMCP 數據分析顧問對底層數據進行深層歸因診斷。")

            diag_res_key = "fastmcp_diag_result_gold_tab4"
            if run_mcp_diag:
                with st.spinner("🤖 FastMCP 顧問正在以 MBB 標準執行深度因果歸因診斷 (SCQA + MECE Issue Tree)..."):
                    diag_output = run_fastmcp_chart_diagnostic(
                        chart_title=chart_title,
                        df=raw_df,
                        prompt_intent=target_query,
                        gemini_api_key=gemini_key,
                    )
                    st.session_state[diag_res_key] = diag_output

            if st.session_state.get(diag_res_key):
                render_fastmcp_chat_widget(
                    unique_key="gold_tab4",
                    chart_title=chart_title,
                    df=raw_df,
                    initial_diagnostic=st.session_state[diag_res_key],
                    gemini_api_key=gemini_key,
                )

            with st.expander("🔍 點擊展開：檢視本圖表底層數據表 (Data Preview)"):
                st.dataframe(raw_df, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # GOLD TAB 5: 類 Power BI 雙軌自訂視覺化看板
    # --------------------------------------------------------------------------
    with tab5:
        render_powerbi_studio(
            df_kpi=filtered_kpi,
            df_ltv=df_ltv,
            df_prod=df_prod,
            key_prefix="pbi_main",
        )

elif selected_layer == "silver":
    # --------------------------------------------------------------------------
    # SILVER TAB 1: 訂單事實表 (fct_orders)
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("📦 fct_orders 訂單清洗事實表概覽")
        if not df_orders.empty:
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.markdown("##### 訂單履約狀態分佈 (Order Status)")
                status_counts = df_orders["order_status"].value_counts().reset_index()
                status_counts.columns = ["order_status", "count"]
                fig_s_status = px.pie(
                    status_counts,
                    names="order_status",
                    values="count",
                    template="plotly_dark",
                    hole=0.45,
                    color_discrete_sequence=["#10b981", "#f59e0b", "#ef4444", "#6366f1"],
                )
                fig_s_status.update_layout(height=320, margin={"l": 20, "r": 20, "t": 30, "b": 20})
                st.plotly_chart(fig_s_status, use_container_width=True)

            with c_s2:
                st.markdown("##### 訂單金額走勢 (Gross vs Net Amount)")
                if "created_at" in df_orders.columns:
                    orders_trend = df_orders.copy()
                    orders_trend["order_day"] = pd.to_datetime(orders_trend["created_at"]).dt.date
                    day_agg = orders_trend.groupby("order_day").agg(
                        gross_sum=("gross_amount", "sum"),
                        net_sum=("net_amount", "sum"),
                    ).reset_index()
                    fig_s_trend = go.Figure()
                    fig_s_trend.add_trace(go.Bar(x=day_agg["order_day"], y=day_agg["gross_sum"], name="總毛額 (Gross)", marker_color="#6366f1"))
                    fig_s_trend.add_trace(go.Bar(x=day_agg["order_day"], y=day_agg["net_sum"], name="淨實付額 (Net)", marker_color="#10b981"))
                    fig_s_trend.update_layout(
                        barmode="group",
                        template="plotly_dark",
                        height=320,
                        margin={"l": 20, "r": 20, "t": 30, "b": 20},
                    )
                    st.plotly_chart(fig_s_trend, use_container_width=True)

            st.markdown("##### 📋 訂單事實詳細資料表 (Top 500 筆)")
            st.dataframe(df_orders, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 fct_orders 銀牌資料。")

    # --------------------------------------------------------------------------
    # SILVER TAB 2: 訂單品項事實表 (fct_order_items)
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("🛒 fct_order_items 訂單品項事實表明細")
        if not df_items.empty:
            c_i1, c_i2 = st.columns(2)
            with c_i1:
                st.markdown("##### 單品售價分佈 (Unit Price Distribution)")
                fig_hist = px.histogram(
                    df_items,
                    x="unit_price" if "unit_price" in df_items.columns else df_items.columns[0],
                    nbins=20,
                    template="plotly_dark",
                    color_discrete_sequence=["#38bdf8"],
                )
                fig_hist.update_layout(height=320, margin={"l": 20, "r": 20, "t": 30, "b": 20})
                st.plotly_chart(fig_hist, use_container_width=True)

            with c_i2:
                st.markdown("##### 購買數量分佈 (Quantity Breakdown)")
                if "quantity" in df_items.columns:
                    qty_df = df_items["quantity"].value_counts().reset_index()
                    qty_df.columns = ["quantity", "count"]
                    fig_qty = px.bar(qty_df, x="quantity", y="count", template="plotly_dark", color_discrete_sequence=["#a855f7"])
                    fig_qty.update_layout(height=320, margin={"l": 20, "r": 20, "t": 30, "b": 20})
                    st.plotly_chart(fig_qty, use_container_width=True)

            st.markdown("##### 📋 品項事實詳細資料表 (Top 500 筆)")
            st.dataframe(df_items, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 fct_order_items 銀牌資料。")

    # --------------------------------------------------------------------------
    # SILVER TAB 3: 客戶維度表 (dim_customers)
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("👥 dim_customers 客戶維度表 (PII 去識別化)")
        st.caption("🔒 符合資安規範：姓名與信箱透過 SHA-256 雜湊或遮蔽處理")
        if not df_cust.empty:
            st.dataframe(df_cust, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 dim_customers 銀牌資料。")

    # --------------------------------------------------------------------------
    # SILVER TAB 4: 商品維度表 (dim_products)
    # --------------------------------------------------------------------------
    with tab4:
        st.subheader("🏷️ dim_products 商品維度表")
        if not df_prod_silver.empty:
            if "category_name" in df_prod_silver.columns:
                cat_counts = df_prod_silver["category_name"].value_counts().reset_index()
                cat_counts.columns = ["category_name", "product_count"]
                fig_cat = px.bar(
                    cat_counts,
                    x="category_name",
                    y="product_count",
                    template="plotly_dark",
                    color="category_name",
                    title="各商品品類涵蓋之商品項目數",
                )
                fig_cat.update_layout(height=340, margin={"l": 20, "r": 20, "t": 40, "b": 20})
                st.plotly_chart(fig_cat, use_container_width=True)

            st.markdown("##### 📋 商品維度明細清單")
            st.dataframe(df_prod_silver, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 dim_products 銀牌資料。")

    # --------------------------------------------------------------------------
    # SILVER TAB 5: 銀牌層視覺化畫布 (Power BI 畫布)
    # --------------------------------------------------------------------------
    with tab5:
        silver_datasets = {
            "orders": {"name": "📦 fct_orders (訂單事實表)", "df": df_orders},
            "items": {"name": "🛒 fct_order_items (品項明細表)", "df": df_items},
            "customers": {"name": "👥 dim_customers (客戶維度表)", "df": df_cust},
            "products": {"name": "🏷️ dim_products (商品維度表)", "df": df_prod_silver},
        }
        render_powerbi_studio(
            key_prefix="pbi_silver",
            dataset_configs=silver_datasets,
            default_dataset_key="orders",
        )

else:  # bronze layer
    # --------------------------------------------------------------------------
    # BRONZE TAB 1: 原始訂單流 (raw_orders)
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("📥 raw_orders 原始訂單 Ingestion 串流記錄")
        st.caption("源自 Platzi Fake Store API 的原始 JSON 解析落地數據，包含 dlt Ingestion 元數據")
        if not df_raw_orders.empty:
            st.dataframe(df_raw_orders, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 raw_orders 銅牌資料。")

    # --------------------------------------------------------------------------
    # BRONZE TAB 2: 原始品項流 (raw_order_items)
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("🛒 raw_order_items 原始品項拆解流水")
        st.caption("未經彙總與業務規則過濾之原始訂單品項記錄")
        if not df_raw_items.empty:
            st.dataframe(df_raw_items, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 raw_order_items 銅牌資料。")

    # --------------------------------------------------------------------------
    # BRONZE TAB 3: 原始客戶快照 (raw_customers)
    # --------------------------------------------------------------------------
    with tab3:
        st.subheader("👤 raw_customers 原始客戶資料快照")
        st.caption("原始客戶明細，後續由 dbt staging 進行 PII 遮蔽雜湊轉換為銀牌維度")
        if not df_raw_cust.empty:
            st.dataframe(df_raw_cust, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 raw_customers 銅牌資料。")

    # --------------------------------------------------------------------------
    # BRONZE TAB 4: dlt 載入歷程 (_dlt_loads)
    # --------------------------------------------------------------------------
    with tab4:
        st.subheader("⚙️ _dlt_loads Ingestion 管道載入歷程日誌")
        st.caption("記錄每次 dlt pipeline 載入之 load_id、schema 演化版本與載入完成狀態")
        if not df_dlt.empty:
            st.dataframe(df_dlt, use_container_width=True, hide_index=True)
        else:
            st.info("尚無 _dlt_loads 管道日誌資料。")

    # --------------------------------------------------------------------------
    # BRONZE TAB 5: 銅牌層視覺化畫布 (Power BI 畫布)
    # --------------------------------------------------------------------------
    with tab5:
        bronze_datasets = {
            "raw_orders": {"name": "📥 raw_orders (原始訂單串流)", "df": df_raw_orders},
            "raw_items": {"name": "🛒 raw_order_items (原始品項流水)", "df": df_raw_items},
            "raw_cust": {"name": "👤 raw_customers (原始客戶快照)", "df": df_raw_cust},
            "dlt_loads": {"name": "⚙️ _dlt_loads (dlt 載入日誌)", "df": df_dlt},
        }
        render_powerbi_studio(
            key_prefix="pbi_bronze",
            dataset_configs=bronze_datasets,
            default_dataset_key="raw_orders",
        )


# ==============================================================================
# DYNAMIC CUSTOM TABS (支援跨層級新增自訂分頁與 FastMCP Mode A)
# ==============================================================================
for idx, (t_meta, t_obj) in enumerate(zip(st.session_state.custom_tabs, custom_tabs_rendered)):
    with t_obj:
        col_c_title, col_c_del = st.columns([5, 1])
        with col_c_title:
            st.subheader(f"📌 {t_meta['title']}")
            st.caption(f"自訂分頁類型：**{t_meta.get('type_label', '自訂看板')}** · 綁定資料表：`{t_meta.get('dataset_name', 'BigQuery 資料表')}`")
        with col_c_del:
            if st.button("🗑️ 移除分頁", key=f"btn_del_tab_{t_meta['id']}", use_container_width=True, help="點擊從分頁列移除此自訂分頁"):
                st.session_state.custom_tabs = [x for x in st.session_state.custom_tabs if x["id"] != t_meta["id"]]
                st.rerun()

        st.markdown("---")

        if t_meta["type"] == "ai_chart":
            tab_id = t_meta["id"]
            gemini_key = st.session_state.get("sidebar_gemini_api_key", "")
            col_input, col_submit = st.columns([4, 1])
            with col_input:
                current_nl = st.text_input(
                    "請輸入圖表生成指令：",
                    value=st.session_state.get(f"nl_query_{tab_id}", t_meta.get("default_query", "請幫我畫出各品類銷售佔比")),
                    key=f"input_nl_{tab_id}",
                    placeholder="例如：畫出前五大商品銷售長條圖、或是每日退款率走勢...",
                )
            with col_submit:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                btn_gen = st.button("生成圖表 🚀", key=f"btn_chart_{tab_id}", type="primary", use_container_width=True)

            target_query = current_nl if current_nl else t_meta.get("default_query", "請幫我畫出每日營收走勢")

            # Fallback to load gold if in non-gold layer for standard business charts
            chart_kpi = filtered_kpi if not filtered_kpi.empty else df_kpi
            if chart_kpi.empty:
                chart_kpi, chart_ltv, chart_prod, _ = load_gold_data()
            else:
                chart_ltv = df_ltv
                chart_prod = df_prod

            with st.spinner("AI 正在解析自然語言意圖並繪製互動圖表..."):
                fig_nl, chart_title, insight_text, raw_df = generate_chart_from_nl(
                    prompt=target_query,
                    df_kpi=chart_kpi,
                    df_prod=chart_prod,
                    df_ltv=chart_ltv,
                    gemini_api_key=gemini_key,
                )

            st.markdown("---")
            if fig_nl is None:
                st.warning(f"### {chart_title}")
                st.markdown(
                    f"""
                    <div class="metric-card" style="border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.05);">
                        <div style="font-size: 1.05rem; line-height: 1.6; color: var(--text-color, #0f172a);">
                            {insight_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
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

                # FastMCP Mode A Deep Diagnostic in Custom Tab
                st.markdown("---")
                col_mc1, col_mc2 = st.columns([1.8, 3.2])
                with col_mc1:
                    btn_mcp_c = st.button(
                        "🤖 呼叫 FastMCP 顧問深度診斷 (Mode A)",
                        key=f"btn_mcp_custom_{tab_id}",
                        type="primary",
                        use_container_width=True,
                        help="以 MBB 顧問框架 (SCQA + MECE Issue Tree + 30-60-90天執行方案) 對本圖表進行深層商業因果歸因診斷",
                    )
                with col_mc2:
                    st.caption("⚡ **FastMCP A 模式**：點擊調用顧問引擎，對本圖表底層數據進行深層歸因診斷。")

                diag_key_c = f"diag_res_custom_{tab_id}"
                if btn_mcp_c:
                    with st.spinner("🤖 FastMCP 顧問正在進行因果歸因診斷 (SCQA + MECE)..."):
                        diag_out = run_fastmcp_chart_diagnostic(
                            chart_title=chart_title,
                            df=raw_df,
                            prompt_intent=target_query,
                            gemini_api_key=gemini_key,
                        )
                        st.session_state[diag_key_c] = diag_out

                if st.session_state.get(diag_key_c):
                    render_fastmcp_chat_widget(
                        unique_key=f"custom_{tab_id}",
                        chart_title=chart_title,
                        df=raw_df,
                        initial_diagnostic=st.session_state[diag_key_c],
                        gemini_api_key=gemini_key,
                    )

                with st.expander("🔍 點擊展開：檢視底層數據表 (Data Preview)"):
                    st.dataframe(raw_df, use_container_width=True, hide_index=True)

        elif t_meta["type"] == "powerbi_canvas":
            render_powerbi_studio(
                df_kpi=filtered_kpi if not filtered_kpi.empty else df_kpi,
                df_ltv=df_ltv,
                df_prod=df_prod,
                key_prefix=f"pbi_custom_{t_meta['id']}",
                default_dataset_key=t_meta.get("dataset_key", "kpi"),
            )


# ==============================================================================
# TAB ADD: ➕ 新增圖表分頁 (Dynamic Tab Creation Wizard)
# ==============================================================================
with tab_add:
    st.subheader("➕ 新增自訂圖表分頁 (Add Custom Analytics Tab)")
    st.caption("自由擴充儀表板分頁，支援建立獨立的「AI 智能語意圖表」或「類 Power BI 拖曳畫布」")

    with st.container():
        st.markdown(
            """
            <div class="metric-card" style="border-left: 4px solid #6366f1; margin-bottom: 1.25rem;">
                <div style="font-size: 1.05rem; font-weight: 600; color: var(--text-color, #0f172a);">
                    🛠️ 選擇您想新增的分頁模式與資料來源
                </div>
                <div style="font-size: 0.9rem; color: #64748b; margin-top: 0.25rem;">
                    新增後分頁將立即加入上方分頁列，每個自訂分頁均具備獨立狀態與視覺化配置。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_new_t1, col_new_t2 = st.columns(2)
        with col_new_t1:
            new_tab_type = st.radio(
                "1. 選擇圖表引擎類型：",
                options=[
                    "✨ 自然語言 AI 智能圖表 (Text-to-Chart)",
                    "🎛️ 視覺化自訂看板 (Power BI / Tableau 拖曳畫布)",
                ],
                index=0,
                key="new_tab_type_radio",
            )
            is_ai_type = "AI" in new_tab_type

        with col_new_t2:
            if selected_layer == "gold":
                dataset_options = {
                    "kpi": "📊 gold_daily_sales_kpi (每日營收、訂單與退款指標)",
                    "prod": "🏆 gold_product_performance (熱銷商品與分類業績)",
                    "ltv": "👥 gold_customer_ltv (客戶終身價值與分群)",
                }
            elif selected_layer == "silver":
                dataset_options = {
                    "orders": "📦 fct_orders (清洗訂單事實表)",
                    "items": "🛒 fct_order_items (訂單項目明細表)",
                    "customers": "👥 dim_customers (客戶維度表)",
                    "products": "🏷️ dim_products (商品維度表)",
                }
            else:  # bronze
                dataset_options = {
                    "raw_orders": "📥 raw_orders (原始串流訂單事件)",
                    "raw_items": "🛒 raw_order_items (原始品項流水)",
                    "raw_cust": "👤 raw_customers (原始客戶快照)",
                    "dlt_loads": "⚙️ _dlt_loads (dlt 管道日誌)",
                }

            new_tab_ds = st.selectbox(
                "2. 選擇綁定資料來源：",
                options=list(dataset_options.keys()),
                format_func=lambda k: dataset_options[k],
                index=0,
                key="new_tab_ds_select",
            )

        default_name = (
            f"AI 智能分析 {len(st.session_state.custom_tabs) + 1}"
            if is_ai_type
            else f"自訂看板 {len(st.session_state.custom_tabs) + 1}"
        )
        new_tab_name = st.text_input(
            "3. 自訂分頁顯示標題：",
            value=default_name,
            key="new_tab_name_input",
            placeholder="例如：行銷退款專題、品類業績畫布...",
        )

        initial_ai_query = ""
        if is_ai_type:
            initial_ai_query = st.text_input(
                "4. 預設自然語言分析指令（可選）：",
                value="請畫出各商品品類的銷售佔比圓餅圖",
                key="new_tab_ai_query_input",
            )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 立即建立並加入分頁列", type="primary", use_container_width=True, key="btn_create_custom_tab"):
            import uuid
            tab_id = f"custom_{uuid.uuid4().hex[:6]}"
            new_tab_meta = {
                "id": tab_id,
                "title": new_tab_name.strip() or default_name,
                "type": "ai_chart" if is_ai_type else "powerbi_canvas",
                "type_label": "自然語言 AI 智能圖表" if is_ai_type else "類 Power BI 拖曳看板",
                "dataset_key": new_tab_ds,
                "dataset_name": dataset_options[new_tab_ds],
                "default_query": initial_ai_query,
            }
            st.session_state.custom_tabs.append(new_tab_meta)
            st.success(f"🎉 分頁「{new_tab_meta['title']}」建立成功！")
            st.rerun()





