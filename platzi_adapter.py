"""Platzi E-Commerce Domain Adapter.

Implements BaseCockpitAdapter for the Platzi Retail E-Commerce Lakehouse.
Provides domain-specific KPI formulas, BigQuery Medallion queries, and FastMCP tools.
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Any, Callable

import pandas as pd
import streamlit as st
from cockpit_core import BaseCockpitAdapter, KPICardSpec, MedallionTabSpec
from fastmcp_diagnostic import (
    DEFAULT_SYSTEM_PROMPT_EN,
    DEFAULT_SYSTEM_PROMPT_ZH,
)
from mcp_server.server import (
    get_customer_metrics,
    get_daily_sales_kpi,
    get_top_products,
)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "de-consulting-508822")


def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize DataFrame returned by BigQuery client to avoid type incompatibilities."""
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
            sample_val = (
                df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            )
            if sample_val is not None:
                if isinstance(sample_val, Decimal):
                    df[col] = df[col].astype(float)
                elif hasattr(sample_val, "isoformat") or hasattr(
                    sample_val, "strftime"
                ):
                    try:
                        df[col] = pd.to_datetime(df[col])
                    except Exception:
                        pass
    return df


class PlatziAdapter(BaseCockpitAdapter):
    """Domain Adapter for Platzi E-Commerce Analytics Platform."""

    @property
    def project_id(self) -> str:
        return PROJECT_ID

    @property
    def brand_title(self) -> str:
        return "Platzi E-Commerce Executive Intelligence"

    @property
    def brand_icon(self) -> str:
        return "🛒"

    @property
    def brand_badge_text(self) -> str:
        return "AI Operations Lakehouse · 100MB FinOps"

    @property
    def default_language(self) -> str:
        return "zh"

    @property
    def default_system_prompt_zh(self) -> str:
        return DEFAULT_SYSTEM_PROMPT_ZH

    @property
    def default_system_prompt_en(self) -> str:
        return DEFAULT_SYSTEM_PROMPT_EN

    @property
    def quick_diagnosis_questions_zh(self) -> list[str]:
        return [
            "📊 每日 GMV 與淨營收走勢診斷",
            "🏆 Top 3 熱銷品及品類佔比分析",
            "⚠️ 取消率與退款率獲利漏斗分析",
        ]

    @property
    def quick_diagnosis_questions_en(self) -> list[str]:
        return [
            "📊 Daily GMV vs. Net Revenue Diagnostic",
            "🏆 Top 3 Products & Category Analysis",
            "⚠️ Refund & Cancellation Funnel Review",
        ]

    @property
    def kpi_cards(self) -> list[KPICardSpec]:
        return [
            KPICardSpec(
                key="gmv",
                title_zh="商品交易總額 (GMV)",
                title_en="Gross Merchandise Value",
                metric_formula="SUM(gross_amount)",
                target_rule="≥ $250,000",
                accent_color="#6366f1",
                calculate=self._calc_gmv,
            ),
            KPICardSpec(
                key="net_rev",
                title_zh="實質淨營收 (Net Rev)",
                title_en="Net Realized Revenue",
                metric_formula="SUM(completed_net_amount)",
                target_rule="≥ 85% Realization",
                accent_color="#10b981",
                calculate=self._calc_net_revenue,
            ),
            KPICardSpec(
                key="orders",
                title_zh="已完成訂單數 (Completed)",
                title_en="Completed Orders",
                metric_formula="COUNTIF(status='completed')",
                target_rule="≥ 1,500 Orders",
                accent_color="#3b82f6",
                calculate=self._calc_completed_orders,
            ),
            KPICardSpec(
                key="customers",
                title_zh="有效購買會員數 (Active)",
                title_en="Active Customers",
                metric_formula="COUNT(DISTINCT customer_id)",
                target_rule="≥ 200 Accounts",
                accent_color="#f59e0b",
                calculate=self._calc_active_customers,
            ),
        ]

    def _calc_gmv(self, data: dict[str, pd.DataFrame]) -> dict[str, Any]:
        df = data.get("kpi", pd.DataFrame())
        gmv_val = (
            float(df["gmv"].sum()) if not df.empty and "gmv" in df.columns else 0.0
        )
        return {
            "value": f"${gmv_val:,.2f}",
            "status": "normal" if gmv_val >= 250000 else "warning",
        }

    def _calc_net_revenue(self, data: dict[str, pd.DataFrame]) -> dict[str, Any]:
        df = data.get("kpi", pd.DataFrame())
        if df.empty or "net_revenue" not in df.columns or "gmv" not in df.columns:
            return {"value": "$0.00 (0.0%)", "status": "warning"}
        net_val = float(df["net_revenue"].sum())
        gmv_val = float(df["gmv"].sum())
        ratio = (net_val / gmv_val * 100.0) if gmv_val > 0 else 0.0
        return {
            "value": f"${net_val:,.2f} ({ratio:.1f}%)",
            "status": "normal" if ratio >= 85.0 else "warning",
        }

    def _calc_completed_orders(self, data: dict[str, pd.DataFrame]) -> dict[str, Any]:
        df = data.get("kpi", pd.DataFrame())
        orders = (
            int(df["completed_orders"].sum())
            if not df.empty and "completed_orders" in df.columns
            else 0
        )
        return {
            "value": f"{orders:,}",
            "status": "normal" if orders >= 1500 else "warning",
        }

    def _calc_active_customers(self, data: dict[str, pd.DataFrame]) -> dict[str, Any]:
        df = data.get("customers", pd.DataFrame())
        cust_cnt = len(df) if not df.empty else 0
        return {
            "value": f"{cust_cnt:,}",
            "status": "normal" if cust_cnt >= 200 else "warning",
        }

    def load_domain_data(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, pd.DataFrame]:
        """Load datasets from BigQuery with local test mock fallback."""
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=self.project_id)
            df_kpi = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_gold.gold_daily_sales_kpi` ORDER BY order_date"
            ).to_dataframe()
            df_ltv = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_gold.gold_customer_ltv` ORDER BY lifetime_net_revenue DESC"
            ).to_dataframe()
            df_prod = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_gold.gold_product_performance` ORDER BY completed_sales_amount DESC"
            ).to_dataframe()

            df_orders = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_silver.fct_orders` ORDER BY created_at DESC LIMIT 500"
            ).to_dataframe()
            df_items = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_silver.fct_order_items` LIMIT 500"
            ).to_dataframe()
            df_cust = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_silver.dim_customers` LIMIT 500"
            ).to_dataframe()
            df_prod_silver = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_silver.dim_products` LIMIT 500"
            ).to_dataframe()

            df_raw_orders = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_bronze.raw_orders` LIMIT 200"
            ).to_dataframe()
            df_raw_items = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_bronze.raw_order_items` LIMIT 200"
            ).to_dataframe()
            df_raw_cust = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_bronze.raw_customers` LIMIT 200"
            ).to_dataframe()
            df_dlt = client.query(
                f"SELECT * FROM `{self.project_id}.platzi_bronze._dlt_loads` ORDER BY inserted_at DESC LIMIT 50"
            ).to_dataframe()

            return {
                "kpi": _sanitize_df(df_kpi),
                "customers": _sanitize_df(df_ltv),
                "products": _sanitize_df(df_prod),
                "fct_orders": _sanitize_df(df_orders),
                "fct_order_items": _sanitize_df(df_items),
                "dim_customers": _sanitize_df(df_cust),
                "dim_products": _sanitize_df(df_prod_silver),
                "raw_orders": _sanitize_df(df_raw_orders),
                "raw_order_items": _sanitize_df(df_raw_items),
                "raw_customers": _sanitize_df(df_raw_cust),
                "_dlt_loads": _sanitize_df(df_dlt),
            }
        except Exception:
            # Fallback mock data for test environments & CI
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
                    "masked_email": [
                        "a***@platzi.com",
                        "b***@platzi.com",
                        "c***@platzi.com",
                    ],
                    "customer_tier": ["Platinum", "Gold", "Silver"],
                    "total_orders": [10, 5, 2],
                    "completed_orders": [10, 5, 2],
                    "lifetime_net_revenue": [1000.0, 500.0, 200.0],
                }
            )
            return {
                "kpi": mock_kpi,
                "customers": mock_ltv,
                "products": mock_prod,
                "fct_orders": pd.DataFrame(
                    {"order_id": [1, 2], "gross_amount": [100.0, 250.0]}
                ),
                "fct_order_items": pd.DataFrame(
                    {"item_id": [1, 2], "quantity": [1, 2]}
                ),
                "dim_customers": pd.DataFrame(
                    {"customer_id": [101, 102], "customer_name": ["Alice", "Bob"]}
                ),
                "dim_products": pd.DataFrame(
                    {"product_id": [1, 2], "product_title": ["Product 1", "Product 2"]}
                ),
                "raw_orders": pd.DataFrame({"order_id": [1, 2]}),
                "raw_order_items": pd.DataFrame({"item_id": [1, 2]}),
                "raw_customers": pd.DataFrame({"customer_id": [101, 102]}),
                "_dlt_loads": pd.DataFrame(
                    {"load_id": ["load_1", "load_2"], "status": [0, 0]}
                ),
            }

    def get_fastmcp_tools(self) -> list[Callable]:
        return [get_daily_sales_kpi, get_top_products, get_customer_metrics]

    @property
    def medallion_layers(self) -> dict[str, Any]:
        """Define the Medallion view tabs for Platzi E-Commerce."""
        return {
            "gold": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="tab_sales_kpi",
                        title_zh="📊 執行長營收與獲利總覽",
                        title_en="📊 Revenue & Profitability",
                        render_content=self._render_gold_kpi_tab,
                    ),
                    MedallionTabSpec(
                        tab_id="tab_products",
                        title_zh="🏷️ 商品類別與熱銷品排行",
                        title_en="🏷️ Product Performance",
                        render_content=self._render_gold_products_tab,
                    ),
                    MedallionTabSpec(
                        tab_id="tab_customers",
                        title_zh="👥 顧客分群與價值貢獻",
                        title_en="👥 Customer Cohorts",
                        render_content=self._render_gold_customers_tab,
                    ),
                ]
            },
            "silver": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="tab_fct_orders",
                        title_zh="📦 訂單事實表 (fct_orders)",
                        title_en="📦 fct_orders",
                        render_content=lambda d, en, a: st.dataframe(
                            d.get("fct_orders", pd.DataFrame()),
                            use_container_width=True,
                        ),
                    ),
                    MedallionTabSpec(
                        tab_id="tab_dim_products",
                        title_zh="🏷️ 商品維度表 (dim_products)",
                        title_en="🏷️ dim_products",
                        render_content=lambda d, en, a: st.dataframe(
                            d.get("dim_products", pd.DataFrame()),
                            use_container_width=True,
                        ),
                    ),
                ]
            },
            "bronze": {
                "tabs": [
                    MedallionTabSpec(
                        tab_id="tab_raw_orders",
                        title_zh="📥 原始訂單日誌 (raw_orders)",
                        title_en="📥 raw_orders",
                        render_content=lambda d, en, a: st.dataframe(
                            d.get("raw_orders", pd.DataFrame()),
                            use_container_width=True,
                        ),
                    ),
                    MedallionTabSpec(
                        tab_id="tab_dlt_loads",
                        title_zh="⚡ dlt 同步歷史 (_dlt_loads)",
                        title_en="⚡ _dlt_loads",
                        render_content=lambda d, en, a: st.dataframe(
                            d.get("_dlt_loads", pd.DataFrame()),
                            use_container_width=True,
                        ),
                    ),
                ]
            },
        }

    def _render_gold_kpi_tab(
        self, data: dict[str, pd.DataFrame], is_en: bool, adapter: Any
    ) -> None:
        import plotly.graph_objects as go

        df = data.get("kpi", pd.DataFrame())
        if df.empty or "order_date" not in df.columns:
            st.info("No KPI data available.")
            return

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["order_date"],
                y=df["gmv"],
                name="GMV ($)",
                line={"color": "#6366f1", "width": 3},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["order_date"],
                y=df["net_revenue"],
                name="Net Revenue ($)",
                line={"color": "#10b981", "width": 3},
            )
        )
        fig.update_layout(
            title="Daily GMV vs. Net Revenue ($)"
            if is_en
            else "每日 GMV 總銷售額 vs. 實質淨營收對比走勢圖 ($)",
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    def _render_gold_products_tab(
        self, data: dict[str, pd.DataFrame], is_en: bool, adapter: Any
    ) -> None:
        import plotly.express as px

        df = data.get("products", pd.DataFrame())
        if df.empty or "product_title" not in df.columns:
            st.info("No Product data available.")
            return

        sub = df.head(10).copy()
        fig = px.bar(
            sub,
            x="completed_sales_amount",
            y="product_title",
            orientation="h",
            title="Top 10 Products by Sales ($)"
            if is_en
            else "熱銷商品排行榜 Top 10 ($)",
            template="plotly_white",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    def _render_gold_customers_tab(
        self, data: dict[str, pd.DataFrame], is_en: bool, adapter: Any
    ) -> None:
        import plotly.express as px

        df = data.get("customers", pd.DataFrame())
        if df.empty or "customer_tier" not in df.columns:
            st.info("No Customer cohort data available.")
            return

        tier_counts = df["customer_tier"].value_counts().reset_index()
        tier_counts.columns = ["customer_tier", "count"]
        fig = px.pie(
            tier_counts,
            names="customer_tier",
            values="count",
            title="Customer Tier Distribution" if is_en else "會員等級顧客價值分佈",
            template="plotly_white",
            hole=0.4,
        )
        st.plotly_chart(fig, use_container_width=True)
