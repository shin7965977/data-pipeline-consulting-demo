"""FastMCP Mode A: In-Dashboard Deep Diagnostic Engine for Charts.

Synthesizes data anomalies from generated charts and applies MBB (McKinsey/BCG/Bain)
Pyramid Principle (SCQA), MECE Issue Tree decomposition, and 30-60-90 day tactical roadmaps.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def get_gemini_candidate_models(client: Any, preferred_model: str = "") -> list[str]:
    """Get an ordered cascade list of candidate Gemini models for graceful degradation.
    Supports user preference and automatically sorts available models by version descending (e.g. 3.8 -> 3.6 -> 2.5).
    """
    import re

    discovered = []
    try:
        for m in client.models.list():
            m_name = m.name.replace("models/", "")
            if "flash" in m_name.lower() and not any(
                bad in m_name.lower()
                for bad in ["omni", "embed", "imagen", "tts", "stt", "realtime"]
            ):
                discovered.append(m_name)

        def version_score(name: str) -> float:
            nums = re.findall(r"(\d+(?:\.\d+)?)", name)
            return float(nums[0]) if nums else 0.0

        discovered.sort(key=version_score, reverse=True)
    except Exception:  # noqa: BLE001, S110
        pass

    fallback_defaults = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-2.5-flash"]
    candidates = discovered if discovered else fallback_defaults

    # Ensure all fallback defaults exist in candidate list
    for fb in fallback_defaults:
        if fb not in candidates:
            candidates.append(fb)

    # If user selected a specific preferred model (e.g. 3.6 to dodge 3.8 peak)
    if preferred_model and preferred_model != "auto":
        candidates = [preferred_model] + [m for m in candidates if m != preferred_model]

    return candidates


def resolve_active_gemini_model(client: Any, preferred_model: str = "") -> str:
    """Dynamically discover and return the best candidate Gemini model."""
    candidates = get_gemini_candidate_models(client, preferred_model=preferred_model)
    return candidates[0] if candidates else "gemini-3.6-flash"


def run_fastmcp_chart_diagnostic(
    chart_title: str,
    df: pd.DataFrame,
    prompt_intent: str = "",
    gemini_api_key: str = "",
) -> str:
    """Run FastMCP consulting diagnostic on the chart's underlying data.

    Returns an executive MBB-grade diagnosis in GitHub-flavored Markdown.
    """
    if df.empty:
        return "⚠️ 本圖表無足夠數據可供 FastMCP 顧問進行歸因分析。"

    # Extract Key Data Metrics & Anomalies for Context
    num_rows = len(df)
    cols = df.columns.tolist()

    data_summary: dict[str, Any] = {
        "num_records": num_rows,
        "columns": cols,
    }

    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

    for nc in numeric_cols[:5]:
        data_summary[nc] = {
            "sum": float(df[nc].sum()),
            "mean": float(df[nc].mean()),
            "max": float(df[nc].max()),
            "min": float(df[nc].min()),
        }

    # Sample top 5 rows
    sample_records = df.head(5).to_dict(orient="records")
    # Clean datetime/decimals
    for row in sample_records:
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
            elif isinstance(v, float):
                row[k] = round(v, 2)

    # 1. Try Gemini AI with MBB System Prompt
    if gemini_api_key:
        try:
            import streamlit as st
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_api_key)
            preferred = st.session_state.get("gemini_selected_model", "auto")
            candidates = get_gemini_candidate_models(client, preferred_model=preferred)

            system_instruction = (
                "You are an MBB Senior Partner / Practice Director (McKinsey/BCG/Bain caliber) "
                "providing an executive performance diagnostic based on e-commerce retail data.\n\n"
                "Strictly adhere to the following consulting standards:\n"
                "1. Three-Test Standard: 'So What?' (Synthesize non-obvious business insight), "
                "'Why So?' (Quantified causal proof with numbers), 'Now What?' (3 concrete high-ROI interventions).\n"
                "2. Pyramid Principle & SCQA structure:\n"
                "   - [Executive Governing Thought / Action Title]: Single bold conclusion sentence.\n"
                "   - [SCQA Diagnostic]:\n"
                "     * Situation (S): Macro state.\n"
                "     * Complication (C): Quantified anomaly/bottleneck found in data.\n"
                "     * Question (Q): Core management challenge.\n"
                "     * Answer (A): Strategic hypothesis.\n"
                "   - [MECE Issue Tree Decomposition]: Structured causal breakdown (e.g. GMV = Volume x Price, Net Leakage = Cancel + Refund).\n"
                "   - [30-60-90 Day Tactical Roadmap]: Day 1-30 Quick Wins, Day 31-60 Process Tuning, Day 61-90 Strategic Anchoring.\n"
                "Use professional Traditional Chinese (繁體中文). Do not use placeholders or generic filler."
            )

            user_prompt = f"""
請針對當前視覺化圖表及其底層數據進行 FastMCP 深度歸因診斷：
- 圖表名稱：{chart_title}
- 使用者分析意圖：{prompt_intent or chart_title}
- 數據摘要：{json.dumps(data_summary, ensure_ascii=False)}
- 數據樣本（前 5 筆）：{json.dumps(sample_records, ensure_ascii=False)}

請輸出完整的 MBB 顧問深度診斷報告（Markdown 格式）。
"""
            res = None
            last_err = None
            for candidate in candidates:
                try:
                    res = client.models.generate_content(
                        model=candidate,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.2,
                        ),
                    )
                    if res and res.text:
                        st.session_state["gemini_active_used_model"] = candidate
                        st.session_state.pop("gemini_api_last_error", None)
                        return res.text.strip()
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    err_str = str(e)
                    # Automatically cascade down on 503, 429, high demand or missing model
                    if any(
                        k in err_str
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

            if last_err is not None:
                err_str = str(last_err)
                if "401" in err_str or "UNAUTHENTICATED" in err_str:
                    st.session_state["gemini_api_last_error"] = (
                        "Google API 驗證失敗 (401 UNAUTHENTICATED)：您輸入的金鑰無效或格式不符。"
                        "Gemini API 專用金鑰固定為「AIzaSy...」開頭，而非「AQ.」或 OAuth 憑證。"
                    )
                elif "403" in err_str or "PERMISSION_DENIED" in err_str:
                    st.session_state["gemini_api_last_error"] = (
                        "Google API 權限不足 (403 PERMISSION_DENIED)：請確認該金鑰已啟用 Gemini API 權限。"
                    )
                elif any(k in err_str for k in ["503", "UNAVAILABLE", "high demand"]):
                    st.session_state["gemini_api_last_error"] = (
                        "Google 模型尖峰高負載 (503 UNAVAILABLE)：系統已自動嘗試多層降級，已啟用 FastMCP 離線顧問引擎。"
                    )
                else:
                    st.session_state["gemini_api_last_error"] = (
                        f"API 呼叫失敗：{err_str[:120]}"
                    )
        except Exception as outer_e:  # noqa: BLE001
            import streamlit as st

            st.session_state["gemini_api_last_error"] = (
                f"API 初始化失敗：{str(outer_e)[:120]}"
            )

    # 2. Rule-Based Offline MBB Synthesizer (Zero-Failure Fallback)
    primary_metric = numeric_cols[0] if numeric_cols else "指標"
    metric_sum = data_summary.get(primary_metric, {}).get("sum", 0.0)
    metric_max = data_summary.get(primary_metric, {}).get("max", 0.0)
    metric_min = data_summary.get(primary_metric, {}).get("min", 0.0)

    # Detect dimension
    dim_name = cols[0] if cols else "維度"
    top_dim_val = str(df.iloc[0][dim_name]) if len(df) > 0 else "主要項目"

    report = f"""### 🤖 [FastMCP MBB 深度診斷] Action Title 核心業務發現：{top_dim_val} 展現高度集中度，需防範邊際利潤稀釋與履約流失

#### 1. SCQA 現況與癥結診斷 (Context & Burning Platform)
* **Situation (現況)**：本圖表「**{chart_title}**」共涵蓋 **{num_rows:,}** 筆數據觀測值，主要監控指標 `{primary_metric}` 累計總值達 **${metric_sum:,.2f}**，整體維持商業運轉基線。
* **Complication (併發痛點)**：數據呈現顯著波動（峰值 **${metric_max:,.2f}** vs 谷底 **${metric_min:,.2f}**），首要項目 **{top_dim_val}** 貢獻了主要份額，暴露出**品類/通路高度集中風險**與潛在訂單取消/退款漏斗損耗。
* **Question (核心命題)**：如何在維持大盤成長動能的同時，縮小極值差距並建立抗風險的結構化防線？
* **Answer (戰略假設)**：透過高毛利配件搭售提高實質客單價（AOV），並針對高波動環節導入動態庫存與物流預警機制。

---

#### 2. MECE 議題樹歸因拆解 (Issue Tree Decomposition)
```text
整體營收漏斗 (Revenue Funnel)
├── [驅動支柱 1] 銷售流量與訂單規模 (Volume Engine)
│   ├── 首要分組 ({top_dim_val})：貢獻核心轉化基底，但成長進入邊際遞減
│   └── 尾部長尾項目：轉化轉速偏低，佔比未達 15%
└── [漏斗支柱 2] 實質淨營收損耗 (Leakage Analysis)
    ├── 取消訂單金流失血：高峰期取消率上升，主因為付款超時與履約等待
    └── 逆向物流與退款侵蝕：大件商品運費與退貨處理成本稀釋貢獻利潤
```

---

#### 3. 30-60-90 天戰術落地藍圖 (Tactical Roadmap)
* **Day 1~30 (速贏止血 · Quick Wins)**：
  - 鎖定 `{primary_metric}` 表現最差的谷底節點，排查付款網關失敗率與前台商品資訊誤導率。
  - 對高取消率品類啟用「訂單即時確認 SMS/Email」，預估可挽回 3%~5% 流失訂單。
* **Day 31~60 (流程深耕 · Process Optimization)**：
  - 針對 `{top_dim_val}` 實施階梯定價與滿額免運策略，拉抬次級品項的連帶購買率。
  - 建立供應商履約 SLA 監控，將平均出貨時效壓降至 24 小時內。
* **Day 61~90 (戰略穩固 · Structural Scaling)**：
  - 導入客戶終身價值 (LTV) 動態分級權益，對高價值忠誠用戶給予專屬售後保證，鎖定 70% 穩定營收盤。
"""
    return report


def continue_fastmcp_chat(
    chat_history: list[dict[str, str]],
    user_message: str,
    chart_title: str,
    df: pd.DataFrame,
    gemini_api_key: str = "",
) -> str:
    """Continue multi-turn follow-up consulting conversation with FastMCP MBB Consultant.

    Args:
        chat_history: List of previous turns [{'role': 'user'|'assistant', 'content': '...'}]
        user_message: The follow-up question from the user
        chart_title: Title of the current chart
        df: Underlying dataframe of the chart
        gemini_api_key: Optional Gemini API Key
    """
    if not user_message.strip():
        return "請輸入您想向 FastMCP 顧問請教的業務問題。"

    # Extract basic dataframe context
    num_rows = len(df) if not df.empty else 0
    cols = df.columns.tolist() if not df.empty else []

    # 1. Try Gemini AI with Multi-Turn Conversation
    if gemini_api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_api_key)

            system_instruction = (
                f"You are an MBB Senior Partner / Practice Director (McKinsey/BCG/Bain caliber) "
                f"advising an executive on e-commerce retail analytics based on chart: '{chart_title}'.\n"
                f"Data context: {num_rows} records, columns: {cols}.\n\n"
                "Strict Consulting Rules:\n"
                "1. Direct & Actionable: Answer the user's question directly in the first sentence (Pyramid Principle).\n"
                "2. Concrete & Practical: Provide tangible examples (e.g. exact SMS copy, priority matrices, ROI calculations).\n"
                "3. MECE Structure: Group recommendations logically without overlaps.\n"
                "4. Language: Professional Traditional Chinese (繁體中文). Tone: Authoritative, strategic, yet commercially grounded."
            )

            # Build multi-turn context
            formatted_contents = []
            for msg in chat_history[-6:]:  # Keep last 6 messages for token efficiency
                role = "user" if msg.get("role") == "user" else "model"
                formatted_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.get("content", ""))],
                    )
                )

            # Add current user message
            formatted_contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message)],
                )
            )

            import streamlit as st

            preferred = st.session_state.get("gemini_selected_model", "auto")
            candidates = get_gemini_candidate_models(client, preferred_model=preferred)

            res = None
            last_err = None
            for candidate in candidates:
                try:
                    res = client.models.generate_content(
                        model=candidate,
                        contents=formatted_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.3,
                        ),
                    )
                    if res and res.text:
                        st.session_state["gemini_active_used_model"] = candidate
                        st.session_state.pop("gemini_api_last_error", None)
                        return res.text.strip()
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    err_str = str(e)
                    if any(
                        k in err_str
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

            if last_err is not None:
                err_str = str(last_err)
                if "401" in err_str or "UNAUTHENTICATED" in err_str:
                    st.session_state["gemini_api_last_error"] = (
                        "Google API 驗證失敗 (401 UNAUTHENTICATED)：您輸入的金鑰無效或格式不符。"
                        "Gemini API 專用金鑰固定為「AIzaSy...」開頭，而非「AQ.」或 OAuth 憑證。"
                    )
                elif "403" in err_str or "PERMISSION_DENIED" in err_str:
                    st.session_state["gemini_api_last_error"] = (
                        "Google API 權限不足 (403 PERMISSION_DENIED)：請確認該金鑰已啟用 Gemini API 權限。"
                    )
                elif any(k in err_str for k in ["503", "UNAVAILABLE", "high demand"]):
                    st.session_state["gemini_api_last_error"] = (
                        "Google 模型尖峰高負載 (503 UNAVAILABLE)：系統已自動嘗試多層降級，已啟用 FastMCP 離線顧問引擎。"
                    )
                else:
                    st.session_state["gemini_api_last_error"] = (
                        f"API 呼叫失敗：{err_str[:120]}"
                    )
        except Exception as outer_e:  # noqa: BLE001
            import streamlit as st

            st.session_state["gemini_api_last_error"] = (
                f"API 初始化失敗：{str(outer_e)[:120]}"
            )

    # 2. Offline Consultant Knowledge Base (Zero-Failure Fallback)
    q_lower = user_message.lower()

    if any(
        k in q_lower for k in ["sms", "簡訊", "email", "模板", "挽回", "文案", "召回"]
    ):
        return (
            "### 📱 MBB 推薦速贏挽回簡訊 (SMS) 與推播文案模板\n\n"
            "**【高轉換召回簡訊模板 · 觸發時機：訂單取消 15 分鐘內】**\n"
            "> 「【Platzi 官方商城】親愛的會員您好，我們注意到您剛才未完成結帳。系統已為您特別保留專屬購物車折扣碼 `VIPRECOVER`，享有 **現折 5% + 免運特權**，有效期限僅剩 6 小時！點擊立即恢復訂單：[https://platzi.store/cart/recovery]」\n\n"
            "**顧問執行要點**：\n"
            "1. **急迫性（Urgency）**：限制 6 小時內有效，刺激心理促購。\n"
            "2. **摩擦力降低（Friction Reduction）**：單擊深層連結（Deep Link）直接恢復原購物車，無須重複填寫資料。\n"
            "3. **邊際利潤防線**：限每位會員每月僅能觸發 1 次，防範常態刷折扣客群。"
        )

    if any(k in q_lower for k in ["預算", "10萬", "有限", "優先", "退款", "取消"]):
        return (
            "### ⚖️ 10 萬元行銷預算配置：【優先止血訂單取消】\n\n"
            "**結論先行 (Action Title)**：**在預算有限情況下，應 70% 投入「預防訂單取消」，30% 投入「退款流程分流優化」**。\n\n"
            "**因果歸因分析 (Why So?)**：\n"
            "* **獲客成本已沉沒**：顧客已進入結帳環節才取消，代表前端廣告費用已支付；若在此時流失，CAC 完全浪費。\n"
            "* **挽回 ROI 高達 1:8**：只需微小誘因（例如 30 元運費補貼或付款失敗即時輔助），即可將 15% 取消單重新救回。\n\n"
            "**預算配比建議 (MECE)**：\n"
            "1. **7 萬元（取消防線）**：串接 SMS 即時自動補救 API + 付款超時彈窗。\n"
            "2. **3 萬元（退款防線）**：針對高發退款品項更換高清尺寸對照圖與強化售前 QA。"
        )

    if any(
        k in q_lower
        for k in ["董事會", "主管", "ceo", "會議", "報告", "摘要", "takeaway", "匯報"]
    ):
        return (
            f"### 👔 給董事會 / C-Level 的 1 分鐘高階匯報摘要 (Executive Brief)\n\n"
            f"**主題**：當前業務動能檢視與漏斗損耗防範（基於 `{chart_title}` 數據指標）\n\n"
            "1. **大盤表現穩定，但呈現結構性集中**：主要營收高度依賴少數頭部時段與主力品項，具備基本安全盤，但抗週期風險脆弱。\n"
            "2. **邊際利潤受到取消與退款侵蝕**：未履約訂單損耗了預期營收，主因為付款時延與物流期望落差，而非需求本身疲軟。\n"
            "3. **本季戰術落地主線**：啟動 30 天速贏行動（挽回 SMS + 付款失敗防護），預計以低於 10 萬成本帶動 3%~5% 淨利潤回流。"
        )

    if any(
        k in q_lower for k in ["商品", "品類", "搭售", "出清", "滯銷", "尾部", "bundle"]
    ):
        return (
            "### 📦 長尾商品搭售 (Bundling) 與庫存出清方案\n\n"
            "**1. 錨定熱銷主力品搭售 (Bundle Anchor)**：將銷量 Top 20% 的暢銷品與長尾低週轉品打包成「組合優惠包」，提供組合價 85 折，利用主力品的強需求拉動庫存去化。\n"
            "2. **滿額加價購 (Tiered Upsell)**：結帳金額滿 $1,500 時，彈出「現省 $200 加購特定品類商品」，刺激購物車 AOV 並兼顧去庫存。\n"
            "3. **階梯清倉紅利**：對滯銷天數超過 60 天的 SKU，直接給予第一線銷售或推播專屬折扣券，止血倉儲租金成本。"
        )

    if any(
        k in q_lower for k in ["會員", "vip", "留存", "ltv", "復購", "分級", "loyalty"]
    ):
        return (
            "### 👑 VIP 核心會員權益與 90 天留存體系 (Loyalty Program)\n\n"
            "**1. 分級特權差異化**：白金與黃金會員享有「免運無門檻」與「退換貨到府免運」，強化心理歸屬感與首選結帳意願。\n"
            "2. **新客首購後 90 天黃金培育旅程**：\n"
            "   * **Day 7**：發送產品使用指南與滿意度調查（預防退款）。\n"
            "   * **Day 21**：發送關聯品類 9 折回購券（建立復購習慣）。\n"
            "   * **Day 60**：發送即將過期的積分點數提醒（促成第三次下單，完成 LTV 鎖定）。\n"
            "3. **休眠預警機制**：顧客超過平均復購週期 1.5 倍未回訪時，自動觸發高吸引力專屬權益簡訊。"
        )

    if any(k in q_lower for k in ["omtm", "指標", "週會", "檢核", "checklist", "每週"]):
        return (
            "### 📋 電商營運團隊每週數據檢核清單 (Weekly Checklist)\n\n"
            "**【核心 OMTM 指標】**：**淨營收實現率 (Net Realization Rate = 淨營收 / GMV)**，目標維持在 88% 以上。\n\n"
            "**週會 5 大排查要點**：\n"
            "1. **訂單取消率異動**：是否有突發的支付超時或金流網關故障？\n"
            "2. **退款品項集中度**：退款集中在哪些特定供應商或 SKU？是否為商品瑕疵？\n"
            "3. **客單價 (AOV) 走勢**：主力商品品類比重是否健康？有無過度依賴降價促銷？\n"
            "4. **庫存週轉天數**：長尾庫存佔比是否壓制現金流？\n"
            "5. **VIP 顧客活躍度**：本週回購訂單佔比是否達到 35% 安全水位？"
        )

    # Generic MBB reply
    return (
        f"### 💡 FastMCP 顧問方針解析\n\n"
        f"針對您的問題「**{user_message}**」，從本圖表「**{chart_title}**」的維度拆解，我們給出以下核心建議：\n\n"
        "1. **數據指標導向**：所有商業改動需監控前後期的 **AOV（客單價）** 與 **Net Revenue Conversion（淨營收轉化率）**，確保投入產出比（ROI）大於 3.5 倍。\n"
        "2. **敏捷 A/B 測試**：切勿全量上線新規則，建議先選定 20% 流量進行為期兩週的雙盲對照組實驗。\n"
        "3. **跨部門協同**：此項調整需前端產品團隊（結帳體驗）與供應鏈團隊（履約 SLA）共同背負同一個 OMTM (One Metric That Matters) 指標。"
    )


def get_dynamic_followup_suggestions(
    chart_title: str,
    chat_history: list[dict],
    df: pd.DataFrame,
) -> list[tuple[str, str]]:
    """Dynamically generate 3 relevant, non-repeating follow-up questions.
    Adapts based on current chart context, previous turns, and randomized rotation.
    """
    past_text = " ".join([m.get("content", "") for m in chat_history]).lower()

    candidates: list[tuple[str, str, list[str]]] = [
        (
            "📱 擬定 Day 1-30 速贏挽回簡訊",
            "請針對當前分析發現，為我擬定一封高轉換的訂單挽回簡訊 (SMS) 模板與發送時機規則。",
            ["sms", "簡訊", "挽回", "文案"],
        ),
        (
            "⚖️ 預算 10 萬優先救退款還是取消？",
            "如果本季只有 10 萬元的行銷或營運補救預算，我們應該優先投在防範取消還是優化退款？",
            ["預算", "10萬", "有限", "優先"],
        ),
        (
            "👔 產出給董事會 / CEO 的 1 分鐘匯報",
            "請以 Pyramid Principle 幫我歸納 3 點核心業務摘要，供我向董事會及 CEO 進行 1 分鐘口頭報告。",
            ["董事會", "ceo", "會議", "匯報", "摘要"],
        ),
        (
            "🛒 結帳超時挽留彈窗機制與文案",
            "針對結帳流程中斷的顧客，推薦最適合的購物車挽留彈窗 (Exit-Intent Popup) 與防流失誘因方案。",
            ["彈窗", "購物車", "結帳超時"],
        ),
        (
            "🚚 物流配送時效承諾與退貨成本壓降",
            "如何透過改善物流履約時效 (SLA) 與逆向退貨分流，降低退款率對淨利潤的衝擊？",
            ["物流", "退貨", "sla", "逆向"],
        ),
        (
            "💳 金流閘道授權失敗漏斗排查",
            "分析數據中未完成訂單，可能有哪些是金流刷卡授權超時或失敗導致的？如何建立及時警報？",
            ["金流", "刷卡", "授權", "gateway"],
        ),
        (
            "📦 尾部 30% 低週轉商品搭售出清策略",
            "針對業績佔比低但佔用庫存的尾部品類，顧問推薦哪些搭售 (Bundling) 或階梯促銷策略？",
            ["搭售", "出清", "滯銷", "尾部", "bundle"],
        ),
        (
            "🏷️ 主力熱銷品（Top 20% SKU）價格彈性測試",
            "針對主力熱銷產品，如何進行價格彈性測試以提升毛利額而不損及銷量？",
            ["價格彈性", "調價", "定價"],
        ),
        (
            "👑 VIP 核心會員專屬權益體系設計",
            "如何針對高貢獻核心客群規劃會員分級權益（Tiered Loyalty Program）以鎖定顧客終身價值？",
            ["vip", "會員", "分級", "loyalty"],
        ),
        (
            "⏳ 首購後 90 天二次復購自動化旅程",
            "針對剛完成首購的新客，如何規劃首購後 90 天內的自動化推播節奏促成二次復購？",
            ["復購", "新客", "90天"],
        ),
        (
            "📋 營運團隊每週週會數據檢核清單",
            "請幫營運團隊擬定一份包含 5 項具體排查要點的每週營運數據檢核清單 (Weekly Checklist)。",
            ["週會", "檢核", "清單", "checklist"],
        ),
        (
            "🎯 擬定下季度的 OMTM 關鍵單一指標",
            "根據當前數據暴露的瓶頸，我們下個季度最應該全員對齊的單一關鍵指標 (OMTM) 是什麼？",
            ["omtm", "單一指標", "關鍵指標"],
        ),
    ]

    # Filter out topics already asked by user
    eligible = []
    for label, prompt, kws in candidates:
        if not any(kw in past_text for kw in kws):
            eligible.append((label, prompt))

    if len(eligible) < 3:
        eligible = [(label, prompt) for label, prompt, _ in candidates]

    # Contextual affinity scoring
    c_lower = chart_title.lower()

    def affinity(item: tuple[str, str]) -> float:
        lbl, _ = item
        score = 1.0
        if (
            any(w in c_lower for w in ["會員", "客群", "ltv", "customer"])
            and any(k in lbl for k in ["會員", "復購", "VIP", "新客"])
            or any(w in c_lower for w in ["商品", "品類", "product", "category"])
            and any(k in lbl for k in ["商品", "搭售", "價格", "尾部"])
            or any(w in c_lower for w in ["退款", "取消", "refund", "cancel"])
            and any(k in lbl for k in ["退款", "取消", "物流", "金流", "預算"])
        ):
            score += 3.0
        return score

    eligible.sort(key=affinity, reverse=True)
    top_candidates = eligible[:6]

    # Dynamically rotate based on conversation turn count
    turn_offset = (len(chat_history) * 2) % len(top_candidates)
    rotated = top_candidates[turn_offset:] + top_candidates[:turn_offset]
    return rotated[:3]


def render_fastmcp_chat_widget(
    unique_key: str,
    chart_title: str,
    df: pd.DataFrame,
    initial_diagnostic: str,
    gemini_api_key: str = "",
) -> None:
    """Render a Gemini-style interactive multi-turn consulting chat room for chart diagnostics.

    All turns (from the initial MBB diagnostic report to subsequent user follow-ups)
    are rendered inside a unified conversational container, allowing seamless ongoing dialogue.
    """
    import os

    import streamlit as st

    if not gemini_api_key:
        gemini_api_key = st.session_state.get(
            "sidebar_gemini_api_key", ""
        ) or os.getenv("GEMINI_API_KEY", "")

    history_key = f"mcp_chat_hist_{unique_key}"

    # Auto-initialize or reset if diagnostic content has changed
    if (
        history_key not in st.session_state
        or not st.session_state[history_key]
        or (
            initial_diagnostic
            and st.session_state[history_key][0].get("content") != initial_diagnostic
        )
    ):
        st.session_state[history_key] = [
            {"role": "assistant", "content": initial_diagnostic}
        ]

    st.markdown("---")

    # Dynamic Model Detection (Avoid hardcoding version 2.5 / 3.6 / 3.8)
    model_state_key = f"active_model_{unique_key}"
    if model_state_key not in st.session_state:
        if gemini_api_key:
            try:
                from google import genai

                client = genai.Client(api_key=gemini_api_key)
                detected_name = resolve_active_gemini_model(client)
                st.session_state[model_state_key] = detected_name
            except Exception:  # noqa: BLE001
                st.session_state[model_state_key] = "Gemini AI"
        else:
            st.session_state[model_state_key] = "FastMCP 離線顧問引擎"

    raw_model_name = st.session_state.get(
        "gemini_active_used_model"
    ) or st.session_state.get(model_state_key, "Gemini AI")
    if "gemini" in raw_model_name.lower():
        parts = raw_model_name.replace("models/", "").split("-")
        model_badge = " ".join([p.capitalize() for p in parts])
    else:
        model_badge = raw_model_name

    # Header section with dynamic model badge
    c_head, c_badge = st.columns([3.5, 1.5])
    with c_head:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                <span style="font-size: 1.35rem;">🏛️</span>
                <span style="font-size: 1.15rem; font-weight: 700; color: var(--text-color, #0f172a);">
                    FastMCP 智慧營運顧問 · 對話診斷室
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"分析主題：**{chart_title}** · 您可於下方對話視窗持續追問商業戰術細節"
        )
    with c_badge:
        st.markdown(
            f"""
            <div style="text-align: right; padding-top: 0.25rem;">
                <span style="background: rgba(99, 102, 241, 0.1); color: #6366f1; border: 1px solid rgba(99, 102, 241, 0.25); padding: 4px 10px; border-radius: 9999px; font-size: 0.78rem; font-weight: 600;">
                    ✨ {model_badge} 驅動
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Surface API connection warning if user provided a key that failed authentication
    api_err = st.session_state.get("gemini_api_last_error")
    if api_err and gemini_api_key:
        st.warning(
            f"⚠️ **Gemini 模型連線提示**：{api_err}\n\n*系統已自動啟用 FastMCP 離線顧問引擎為您提供 MBB 結構化分析。*"
        )

    # Render ALL conversation turns in the same unified chat stream (Gemini-style)
    chat_container = st.container()
    with chat_container:
        for idx, msg in enumerate(st.session_state[history_key]):
            if msg["role"] == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    if idx == 0:
                        st.caption("📋 **【初次深入診斷報告 · MBB 基準分析】**")
                    st.markdown(msg["content"])
            else:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])

    # Dynamic & Randomized Follow-up Suggestions based on conversation history
    dynamic_suggestions = get_dynamic_followup_suggestions(
        chart_title=chart_title,
        chat_history=st.session_state[history_key],
        df=df,
    )

    st.markdown("💡 **點選常見追問方向（選項隨對話歷程動態更新）：**")
    cols_sug = st.columns(len(dynamic_suggestions))
    preset_query = None
    turn_idx = len(st.session_state[history_key])

    for i, (label, prompt) in enumerate(dynamic_suggestions):
        with cols_sug[i]:
            if st.button(
                label,
                key=f"btn_sug_{unique_key}_{turn_idx}_{i}",
                width="stretch",
            ):
                preset_query = prompt

    # Gemini-style Chat Input Bar (Form with Enter-to-send support)
    with st.form(key=f"form_chat_{unique_key}_{turn_idx}", clear_on_submit=True):
        col_inp, col_send = st.columns([5, 1])
        with col_inp:
            user_input = st.text_input(
                "輸入您的追問問題",
                value="",
                placeholder="在此輸入問題進一步請教顧問...（例如：若要降低尾部品類流失，推薦具體促銷方案？支援按 Enter 發送）",
                label_visibility="collapsed",
                key=f"input_box_{unique_key}_{turn_idx}",
            )
        with col_send:
            send_btn = st.form_submit_button(
                "發送 💬", type="primary", width="stretch"
            )

    query_to_send = preset_query or (
        user_input.strip() if send_btn and user_input.strip() else None
    )

    if query_to_send:
        # Append user message
        st.session_state[history_key].append({"role": "user", "content": query_to_send})
        with st.spinner("🤖 FastMCP 顧問正在思考並撰寫戰術建議..."):
            reply = continue_fastmcp_chat(
                chat_history=st.session_state[history_key],
                user_message=query_to_send,
                chart_title=chart_title,
                df=df,
                gemini_api_key=gemini_api_key,
            )
            st.session_state[history_key].append(
                {"role": "assistant", "content": reply}
            )
        st.rerun()

    # Reset chat option
    if len(st.session_state[history_key]) > 1:
        _col_opt1, col_opt2 = st.columns([4.2, 1.8])
        with col_opt2:
            if st.button(
                "🗑️ 清空追問歷程",
                key=f"btn_reset_chat_{unique_key}",
                help="清空後續追問，重新回到初次診斷基準報告",
                width="stretch",
            ):
                st.session_state[history_key] = [
                    {"role": "assistant", "content": initial_diagnostic}
                ]
                st.rerun()


def _synthesize_offline_tab_report(
    user_query: str,
    tab_title: str,
    kpis: dict[str, Any],
    tab_payload: dict[str, Any],
    all_tabs_payload: dict[str, Any] | None = None,
    is_zh: bool = True,
) -> str:
    """Offline rule-based MBB diagnostic synthesis grounded on full visibility with current focus priority."""
    gmv_val = kpis.get("總銷售額 (GMV)", kpis.get("gmv", "$1,248,500.00"))
    net_val = kpis.get("實質淨營收 (Net Revenue)", kpis.get("net_revenue", "$1,085,200.00"))
    aov_val = kpis.get("客單價 (AOV)", kpis.get("aov", "$85.50"))
    cancel_val = kpis.get("取消率", "4.2%")
    refund_val = kpis.get("退款率", "2.8%")

    # Optional cross-tab metadata enrichment
    cross_insights = []
    if all_tabs_payload:
        for t_k, t_v in all_tabs_payload.items():
            if t_k != tab_title and isinstance(t_v, dict):
                sub_t = t_v.get("title", t_k)
                if "top_products_summary" in t_v:
                    cross_insights.append(f"【{sub_t}】：高銷售額主力商品呈現 80/20 集中效應")
                elif "customer_segments_summary" in t_v:
                    cross_insights.append(f"【{sub_t}】：Platinum VIP 與 At-Risk 客群回購分化加劇")

    cross_notes = ("\n  - **跨維度全盤視野**：" + "；".join(cross_insights)) if cross_insights else ""

    if is_zh:
        return f"""### 📌 【MBB 核心診斷 Action Title】
**【{tab_title}】業務走勢顯示實質淨營收為 {net_val}，當前取消/退款漏斗耗損約 {cancel_val} / {refund_val}；全盤分析建議聚焦「高毛利品搭售」與「精準定價治理」。**

#### 1. MECE 獲利樹漏斗分解 (Profitability Decomposition · 當前焦點加權)
- **當前焦點指標基線**：GMV 為 {gmv_val}，折損後實質淨額為 {net_val}（平均客單價 {aov_val}）。
- **關鍵議題樹癥結**：
  - **體積與運費漏斗**：大件品項若退貨成本過高，侵蝕邊際貢獻毛利率。
  - **高價值客群黏著度**：核心 VIP 客群貢獻超過 60% 營收，需避免全面促銷折讓傷害品牌價值。{cross_notes}

#### 2. 針對提問「{user_query}」之 30-60-90 天落地藍圖
- **Day 1~30 (速贏止血 Quick Wins)**：排查結帳取消高發環節，檢視異常訂單並建立專屬防漏機制。
- **Day 31~60 (系統優化 Structural Plays)**：在當前分頁核心維度中，強化高 LTV 客群回購機制，停止無差別滿額折扣。
- **Day 61~90 (戰略穩固 Strategic Scale)**：建立常態性退款與毛利預警雷達，鎖定供應商階梯折讓以降低單位成本。
"""
    return f"""### 📌 【MBB Executive Action Title】
**Net Revenue in 【{tab_title}】 stands at {net_val}; recommended immediate focus on high-margin cross-selling and refund leakage mitigation across full lakehouse metrics.**

#### 1. MECE Profitability Tree Decomposition (Current Focus Weighted)
- **Baseline Metrics**: GMV {gmv_val}, Net Revenue {net_val}, AOV {aov_val} (Cancellation {cancel_val}, Refund {refund_val}).
- **Key Bottlenecks**: High refund frequency on bulky categories and excessive promotional markdowns.

#### 2. 30-60-90 Day Tactical Roadmap for: "{user_query}"
- **Day 1-30 (Quick Wins)**: Audit checkout drop-offs and optimize freight charges on return-prone items.
- **Day 31-60 (Structural Plays)**: Implement VIP retention bundles and personalized re-engagement campaigns.
- **Day 61-90 (Strategic Scale)**: Establish automated unit-economic margin guards and volume tiered discounts.
"""


def _execute_tab_scoped_diagnostic(
    user_query: str,
    tab_title: str,
    tab_payload: dict[str, Any],
    all_tabs_payload: dict[str, Any] | None = None,
    api_key: str = "",
    preferred_model: str = "auto",
    language: str = "zh",
) -> str:
    """Execute MBB consulting diagnosis with Global Lakehouse Visibility + Current Visual Focus Priority."""
    import json
    import os

    is_zh = language == "zh"
    clean_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    system_instruction = (
        "你是擁有麥肯錫 (McKinsey) / 貝恩 (Bain) / BCG 資深合夥人（Senior Partner）水準的頂級管理顧問，"
        "專精於現代零售電商與現代數據架構（Lakehouse）全盤商業診斷與營運獲利優化。\n\n"
        "【分析架構規範：全盤視野 ＋ 當前焦點加權】：\n"
        "1. 全盤視野 (Global Lakehouse Visibility)：\n"
        "   - 你擁有當前資料層的全盤數據視角（涵蓋營收走勢、訂單狀態、商品類別排行、客戶 LTV 分群、資料工程管線等全維度指標）。\n"
        "   - 鼓勵且主動進行跨分頁、跨維度的綜合交叉歸因（例如：若探討營收漏斗退款，可直接關聯熱銷商品分類退貨、高風險客群流失等全盤維度）。\n"
        "   - 嚴禁以「我看不到其他分頁數據」或「請先切換至該分頁」等受限理由拒答！只要全盤數據字典中有相應指標，均應積極綜合推演。\n"
        f"2. 當前焦點加權 (Current Visual Focus Priority)：\n"
        f"   - 使用者當前正在查看的分頁為【當前視覺焦點：{tab_title}】。\n"
        "   - 若使用者提出廣義問題或未指明特定圖表，請給予當前視覺焦點最高權重（約 60-70%），並以其核心指標為論述主軸，輔以全盤其他維度（約 30-40%）作為交叉論證，提供立體且縱深的商業診斷。\n\n"
        "【你的核心方法論規範（源自 claude-skill-management-consultant-B1 知識庫）】：\n"
        "1. 嚴格通過「顧問三大檢驗」：\n"
        "   - So What?（提煉高階商業洞察，而非單純復述或朗讀數據）\n"
        "   - Why So?（MECE 因果歸因與單位經濟學數學論證）\n"
        "   - Now What?（高 ROI 且具體可落地的商業行動處方）\n"
        "2. 金字塔原理 (Pyramid Principle) 與結論先行 (Action Title)：\n"
        "   - 嚴禁廢話或寒暄客套（絕對不要以『你好！我是顧問...』開場）。\n"
        "   - 報告第一句話必須是加粗顯眼的【核心診斷結論 / Action Title】：一針見血指出當前商業與財務癥結點。\n"
        "3. MECE 議題樹與獲利算式拆解 (Show the Math)：\n"
        "   - 運用獲利樹拆解核心指標：Profit = GMV × (1 - 取消率 - 退款率) × 毛利率 - Opex。\n"
        "   - 計算淨營收實現率 (Net Realization Rate = Net Revenue / GMV)，明確量化流失的具體金額。\n"
        "4. 30-60-90 天戰術落地路徑 (Actionable 30-60-90 Day Roadmap)：\n"
        "   - Day 1~30 (速贏止血 Quick Wins)\n"
        "   - Day 31~60 (系統優化 Structural Plays)\n"
        "   - Day 61~90 (戰略穩固 Strategic Scale)"
        if is_zh
        else (
            "You are an MBB Senior Partner management consultant specializing in e-commerce profitability and unit economics.\n"
            "Framework: Global Lakehouse Visibility + Current Visual Focus Priority.\n"
            f"- Current Visual Focus (Primary Weight ~60-70%): 【{tab_title}】.\n"
            "- Global Lakehouse Visibility: You have full access to all layer dimensions (revenue, products, customer cohorts, pipeline logs). "
            "Cross-correlate insights freely; never refuse questions or claim data from other tabs is unavailable.\n"
            "Apply Pyramid Principle: Action Title first in bold, MECE decomposition, and 30-60-90 day tactical roadmap."
        )
    )

    prompt_content = (
        f"【使用者業務問題】：{user_query}\n\n"
        f"【當前視覺焦點（最高權重主軸）：{tab_title}】指標數據：\n"
        f"```json\n{json.dumps(tab_payload, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
        f"【全盤湖倉視野（可跨分頁自由交叉推演）】全維度數據字典：\n"
        f"```json\n{json.dumps(all_tabs_payload or {}, ensure_ascii=False, indent=2, default=str)}\n```"
    )

    if clean_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=clean_key)
            candidate_models = get_gemini_candidate_models(client, preferred_model=preferred_model)

            for cand in candidate_models:
                try:
                    resp = client.models.generate_content(
                        model=cand,
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.2,
                        ),
                    )
                    if resp and resp.text:
                        badge = f"✨ **[模型：`{cand}` · 全盤視野 ＋ 當前焦點加權]**\n\n"
                        return badge + resp.text
                except Exception as e:
                    err_msg = str(e)
                    if any(k in err_msg for k in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand", "404", "NOT_FOUND"]):
                        continue
                    raise e
        except Exception:  # noqa: BLE001
            pass

    # Offline Fallback MBB synthesis based on tab_payload + all_tabs_payload
    kpis = tab_payload.get("kpis", {})
    return _synthesize_offline_tab_report(user_query, tab_title, kpis, tab_payload, all_tabs_payload, is_zh)


def render_fastmcp_advisor_drawer(
    current_layer: str,
    base_tab_titles: list[str],
    tab_data_map: dict[str, Any],
    active_tab_title: str | None = None,
    language: str = "zh",
) -> None:
    """Render the symmetrical Right Collapsible Sidebar (Right Sidebar / Mode B).

    Engineered as an independent app-level right sidebar matching Streamlit's left st.sidebar:
    - Fixed full height (100vh), anchored to the right viewport.
    - Zero overlay / zero backdrop mask.
    - Dynamic margin-push on .main .block-container so the main dashboard resizes side-by-side.
    - Symmetrical collapse button '>>' mirroring the left sidebar's '<<'.
    - Global lakehouse visibility with current focus priority weighting.
    """
    import os
    import re
    import streamlit as st

    is_zh = language == "zh"

    # Determine Active Tab Context Scope automatically
    active_scope = None
    if active_tab_title:
        if active_tab_title in tab_data_map:
            active_scope = active_tab_title
        else:
            for k in tab_data_map:
                if k in active_tab_title or active_tab_title in k:
                    active_scope = k
                    break
    if not active_scope:
        active_scope = base_tab_titles[0] if base_tab_titles else (list(tab_data_map.keys())[0] if tab_data_map else "")

    tab_payload = tab_data_map.get(active_scope, {})
    tab_display_title = tab_payload.get("title", active_scope)
    safe_scope_id = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]", "", active_scope or "default")

    # Inject Pinned Floating Viewport-Following CSS for AI Advisor Right Column
    st.markdown(
        """
        <style>
        /* 1. Ensure top-level two-column layout stretches cleanly */
        div[data-testid="stHorizontalBlock"]:has(#right-ai-sidebar-marker),
        div[data-testid="stHorizontalBlock"]:has(.st-key-ai_advisor_sticky_card) {
            align-items: stretch !important;
        }

        /* 2. Pinned Viewport Full-Height: AI Advisor extends vertically from top to bottom (100vh) */
        @media (min-width: 992px) {
            .st-key-ai_advisor_sticky_card,
            div.st-key-ai_advisor_sticky_card,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#right-ai-sidebar-marker),
            div[data-testid="column"]:has(#right-ai-sidebar-marker) > div[data-testid="stVerticalBlock"] > div.element-container:has(#right-ai-sidebar-marker) + div,
            div[data-testid="column"]:has(#right-ai-sidebar-marker) div[data-testid="stVerticalBlockBorderWrapper"] {
                position: fixed !important;
                top: 0 !important;
                bottom: 0 !important;
                right: 0 !important;
                height: 100vh !important;
                max-height: 100vh !important;
                width: 28.5vw !important;
                max-width: 480px !important;
                min-width: 340px !important;
                overflow-y: auto !important;
                z-index: 999 !important;
                box-shadow: -6px 0 28px rgba(0, 0, 0, 0.06) !important;
                border-top: none !important;
                border-bottom: none !important;
                border-right: none !important;
                border-left: 1px solid rgba(226, 232, 240, 0.95) !important;
                background-color: #ffffff !important;
                border-radius: 0 !important;
                padding: 3.85rem 1.25rem 1.5rem 1.25rem !important;
                box-sizing: border-box !important;
                color: #0f172a !important;
            }
        }

        @media (max-width: 991px) {
            .st-key-ai_advisor_sticky_card,
            div.st-key-ai_advisor_sticky_card,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(#right-ai-sidebar-marker) {
                position: relative !important;
                width: 100% !important;
                max-width: 100% !important;
                height: auto !important;
                max-height: none !important;
                background-color: #ffffff !important;
                border: 1px solid rgba(226, 232, 240, 0.95) !important;
                border-radius: 14px !important;
                padding: 1.25rem !important;
                color: #0f172a !important;
            }
        }

        /* White theme styling for chat messages and containers inside advisor card */
        .st-key-ai_advisor_sticky_card div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
        }

        /* Dynamic vertical stretch for chat messages container */
        .st-key-ai_advisor_sticky_card div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatMessage"]) {
            height: calc(100vh - 395px) !important;
            max-height: calc(100vh - 395px) !important;
            min-height: 420px !important;
        }

        .st-key-ai_advisor_sticky_card [data-testid="stChatMessage"] {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
            color: #1e293b !important;
        }

        .st-key-ai_advisor_sticky_card [data-testid="stChatMessage"] * {
            color: #1e293b !important;
        }

        .st-key-ai_advisor_sticky_card [data-testid="stChatMessage"] strong {
            color: #0f172a !important;
        }

        .st-key-ai_advisor_sticky_card [data-testid="stChatMessage"] code {
            background-color: #f1f5f9 !important;
            color: #2563eb !important;
            border-radius: 4px !important;
            padding: 2px 5px !important;
        }

        .st-key-ai_advisor_sticky_card [data-testid="stExpander"] {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
        }

        .st-key-ai_advisor_sticky_card [data-testid="stExpander"] summary span {
            color: #334155 !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.html(
        """
        <script>
        (function() {
            function syncAdvisorPosition() {
                try {
                    const doc = window.parent.document || document;
                    const marker = doc.getElementById('right-ai-sidebar-marker');
                    if (!marker) return;
                    
                    const card = marker.closest('[data-testid="stVerticalBlockBorderWrapper"]') || 
                                 marker.closest('.st-key-ai_advisor_sticky_card') ||
                                 doc.querySelector('.st-key-ai_advisor_sticky_card');
                    
                    const col = marker.closest('[data-testid="column"]') || 
                                doc.querySelector('[data-testid="column"]:has(#right-ai-sidebar-marker)');
                    
                    if (card && col && window.innerWidth >= 992) {
                        const colRect = col.getBoundingClientRect();
                        const rightWidth = Math.max(340, window.innerWidth - colRect.left);
                        card.style.position = 'fixed';
                        card.style.top = '0px';
                        card.style.bottom = '0px';
                        card.style.right = '0px';
                        card.style.height = '100vh';
                        card.style.maxHeight = '100vh';
                        card.style.width = Math.min(480, rightWidth) + 'px';
                        card.style.overflowY = 'auto';
                        card.style.zIndex = '999';
                        card.style.borderRadius = '0px';
                        card.style.borderTop = 'none';
                        card.style.borderBottom = 'none';
                        card.style.borderRight = 'none';
                        card.style.paddingTop = '3.85rem';
                        card.style.boxSizing = 'border-box';
                    }
                } catch(e) {}
            }
            syncAdvisorPosition();
            setTimeout(syncAdvisorPosition, 80);
            setTimeout(syncAdvisorPosition, 250);
            setTimeout(syncAdvisorPosition, 600);
            window.addEventListener('resize', syncAdvisorPosition);
            if (window.parent && window.parent !== window) {
                window.parent.addEventListener('resize', syncAdvisorPosition);
            }
        })();
        </script>
        """
    )

    # Right Sidebar Container (Fixed viewport-pinned within top-level right column)
    with st.container(key="ai_advisor_sticky_card", border=True):
        st.markdown('<div id="right-ai-sidebar-marker"></div>', unsafe_allow_html=True)

        # Header section: Title, FAST MCP badge, active scope & Symmetrical Collapse button '>>'
        head_col, close_col = st.columns([3.8, 1.2])
        with head_col:
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 2px;">
                    <span style="font-size: 1.2rem;">✨</span>
                    <span style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">
                        {'AI 決策顧問' if is_zh else 'AI Operations Advisor'}
                    </span>
                    <span style="font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; background: rgba(99, 102, 241, 0.1); color: #4f46e5; border: 1px solid rgba(99, 102, 241, 0.25); font-weight: 700; font-family: monospace;">FAST MCP</span>
                </div>
                <div style="font-size: 0.76rem; color: #64748b; margin-top: 4px; line-height: 1.4;">
                    🌐 {'全盤湖倉視野' if is_zh else 'Global Visibility'} · 🎯 {'當前焦點：' if is_zh else 'Focus: '}<strong style="color: #2563eb;">【{tab_display_title}】</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with close_col:
            if st.button(
                ">>",
                key=f"btn_collapse_advisor_{safe_scope_id}",
                width="stretch",
                help="收起 AI 顧問右側邊欄 (>>)" if is_zh else "Collapse Right Sidebar (>>)",
            ):
                st.session_state["show_ai_drawer"] = False
                st.rerun()

        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

        # One-Click Diagnostic Recommendations (Directly matching ERP ai-consultant-drawer.tsx)
        st.markdown(
            f"""
            <div style="font-size: 0.78rem; font-weight: 600; color: #475569; margin-bottom: 6px; display: flex; align-items: center; gap: 4px;">
                <span>⚡</span> {'一鍵管理診斷推薦：' if is_zh else 'One-Click Quick Diagnostics:'}
            </div>
            """,
            unsafe_allow_html=True,
        )

        quick_prompts = [
            {
                "label": "🔍 診斷指標異常" if is_zh else "🔍 Metric Anomalies",
                "query": f"請以麥肯錫 SCQA 結構診斷【{tab_display_title}】目前是否有隱匿的毛利、訂單或營運異常，並結合全盤指標給予歸因？"
                if is_zh
                else f"Diagnose latent anomalies in 【{tab_display_title}】 using McKinsey SCQA framework with cross-chart correlation.",
            },
            {
                "label": "🔮 預測營運風險" if is_zh else "🔮 Forecast Risk",
                "query": f"依據當前數據模型，請評估未來 90 天【{tab_display_title}】可能面臨的風險與對應策略方案。"
                if is_zh
                else f"Forecast next 90-day risks and tactical counter-measures for 【{tab_display_title}】.",
            },
            {
                "label": "📋 C-Level 清單" if is_zh else "📋 C-Level Action",
                "query": f"請依金字塔原理列出【{tab_display_title}】優先級最高 3 項管理改善建議、負責人與追蹤指標。"
                if is_zh
                else f"List top 3 C-Level actionable interventions and KPIs for 【{tab_display_title}】 via Pyramid Principle.",
            },
        ]

        clicked_prompt_query = None
        qp_col1, qp_col2, qp_col3 = st.columns(3)
        cols = [qp_col1, qp_col2, qp_col3]
        for idx, p in enumerate(quick_prompts):
            with cols[idx]:
                if st.button(p["label"], key=f"quick_prompt_{idx}_{safe_scope_id}", width="stretch", help=p["query"]):
                    clicked_prompt_query = p["query"]

        # Chat history state for active tab scope
        hist_key = f"ai_advisor_chat_hist_{safe_scope_id}"
        if hist_key not in st.session_state:
            welcome_intro = (
                f"您好！我是您的 **MBB 商業管理諮詢顧問 AI**（基於 Gemini 與 FAST MCP）。\n\n"
                f"🌐 **全盤視野**：我已同步載入當前資料層之所有業務指標與維度字典，支援跨分頁全域因果歸因。\n"
                f"🎯 **當前焦點**：當前視覺焦點鎖定在 **【{tab_display_title}】**，提問將優先以本維度為主軸進行深度診斷。\n\n"
                f"您可以直接提問（例：指標異常、跨品類退款歸因、或預測風險），或點選上方一鍵快捷診斷。"
                if is_zh
                else f"Hello! I am your **MBB Management Consulting Advisor AI** (Powered by Gemini & FastMCP).\n\n"
                f"🌐 **Global Visibility**: Full layer metrics loaded for cross-chart root-cause correlation.\n"
                f"🎯 **Current Focus**: Anchored on **【{tab_display_title}】**.\n\n"
                f"Ask any question or click the quick diagnostics above!"
            )
            st.session_state[hist_key] = [{"role": "assistant", "content": welcome_intro}]

        # Chat conversation messages container (Vertically expanded to fill full height)
        with st.container(height=540, border=True):
            for msg in st.session_state[hist_key]:
                avatar = "🤖" if msg["role"] == "assistant" else "👤"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # Chat Input Form
        with st.form(key=f"advisor_form_{safe_scope_id}", clear_on_submit=True):
            f_inp, f_btn = st.columns([4.2, 1.2])
            with f_inp:
                form_text = st.text_input(
                    "向 AI 顧問提問...",
                    placeholder="向 AI 顧問提問（例：分析指標異常、制定改善策略...）" if is_zh else "Ask AI Advisor...",
                    label_visibility="collapsed",
                    key=f"inp_text_{safe_scope_id}",
                )
            with f_btn:
                form_submitted = st.form_submit_button("送出 🚀" if is_zh else "Send 🚀", type="primary", width="stretch")

        query_to_run = clicked_prompt_query or (form_text.strip() if form_submitted and form_text.strip() else None)

        if query_to_run:
            st.session_state[hist_key].append({"role": "user", "content": query_to_run})

            with st.spinner("🤖 Gemini 正在調用 MBB 顧問框架推演模型..." if is_zh else "🤖 Gemini analyzing with MBB consulting framework..."):
                reply_report = _execute_tab_scoped_diagnostic(
                    user_query=query_to_run,
                    tab_title=tab_display_title,
                    tab_payload=tab_payload,
                    all_tabs_payload=tab_data_map,
                    api_key=st.session_state.get("gemini_api_key", ""),
                    preferred_model=st.session_state.get("drawer_selected_model", "auto"),
                    language=language,
                )
                st.session_state[hist_key].append({"role": "assistant", "content": reply_report})
            st.rerun()

        # Collapsible Settings Expander (Matching ERP's API key toggle, collapsed by default)
        current_key = st.session_state.get("gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")
        expander_title = (
            f"⚙️ 設定 Gemini API Key {'(✅ 已連線即時模型)' if current_key else '(💡 使用內建 MBB 推演·可點此填寫金鑰)'}"
            if is_zh
            else f"⚙️ Gemini API Key Settings {'(Connected)' if current_key else '(Offline MBB Engine)'}"
        )

        with st.expander(expander_title, expanded=False):
            # LocalStorage Auto-loader
            st.html(
                """
                <script>
                (function() {
                    try {
                        const saved = localStorage.getItem("platzi_gemini_api_key");
                        if (saved) {
                            const inputs = window.parent.document.querySelectorAll('input[type="password"]');
                            inputs.forEach(inp => {
                                if (!inp.value) {
                                    inp.value = saved;
                                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                            });
                        }
                    } catch(e) {}
                })();
                </script>
                """
            )

            user_input_key = st.text_input(
                "輸入 Google Gemini API Key" if is_zh else "Enter Google Gemini API Key",
                type="password",
                value=current_key,
                placeholder="AIzaSy...",
                key=f"key_input_{safe_scope_id}",
                help="輸入您的 Gemini API Key 啟用雲端即時 LLM 推論。未輸入時自動啟用內建 MBB 諮詢引擎。",
            )

            if user_input_key:
                st.session_state["gemini_api_key"] = user_input_key.strip()
                clean_k = user_input_key.strip()
                if clean_k.startswith("AIza"):
                    st.success("✅ 金鑰格式正確 (AIzaSy...)" if is_zh else "✅ Valid API Key format")
                elif clean_k.startswith("AQ.") or clean_k.startswith("ya29."):
                    st.error("❌ OAuth 憑證，非 Gemini API Key" if is_zh else "❌ OAuth token, not Gemini Key")
                else:
                    st.warning("⚠️ 提醒：通常以 AIzaSy 開頭" if is_zh else "⚠️ Notice: Usually starts with AIzaSy")

            remember_key = st.checkbox(
                "💾 在此瀏覽器記住金鑰 (LocalStorage)" if is_zh else "💾 Remember Key in browser",
                value=st.session_state.get("remember_gemini_key", False),
                key=f"remember_key_cb_{safe_scope_id}",
            )

            if remember_key and user_input_key:
                st.session_state["remember_gemini_key"] = True
                st.html(
                    f"""
                    <script>
                    try {{ localStorage.setItem("platzi_gemini_api_key", "{user_input_key.strip()}"); }} catch(e) {{}}
                    </script>
                    """
                )
            elif not remember_key:
                st.session_state["remember_gemini_key"] = False
                st.html(
                    """
                    <script>
                    try { localStorage.removeItem("platzi_gemini_api_key"); } catch(e) {}
                    </script>
                    """
                )

            st.selectbox(
                "⚡ 偏好 Gemini 模型：" if is_zh else "⚡ Preferred Model:",
                options=["auto", "gemini-2.5-flash", "gemini-3.6-flash", "gemini-3.8-flash"],
                format_func=lambda x: {
                    "auto": "🚀 自動最適配（遇負載自動降級）" if is_zh else "🚀 Auto Adaptive",
                    "gemini-2.5-flash": "🛡️ Gemini 2.5 Flash（穩定推薦）" if is_zh else "🛡️ Gemini 2.5 Flash",
                    "gemini-3.6-flash": "⚡ Gemini 3.6 Flash" if is_zh else "⚡ Gemini 3.6 Flash",
                    "gemini-3.8-flash": "⭐ Gemini 3.8 Flash" if is_zh else "⭐ Gemini 3.8 Flash",
                }.get(x, x),
                key=f"model_sel_{safe_scope_id}",
            )

        # Clear Chat History Button
        if len(st.session_state[hist_key]) > 1:
            if st.button("🗑️ 清空對話記錄" if is_zh else "🗑️ Clear Chat History", key=f"clear_hist_{safe_scope_id}", width="stretch", type="secondary"):
                del st.session_state[hist_key]
                st.rerun()

