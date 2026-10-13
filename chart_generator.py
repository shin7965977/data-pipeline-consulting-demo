"""Natural Language AI Chart Generation Engine (Text-to-Visualization).

Decoupled from Streamlit UI runtime for clean architectural separation,
resilience during test execution, and headless CI execution.
"""

from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def generate_chart_from_nl(
    prompt: str,
    df_kpi: pd.DataFrame,
    df_prod: pd.DataFrame,
    df_ltv: pd.DataFrame,
    gemini_api_key: str = "",
    language: str = "zh",
) -> tuple[go.Figure | None, str, str, pd.DataFrame]:
    """Analyze natural language prompt and generate an interactive Plotly chart with consulting insights.

    Supports bilingual rendering (Traditional Chinese and English) with automatic language detection.
    Returns: (fig, title, insight_text, raw_df)
    """
    clean_prompt = prompt.strip().lower()

    # Determine language: explicit parameter or English text patterns
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in prompt)
    is_en = (
        language.lower() == "en"
        or "in english" in clean_prompt
        or "english" in clean_prompt
        or (
            not has_cjk
            and any(
                w in clean_prompt
                for w in [
                    "chart",
                    "sales",
                    "revenue",
                    "product",
                    "show me",
                    "plot",
                    "category",
                    "trend",
                    "customer",
                    "order",
                    "refund",
                    "cancel",
                    "gmv",
                    "aov",
                    "tier",
                    "ltv",
                    "bar",
                    "pie",
                    "line",
                ]
            )
        )
    )

    # Step 0: Domain Relevance Guardrail - strictly reject non-ecommerce or unrelated queries
    BUSINESS_CHART_KEYWORDS = [
        "銷售",
        "營收",
        "gmv",
        "訂單",
        "商品",
        "客戶",
        "ltv",
        "業績",
        "退款",
        "會員",
        "暢銷",
        "買",
        "賣",
        "kpi",
        "vip",
        "排行",
        "利潤",
        "金額",
        "單價",
        "aov",
        "平台",
        "電商",
        "庫存",
        "品類",
        "tier",
        "platinum",
        "gold",
        "silver",
        "bronze",
        "數據",
        "指標",
        "概況",
        "圖",
        "走勢",
        "趨勢",
        "圓餅",
        "長條",
        "柱狀",
        "散佈",
        "佔比",
        "比較",
        "分析",
        "chart",
        "plot",
        "revenue",
        "sales",
        "order",
        "product",
        "customer",
        "履約",
        "取消",
        "完成",
        "均額",
        "流失",
        "回購",
        "消費",
        "折扣",
        "折線",
        "關係",
        "分佈",
        "categories",
        "category",
        "show",
        "bar",
        "pie",
        "line",
    ]
    if not any(kw in clean_prompt for kw in BUSINESS_CHART_KEYWORDS):
        if is_en:
            return (
                None,
                "⚠️ Domain Scope Guardrail",
                (
                    "Sorry, I am dedicated strictly as the **Platzi E-Commerce Analytics Advisor**.\n\n"
                    f'Your query *"{prompt}"* is unrelated to Platzi e-commerce operations, sales performance, products, or customer metrics, and cannot generate a chart.\n\n'
                    "💡 **Suggested business questions you can ask:**\n"
                    '- 📈 *"Show daily GMV vs Net Revenue comparison trend"*\n'
                    '- 🏆 *"Display top 10 best-selling products in a bar chart"*\n'
                    '- ⚠️ *"Plot daily cancellation and refund rate monitoring"*\n'
                    '- 👥 *"Show revenue contribution by customer tier in a pie chart"*'
                ),
                pd.DataFrame(),
            )
        return (
            None,
            "⚠️ 業務範疇約束提醒",
            (
                "抱歉，我是專屬於 **Platzi 電商數據分析顧問**。\n\n"
                f"您輸入的提問 *「{prompt}」* 與本電商營運、銷售績效、商品或顧客等業務數據無關，因此無法為您生成圖表。\n\n"
                "💡 **建議您可以提問與業務數據相關之問題，例如：**\n"
                "- 📈 *「請畫出每日 GMV 與實質淨營收的對比走勢圖」*\n"
                "- 🏆 *「用長條圖呈現銷售額前 10 大熱銷商品」*\n"
                "- ⚠️ *「畫出每日退款率與取消率的監控走勢圖」*\n"
                "- 👥 *「幫我用圓餅圖呈現不同會員等級 (Tier) 的營收貢獻」*"
            ),
            pd.DataFrame(),
        )

    # Step 1: Check if Gemini is available for AI-powered visualization reasoning
    gemini_spec = None
    if gemini_api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_api_key)
            lang_desc = "in English" if is_en else "in Traditional Chinese"
            system_instruction = (
                "You are an expert Data Visualization and MBB Strategy Consultant dedicated strictly and exclusively to Platzi E-Commerce analytics. "
                "The user will ask for a chart or business insight in natural language.\n"
                "If the user's prompt is NOT related to Platzi E-Commerce business, sales, orders, products, customers, KPIs, or chart visualization "
                "(e.g. general chat, politics, entertainment, philosophy, history, coding unrelated to this app), "
                'you MUST respond with: {"is_irrelevant": true}\n\n'
                "Otherwise, analyze the available BigQuery datasets:\n"
                "1. 'kpi' columns: order_date, total_orders, completed_orders, cancelled_orders, refunded_orders, gmv, net_revenue, aov, cancellation_rate, refund_rate\n"
                "2. 'products' columns: product_id, product_title, category_name, completed_sales_amount, units_sold, unit_price\n"
                "3. 'customers' columns: customer_id, customer_name, customer_tier, total_orders, completed_orders, lifetime_net_revenue\n\n"
                "Respond ONLY with a valid JSON object (no markdown quotes, no explanations):\n"
                "{\n"
                '  "is_irrelevant": false,\n'
                '  "dataset": "kpi" | "products" | "customers",\n'
                '  "chart_type": "line" | "bar" | "pie" | "scatter" | "area",\n'
                '  "x": "column_name",\n'
                '  "y": ["col1", "col2"] or "col1",\n'
                '  "color": "col" or null,\n'
                f'  "title": "Clear descriptive chart title {lang_desc}",\n'
                '  "top_n": 10 or null,\n'
                f'  "insight": "1-2 sentences of MBB-level business insight {lang_desc}"\n'
                "}"
            )
            import streamlit as st

            from fastmcp_diagnostic import get_gemini_candidate_models

            pref_m = st.session_state.get("gemini_selected_model", "auto")
            candidates = get_gemini_candidate_models(client, preferred_model=pref_m)

            for candidate in candidates:
                try:
                    res = client.models.generate_content(
                        model=candidate,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.1,
                            response_mime_type="application/json",
                        ),
                    )
                    if res and res.text:
                        gemini_spec = json.loads(res.text)
                        break
                except Exception as e:  # noqa: BLE001
                    err_s = str(e)
                    if any(
                        k in err_s
                        for k in [
                            "503",
                            "UNAVAILABLE",
                            "429",
                            "RESOURCE_EXHAUSTED",
                            "high demand",
                            "404",
                            "NOT_FOUND",
                            "overloaded",
                            "Spikes in demand",
                        ]
                    ):
                        continue
                    break
        except Exception:  # noqa: BLE001
            gemini_spec = None

    # Step 2: If Gemini returned a valid spec, check relevance and render using that spec
    if gemini_spec and isinstance(gemini_spec, dict):
        if gemini_spec.get("is_irrelevant"):
            if is_en:
                return (
                    None,
                    "⚠️ Domain Scope Guardrail",
                    (
                        "Sorry, I am dedicated strictly as the **Platzi E-Commerce Analytics Advisor**.\n\n"
                        f'Your query *"{prompt}"* is unrelated to Platzi e-commerce operations, sales performance, products, or customer metrics, and cannot generate a chart.\n\n'
                        "💡 **Suggested business questions you can ask:**\n"
                        '- 📈 *"Show daily GMV vs Net Revenue comparison trend"*\n'
                        '- 🏆 *"Display top 10 best-selling products in a bar chart"*\n'
                        '- ⚠️ *"Plot daily cancellation and refund rate monitoring"*\n'
                        '- 👥 *"Show revenue contribution by customer tier in a pie chart"*'
                    ),
                    pd.DataFrame(),
                )
            return (
                None,
                "⚠️ 業務範疇約束提醒",
                (
                    "抱歉，我是專屬於 **Platzi 電商數據分析顧問**。\n\n"
                    f"您輸入的提問 *「{prompt}」* 與本電商營運、銷售績效、商品或顧客等業務數據無關，因此無法為您生成圖表。\n\n"
                    "💡 **建議您可以提問與業務數據相關之問題，例如：**\n"
                    "- 📈 *「請畫出每日 GMV 與實質淨營收的對比走勢圖」*\n"
                    "- 🏆 *「用長條圖呈現銷售額前 10 大熱銷商品」*\n"
                    "- ⚠️ *「畫出每日退款率與取消率的監控走勢圖」*\n"
                    "- 👥 *「幫我用圓餅圖呈現不同會員等級 (Tier) 的營收貢獻」*"
                ),
                pd.DataFrame(),
            )

        ds_name = gemini_spec.get("dataset")
        c_type = gemini_spec.get("chart_type", "line")
        x_col = gemini_spec.get("x")
        y_col = gemini_spec.get("y")
        title = gemini_spec.get("title", prompt)
        insight = gemini_spec.get(
            "insight",
            (
                "AI has successfully synthesized the interactive visualization."
                if is_en
                else "AI 已依據您的需求完成動態可視化圖表。"
            ),
        )

        if ds_name == "products":
            target_df = df_prod.copy()
            if gemini_spec.get("top_n"):
                sort_col = y_col[0] if isinstance(y_col, list) else y_col
                if sort_col in target_df.columns:
                    target_df = target_df.sort_values(
                        by=sort_col, ascending=False
                    ).head(gemini_spec["top_n"])
        elif ds_name == "customers":
            target_df = df_ltv.copy()
        else:
            target_df = df_kpi.copy()

        fig = None
        if c_type == "line":
            fig = px.line(
                target_df,
                x=x_col,
                y=y_col,
                markers=True,
                title=title,
                template="plotly_dark",
            )
        elif c_type == "bar":
            fig = px.bar(
                target_df,
                x=x_col,
                y=y_col,
                title=title,
                template="plotly_dark",
                color=gemini_spec.get("color"),
            )
        elif c_type == "pie":
            fig = px.pie(
                target_df,
                names=x_col,
                values=y_col if isinstance(y_col, str) else y_col[0],
                hole=0.45,
                title=title,
                template="plotly_dark",
            )
        elif c_type == "scatter":
            fig = px.scatter(
                target_df,
                x=x_col,
                y=y_col,
                color=gemini_spec.get("color"),
                title=title,
                template="plotly_dark",
            )
        elif c_type == "area":
            fig = px.area(
                target_df, x=x_col, y=y_col, title=title, template="plotly_dark"
            )

        if fig:
            fig.update_layout(margin={"l": 20, "r": 20, "t": 40, "b": 20})
            return fig, title, insight, target_df

    # Step 3: Intelligent Deterministic Rule-Based Fallback (Works 100% offline & without API Key)
    # Check Product dataset keywords
    if any(
        kw in clean_prompt
        for kw in [
            "商品",
            "產品",
            "品類",
            "類別",
            "category",
            "categories",
            "product",
            "products",
            "暢銷",
            "熱銷",
            "庫存",
        ]
    ):
        if any(kw in clean_prompt for kw in ["品類", "類別", "category", "categories"]):
            cat_df = (
                df_prod.groupby("category_name")[
                    ["completed_sales_amount", "units_sold"]
                ]
                .sum()
                .reset_index()
            )
            cat_df = cat_df.sort_values(by="completed_sales_amount", ascending=False)
            if any(
                kw in clean_prompt for kw in ["圓餅", "佔比", "比例", "分佈", "pie"]
            ):
                fig = px.pie(
                    cat_df,
                    names="category_name",
                    values="completed_sales_amount",
                    title=(
                        "Revenue Breakdown by Product Category"
                        if is_en
                        else "各商品品類 (Category) 銷售金額分佈佔比"
                    ),
                    hole=0.45,
                    template="plotly_dark",
                )
                title = (
                    "Product Category Sales Share Pie Chart"
                    if is_en
                    else "各商品品類銷售佔比圓餅圖"
                )
                insight = (
                    f"Top category is [{cat_df.iloc[0]['category_name']}], generating total revenue of ${cat_df.iloc[0]['completed_sales_amount']:,.2f}."
                    if is_en
                    else f"主力品類為【{cat_df.iloc[0]['category_name']}】，貢獻了全站最高銷售金額 (${cat_df.iloc[0]['completed_sales_amount']:,.2f})。"
                )
            else:
                fig = px.bar(
                    cat_df,
                    x="category_name",
                    y="completed_sales_amount",
                    color="completed_sales_amount",
                    title=(
                        "Total Revenue Ranking by Product Category"
                        if is_en
                        else "各商品品類 (Category) 總營收排行榜"
                    ),
                    template="plotly_dark",
                    labels={
                        "completed_sales_amount": (
                            "Total Revenue ($)" if is_en else "銷售總額 ($)"
                        ),
                        "category_name": "Category" if is_en else "品類名稱",
                    },
                    color_continuous_scale="Purples",
                )
                title = (
                    "Product Category Total Revenue Bar Chart"
                    if is_en
                    else "各商品品類總營收長條圖"
                )
                insight = (
                    f"Highest revenue category is [{cat_df.iloc[0]['category_name']}], with {cat_df.iloc[0]['units_sold']:,} units sold."
                    if is_en
                    else f"品類營收最高為【{cat_df.iloc[0]['category_name']}】，共售出 {cat_df.iloc[0]['units_sold']} 件商品。"
                )
            return fig, title, insight, cat_df
        else:
            is_units = any(
                kw in clean_prompt
                for kw in ["件數", "數量", "銷量", "units", "quantity"]
            )
            val_col = "units_sold" if is_units else "completed_sales_amount"
            unit_lbl = (
                ("Units Sold (Qty)" if is_en else "銷售件數 (件)")
                if is_units
                else ("Total Sales ($)" if is_en else "銷售總額 ($)")
            )
            top_df = df_prod.sort_values(by=val_col, ascending=True).tail(10)
            fig = px.bar(
                top_df,
                x=val_col,
                y="product_title",
                orientation="h",
                color="category_name",
                title=(
                    f"Top 10 Best-Selling Products ({unit_lbl})"
                    if is_en
                    else f"Top 10 熱銷商品排行榜 ({unit_lbl})"
                ),
                labels={
                    val_col: unit_lbl,
                    "product_title": "Product Title" if is_en else "商品名稱",
                    "category_name": "Category" if is_en else "品類",
                },
                template="plotly_dark",
            )
            title = (
                f"Top 10 Best-Selling Products Ranking ({unit_lbl})"
                if is_en
                else f"Top 10 熱銷商品業績排行圖 ({unit_lbl})"
            )
            best_prod = top_df.iloc[-1]
            insight = (
                f"Top product is [{best_prod['product_title']}], contributing {best_prod[val_col]:,.0f} {unit_lbl}."
                if is_en
                else f"冠軍商品為【{best_prod['product_title']}】，累積貢獻 {best_prod[val_col]:,.0f} {unit_lbl}。"
            )
            return fig, title, insight, top_df

    # Check Customer dataset keywords
    elif any(
        kw in clean_prompt
        for kw in [
            "會員",
            "客戶",
            "顧客",
            "customer",
            "customers",
            "tier",
            "tiers",
            "白金",
            "黃金",
            "platinum",
            "gold",
            "silver",
            "bronze",
            "ltv",
            "rfm",
            "人",
        ]
    ):
        tier_colors = {
            "Platinum": "#a855f7",
            "Gold": "#eab308",
            "Silver": "#94a3b8",
            "Bronze": "#b45309",
        }
        if any(kw in clean_prompt for kw in ["圓餅", "佔比", "比例", "分佈", "pie"]):
            tier_summary = (
                df_ltv.groupby("customer_tier")["lifetime_net_revenue"]
                .sum()
                .reset_index()
            )
            fig = px.pie(
                tier_summary,
                names="customer_tier",
                values="lifetime_net_revenue",
                color="customer_tier",
                color_discrete_map=tier_colors,
                title=(
                    "Revenue Contribution by Customer Tier"
                    if is_en
                    else "各會員等級 (Customer Tiers) 營收貢獻分佈"
                ),
                hole=0.45,
                template="plotly_dark",
            )
            title = (
                "Customer Tier Revenue Share Pie Chart"
                if is_en
                else "會員等級營收分佈圓餅圖"
            )
            insight = (
                "Platinum & Gold tiers account for core platform revenue (Pareto 80/20). Recommend VIP retention loyalty programs."
                if is_en
                else "Platinum 與 Gold 會員貢獻全站核心營收，符合二八法則 (Pareto 80/20)，建議強化高階會員權益維護。"
            )
            return fig, title, insight, tier_summary
        elif any(kw in clean_prompt for kw in ["散佈", "散點", "關係", "scatter"]):
            fig = px.scatter(
                df_ltv,
                x="total_orders",
                y="lifetime_net_revenue",
                color="customer_tier",
                color_discrete_map=tier_colors,
                title=(
                    "Order Frequency vs. Customer Lifetime Value (LTV)"
                    if is_en
                    else "顧客下單次數 vs. 終生累積貢獻額 (LTV) 散佈圖"
                ),
                labels={
                    "total_orders": "Total Orders" if is_en else "累計下單次數",
                    "lifetime_net_revenue": (
                        "Lifetime Value LTV ($)" if is_en else "終生價值 LTV ($)"
                    ),
                },
                template="plotly_dark",
            )
            title = (
                "Order Frequency vs. LTV Scatter Plot"
                if is_en
                else "顧客下單次數 vs 終生價值散佈圖"
            )
            insight = (
                "Order count exhibits a strong positive correlation with customer LTV. Customers with >5 orders transition into top tier."
                if is_en
                else "顧客下單次數與終生價值呈現強烈正相關，回購次數超過 5 次的顧客顯著晉升為高價值客群。"
            )
            return fig, title, insight, df_ltv
        else:
            tier_agg = (
                df_ltv.groupby("customer_tier")
                .agg(
                    customer_count=("customer_id", "count"),
                    total_revenue=("lifetime_net_revenue", "sum"),
                    avg_orders=("total_orders", "mean"),
                )
                .reset_index()
            )
            fig = px.bar(
                tier_agg,
                x="customer_tier",
                y="total_revenue",
                color="customer_tier",
                color_discrete_map=tier_colors,
                title=(
                    "Cumulative Net Revenue by Customer Tier ($)"
                    if is_en
                    else "各會員等級累積淨營收總額 ($)"
                ),
                labels={
                    "total_revenue": ("Net Revenue ($)" if is_en else "累積總營收 ($)"),
                    "customer_tier": "Customer Tier" if is_en else "會員等級",
                },
                template="plotly_dark",
            )
            title = (
                "Cumulative Net Revenue by Customer Tier Bar Chart"
                if is_en
                else "各會員等級累積淨營收長條圖"
            )
            insight = (
                "Revenue distribution reflects sharp segmentation. Recommend tailored incentives for Silver/Bronze cohorts to boost repeat conversions."
                if is_en
                else "各等級營收結構分明，建議對 Silver/Bronze 會員推播專屬回購誘因以加速升級。"
            )
            return fig, title, insight, tier_agg

    # Check KPI / Timeseries keywords
    else:
        kpi_df = df_kpi.sort_values(by="order_date").copy()
        if any(
            kw in clean_prompt
            for kw in [
                "退款",
                "取消",
                "refund",
                "refunds",
                "cancel",
                "cancellation",
                "損耗",
                "流失",
            ]
        ):
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=kpi_df["order_date"],
                    y=kpi_df["refund_rate"] * 100,
                    mode="lines+markers",
                    name="Refund Rate (%)" if is_en else "退款率 (%)",
                    line={"color": "#ef4444", "width": 3},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=kpi_df["order_date"],
                    y=kpi_df["cancellation_rate"] * 100,
                    mode="lines+markers",
                    name="Cancellation Rate (%)" if is_en else "取消率 (%)",
                    line={"color": "#f59e0b", "width": 3},
                )
            )
            fig.update_layout(
                title=(
                    "Daily Cancellation Rate vs. Refund Rate Monitoring (%)"
                    if is_en
                    else "每日訂單取消率 vs. 退款率趨勢監控 (%)"
                ),
                template="plotly_dark",
                yaxis={
                    "title": "Percentage (%)" if is_en else "百分比 (%)",
                    "showgrid": True,
                },
            )
            title = (
                "Daily Refund and Cancellation Rate Trends"
                if is_en
                else "每日退款率與取消率走勢圖"
            )
            avg_ref = kpi_df["refund_rate"].mean() * 100
            avg_can = kpi_df["cancellation_rate"].mean() * 100
            insight = (
                f"Period average refund rate is {avg_ref:.1f}%, cancellation rate is {avg_can:.1f}%, showing healthy operational control."
                if is_en
                else f"期間平均退款率為 {avg_ref:.1f}%，取消率為 {avg_can:.1f}%，走勢平穩無異常劇烈尖峰。"
            )
            return fig, title, insight, kpi_df
        elif any(kw in clean_prompt for kw in ["客單價", "aov", "均額", "單價"]):
            fig = px.line(
                kpi_df,
                x="order_date",
                y="aov",
                markers=True,
                title=(
                    "Historical Average Order Value (AOV) Trend ($)"
                    if is_en
                    else "歷史平均客單價 (AOV) 走勢分析 ($)"
                ),
                template="plotly_dark",
                labels={
                    "aov": "AOV ($)" if is_en else "平均客單價 ($)",
                    "order_date": "Date" if is_en else "日期",
                },
                color_discrete_sequence=["#38bdf8"],
            )
            title = (
                "Historical Average Order Value (AOV) Trend"
                if is_en
                else "歷史平均客單價 (AOV) 走勢圖"
            )
            insight = (
                f"Peak AOV reached ${kpi_df['aov'].max():,.2f}, with period average of ${kpi_df['aov'].mean():,.2f}."
                if is_en
                else f"平均客單價最高達 ${kpi_df['aov'].max():,.2f}，全期均值為 ${kpi_df['aov'].mean():,.2f}。"
            )
            return fig, title, insight, kpi_df
        elif any(
            kw in clean_prompt
            for kw in ["訂單", "單數", "完成", "狀態", "orders", "order"]
        ):
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=kpi_df["order_date"],
                    y=kpi_df["completed_orders"],
                    name="Completed Orders" if is_en else "已完成訂單",
                    marker_color="#10b981",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=kpi_df["order_date"],
                    y=kpi_df["cancelled_orders"],
                    name="Cancelled Orders" if is_en else "已取消訂單",
                    marker_color="#f59e0b",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=kpi_df["order_date"],
                    y=kpi_df["refunded_orders"],
                    name="Refunded Orders" if is_en else "已退款訂單",
                    marker_color="#ef4444",
                )
            )
            fig.update_layout(
                barmode="stack",
                title=(
                    "Daily Order Fulfillment Distribution (Stacked Bar)"
                    if is_en
                    else "每日訂單狀態履約分佈 (堆疊長條圖)"
                ),
                template="plotly_dark",
            )
            title = (
                "Daily Order Fulfillment Distribution Chart"
                if is_en
                else "每日訂單狀態履約分佈圖"
            )
            insight = (
                f"Total volume is {kpi_df['total_orders'].sum():,} orders, with fulfillment completion rate of {kpi_df['completed_orders'].sum() / kpi_df['total_orders'].sum() * 100:.1f}%."
                if is_en
                else f"總訂單量達 {kpi_df['total_orders'].sum():,} 筆，其中完成履約比率達 {kpi_df['completed_orders'].sum() / kpi_df['total_orders'].sum() * 100:.1f}%。"
            )
            return fig, title, insight, kpi_df
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=kpi_df["order_date"],
                    y=kpi_df["gmv"],
                    mode="lines+markers",
                    name="GMV ($)" if is_en else "GMV 總銷售額 ($)",
                    line={"color": "#6366f1", "width": 3},
                    fill="tozeroy",
                    fillcolor="rgba(99, 102, 241, 0.1)",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=kpi_df["order_date"],
                    y=kpi_df["net_revenue"],
                    mode="lines+markers",
                    name="Net Revenue ($)" if is_en else "Net Revenue 實質淨營收 ($)",
                    line={"color": "#10b981", "width": 3},
                )
            )
            fig.update_layout(
                title=(
                    "Daily GMV vs. Net Revenue Trend ($)"
                    if is_en
                    else "每日 GMV 總銷售額 vs. 實質淨營收對比走勢圖 ($)"
                ),
                template="plotly_dark",
                yaxis={
                    "title": "Amount ($)" if is_en else "金額 ($)",
                    "showgrid": True,
                },
            )
            title = (
                "Daily GMV vs. Net Revenue Comparison Chart"
                if is_en
                else "每日 GMV 與實質淨營收對比圖"
            )
            insight = (
                f"Total GMV reached ${kpi_df['gmv'].sum():,.2f}, with net revenue realization of {kpi_df['net_revenue'].sum() / kpi_df['gmv'].sum() * 100:.1f}%."
                if is_en
                else f"全期 GMV 累計達 ${kpi_df['gmv'].sum():,.2f}，淨營收實現率達 {kpi_df['net_revenue'].sum() / kpi_df['gmv'].sum() * 100:.1f}%。"
            )
            return fig, title, insight, kpi_df
