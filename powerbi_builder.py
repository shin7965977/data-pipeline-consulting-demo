import importlib.util

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ==============================================================================
# 1. Dynamic Chart Engine for Power BI-Style Custom Visualizations
# ==============================================================================
def build_custom_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str,
    agg_func: str = "sum",
    color_col: str | None = None,
    sort_by: str = "y_desc",
    top_n: int | None = None,
    custom_title: str | None = None,
) -> tuple[go.Figure, pd.DataFrame, str]:
    """Dynamically aggregate and generate high-aesthetic Plotly figures."""
    if df.empty or x_col not in df.columns or y_col not in df.columns:
        fig_empty = go.Figure()
        fig_empty.update_layout(
            template="plotly_dark",
            annotations=[
                {
                    "text": "無足夠數據可生成圖表，請檢查選取欄位",
                    "showarrow": False,
                    "font": {"size": 16, "color": "#94a3b8"},
                }
            ],
        )
        return fig_empty, df, "資料集為空或欄位不存在"

    work_df = df.copy()

    # Determine grouping columns
    group_cols = [x_col]
    if color_col and color_col in work_df.columns and color_col != x_col:
        group_cols.append(color_col)

    # Apply Aggregation
    agg_mapping = {
        "sum": "sum",
        "avg": "mean",
        "count": "count",
        "max": "max",
        "min": "min",
    }
    pandas_agg = agg_mapping.get(agg_func.lower(), "sum")

    try:
        # Box plot uses raw unaggregated distribution
        if chart_type == "box":
            agg_df = work_df
        else:
            if pandas_agg == "count":
                agg_df = work_df.groupby(group_cols)[y_col].count().reset_index()
            else:
                agg_df = (
                    work_df.groupby(group_cols)[y_col].agg(pandas_agg).reset_index()
                )

            # Sorting & Top N
            if sort_by == "y_desc":
                agg_df = agg_df.sort_values(by=y_col, ascending=False)
            elif sort_by == "y_asc":
                agg_df = agg_df.sort_values(by=y_col, ascending=True)
            elif sort_by == "x_asc":
                agg_df = agg_df.sort_values(by=x_col, ascending=True)

            if top_n and top_n > 0:
                agg_df = agg_df.head(top_n)

    except Exception as ex:  # noqa: BLE001
        fig_err = go.Figure()
        fig_err.update_layout(
            template="plotly_dark",
            annotations=[
                {
                    "text": f"聚合運算失敗: {ex}",
                    "showarrow": False,
                    "font": {"size": 15, "color": "#ef4444"},
                }
            ],
        )
        return fig_err, work_df, str(ex)

    # Generate Chart based on chart_type
    title_text = (
        custom_title
        if custom_title
        else f"{x_col} 與 {y_col} 之 {agg_func.upper()} 分析"
    )

    color_arg = color_col if (color_col and color_col in agg_df.columns) else None

    if chart_type == "bar":
        fig = px.bar(
            agg_df,
            x=x_col,
            y=y_col,
            color=color_arg,
            template="plotly_dark",
            title=title_text,
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
    elif chart_type == "line":
        fig = px.line(
            agg_df,
            x=x_col,
            y=y_col,
            color=color_arg,
            template="plotly_dark",
            title=title_text,
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
    elif chart_type == "area":
        fig = px.area(
            agg_df,
            x=x_col,
            y=y_col,
            color=color_arg,
            template="plotly_dark",
            title=title_text,
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
    elif chart_type == "scatter":
        fig = px.scatter(
            agg_df,
            x=x_col,
            y=y_col,
            color=color_arg,
            size=y_col if (agg_df[y_col] > 0).all() else None,
            template="plotly_dark",
            title=title_text,
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
    elif chart_type == "donut":
        fig = px.pie(
            agg_df,
            names=x_col,
            values=y_col,
            hole=0.5,
            template="plotly_dark",
            title=title_text,
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
    elif chart_type == "box":
        fig = px.box(
            agg_df,
            x=x_col,
            y=y_col,
            color=color_arg,
            template="plotly_dark",
            title=title_text,
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
    else:
        fig = px.bar(
            agg_df,
            x=x_col,
            y=y_col,
            template="plotly_dark",
            title=title_text,
        )

    fig.update_layout(
        height=450,
        margin={"l": 25, "r": 25, "t": 45, "b": 25},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )

    # Executive Summary Text
    total_val = (
        agg_df[y_col].sum()
        if (pandas_agg != "count" and chart_type != "box")
        else len(agg_df)
    )
    top_leader = str(agg_df.iloc[0][x_col]) if len(agg_df) > 0 else "無"
    summary_text = (
        f"📊 已成功繪製 **{title_text}**。共涵蓋 **{len(agg_df):,}** 個維度分組，"
        f"首要項目為 **{top_leader}**，數值總計約 **${total_val:,.2f}**。"
    )

    return fig, agg_df, summary_text


# ==============================================================================
# 2. Graphic Walker Spec Builder & AI Natural Language Copilot
# ==============================================================================
def build_pygwalker_spec(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    geom: str = "bar",
    agg: str = "sum",
    color_col: str | None = None,
) -> str:
    """Construct Graphic Walker JSON specification to pre-populate axes and visual geometry."""
    import json

    def get_field_meta(col: str):
        is_num = pd.api.types.is_numeric_dtype(df[col]) if col in df.columns else False
        is_date = (
            pd.api.types.is_datetime64_any_dtype(df[col])
            if col in df.columns
            else False
        )
        if is_date:
            return {
                "fid": col,
                "name": col,
                "semanticType": "temporal",
                "analyticType": "dimension",
            }
        elif is_num:
            return {
                "fid": col,
                "name": col,
                "semanticType": "quantitative",
                "analyticType": "measure",
                "aggName": agg,
            }
        else:
            return {
                "fid": col,
                "name": col,
                "semanticType": "nominal",
                "analyticType": "dimension",
            }

    x_meta = get_field_meta(x_col)
    y_meta = get_field_meta(y_col)
    dimensions = [
        get_field_meta(c)
        for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
    ]
    measures = [
        get_field_meta(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
    ]

    encodings = {
        "dimensions": dimensions,
        "measures": measures,
        "rows": [y_meta],
        "columns": [x_meta],
        "color": [get_field_meta(color_col)]
        if color_col and color_col in df.columns
        else [],
        "opacity": [],
        "size": [],
        "shape": [],
        "details": [],
        "filters": [],
    }
    spec_list = [
        {
            "visId": f"gw_{x_col}_{y_col}",
            "name": f"{x_col} vs {y_col}",
            "encodings": encodings,
            "config": {
                "geoms": [
                    geom if geom in ["bar", "line", "circle", "area", "arc"] else "bar"
                ],
                "coordSystem": "generic",
                "limit": -1,
            },
        }
    ]
    return json.dumps(spec_list)


def generate_pygwalker_spec_from_nl(
    prompt: str,
    df: pd.DataFrame,
    gemini_api_key: str = "",
) -> tuple[str | None, str]:
    """Analyze natural language prompt and generate Graphic Walker JSON spec to configure the canvas."""
    import json

    clean_prompt = prompt.strip().lower()
    x_col = None
    y_col = None
    geom = "bar"
    agg = "sum"
    color_col = None

    # 1. Try Gemini AI if API Key is available
    if gemini_api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_api_key)
            cols_summary = ", ".join(df.columns.tolist())
            system_instruction = (
                f"You are a BI Data Analyst assistant. The user wants to configure a visual chart on a dataset with columns: [{cols_summary}].\n"
                "Extract the best X-axis column (dimension or date), Y-axis column (metric/number), chart geometry ('bar', 'line', 'circle', 'area', 'arc'), and aggregation ('sum', 'mean', 'count').\n"
                'Respond ONLY with a valid JSON object: {"x": "col", "y": "col", "geom": "bar"|"line"|"circle"|"area"|"arc", "agg": "sum"|"mean"|"count", "color": "col"|null}'
            )
            from fastmcp_diagnostic import get_gemini_candidate_models

            pref_m = st.session_state.get("gemini_selected_model", "auto")
            candidates = get_gemini_candidate_models(client, preferred_model=pref_m)

            res = None
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
            if res and res.text:
                parsed = json.loads(res.text)
                if parsed.get("x") in df.columns and parsed.get("y") in df.columns:
                    x_col = parsed["x"]
                    y_col = parsed["y"]
                    geom = parsed.get("geom", "bar")
                    agg = parsed.get("agg", "sum")
                    if parsed.get("color") in df.columns:
                        color_col = parsed["color"]
        except Exception:  # noqa: BLE001, S110
            pass

    # 2. Heuristic rule-based fallback (Works 100% offline)
    if not (x_col and y_col):
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        non_num_cols = [
            c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])
        ]

        # Determine X
        if any(
            w in clean_prompt
            for w in ["日期", "date", "趨勢", "走勢", "時間", "每日", "歷史"]
        ) and any("date" in c.lower() for c in df.columns):
            x_col = next(c for c in df.columns if "date" in c.lower())
            geom = "line"
        elif (
            any(w in clean_prompt for w in ["類別", "分類", "category"])
            and "category_name" in df.columns
        ):
            x_col = "category_name"
        elif (
            any(w in clean_prompt for w in ["商品", "產品", "product"])
            and "product_title" in df.columns
        ):
            x_col = "product_title"
        elif (
            any(w in clean_prompt for w in ["會員", "等級", "tier", "客戶"])
            and "customer_tier" in df.columns
        ):
            x_col = "customer_tier"
        elif non_num_cols:
            x_col = non_num_cols[0]
        elif df.columns.tolist():
            x_col = df.columns[0]

        # Determine Y
        if (
            any(w in clean_prompt for w in ["淨營收", "net_revenue", "淨收入"])
            and "net_revenue" in df.columns
        ):
            y_col = "net_revenue"
        elif (
            any(w in clean_prompt for w in ["gmv", "總額", "總營收", "銷售額", "金流"])
            and "gmv" in df.columns
        ):
            y_col = "gmv"
        elif (
            any(w in clean_prompt for w in ["銷售額", "業績", "amount"])
            and "completed_sales_amount" in df.columns
        ):
            y_col = "completed_sales_amount"
        elif (
            any(w in clean_prompt for w in ["終身價值", "ltv", "lifetime"])
            and "lifetime_net_revenue" in df.columns
        ):
            y_col = "lifetime_net_revenue"
        elif any(w in clean_prompt for w in ["客單價", "aov"]) and "aov" in df.columns:
            y_col = "aov"
            agg = "mean"
        elif (
            any(w in clean_prompt for w in ["件數", "數量", "units"])
            and "units_sold" in df.columns
        ):
            y_col = "units_sold"
        elif (
            any(w in clean_prompt for w in ["退款", "refund"])
            and "refunded_orders" in df.columns
        ):
            y_col = "refunded_orders"
        elif (
            any(w in clean_prompt for w in ["取消", "cancel"])
            and "cancelled_orders" in df.columns
        ):
            y_col = "cancelled_orders"
        elif (
            any(w in clean_prompt for w in ["訂單數", "orders"])
            and "total_orders" in df.columns
        ):
            y_col = "total_orders"
        elif num_cols:
            y_col = num_cols[0]
        else:
            y_col = df.columns[-1]

    if not (x_col and y_col and x_col in df.columns and y_col in df.columns):
        return (
            None,
            "⚠️ 無法根據指令比對到合適的資料維度與度量，請嘗試具體描述欄位名稱。",
        )

    spec = build_pygwalker_spec(
        df, x_col=x_col, y_col=y_col, geom=geom, agg=agg, color_col=color_col
    )
    msg = f"✨ **AI 自動配置成功**：X 軸 ➔ `{x_col}`、Y 軸 ➔ `{y_col}`（{agg}）、圖表形狀 ➔ `{geom.upper()}`。您可於下方畫布繼續滑鼠自由拖曳微調！"
    return spec, msg


def sanitize_df_for_pygwalker(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize DataFrame types for PyGWalker and DuckDB compatibility.
    Converts BigQuery dbdate, date, datetime objects to standard pandas datetimes,
    and Decimals to float, avoiding DuckDB 'dbdate not recognized' and transaction aborts.
    """
    if df is None or df.empty:
        return df
    clean_df = df.copy()
    from decimal import Decimal

    for col in clean_df.columns:
        dtype_str = str(clean_df[col].dtype).lower()
        if "dbdate" in dtype_str or "date" in col.lower() or "time" in col.lower():
            try:
                clean_df[col] = pd.to_datetime(clean_df[col])
            except Exception:  # noqa: BLE001
                clean_df[col] = clean_df[col].astype(str)
        elif clean_df[col].dtype == object and len(clean_df) > 0:
            sample_val = (
                clean_df[col].dropna().iloc[0]
                if not clean_df[col].dropna().empty
                else None
            )
            if sample_val is not None:
                if isinstance(sample_val, Decimal):
                    clean_df[col] = clean_df[col].astype(float)
                elif hasattr(sample_val, "isoformat") or hasattr(
                    sample_val, "strftime"
                ):
                    try:
                        clean_df[col] = pd.to_datetime(clean_df[col])
                    except Exception:  # noqa: BLE001
                        clean_df[col] = clean_df[col].astype(str)
    return clean_df


# ==============================================================================
# 3. Power BI / Tableau Studio Component (PyGWalker + Chinese i18n + AI Copilot)
# ==============================================================================
def render_powerbi_studio(
    df_kpi: pd.DataFrame | None = None,
    df_ltv: pd.DataFrame | None = None,
    df_prod: pd.DataFrame | None = None,
    *args,
    key_prefix: str = "pbi_pyg",
    default_dataset_key: str = "kpi",
    **kwargs,
):
    """Render the full Power BI/Tableau drag-and-drop interactive canvas with AI Copilot."""
    st.subheader("🎛️ 類 Power BI / Tableau 視覺化自訂看板")
    st.caption(
        "基於 Google Cloud BigQuery 金牌數據庫 · 支援 AI 自然語言指令自動排版與滑鼠自由拖曳"
    )

    # Dataset Configurations (Supports custom datasets from Silver / Bronze layers)
    dataset_configs = kwargs.get("dataset_configs") or {
        "kpi": {
            "name": "📊 de-consulting-508822.platzi_gold.gold_daily_sales_kpi (每日營收與轉換指標)",
            "df": df_kpi,
        },
        "ltv": {
            "name": "👥 de-consulting-508822.platzi_gold.gold_customer_ltv (顧客終身價值分群)",
            "df": df_ltv,
        },
        "prod": {
            "name": "🏆 de-consulting-508822.platzi_gold.gold_product_performance (商品業績與分類排行)",
            "df": df_prod,
        },
    }

    if importlib.util.find_spec("pygwalker") is not None:
        try:
            import pygwalker as pyg
            import streamlit.components.v1 as components

            col_ds, col_lang = st.columns([3, 1])
            with col_ds:
                ds_keys = list(dataset_configs.keys())
                ds_names = [cfg["name"] for cfg in dataset_configs.values()]
                default_idx = (
                    ds_keys.index(default_dataset_key)
                    if default_dataset_key in ds_keys
                    else 0
                )
                selected_ds_name = st.selectbox(
                    "📁 選擇要載入探索工作台的 BigQuery 金牌資料表：",
                    options=ds_names,
                    index=default_idx,
                    key=f"{key_prefix}_dataset_select",
                )
            with col_lang:
                lang_options = {
                    "🌐 繁簡中文 (Chinese)": "zh-CN",
                    "🌐 English (英文)": "en-US",
                }
                selected_lang_label = st.selectbox(
                    "介面語言 (Language)",
                    options=list(lang_options.keys()),
                    index=0,
                    key=f"{key_prefix}_lang_select",
                )
                i18n_code = lang_options[selected_lang_label]

            active_cfg = next(
                v for v in dataset_configs.values() if v["name"] == selected_ds_name
            )
            walker_df = active_cfg["df"]

            # AI Natural Language to Canvas Copilot
            st.markdown("##### 🪄 AI 自然語言輔助排版 (NL-to-Canvas)")
            c_copilot_in, c_copilot_btn, c_copilot_reset = st.columns([3, 1, 1])
            with c_copilot_in:
                nl_canvas_input = st.text_input(
                    "輸入自然語言指令讓 AI 為您排版畫布：",
                    value=st.session_state.get(f"{key_prefix}_nl_query", ""),
                    placeholder="例：以長條圖顯示各商品分類的累積銷售金額、或是每日 GMV 走勢...",
                    key=f"{key_prefix}_nl_input",
                    label_visibility="collapsed",
                )
            with c_copilot_btn:
                if st.button(
                    "🪄 AI 自動排版",
                    key=f"{key_prefix}_btn_apply_ai",
                    type="primary",
                    use_container_width=True,
                ):
                    gemini_key = st.session_state.get("sidebar_gemini_api_key", "")
                    if nl_canvas_input.strip():
                        spec_json, status_msg = generate_pygwalker_spec_from_nl(
                            prompt=nl_canvas_input,
                            df=walker_df,
                            gemini_api_key=gemini_key,
                        )
                        if spec_json:
                            st.session_state[f"{key_prefix}_active_spec"] = spec_json
                            st.session_state[f"{key_prefix}_msg"] = status_msg
                        else:
                            st.session_state[f"{key_prefix}_msg"] = status_msg
            with c_copilot_reset:
                if st.button(
                    "🔄 清空重設",
                    key=f"{key_prefix}_btn_reset_spec",
                    use_container_width=True,
                    help="重設為空白工作台",
                ):
                    st.session_state[f"{key_prefix}_active_spec"] = ""
                    st.session_state[f"{key_prefix}_msg"] = "已重設為空白探索工作台。"

            # Display Status / Guide Message
            active_spec = st.session_state.get(f"{key_prefix}_active_spec", "")
            current_msg = st.session_state.get(f"{key_prefix}_msg")
            if current_msg:
                st.info(current_msg)
            else:
                st.caption(
                    "💡 **無代碼操作指引**：亦可從左側欄位清單，將 **維度（Categorical）** 或 **度量（Quantitative）** "
                    "用滑鼠直接拖曳進上方 **X 軸** 與 **Y 軸** 即席探索！"
                )

            # Reset DuckDB transaction state if previously aborted
            try:
                import duckdb

                duckdb.execute("ROLLBACK")
            except Exception:  # noqa: BLE001, S110
                pass

            clean_walker_df = sanitize_df_for_pygwalker(walker_df)

            with st.spinner("正在加載互動探索工作台..."):
                pyg_html = pyg.to_html(
                    clean_walker_df,
                    spec=active_spec,
                    i18nLang=i18n_code,
                    i18n_lang=i18n_code,
                )
                components.html(pyg_html, height=950, scrolling=True)

            # FastMCP Mode A Diagnostic for Active Dataset in Power BI Canvas
            st.markdown("---")
            col_pbi_mcp_btn, col_pbi_mcp_info = st.columns([1.8, 3.2])
            with col_pbi_mcp_btn:
                run_pbi_mcp = st.button(
                    "🤖 呼叫 FastMCP 顧問深度診斷當前自訂畫布 (Mode A)",
                    key=f"{key_prefix}_btn_fastmcp_pbi",
                    type="primary",
                    use_container_width=True,
                    help="調用 FastMCP 顧問引擎：對目前在畫布中探索的資料表進行 MBB 深度歸因診斷與戰術方針規劃",
                )
            with col_pbi_mcp_info:
                st.caption(
                    f"⚡ **FastMCP 畫布即時診斷**：針對當前選定之 `{selected_ds_name}` 執行 SCQA + MECE 議題樹歸因，並支援連續對話追問！"
                )

            diag_pbi_key = f"{key_prefix}_fastmcp_diag_result"
            if run_pbi_mcp:
                # Check if the canvas has actually been configured with a chart
                has_active_chart = bool(active_spec and active_spec.strip())

                if not has_active_chart and not nl_canvas_input.strip():
                    st.warning("⚠️ **偵測到當前畫布為空白狀態 (Blank Canvas)**")
                    st.markdown(
                        """
                        <div class="metric-card" style="border-left: 4px solid #f59e0b; background: rgba(245, 158, 11, 0.05); margin-bottom: 1rem;">
                            <div style="font-weight: 600; font-size: 1rem; color: var(--text-color, #0f172a);">
                                💡 建議先完成畫布排版，診斷將更具針對性：
                            </div>
                            <ul style="margin: 0.5rem 0 0 1.25rem; font-size: 0.925rem; color: #64748b; line-height: 1.6;">
                                <li><strong>方式 1（AI 自動排版）</strong>：於上方「AI 自然語言輔助排版」輸入指令（如：<em>「每日 GMV 走勢」</em>），點擊「🪄 AI 自動排版」。</li>
                                <li><strong>方式 2（滑鼠拖曳）</strong>：從左側欄位清單將 <code>order_date</code> 拖入「列 (X軸)」，將 <code>gmv</code> 拖入「行 (Y軸)」。</li>
                            </ul>
                            <div style="margin-top: 0.5rem; font-size: 0.85rem; color: #94a3b8;">
                                <em>備註：下方顧問目前已自動切換為針對本張資料表全量的<strong>「底層數據庫全域預檢診斷 (Table Baseline Audit)」</strong>。</em>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with st.spinner(
                    "🤖 FastMCP 顧問正在分析當前畫布資料庫並生成商業歸因診斷..."
                ):
                    import fastmcp_diagnostic

                    gemini_key = st.session_state.get("sidebar_gemini_api_key", "")
                    chart_desc = (
                        f"Power BI 視覺化畫布 - {selected_ds_name}"
                        if has_active_chart
                        else f"BigQuery 資料表全量健檢 - {selected_ds_name}"
                    )
                    prompt_desc = (
                        nl_canvas_input
                        if has_active_chart and nl_canvas_input
                        else f"針對 {selected_ds_name} 進行全表基線健康度診斷"
                    )

                    pbi_diag_report = fastmcp_diagnostic.run_fastmcp_chart_diagnostic(
                        chart_title=chart_desc,
                        df=walker_df,
                        prompt_intent=prompt_desc,
                        gemini_api_key=gemini_key,
                    )
                    st.session_state[diag_pbi_key] = pbi_diag_report

            if st.session_state.get(diag_pbi_key):
                import fastmcp_diagnostic

                gemini_key = st.session_state.get("sidebar_gemini_api_key", "")
                fastmcp_diagnostic.render_fastmcp_chat_widget(
                    unique_key=f"pbi_{key_prefix}",
                    chart_title=f"Power BI 視覺化畫布 - {selected_ds_name}",
                    df=walker_df,
                    initial_diagnostic=st.session_state[diag_pbi_key],
                    gemini_api_key=gemini_key,
                )

        except Exception as ex:  # noqa: BLE001
            try:
                import duckdb

                duckdb.execute("ROLLBACK")
            except Exception:  # noqa: BLE001, S110
                pass
            st.error(f"PyGWalker 載入時發生異常：{ex}")
    else:
        st.markdown(
            """
            <div class="metric-card" style="border-left: 4px solid #f59e0b; background: rgba(245, 158, 11, 0.05);">
                <h4 style="margin: 0; color: #f59e0b;">💡 PyGWalker 探索套件尚未安裝</h4>
                <p style="margin-top: 0.5rem; color: var(--text-color, #334155); font-size: 0.95rem; line-height: 1.6;">
                    <strong>PyGWalker</strong> 可以將真正的 Tableau / Power BI 拖放式畫布直接嵌入此頁面。<br>
                    請在終端機中執行下方指令完成安裝：
                </p>
                <code style="background: rgba(0,0,0,0.15); padding: 0.4rem 0.8rem; border-radius: 6px; font-weight: 600;">pip install pygwalker tornado</code>
            </div>
            """,
            unsafe_allow_html=True,
        )
