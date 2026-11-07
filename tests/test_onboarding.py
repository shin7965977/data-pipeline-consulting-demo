"""Unit tests for the Dynamic Codebase Introspection Engine and Onboarding Wizard."""

import json
from pathlib import Path

from onboarding_wizard import introspect_codebase, main


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

    # Health & FinOps
    assert "finops_budget_limit_mb" in result["health"]
    assert result["health"]["finops_budget_limit_mb"] == 100


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


def test_recommend_dynamic_charts_iot_domain():
    """Verify chart recommendations for non-ecommerce IoT sensor data."""
    iot_cols = ["device_id", "timestamp", "temperature", "voltage", "status"]
    from onboarding_wizard import recommend_dynamic_charts

    charts = recommend_dynamic_charts(iot_cols)
    assert len(charts) == 3

    # Must suggest waterfall or funnel for status + metric
    assert any(c["chart_type"] in ["waterfall", "funnel"] for c in charts)
    # Must suggest line trend for timestamp + metric
    assert any(c["chart_type"] == "line" for c in charts)
    # Must suggest 2x2 quadrant for temperature vs voltage
    assert any(c["chart_type"] == "quadrant_2x2" for c in charts)
    # Assert column names are dynamically embedded in titles
    assert any(
        "temperature" in c["action_title"].lower()
        or "voltage" in c["action_title"].lower()
        for c in charts
    )


def test_recommend_dynamic_charts_hr_domain():
    """Verify chart recommendations for HR workforce dataset."""
    hr_cols = [
        "employee_id",
        "department",
        "salary",
        "performance_score",
        "attrition_status",
    ]
    from onboarding_wizard import recommend_dynamic_charts

    charts = recommend_dynamic_charts(hr_cols)
    assert len(charts) == 3

    # Must suggest status attrition waterfall
    assert any(c["chart_type"] == "waterfall" for c in charts)
    # Must suggest 2x2 matrix for salary vs performance_score
    assert any(c["chart_type"] == "quadrant_2x2" for c in charts)


def test_onboarding_wizard_cli_recommend_charts(monkeypatch, capsys):
    """Test CLI --recommend-charts flag output."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "onboarding_wizard.py",
            "--recommend-charts",
            "event_time",
            "severity_score",
            "cluster_region",
            "stage",
        ],
    )
    main()
    captured = capsys.readouterr()
    charts = json.loads(captured.out)
    assert len(charts) >= 2
    assert any("severity_score" in c["y"] or "severity_score" in c["x"] for c in charts)
