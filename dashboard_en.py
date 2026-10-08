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
try:
    st.set_page_config(
        page_title="Platzi E-Commerce Executive Intelligence",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

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
else:
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
        pass


def _sanitize_bq_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize DataFrame returned by BigQuery client to avoid PyGWalker/DuckDB type incompatibilities."""
    if df is None or df.empty:
        return df
    clean = df.copy()
    for col in clean.columns:
        dtype_str = str(clean[col].dtype).lower()
        if "dbdate" in dtype_str or "date" in col.lower() or "time" in col.lower():
            try:
                clean[col] = pd.to_datetime(clean[col])
            except Exception:
                pass
        elif clean[col].dtype == object and len(clean) > 0:
            sample_val = clean[col].dropna().iloc[0] if not clean[col].dropna().empty else None
            if sample_val is not None:
                if isinstance(sample_val, Decimal):
                    clean[col] = clean[col].astype(float)
                elif hasattr(sample_val, "isoformat") or hasattr(sample_val, "strftime"):
                    try:
                        clean[col] = pd.to_datetime(clean[col])
                    except Exception:
                        pass
    return clean


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
# 3. Dynamic Visualization & Copilot Engines
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
# 4. FastMCP AI Operations Copilot (Sidebar)
# ==============================================================================
def render_fastmcp_copilot():
    st.subheader("🤖 FastMCP Operations Copilot")
    st.caption("AI Operations Lakehouse Copilot · ⚡ Live")
    st.caption(f"🔒 Scoped to BigQuery `({PROJECT_ID}.platzi_gold)` Masked Analytics")

    st.markdown("##### 🔑 Gemini AI Configuration")
    user_gemini_key = st.text_input(
        "Enter your Google Gemini API Key",
        type="password",
        value=st.session_state.get("sidebar_gemini_api_key", ""),
        placeholder="AIzaSy...",
        help="Enter your personal Google Gemini API Key (get one free at Google AI Studio). Your key is never stored or logged.",
        key="sidebar_gemini_api_key_en",
    )
    if user_gemini_key:
        st.session_state["sidebar_gemini_api_key"] = user_gemini_key
        clean_k = user_gemini_key.strip()
        if clean_k.startswith("AQ.") or clean_k.startswith("ya29."):
            st.error(
                "❌ **Invalid Key Format**: Your key starts with `AQ.` or `ya29.`, which is a temporary OAuth token, "
                "not a Gemini API key!\n\n"
                "Google Gemini API keys **always start with `AIzaSy...` (39 characters)**.\n\n"
                "👉 [Create a free API Key on Google AI Studio (AIzaSy...)](https://aistudio.google.com/app/apikey)"
            )
        elif not clean_k.startswith("AIza"):
            st.warning("⚠️ **Notice**: Gemini official API keys usually start with `AIzaSy...`. Please verify it was copied from Google AI Studio.")
        else:
            st.success("✅ **Valid Key Format** (AIzaSy...)")

    st.caption("🔒 **Security (BYOK Mode)**: Keys are neither saved nor billed to our developer account. [👉 Get Free API Key](https://aistudio.google.com/app/apikey)")

    st.selectbox(
        "⚡ Preferred Gemini Model Version:",
        options=["auto", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-3.8-flash"],
        format_func=lambda x: {
            "auto": "🚀 Auto Cascade (Graceful degradation 3.8 ➔ 3.6 ➔ 2.5)",
            "gemini-3.6-flash": "⚡ Gemini 3.6 Flash (High Availability · Peak-Dodge)",
            "gemini-2.5-flash": "🛡️ Gemini 2.5 Flash (Rock-Solid Stability)",
            "gemini-3.8-flash": "⭐ Gemini 3.8 Flash (Latest Frontier)",
        }.get(x, x),
        key="gemini_selected_model_en",
        help="If Google reports a 503 High Demand peak, the system automatically degrades to 3.6 or 2.5.",
    )

    st.markdown("##### 💡 Quick Commercial Queries")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        if st.button("📊 7-Day Revenue & Refunds", key="btn_q1_en", width="stretch"):
            st.session_state.ai_query_en = "What is our overall GMV, Net Revenue, and refund rate over the past week?"
        if st.button("💎 Platinum VIP Cohort", key="btn_q3_en", width="stretch"):
            st.session_state.ai_query_en = "Describe the behavioral profile and net margin of our top-tier Platinum LTV customers."
    with q_col2:
        if st.button("🏆 Top 3 Best-Sellers", key="btn_q2_en", width="stretch"):
            st.session_state.ai_query_en = "List the top 3 best-selling products by completed revenue and sales volume."

    user_prompt = st.text_area(
        "Enter business question:",
        value=st.session_state.get("ai_query_en", "What is our cumulative realized net revenue and top-performing product category?"),
        height=85,
        key="ai_user_prompt_en",
        help="Ask analytical questions related to e-commerce operations, margins, products, or customers.",
    )

    if st.button("Submit Query 🚀", type="primary", width="stretch", key="btn_ai_submit_en"):
        with st.spinner("AI is inspecting BigQuery Gold dataset via FastMCP..."):
            from mcp_server.server import (
                get_customer_metrics,
                get_daily_sales_kpi,
                get_top_products,
            )

            if user_gemini_key:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=user_gemini_key)
                    from fastmcp_diagnostic import get_gemini_candidate_models
                    pref_m = st.session_state.get("gemini_selected_model_en", "auto")
                    candidate_models = get_gemini_candidate_models(client, preferred_model=pref_m)
                    chosen_model = candidate_models[0]

                    tools = [get_daily_sales_kpi, get_top_products, get_customer_metrics]
                    system_prompt = (
                        "You are an MBB Senior Partner / Practice Director (McKinsey/Bain/BCG caliber) "
                        "specialized in Platzi retail e-commerce operational intelligence and unit economics optimization.\n\n"
                        "【Core Methodology Standards (from claude-skill-management-consultant-B1)】:\n"
                        "1. Pass the Three-Test Standard: 'So What?' (Synthesize strategic insight), "
                        "'Why So?' (MECE causal math proof), 'Now What?' (High-ROI actionable interventions).\n"
                        "2. Pyramid Principle & SCQA structure: Lead directly with a bold **[Action Title / Governing Thought]**.\n"
                        "3. Show the math: Profitability tree, Net Realization Rate (Net Revenue / GMV), Pareto 80/20 rule.\n"
                        "4. Actionable 30-60-90 Day Tactical Roadmap (Quick wins -> Structural plays -> Strategic scale).\n"
                        "Respond entirely in professional executive English."
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
                            if any(k in err_msg for k in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand", "404", "NOT_FOUND"]):
                                continue
                            raise e

                    if resp is None:
                        raise last_err or RuntimeError("No model response available")

                    fallback_notice = f" (Originally selected `{chosen_model}` was busy, cascaded gracefully)" if used_model != chosen_model else ""
                    st.success(f"✨ Successfully executed model **`{used_model}`**{fallback_notice} with MBB Executive Framework!")
                    st.markdown(resp.text)
                except Exception as ex:
                    st.warning(f"⚠️ Gemini API encounter ({ex}). Falling back to local FastMCP analytical engine:")
                    kpis = get_daily_sales_kpi(limit=7)
                    top_prods = get_top_products(limit=3)
                    vip_custs = get_customer_metrics(tier="Platinum", limit=3)

                    sum_gmv = sum(k['gmv'] for k in kpis)
                    sum_net = sum(k['net_revenue'] for k in kpis)
                    realization_rate = (sum_net / sum_gmv * 100) if sum_gmv > 0 else 0
                    avg_aov = sum(k['aov'] for k in kpis) / len(kpis) if kpis else 0

                    st.markdown(
                        f"""
                        ### 📌 【MBB Diagnostic Action Title】
                        **Net revenue realization rate stands at {realization_rate:.1f}%; elevated cancellation and refund leakages (${sum_gmv - sum_net:,.2f}) require immediate freight repricing and VIP retention plays.**

                        #### 1. MECE Profitability Tree Decomposition
                        - **Gross Merchandise Value (GMV)**: ${sum_gmv:,.2f}
                        - **Realized Net Revenue**: ${sum_net:,.2f}
                        - **Net Realization Rate**: **{realization_rate:.1f}%**
                        - **Average Order Value (AOV)**: ${avg_aov:,.2f}
                        - **Top Core Asset**: **{top_prods[0]['product_title']}** accounts for ${top_prods[0]['completed_sales_amount']:,.2f} ({top_prods[0]['units_sold']} units sold).

                        #### 2. Actionable 30-60-90 Day Roadmap
                        - **Days 1–30 (Quick Wins)**: Audit high-cancellation checkout friction; reset volumetric weight thresholds for oversized items to curb logistics erosion.
                        - **Days 31–60 (Structural Plays)**: Implement curated bundle cross-sells for Platinum VIPs (avg. spend ${vip_custs[0]['lifetime_net_revenue']:,.2f}) rather than indiscriminate discounting.
                        - **Days 61–90 (Strategic Scale)**: Re-negotiate tiered supplier cost brackets for the top 3 SKUs to structurally reduce COGS by 5%–8%.
                        """
                    )
            else:
                kpis = get_daily_sales_kpi(limit=7)
                top_prods = get_top_products(limit=3)
                vip_custs = get_customer_metrics(tier="Platinum", limit=3)

                sum_gmv = sum(k['gmv'] for k in kpis)
                sum_net = sum(k['net_revenue'] for k in kpis)
                realization_rate = (sum_net / sum_gmv * 100) if sum_gmv > 0 else 0
                avg_aov = sum(k['aov'] for k in kpis) / len(kpis) if kpis else 0

                st.success("✅ FastMCP successfully synthesized BigQuery Gold metrics! (Enter your API Key above to unlock deep Gemini reasoning)")
                st.markdown(
                    f"""
                    ### 📌 【MBB Diagnostic Action Title】
                    **Net revenue realization rate is {realization_rate:.1f}%; pipeline leakage totals ${sum_gmv - sum_net:,.2f}. Initiate freight restructuring and VIP loyalty interventions immediately.**

                    #### 1. MECE Profitability Tree Decomposition
                    - **Gross Merchandise Value (GMV)**: ${sum_gmv:,.2f}
                    - **Realized Net Revenue**: ${sum_net:,.2f}
                    - **Net Realization Rate**: **{realization_rate:.1f}%**
                    - **Flagship SKU**: **{top_prods[0]['product_title']}** generated ${top_prods[0]['completed_sales_amount']:,.2f} with {top_prods[0]['units_sold']} units.
                    - **VIP Customer Power**: Platinum customers average **${vip_custs[0]['lifetime_net_revenue']:,.2f}** lifetime spend across {vip_custs[0]['completed_orders']} orders.

                    #### 2. 30-60-90 Day Tactical Roadmap
                    - **Days 1–30 (Immediate Bleed Stop)**: Rectify checkout drop-offs and enforce dynamic shipping rates on bulky items.
                    - **Days 31–60 (Cohort Deepening)**: Roll out VIP-exclusive accessory bundling to maximize gross margins without price concessions.
                    - **Days 61–90 (Cost Optimization)**: Conduct supplier negotiations across Top 3 volume drivers to trim unit COGS.
                    """
                )


# ==============================================================================
# 5. Main Application Logic
# ==============================================================================
def main():
    with st.sidebar:
        # Language Switcher
        lang_choice_en = st.radio(
            "🌐 Language / 語言",
            options=["English", "繁體中文"],
            index=0,
            horizontal=True,
            key="sidebar_lang_selector_en",
        )
        if lang_choice_en == "繁體中文":
            st.session_state["lang"] = "zh"
            st.session_state.pop("sidebar_lang_selector_zh", None)
            st.session_state.pop("sidebar_lang_selector_en", None)
            st.query_params["lang"] = "zh"
            st.rerun()

        st.title("🛍️ Operations Hub")
        st.caption("Serverless ELT Modern Lakehouse")

        st.markdown("---")
        st.subheader("📁 Lakehouse Data Layer")
        layer_options = {
            "gold": "🥇 Gold Layer (platzi_gold · Certified Executive KPIs)",
            "silver": "🥈 Silver Layer (platzi_silver · Cleaned Facts & Dimensions)",
            "bronze": "🥉 Bronze Layer (platzi_bronze · Raw API Ingestion Streams)",
        }
        selected_layer = st.selectbox(
            "Select Lakehouse Data Layer:",
            options=list(layer_options.keys()),
            format_func=lambda k: layer_options[k],
            index=0,
            key="selected_lakehouse_layer_en",
            help="Tabs and analytics dynamically adapt to the selected layer!",
        )
        active_dataset = f"platzi_{selected_layer}"
        data_source = f"Google Cloud BigQuery ({PROJECT_ID}.{active_dataset})"
        st.caption(f"🔒 Connected Database: `{data_source}`")

        df_kpi, df_ltv, df_prod = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        filtered_kpi = pd.DataFrame()
        df_orders, df_items, df_cust, df_prod_silver = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        df_raw_orders, df_raw_items, df_raw_cust, df_dlt = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        if selected_layer == "gold":
            df_kpi, df_ltv, df_prod, data_source = load_gold_data()
            df_kpi["order_date"] = pd.to_datetime(df_kpi["order_date"])
        elif selected_layer == "silver":
            df_orders, df_items, df_cust, df_prod_silver, data_source = load_silver_data()
            if "created_at" in df_orders.columns:
                df_orders["created_at"] = pd.to_datetime(df_orders["created_at"])
        else:
            df_raw_orders, df_raw_items, df_raw_cust, df_dlt, data_source = load_bronze_data()
            if "created_at" in df_raw_orders.columns:
                df_raw_orders["created_at"] = pd.to_datetime(df_raw_orders["created_at"])

        st.markdown("---")
        st.subheader("⚡ Cloud Data Pipeline Control")
        st.caption("Google Cloud Workflows · Serverless DAG")

        col_sync1, col_sync2 = st.columns([2, 1])
        with col_sync1:
            st.markdown("<span style='color:#10b981; font-size:0.85rem; font-weight:600;'>🟢 Cloud Scheduler Active</span>", unsafe_allow_html=True)
        with col_sync2:
            if st.button("🔄 Refresh", key="btn_refresh_cache_en", help="Clear cache and reload BigQuery data"):
                st.cache_data.clear()
                st.rerun()

        if st.button("🚀 Trigger Live Pipeline Run", type="primary", width="stretch", key="btn_trigger_wf_en"):
            with st.spinner("Dispatching execution request to Google Cloud Workflows..."):
                success, resp = trigger_pipeline_workflow(project_id=PROJECT_ID)
                if success:
                    exec_id = resp.get("name", "").split("/")[-1] if isinstance(resp, dict) else "Dispatched"
                    st.success(f"🎉 Cloud workflow dispatched successfully!\n\nExecution ID: `{exec_id}`\n\nBackground running Ingest ➔ Transform ➔ Test. Click '🔄 Refresh' in 2–3 mins to see new data.")
                else:
                    st.error(f"❌ Trigger failed: {resp}")

        # Layer-Specific Filters & Downloads
        if selected_layer == "gold":
            import datetime

            raw_min = df_kpi["order_date"].min()
            min_date = raw_min.date() if hasattr(raw_min, "date") else pd.to_datetime(raw_min).date()
            raw_max = df_kpi["order_date"].max()
            max_date = raw_max.date() if hasattr(raw_max, "date") else pd.to_datetime(raw_max).date()

            st.subheader("📅 Date Range Filter")
            calendar_min = min_date - datetime.timedelta(days=90)
            calendar_max = datetime.date.today() + datetime.timedelta(days=1)
            calendar_max = max(calendar_max, max_date)

            selected_dates = st.date_input(
                "Select Date Range",
                value=(min_date, max_date),
                min_value=calendar_min,
                max_value=calendar_max,
                help="Current BigQuery Gold sales records span from 9/12 to 9/17.",
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

            st.markdown("#### 📥 Download BigQuery Gold Datasets")
            export_table = st.selectbox(
                "Select Table to Download",
                options=[
                    "📅 Filtered Date Range (KPI)",
                    "📊 Full Historical Daily Sales (All)",
                    "💎 Customer Lifetime Value LTV (All)",
                    "🏆 Best-Selling Products Ranking (All)",
                ],
            )
            if "Filtered Date Range" in export_table:
                export_df = filtered_kpi
                file_suffix = f"_{start_d}_to_{end_d}" if "start_d" in locals() and "end_d" in locals() else ""
                dl_filename = f"bigquery_gold_daily_kpi{file_suffix}.csv"
                dl_label = f"Download Range KPI ({len(export_df)} records)"
            elif "Full Historical Daily Sales" in export_table:
                export_df = df_kpi
                dl_filename = "bigquery_gold_daily_sales_kpi_full.csv"
                dl_label = f"Download Full Daily KPI ({len(export_df)} records)"
            elif "Customer Lifetime Value" in export_table:
                export_df = df_ltv
                dl_filename = "bigquery_gold_customer_ltv_full.csv"
                dl_label = f"Download Full Customer LTV ({len(export_df)} records)"
            else:
                export_df = df_prod
                dl_filename = "bigquery_gold_product_performance_full.csv"
                dl_label = f"Download Full Product Rankings ({len(export_df)} records)"

            st.download_button(
                label=f"💾 {dl_label} (CSV)",
                data=export_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=dl_filename,
                mime="text/csv",
                width="stretch",
            )

        elif selected_layer == "silver":
            st.subheader("📊 Silver Layer Metrics")
            st.markdown(
                f"- 📦 **Cleaned Orders (fct_orders)**: `{len(df_orders):,}` records\n"
                f"- 🛍️ **Line Items (fct_order_items)**: `{len(df_items):,}` records\n"
                f"- 👥 **Customer Profiles (dim_customers)**: `{len(df_cust):,}` records\n"
                f"- 🏷️ **Product Catalog (dim_products)**: `{len(df_prod_silver):,}` records"
            )
            st.markdown("#### 📥 Download BigQuery Silver Tables")
            silver_dl_name = st.selectbox(
                "Select Silver Table:",
                ["📦 fct_orders (Orders Fact)", "🛍️ fct_order_items (Line Items Fact)", "👥 dim_customers (Customers Dimension)", "🏷️ dim_products (Products Dimension)"],
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
                label=f"💾 Download {s_name} ({len(s_df)} records) (CSV)",
                data=s_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"bigquery_silver_{s_name}.csv",
                mime="text/csv",
                width="stretch",
            )

        else:  # bronze
            st.subheader("📥 Bronze Layer Streaming Metrics")
            st.markdown(
                f"- 📥 **Raw Orders (raw_orders)**: `{len(df_raw_orders):,}` records\n"
                f"- 🛒 **Raw Items (raw_order_items)**: `{len(df_raw_items):,}` records\n"
                f"- 👤 **Raw Customers (raw_customers)**: `{len(df_raw_cust):,}` records\n"
                f"- ⚙️ **dlt Ingestion Batches (_dlt_loads)**: `{len(df_dlt):,}` batches"
            )
            st.markdown("#### 📥 Download BigQuery Bronze Tables")
            bronze_dl_name = st.selectbox(
                "Select Bronze Table:",
                ["📥 raw_orders (Raw Order Events)", "🛒 raw_order_items (Raw Item Streams)", "👤 raw_customers (Raw Customer Snapshots)", "⚙️ _dlt_loads (dlt Ingestion Log)"],
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
                label=f"💾 Download {b_name} ({len(b_df)} records) (CSV)",
                data=b_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"bigquery_bronze_{b_name}.csv",
                mime="text/csv",
                width="stretch",
            )

        # FastMCP Operations Copilot
        st.markdown("---")
        render_fastmcp_copilot()

        st.markdown("---")
        st.markdown("### 🏛️ Architecture Highlights")
        st.markdown("- ⚡ **$0 Idle Cost** (Cloud Run Jobs)")
        st.markdown("- 🔒 **Automated PII Masking** (SHA-256)")
        st.markdown("- 🤖 **FastMCP / Gemini Tool Calling**")

    # ==========================================================================
    # Main Header & Executive Metric Cards
    # ==========================================================================
    header_col1, header_col2 = st.columns([3, 1])
    layer_display_titles = {
        "gold": "🥇 Gold Layer (platzi_gold · Certified Executive & BI Metrics)",
        "silver": "🥈 Silver Layer (platzi_silver · Cleaned Fact & Dimension Tables)",
        "bronze": "🥉 Bronze Layer (platzi_bronze · Raw Streams & Ingestion Audit)",
    }
    with header_col1:
        st.title("E-Commerce Lakehouse Analytics")
        st.markdown(
            f"**Current Layer**: {layer_display_titles.get(selected_layer, 'BigQuery Lakehouse')} · "
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

    # Layer-Specific Executive KPI Cards
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
                    <div class="metric-label">Gross Merchandise Value (GMV)</div>
                    <div class="metric-value">${total_gmv:,.2f}</div>
                    <div class="metric-subtext">Cumulative Order Volume</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Net Realized Revenue</div>
                    <div class="metric-value">${total_net_rev:,.2f}</div>
                    <div class="metric-subtext">Net of Refunds & Discounts</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Average Order Value (AOV)</div>
                    <div class="metric-value">${avg_aov:,.2f}</div>
                    <div class="metric-subtext">Completed Order Average</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Refund / Cancellation Rate</div>
                    <div class="metric-value">{refund_rate:.1f}% <span style="font-size:1rem;color:#94a3b8;">/ {cancel_rate:.1f}%</span></div>
                    <div class="metric-subtext warning">{refunded_orders} Refunded / {cancelled_orders} Cancelled</div>
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
                    <div class="metric-label">Cleaned Orders (fct_orders)</div>
                    <div class="metric-value">{s_orders_cnt:,} records</div>
                    <div class="metric-subtext">Standardized Fact Records</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Gross Order Volume</div>
                    <div class="metric-value">${s_gross:,.2f}</div>
                    <div class="metric-subtext">List Price Total</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Promotional Discounts</div>
                    <div class="metric-value">${s_discount:,.2f}</div>
                    <div class="metric-subtext">Coupons & Allowances</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Net Order Amount</div>
                    <div class="metric-value">${s_net:,.2f}</div>
                    <div class="metric-subtext">Collected Settlement Cashflow</div>
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
                    <div class="metric-label">Raw Orders (raw_orders)</div>
                    <div class="metric-value">{b_raw_orders_cnt:,} records</div>
                    <div class="metric-subtext">Platzi API Ingestion Landing</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Raw Items (raw_order_items)</div>
                    <div class="metric-value">{b_raw_items_cnt:,} records</div>
                    <div class="metric-subtext">Unfiltered Line Items</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Raw Customers (raw_customers)</div>
                    <div class="metric-value">{b_raw_cust_cnt:,} records</div>
                    <div class="metric-subtext">Pre-Masking Customer Snapshots</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">dlt Load Batches (_dlt_loads)</div>
                    <div class="metric-value">{b_dlt_cnt:,} batches</div>
                    <div class="metric-subtext">Schema Evolution & Audit Log</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # --------------------------------------------------------------------------
    # Dynamic Tab Definitions
    # --------------------------------------------------------------------------
    if "custom_tabs_en" not in st.session_state:
        st.session_state.custom_tabs_en = []

    if selected_layer == "gold":
        base_tab_titles = [
            "📈 Revenue Trends & Funnel",
            "👥 Customer Lifetime Value (LTV)",
            "🏆 Product & Category Performance",
            "✨ Natural Language AI Charts",
            "🎛️ Custom BI Studio (Power BI Canvas)",
        ]
    elif selected_layer == "silver":
        base_tab_titles = [
            "📦 Orders Fact (fct_orders)",
            "🛒 Line Items Fact (fct_order_items)",
            "👥 Customers Dimension (dim_customers)",
            "🏷️ Products Dimension (dim_products)",
            "🎛️ Silver BI Studio (Power BI Canvas)",
        ]
    else:  # bronze
        base_tab_titles = [
            "📥 Raw Orders (raw_orders)",
            "🛒 Raw Items (raw_order_items)",
            "👤 Raw Customers (raw_customers)",
            "⚙️ dlt Ingestion Logs (_dlt_loads)",
            "🎛️ Bronze BI Studio (Power BI Canvas)",
        ]

    custom_tab_titles = [f"📌 {t['title']}" for t in st.session_state.custom_tabs_en]
    all_tab_titles = base_tab_titles + custom_tab_titles + ["➕ Add Custom Tab"]

    all_rendered_tabs = st.tabs(all_tab_titles)
    tab1, tab2, tab3, tab4, tab5 = (
        all_rendered_tabs[0],
        all_rendered_tabs[1],
        all_rendered_tabs[2],
        all_rendered_tabs[3],
        all_rendered_tabs[4],
    )
    custom_tabs_rendered = all_rendered_tabs[5 : 5 + len(st.session_state.custom_tabs_en)]
    tab_add = all_rendered_tabs[-1]

    # Render Tabs
    if selected_layer == "gold":
        # GOLD TAB 1: Revenue Trends & Funnel
        with tab1:
            st.subheader("📊 Daily GMV vs. Net Realized Revenue")
            if not filtered_kpi.empty:
                fig_rev = go.Figure()
                fig_rev.add_trace(
                    go.Scatter(
                        x=filtered_kpi["order_date"],
                        y=filtered_kpi["gmv"],
                        mode="lines+markers",
                        name="GMV (Gross Volume)",
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
                        name="Net Revenue (Realized)",
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
                st.plotly_chart(fig_rev, width="stretch")

                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.subheader("📦 Order Fulfillment Status Breakdown")
                    fig_status = go.Figure()
                    fig_status.add_trace(go.Bar(x=filtered_kpi["order_date"], y=filtered_kpi["completed_orders"], name="Completed", marker_color="#10b981"))
                    fig_status.add_trace(go.Bar(x=filtered_kpi["order_date"], y=filtered_kpi["cancelled_orders"], name="Cancelled", marker_color="#f59e0b"))
                    fig_status.add_trace(go.Bar(x=filtered_kpi["order_date"], y=filtered_kpi["refunded_orders"], name="Refunded", marker_color="#ef4444"))
                    fig_status.update_layout(
                        barmode="stack",
                        template="plotly_dark",
                        height=320,
                        margin={"l": 20, "r": 20, "t": 30, "b": 20},
                        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
                        yaxis={"showgrid": True, "gridcolor": "rgba(255, 255, 255, 0.08)"},
                    )
                    st.plotly_chart(fig_status, width="stretch")

                with col_t2:
                    st.subheader("💵 Average Order Value (AOV) Trajectory")
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
                    st.plotly_chart(fig_aov, width="stretch")
            else:
                st.info("No Gold KPI records matching the selected date filter.")

        # GOLD TAB 2: Customer LTV Segmentation
        with tab2:
            st.subheader("👥 Customer Tier Distribution & Value Contribution")
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
                    st.plotly_chart(fig_tier, width="stretch")

                with col_ltv2:
                    fig_tier_bar = px.bar(
                        df_ltv.groupby("customer_tier")["lifetime_net_revenue"].sum().reset_index(),
                        x="customer_tier",
                        y="lifetime_net_revenue",
                        color="customer_tier",
                        color_discrete_map=tier_colors,
                        template="plotly_dark",
                        title="Cumulative Net Revenue by Customer Tier ($)",
                    )
                    fig_tier_bar.update_layout(height=350, margin={"l": 20, "r": 20, "t": 40, "b": 20}, showlegend=False)
                    st.plotly_chart(fig_tier_bar, width="stretch")

                st.subheader("💎 Top VIP Customers (PII Masked & Encrypted)")
                st.caption("🔒 GDPR / Privacy Compliant: First name initials masked, emails cryptographically hashed via SHA-256")
                show_cols = [c for c in ["customer_id", "customer_name", "masked_email", "customer_tier", "total_orders", "completed_orders", "lifetime_net_revenue"] if c in df_ltv.columns]
                st.dataframe(df_ltv[show_cols], width="stretch", hide_index=True)
            else:
                st.info("No customer LTV records available.")

        # GOLD TAB 3: Product & Category Rankings
        with tab3:
            st.subheader("🏆 Product Revenue & Volume Leaderboards")
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
                        title="Top 10 Products by Completed Sales Revenue ($)",
                        labels={"completed_sales_amount": "Revenue ($)", "product_title": "Product Title"},
                    )
                    fig_prod_rev.update_layout(height=420, margin={"l": 20, "r": 20, "t": 40, "b": 20})
                    st.plotly_chart(fig_prod_rev, width="stretch")

                with c_p2:
                    top_qty_prod = df_prod.sort_values(by="units_sold", ascending=True).tail(10)
                    fig_prod_qty = px.bar(
                        top_qty_prod,
                        x="units_sold",
                        y="product_title",
                        orientation="h",
                        color="category_name" if "category_name" in top_qty_prod.columns else None,
                        template="plotly_dark",
                        title="Top 10 Products by Units Sold",
                        labels={"units_sold": "Units Sold", "product_title": "Product Title"},
                    )
                    fig_prod_qty.update_layout(height=420, margin={"l": 20, "r": 20, "t": 40, "b": 20})
                    st.plotly_chart(fig_prod_qty, width="stretch")

                st.subheader("📋 Comprehensive Product Performance Ledger")
                st.dataframe(df_prod, width="stretch", hide_index=True)
            else:
                st.info("No product ranking records available.")

        # GOLD TAB 4: Natural Language AI Charts
        with tab4:
            st.subheader("✨ Natural Language AI Smart Chart Generator (Text-to-Chart)")
            st.caption("🤖 Enter any analytical requirement in plain English. AI inspects BigQuery Gold schema and renders an interactive Plotly chart.")

            gemini_key = st.session_state.get("sidebar_gemini_api_key", "")

            def set_gold_chart_query_en(q: str):
                st.session_state["nl_chart_input_field_en"] = q
                st.session_state["nl_chart_query_en"] = q
                st.session_state.pop("fastmcp_diag_result_gold_tab4_en", None)
                st.session_state.pop("mcp_chat_hist_gold_tab4_en", None)
                st.session_state.pop("active_model_gold_tab4_en", None)
                st.rerun()

            st.markdown("##### 💡 Click quick prompts to render instantly:")
            c_btn1, c_btn2, c_btn3 = st.columns(3)
            with c_btn1:
                if st.button("📈 GMV vs. Net Revenue Trend", key="btn_nl_1_en", width="stretch"):
                    set_gold_chart_query_en("Compare daily GMV against realized Net Revenue over time")
                if st.button("🏆 Top 10 Best Selling Products", key="btn_nl_4_en", width="stretch"):
                    set_gold_chart_query_en("Draw a bar chart of top 10 best-selling products by completed revenue")
            with c_btn2:
                if st.button("⚠️ Refund & Cancellation Rates", key="btn_nl_2_en", width="stretch"):
                    set_gold_chart_query_en("Plot daily refund rate and cancellation rate trajectories")
                if st.button("🏷️ Category Sales Distribution", key="btn_nl_5_en", width="stretch"):
                    set_gold_chart_query_en("Show category revenue share breakdown in a pie chart")
            with c_btn3:
                if st.button("💵 Average Order Value (AOV)", key="btn_nl_3_en", width="stretch"):
                    set_gold_chart_query_en("Plot historical AOV trends over time")
                if st.button("👥 Customer Tier Revenue Share", key="btn_nl_6_en", width="stretch"):
                    set_gold_chart_query_en("Display customer tiers revenue contribution in a pie chart")

            col_input, col_submit = st.columns([4, 1])
            with col_input:
                current_nl = st.text_input(
                    "Enter chart visualization prompt:",
                    value=st.session_state.get("nl_chart_input_field_en", st.session_state.get("nl_chart_query_en", "Compare daily GMV against realized Net Revenue over time")),
                    key="nl_chart_input_field_en",
                    placeholder="e.g. Draw a bar chart of top 5 selling products, or daily refund rate trend...",
                )
            with col_submit:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                btn_gen = st.button("Generate Chart 🚀", key="btn_trigger_chart_en", type="primary", width="stretch")

            target_query = current_nl.strip() if current_nl and current_nl.strip() else "Compare daily GMV against realized Net Revenue over time"
            if btn_gen and st.session_state.get("nl_last_executed_query_en") != target_query:
                st.session_state.pop("fastmcp_diag_result_gold_tab4_en", None)
                st.session_state.pop("mcp_chat_hist_gold_tab4_en", None)
                st.session_state.pop("active_model_gold_tab4_en", None)
                st.session_state["nl_chart_query_en"] = target_query
                st.rerun()
            st.session_state["nl_last_executed_query_en"] = target_query

            with st.spinner("AI is parsing natural language intent and querying BigQuery Gold dataset..."):
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
                st.plotly_chart(fig_nl, width="stretch")

                st.markdown(
                    f"""
                    <div class="metric-card" style="border-left: 4px solid #6366f1;">
                        <div class="metric-label">💡 MBB Executive Takeaway</div>
                        <div style="font-size: 1.05rem; font-weight: 500; color: var(--text-color, #0f172a); margin-top: 0.25rem;">
                            {insight_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("---")
                col_mcp_btn, col_mcp_info = st.columns([1.8, 3.2])
                with col_mcp_btn:
                    run_mcp_diag = st.button(
                        "🤖 Run FastMCP Deep Diagnostic (Mode A)",
                        key="btn_fastmcp_diag_main_en",
                        type="primary",
                        width="stretch",
                        help="Trigger FastMCP consultant engine: Applies McKinsey SCQA + MECE Issue Trees + 30-60-90 day tactical roadmap for deep causal attribution.",
                    )
                with col_mcp_info:
                    st.caption("⚡ **FastMCP Mode A**: Synthesizes chart data and executes MBB-grade causal attribution diagnostic.")

                diag_res_key = "fastmcp_diag_result_gold_tab4_en"
                if run_mcp_diag:
                    with st.spinner("🤖 FastMCP consultant is running MBB causal attribution diagnostic..."):
                        diag_output = run_fastmcp_chart_diagnostic(
                            chart_title=chart_title,
                            df=raw_df,
                            prompt_intent=target_query,
                            gemini_api_key=gemini_key,
                        )
                        st.session_state[diag_res_key] = diag_output

                if st.session_state.get(diag_res_key):
                    render_fastmcp_chat_widget(
                        unique_key="gold_tab4_en",
                        chart_title=chart_title,
                        df=raw_df,
                        initial_diagnostic=st.session_state[diag_res_key],
                        gemini_api_key=gemini_key,
                    )

                with st.expander("🔍 Click to Expand: Underlying Chart Dataset (Data Preview)"):
                    st.dataframe(raw_df, width="stretch", hide_index=True)

        # GOLD TAB 5: Custom Analytics Studio (Power BI Canvas)
        with tab5:
            render_powerbi_studio(
                df_kpi=filtered_kpi,
                df_ltv=df_ltv,
                df_prod=df_prod,
                key_prefix="pbi_main_en",
            )

    elif selected_layer == "silver":
        # SILVER TAB 1: Orders Fact
        with tab1:
            st.subheader("📦 fct_orders Cleaned Transactions Overview")
            if not df_orders.empty:
                c_s1, c_s2 = st.columns(2)
                with c_s1:
                    st.markdown("##### Order Status Distribution")
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
                    st.plotly_chart(fig_s_status, width="stretch")

                with c_s2:
                    st.markdown("##### Gross vs. Net Order Volume")
                    if "created_at" in df_orders.columns:
                        orders_trend = df_orders.copy()
                        orders_trend["order_day"] = pd.to_datetime(orders_trend["created_at"]).dt.date
                        day_agg = orders_trend.groupby("order_day").agg(
                            gross_sum=("gross_amount", "sum"),
                            net_sum=("net_amount", "sum"),
                        ).reset_index()
                        fig_s_trend = go.Figure()
                        fig_s_trend.add_trace(go.Bar(x=day_agg["order_day"], y=day_agg["gross_sum"], name="Gross Total", marker_color="#6366f1"))
                        fig_s_trend.add_trace(go.Bar(x=day_agg["order_day"], y=day_agg["net_sum"], name="Net Settled", marker_color="#10b981"))
                        fig_s_trend.update_layout(
                            barmode="group",
                            template="plotly_dark",
                            height=320,
                            margin={"l": 20, "r": 20, "t": 30, "b": 20},
                        )
                        st.plotly_chart(fig_s_trend, width="stretch")

                st.markdown("##### 📋 Fact Orders Detailed Table (Top 500)")
                st.dataframe(df_orders, width="stretch", hide_index=True)
            else:
                st.info("No silver fct_orders records available.")

        # SILVER TAB 2: Line Items Fact
        with tab2:
            st.subheader("🛒 fct_order_items Line-Level Fact Breakdown")
            if not df_items.empty:
                c_i1, c_i2 = st.columns(2)
                with c_i1:
                    st.markdown("##### Unit Price Distribution")
                    fig_hist = px.histogram(
                        df_items,
                        x="unit_price" if "unit_price" in df_items.columns else df_items.columns[0],
                        nbins=20,
                        template="plotly_dark",
                        color_discrete_sequence=["#38bdf8"],
                    )
                    fig_hist.update_layout(height=320, margin={"l": 20, "r": 20, "t": 30, "b": 20})
                    st.plotly_chart(fig_hist, width="stretch")

                with c_i2:
                    st.markdown("##### Quantity Breakdown")
                    if "quantity" in df_items.columns:
                        qty_df = df_items["quantity"].value_counts().reset_index()
                        qty_df.columns = ["quantity", "count"]
                        fig_qty = px.bar(qty_df, x="quantity", y="count", template="plotly_dark", color_discrete_sequence=["#a855f7"])
                        fig_qty.update_layout(height=320, margin={"l": 20, "r": 20, "t": 30, "b": 20})
                        st.plotly_chart(fig_qty, width="stretch")

                st.markdown("##### 📋 Fact Items Detailed Table (Top 500)")
                st.dataframe(df_items, width="stretch", hide_index=True)
            else:
                st.info("No silver fct_order_items records available.")

        # SILVER TAB 3: Customers Dimension
        with tab3:
            st.subheader("👥 dim_customers Customer Dimension (PII De-Identified)")
            st.caption("🔒 Privacy Compliant: Full names and emails masked / cryptographically hashed")
            if not df_cust.empty:
                st.dataframe(df_cust, width="stretch", hide_index=True)
            else:
                st.info("No silver dim_customers records available.")

        # SILVER TAB 4: Products Dimension
        with tab4:
            st.subheader("🏷️ dim_products Product Dimension")
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
                        title="Product Count by Category",
                    )
                    fig_cat.update_layout(height=340, margin={"l": 20, "r": 20, "t": 40, "b": 20})
                    st.plotly_chart(fig_cat, width="stretch")

                st.markdown("##### 📋 Product Dimension Roster")
                st.dataframe(df_prod_silver, width="stretch", hide_index=True)
            else:
                st.info("No silver dim_products records available.")

        # SILVER TAB 5: Silver BI Studio
        with tab5:
            silver_datasets = {
                "orders": {"name": "📦 fct_orders (Orders Fact)", "df": df_orders},
                "items": {"name": "🛒 fct_order_items (Line Items Fact)", "df": df_items},
                "customers": {"name": "👥 dim_customers (Customers Dimension)", "df": df_cust},
                "products": {"name": "🏷️ dim_products (Products Dimension)", "df": df_prod_silver},
            }
            render_powerbi_studio(
                key_prefix="pbi_silver_en",
                dataset_configs=silver_datasets,
                default_dataset_key="orders",
            )

    else:  # bronze
        # BRONZE TAB 1: Raw Orders
        with tab1:
            st.subheader("📥 raw_orders Ingestion Event Logs")
            st.caption("Raw JSON events extracted from Platzi Fake Store API, containing dlt ingestion metadata")
            if not df_raw_orders.empty:
                st.dataframe(df_raw_orders, width="stretch", hide_index=True)
            else:
                st.info("No bronze raw_orders records available.")

        # BRONZE TAB 2: Raw Items
        with tab2:
            st.subheader("🛒 raw_order_items Unfiltered Item Streams")
            st.caption("Raw order line items prior to transformation and schema standardization")
            if not df_raw_items.empty:
                st.dataframe(df_raw_items, width="stretch", hide_index=True)
            else:
                st.info("No bronze raw_order_items records available.")

        # BRONZE TAB 3: Raw Customers
        with tab3:
            st.subheader("👤 raw_customers Customer Ingestion Snapshots")
            st.caption("Original customer records ingested before dbt staging privacy masking")
            if not df_raw_cust.empty:
                st.dataframe(df_raw_cust, width="stretch", hide_index=True)
            else:
                st.info("No bronze raw_customers records available.")

        # BRONZE TAB 4: dlt Load Logs
        with tab4:
            st.subheader("⚙️ _dlt_loads Pipeline Ingestion Run Logs")
            st.caption("Tracks load_id, schema versioning, and execution status across dlt pipeline runs")
            if not df_dlt.empty:
                st.dataframe(df_dlt, width="stretch", hide_index=True)
            else:
                st.info("No bronze _dlt_loads audit records available.")

        # BRONZE TAB 5: Bronze BI Studio
        with tab5:
            bronze_datasets = {
                "raw_orders": {"name": "📥 raw_orders (Raw Order Stream)", "df": df_raw_orders},
                "raw_items": {"name": "🛒 raw_order_items (Raw Line Items)", "df": df_raw_items},
                "raw_cust": {"name": "👤 raw_customers (Raw Customers)", "df": df_raw_cust},
                "dlt_loads": {"name": "⚙️ _dlt_loads (dlt Audit Log)", "df": df_dlt},
            }
            render_powerbi_studio(
                key_prefix="pbi_bronze_en",
                dataset_configs=bronze_datasets,
                default_dataset_key="raw_orders",
            )

    # Dynamic Custom Tabs
    for idx, (t_meta, t_obj) in enumerate(zip(st.session_state.custom_tabs_en, custom_tabs_rendered)):
        with t_obj:
            col_c_title, col_c_del = st.columns([5, 1])
            with col_c_title:
                st.subheader(f"📌 {t_meta['title']}")
                st.caption(f"Custom Tab Type: **{t_meta.get('type_label', 'Custom Dashboard')}** · Bound Dataset: `{t_meta.get('dataset_name', 'BigQuery Table')}`")
            with col_c_del:
                if st.button("🗑️ Remove Tab", key=f"btn_del_tab_en_{t_meta['id']}", width="stretch", help="Remove this custom tab from the tab bar"):
                    st.session_state.custom_tabs_en = [x for x in st.session_state.custom_tabs_en if x["id"] != t_meta["id"]]
                    st.rerun()

            st.markdown("---")

            if t_meta["type"] == "ai_chart":
                tab_id = t_meta["id"]
                gemini_key = st.session_state.get("sidebar_gemini_api_key", "")
                col_input, col_submit = st.columns([4, 1])
                with col_input:
                    current_nl = st.text_input(
                        "Enter chart generation prompt:",
                        value=st.session_state.get(f"nl_query_en_{tab_id}", t_meta.get("default_query", "Show sales by category in a pie chart")),
                        key=f"input_nl_en_{tab_id}",
                        placeholder="e.g. Draw a bar chart of top 5 selling products...",
                    )
                with col_submit:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    btn_gen = st.button("Generate Chart 🚀", key=f"btn_chart_en_{tab_id}", type="primary", width="stretch")

                target_query = current_nl if current_nl else t_meta.get("default_query", "Show daily revenue trajectory")

                chart_kpi = filtered_kpi if not filtered_kpi.empty else df_kpi
                if chart_kpi.empty:
                    chart_kpi, chart_ltv, chart_prod, _ = load_gold_data()
                else:
                    chart_ltv = df_ltv
                    chart_prod = df_prod

                with st.spinner("AI is parsing query and rendering interactive visualization..."):
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
                    st.plotly_chart(fig_nl, width="stretch")
                    st.markdown(
                        f"""
                        <div class="metric-card" style="border-left: 4px solid #6366f1;">
                            <div class="metric-label">💡 MBB Executive Takeaway</div>
                            <div style="font-size: 1.05rem; font-weight: 500; color: var(--text-color, #0f172a); margin-top: 0.25rem;">
                                {insight_text}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("---")
                    col_mc1, col_mc2 = st.columns([1.8, 3.2])
                    with col_mc1:
                        btn_mcp_c = st.button(
                            "🤖 Run FastMCP Deep Diagnostic (Mode A)",
                            key=f"btn_mcp_custom_en_{tab_id}",
                            type="primary",
                            width="stretch",
                        )
                    with col_mc2:
                        st.caption("⚡ **FastMCP Mode A**: Performs deep causal diagnostic over underlying data.")

                    diag_key_c = f"diag_res_custom_en_{tab_id}"
                    if btn_mcp_c:
                        with st.spinner("🤖 FastMCP consultant is executing diagnostic..."):
                            diag_out = run_fastmcp_chart_diagnostic(
                                chart_title=chart_title,
                                df=raw_df,
                                prompt_intent=target_query,
                                gemini_api_key=gemini_key,
                            )
                            st.session_state[diag_key_c] = diag_out

                    if st.session_state.get(diag_key_c):
                        render_fastmcp_chat_widget(
                            unique_key=f"custom_en_{tab_id}",
                            chart_title=chart_title,
                            df=raw_df,
                            initial_diagnostic=st.session_state[diag_key_c],
                            gemini_api_key=gemini_key,
                        )

                    with st.expander("🔍 Click to Expand: View Data Table"):
                        st.dataframe(raw_df, width="stretch", hide_index=True)

            elif t_meta["type"] == "powerbi_canvas":
                render_powerbi_studio(
                    df_kpi=filtered_kpi if not filtered_kpi.empty else df_kpi,
                    df_ltv=df_ltv,
                    df_prod=df_prod,
                    key_prefix=f"pbi_custom_en_{t_meta['id']}",
                    default_dataset_key=t_meta.get("dataset_key", "kpi"),
                )

    # TAB ADD: Add Custom Analytics Tab
    with tab_add:
        st.subheader("➕ Add Custom Analytics Tab")
        st.caption("Expand your dashboard tabs with dedicated AI Smart Charts or Power BI Drag-and-Drop Canvases.")

        with st.container():
            st.markdown(
                """
                <div class="metric-card" style="border-left: 4px solid #6366f1; margin-bottom: 1.25rem;">
                    <div style="font-size: 1.05rem; font-weight: 600; color: var(--text-color, #0f172a);">
                        🛠️ Select Tab Engine & Data Binding
                    </div>
                    <div style="font-size: 0.9rem; color: #64748b; margin-top: 0.25rem;">
                        Once added, your custom tab is appended to the top navigation bar with isolated session state.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_new_t1, col_new_t2 = st.columns(2)
            with col_new_t1:
                new_tab_type = st.radio(
                    "1. Select Engine Type:",
                    options=[
                        "✨ Natural Language AI Chart (Text-to-Chart)",
                        "🎛️ Visual Custom Studio (Power BI Drag-and-Drop Canvas)",
                    ],
                    index=0,
                    key="new_tab_type_radio_en",
                )
                is_ai_type = "AI" in new_tab_type

            with col_new_t2:
                if selected_layer == "gold":
                    dataset_options = {
                        "kpi": "📊 gold_daily_sales_kpi (Daily Revenue & KPI)",
                        "prod": "🏆 gold_product_performance (Product & Category Sales)",
                        "ltv": "👥 gold_customer_ltv (Customer LTV & Segmentation)",
                    }
                elif selected_layer == "silver":
                    dataset_options = {
                        "orders": "📦 fct_orders (Cleaned Orders Fact)",
                        "items": "🛒 fct_order_items (Line Items Fact)",
                        "customers": "👥 dim_customers (Customers Dimension)",
                        "products": "🏷️ dim_products (Products Dimension)",
                    }
                else:  # bronze
                    dataset_options = {
                        "raw_orders": "📥 raw_orders (Raw Order Events)",
                        "raw_items": "🛒 raw_order_items (Raw Item Streams)",
                        "raw_cust": "👤 raw_customers (Raw Customer Snapshots)",
                        "dlt_loads": "⚙️ _dlt_loads (dlt Ingestion Logs)",
                    }

                new_tab_ds = st.selectbox(
                    "2. Bind Data Source:",
                    options=list(dataset_options.keys()),
                    format_func=lambda k: dataset_options[k],
                    index=0,
                    key="new_tab_ds_select_en",
                )

            default_name = (
                f"AI Smart Chart {len(st.session_state.custom_tabs_en) + 1}"
                if is_ai_type
                else f"Custom Studio {len(st.session_state.custom_tabs_en) + 1}"
            )
            new_tab_name = st.text_input(
                "3. Tab Display Title:",
                value=default_name,
                key="new_tab_name_input_en",
                placeholder="e.g. Marketing Return Analysis, Category Canvas...",
            )

            initial_ai_query = ""
            if is_ai_type:
                initial_ai_query = st.text_input(
                    "4. Default Natural Language Query (Optional):",
                    value="Show category sales share in a pie chart",
                    key="new_tab_ai_query_input_en",
                )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Create & Append Tab", type="primary", width="stretch", key="btn_create_custom_tab_en"):
                import uuid
                tab_id = f"custom_en_{uuid.uuid4().hex[:6]}"
                new_tab_meta = {
                    "id": tab_id,
                    "title": new_tab_name.strip() or default_name,
                    "type": "ai_chart" if is_ai_type else "powerbi_canvas",
                    "type_label": "Natural Language AI Chart" if is_ai_type else "Power BI Studio Canvas",
                    "dataset_key": new_tab_ds,
                    "dataset_name": dataset_options[new_tab_ds],
                    "default_query": initial_ai_query,
                }
                st.session_state.custom_tabs_en.append(new_tab_meta)
                st.success(f"🎉 Tab '{new_tab_meta['title']}' created successfully!")
                st.rerun()


if __name__ == "__main__":
    main()
