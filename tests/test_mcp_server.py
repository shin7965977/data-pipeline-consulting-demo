import pytest

from mcp_server.server import (
    get_customer_metrics,
    get_daily_sales_kpi,
    get_top_products,
    sanitize_dataset_access,
)


def test_sanitize_dataset_access_blocks_bronze_silver():
    """Security invariant: Access to bronze or silver datasets must raise ValueError."""
    with pytest.raises(ValueError, match="Access denied"):
        sanitize_dataset_access("platzi_bronze")

    with pytest.raises(ValueError, match="Access denied"):
        sanitize_dataset_access("platzi_silver")

    # Allowed
    assert sanitize_dataset_access("platzi_gold") == "platzi_gold"


def test_get_daily_sales_kpi_mock():
    """Verify daily sales KPI tool execution and expected output format."""
    res = get_daily_sales_kpi(limit=5, mock_mode=True)
    assert isinstance(res, list)
    assert len(res) <= 5
    for record in res:
        assert "order_date" in record
        assert "gmv" in record
        assert "net_revenue" in record
        assert "aov" in record
        assert record["gmv"] >= record["net_revenue"]


def test_get_top_products_mock():
    """Verify top products tool execution and fields."""
    res = get_top_products(limit=3, mock_mode=True)
    assert isinstance(res, list)
    assert len(res) <= 3
    for record in res:
        assert "product_id" in record
        assert "product_title" in record
        assert "units_sold" in record
        assert "completed_sales_amount" in record


def test_get_customer_metrics_excludes_pii():
    """Security invariant: Customer queries must never expose raw PII."""
    res = get_customer_metrics(tier="Gold", limit=10, mock_mode=True)
    assert isinstance(res, list)
    for record in res:
        # PII fields must NEVER be returned to AI
        assert "email" not in record
        assert "phone" not in record
        assert "address" not in record
        assert "customer_id" in record
        assert "lifetime_net_revenue" in record


def test_execute_gold_query_enforces_budget_config(monkeypatch):
    """Verify that BigQuery queries are submitted with maximum_bytes_billed limit."""
    from unittest.mock import MagicMock

    from mcp_server.server import MAX_BYTES_BILLED, _execute_gold_query

    mock_client = MagicMock()
    mock_job = MagicMock()
    mock_job.result.return_value = [{"metric": 100}]
    mock_client.query.return_value = mock_job

    res = _execute_gold_query("SELECT 1", mock_client, [], 10)
    assert res == [{"metric": 100}]
    assert mock_client.query.called
    job_config = mock_client.query.call_args[1].get("job_config")
    assert job_config is not None
    assert job_config.maximum_bytes_billed == MAX_BYTES_BILLED
