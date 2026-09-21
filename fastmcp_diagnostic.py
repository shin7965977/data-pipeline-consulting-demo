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
                use_container_width=True,
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
                "發送 💬", type="primary", use_container_width=True
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
                use_container_width=True,
            ):
                st.session_state[history_key] = [
                    {"role": "assistant", "content": initial_diagnostic}
                ]
                st.rerun()
