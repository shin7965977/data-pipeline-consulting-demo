import pandas as pd

from fastmcp_diagnostic import run_fastmcp_chart_diagnostic


def test_run_fastmcp_chart_diagnostic_offline():
    """Test FastMCP Mode A offline synthesis without Gemini API key."""
    df_sample = pd.DataFrame(
        {
            "order_date": pd.to_datetime(["2026-09-15", "2026-09-16", "2026-09-17"]),
            "gmv": [1000.0, 1500.0, 800.0],
            "net_revenue": [900.0, 1350.0, 700.0],
            "completed_orders": [18, 27, 14],
            "refunded_orders": [2, 3, 4],
            "cancelled_orders": [1, 2, 2],
        }
    )

    report = run_fastmcp_chart_diagnostic(
        chart_title="每日 GMV 與實質淨營收對比走勢",
        df=df_sample,
        prompt_intent="請幫我畫出每日 GMV 與實質淨營收的對比走勢圖",
        gemini_api_key="",
    )

    # Verify MBB consulting standards
    assert "FastMCP" in report or "MBB" in report
    assert "SCQA" in report or "現狀" in report or "痛點" in report
    assert "MECE" in report or "議題樹" in report
    assert "30-60-90" in report or "落地方針" in report
    assert "GMV" in report or "淨營收" in report


def test_run_fastmcp_chart_diagnostic_empty_df():
    """Test FastMCP Mode A when given empty dataframe."""
    df_empty = pd.DataFrame()
    report = run_fastmcp_chart_diagnostic(
        chart_title="空圖表",
        df=df_empty,
    )
    assert "無足夠數據" in report


def test_continue_fastmcp_chat_offline_suggestions():
    """Test multi-turn chat offline responses for common consulting follow-ups."""
    from fastmcp_diagnostic import continue_fastmcp_chat

    df_sample = pd.DataFrame({"gmv": [1000.0, 2000.0], "net_revenue": [900.0, 1800.0]})
    history = [{"role": "assistant", "content": "Initial report"}]

    # Test 1: SMS template
    reply_sms = continue_fastmcp_chat(
        history, "請給我挽回簡訊 SMS 模板", "營收走勢", df_sample
    )
    assert "SMS" in reply_sms or "簡訊" in reply_sms
    assert "VIPRECOVER" in reply_sms

    # Test 2: Budget allocation
    reply_budget = continue_fastmcp_chat(
        history, "10萬元預算該優先投退款還是取消？", "營收走勢", df_sample
    )
    assert "預算" in reply_budget
    assert "取消" in reply_budget

    # Test 3: Board executive summary
    reply_board = continue_fastmcp_chat(
        history, "幫我產出給董事會的摘要", "營收走勢", df_sample
    )
    assert "董事會" in reply_board or "C-Level" in reply_board

    # Test 4: Empty query handling
    reply_empty = continue_fastmcp_chat(history, "", "營收走勢", df_sample)
    assert "請輸入" in reply_empty


def test_render_fastmcp_chat_widget_signature():
    """Verify render_fastmcp_chat_widget parameters and fallback handling."""
    import inspect

    from fastmcp_diagnostic import render_fastmcp_chat_widget

    sig = inspect.signature(render_fastmcp_chat_widget)
    params = list(sig.parameters.keys())
    assert "unique_key" in params
    assert "chart_title" in params
    assert "df" in params
    assert "initial_diagnostic" in params
    assert "gemini_api_key" in params


def test_get_dynamic_followup_suggestions():
    from fastmcp_diagnostic import get_dynamic_followup_suggestions

    df_sample = pd.DataFrame({"gmv": [1000.0, 2000.0]})

    # 1. Opening turn: returns 3 suggestions
    hist_turn1 = [{"role": "assistant", "content": "Initial report"}]
    suggs1 = get_dynamic_followup_suggestions("每日 GMV 走勢", hist_turn1, df_sample)
    assert len(suggs1) == 3

    # 2. If user already asked about SMS, SMS should be filtered out
    hist_turn2 = [
        {"role": "assistant", "content": "Initial report"},
        {"role": "user", "content": "請給我挽回簡訊 SMS 模板"},
        {"role": "assistant", "content": "這是 VIPRECOVER 簡訊模板"},
    ]
    suggs2 = get_dynamic_followup_suggestions("每日 GMV 走勢", hist_turn2, df_sample)
    assert len(suggs2) == 3
    # Ensure SMS is filtered out
    labels2 = [s[0] for s in suggs2]
    assert not any("簡訊" in lbl for lbl in labels2)


def test_resolve_active_gemini_model_fallback():
    from fastmcp_diagnostic import resolve_active_gemini_model

    class MockModel:
        def __init__(self, name):
            self.name = name

    class MockClient:
        class models:
            @staticmethod
            def list():
                return [
                    MockModel("models/gemini-2.5-flash"),
                    MockModel("models/gemini-3.6-flash"),
                    MockModel("models/gemini-3.8-flash"),
                    MockModel("models/gemini-1.0-pro"),
                ]

    best_model = resolve_active_gemini_model(MockClient())
    assert best_model == "gemini-3.8-flash"


def test_get_gemini_candidate_models():
    from fastmcp_diagnostic import get_gemini_candidate_models

    class MockModel:
        def __init__(self, name):
            self.name = name

    class MockClient:
        class models:
            @staticmethod
            def list():
                return [
                    MockModel("models/gemini-2.5-flash"),
                    MockModel("models/gemini-3.6-flash"),
                    MockModel("models/gemini-3.8-flash"),
                ]

    # Test auto candidate list
    cands_auto = get_gemini_candidate_models(MockClient(), preferred_model="auto")
    assert cands_auto[0] == "gemini-3.8-flash"
    assert "gemini-3.6-flash" in cands_auto
    assert "gemini-2.5-flash" in cands_auto

    # Test manual preference to 3.6
    cands_36 = get_gemini_candidate_models(
        MockClient(), preferred_model="gemini-3.6-flash"
    )
    assert cands_36[0] == "gemini-3.6-flash"
    assert "gemini-2.5-flash" in cands_36
