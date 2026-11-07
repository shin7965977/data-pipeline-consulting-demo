"""Unit tests for the Dynamic Codebase Introspection Engine and Onboarding Wizard."""

import json
from pathlib import Path

from onboarding_wizard import (
    introspect_codebase,
    main,
    synthesize_dynamic_chart_proposals,
)


def test_introspect_codebase_detects_existing_modules():
    """Verify that the introspection engine discovers standard repository components."""
    result = introspect_codebase()

    # Sources and Adapters
    source_names = [s["name"] for s in result["sources"]]
    assert "platzi_store" in source_names

    adapter_names = [a["name"] for a in result["adapters"]]
    assert "platzi_adapter" in adapter_names

    # Gold Marts
    mart_names = [m["model_name"] for m in result["gold_marts"]]
    assert "gold_daily_sales_kpi" in mart_names
    assert "gold_customer_ltv" in mart_names
    assert "gold_product_performance" in mart_names

    # Destinations
    assert "duckdb" in result["destinations"]
    assert "bigquery" in result["destinations"]

    # Deliverables
    deliverable_names = [d["name"] for d in result["deliverables"]]
    assert "generate_pitch_deck.py" in deliverable_names
    assert "chart_generator.py" in deliverable_names

    # Health & FinOps & Looker
    assert "finops_budget_limit_mb" in result["health"]
    assert result["health"]["finops_budget_limit_mb"] == 100
    assert "Looker Studio" in result["health"]["default_bi_engine"]


def test_dynamic_chart_proposals_data_driven():
    """Verify chart proposals dynamically adapt to arbitrary datasets and default to Looker on Streamlit."""
    # Scenario A: Ad Marketing Campaign Data
    marketing_cols = [
        "campaign_date",
        "ad_channel",
        "clicks",
        "impressions",
        "cost",
        "conversions",
    ]
    proposals_mkt = synthesize_dynamic_chart_proposals(marketing_cols)
    assert len(proposals_mkt) == 3

    # Engine must default to Looker Studio embedded in Streamlit Cockpit
    for p in proposals_mkt:
        assert "Looker Studio" in p["framework"]["C_Tool_Engine"]
        assert "Streamlit" in p["framework"]["C_Tool_Engine"]

    # Proposals must reference the actual marketing fields, not hardcoded retail terms
    assert "campaign_date" in str(proposals_mkt[0]["framework"]["D_Data_Specs"])
    assert any(
        col in str(proposals_mkt[1]["framework"]["D_Data_Specs"])
        for col in ["ad_channel", "clicks", "cost", "conversions"]
    )

    # Scenario B: Human Resources / Staffing Data
    hr_cols = ["hire_date", "department", "headcount", "salary", "attrition_rate"]
    proposals_hr = synthesize_dynamic_chart_proposals(hr_cols)
    assert len(proposals_hr) == 3
    assert "department" in str(proposals_hr[1]["framework"]["D_Data_Specs"])
    # Ensure no hardcoded retail terms appear
    for p in proposals_hr:
        assert "gmv" not in str(p).lower()
        assert "platzi" not in str(p).lower()


def test_dynamic_adaptation_on_new_modules(tmp_path: Path):
    """Verify that adding new source adapters or Gold models dynamically updates introspection."""
    # Scaffold temporary mock project
    mock_sources = tmp_path / "ingestion" / "sources"
    mock_sources.mkdir(parents=True)
    (mock_sources / "shopify_store.py").write_text("# shopify source", encoding="utf-8")

    mock_domain = tmp_path / "domain"
    mock_domain.mkdir(parents=True)
    (mock_domain / "shopify_adapter.py").write_text(
        "# shopify adapter", encoding="utf-8"
    )

    mock_marts = tmp_path / "transform_dbt" / "models" / "marts"
    mock_marts.mkdir(parents=True)
    (mock_marts / "gold_marketing_attribution.sql").write_text(
        "SELECT 1", encoding="utf-8"
    )

    result = introspect_codebase(base_dir=tmp_path)

    # Must dynamically detect newly created shopify source and adapter
    assert any(s["name"] == "shopify_store" for s in result["sources"])
    assert any(a["name"] == "shopify_adapter" for a in result["adapters"])

    # Must dynamically detect newly created gold marketing attribution mart
    assert any(
        m["model_name"] == "gold_marketing_attribution" for m in result["gold_marts"]
    )


def test_onboarding_wizard_cli_json(monkeypatch, capsys):
    """Test CLI --introspect flag prints valid JSON."""
    monkeypatch.setattr("sys.argv", ["onboarding_wizard.py", "--introspect"])
    main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "sources" in data
    assert "gold_marts" in data
    assert "health" in data
