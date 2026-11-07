"""Unit & Contract Tests for PlatziAdapter."""

import pandas as pd
import pytest
from platzi_adapter import PlatziAdapter


@pytest.fixture
def adapter():
    return PlatziAdapter()


def test_adapter_metadata(adapter):
    assert adapter.project_id
    assert "Platzi" in adapter.brand_title
    assert adapter.brand_icon == "🛒"
    assert adapter.default_language == "zh"
    assert len(adapter.kpi_cards) == 4


def test_adapter_kpi_calculations(adapter):
    mock_data = {
        "kpi": pd.DataFrame(
            {
                "order_date": pd.to_datetime(["2026-09-15"]),
                "gmv": [300000.0],
                "net_revenue": [270000.0],
                "completed_orders": [2000],
            }
        ),
        "customers": pd.DataFrame({"customer_id": range(250)}),
    }

    card_results = {card.key: card.calculate(mock_data) for card in adapter.kpi_cards}
    assert card_results["gmv"]["status"] == "normal"
    assert "$300,000.00" in card_results["gmv"]["value"]
    assert card_results["net_rev"]["status"] == "normal"
    assert "90.0%" in card_results["net_rev"]["value"]
    assert card_results["orders"]["status"] == "normal"
    assert card_results["customers"]["status"] == "normal"


def test_adapter_medallion_layers_and_tools(adapter):
    layers = adapter.medallion_layers
    assert "gold" in layers
    assert "silver" in layers
    assert "bronze" in layers

    tools = adapter.get_fastmcp_tools()
    assert len(tools) == 3
    tool_names = [t.__name__ for t in tools]
    assert "get_daily_sales_kpi" in tool_names
    assert "get_top_products" in tool_names
    assert "get_customer_metrics" in tool_names
