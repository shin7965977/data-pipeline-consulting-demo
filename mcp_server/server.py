import os
from typing import Any

from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("platzi-ecommerce-analytics")

ALLOWED_DATASET = "platzi_gold"


def sanitize_dataset_access(dataset_name: str) -> str:
    """Security Boundary: Restrict queries strictly to the Gold analytical layer.

    Access to Bronze or Silver is explicitly denied to prevent PII leakage.
    """
    clean_name = dataset_name.strip().lower()
    if clean_name != ALLOWED_DATASET:
        raise ValueError(
            f"Access denied: Dataset '{dataset_name}' is protected. "
            f"AI agents are only permitted to query '{ALLOWED_DATASET}'."
        )
    return clean_name


def _get_bigquery_client():
    """Lazily instantiate BigQuery client if credentials are configured."""
    try:
        from google.cloud import bigquery

        return bigquery.Client()
    except Exception:  # noqa: BLE001
        return None


@mcp.tool()
def get_daily_sales_kpi(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 30,
    mock_mode: bool = False,
) -> list[dict[str, Any]]:
    """Retrieve daily sales KPIs (GMV, Net Revenue, completed orders, AOV, cancellation and refund rates).

    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
        limit: Max records to return (default: 30, max: 100)
        mock_mode: Force synthetic response for offline/testing use
    """
    limit = min(limit, 100)
    client = None if mock_mode else _get_bigquery_client()

    if client:
        project_id = os.getenv("GCP_PROJECT_ID", client.project)
        query = f"""
            SELECT order_date, total_orders, completed_orders, cancelled_orders,
                   refunded_orders, gmv, net_revenue, aov, cancellation_rate, refund_rate
            FROM `{project_id}.{ALLOWED_DATASET}.gold_daily_sales_kpi`
            WHERE 1=1
        """
        if start_date:
            query += f" AND order_date >= '{start_date}'"
        if end_date:
            query += f" AND order_date <= '{end_date}'"
        query += f" ORDER BY order_date DESC LIMIT {limit}"

        query_job = client.query(query)
        return [dict(row.items()) for row in query_job.result()]

    # Deterministic fallback data for testing/demo when offline
    return [
        {
            "order_date": "2026-09-15",
            "total_orders": 45,
            "completed_orders": 39,
            "cancelled_orders": 4,
            "refunded_orders": 2,
            "gmv": 3250.00,
            "net_revenue": 2890.50,
            "aov": 74.12,
            "cancellation_rate": 0.0889,
            "refund_rate": 0.0444,
        },
        {
            "order_date": "2026-09-14",
            "total_orders": 58,
            "completed_orders": 50,
            "cancelled_orders": 6,
            "refunded_orders": 2,
            "gmv": 4120.00,
            "net_revenue": 3680.00,
            "aov": 73.60,
            "cancellation_rate": 0.1034,
            "refund_rate": 0.0345,
        },
    ][:limit]


@mcp.tool()
def get_top_products(limit: int = 10, mock_mode: bool = False) -> list[dict[str, Any]]:
    """Retrieve top-selling products by completed sales amount and units sold.

    Args:
        limit: Max products to return (default: 10, max: 50)
        mock_mode: Force synthetic response for offline/testing use
    """
    limit = min(limit, 50)
    client = None if mock_mode else _get_bigquery_client()

    if client:
        project_id = os.getenv("GCP_PROJECT_ID", client.project)
        query = f"""
            SELECT product_id, product_title, category_name, unit_price,
                   units_sold, completed_sales_amount, refunded_units
            FROM `{project_id}.{ALLOWED_DATASET}.gold_product_performance`
            ORDER BY completed_sales_amount DESC
            LIMIT {limit}
        """
        query_job = client.query(query)
        return [dict(row.items()) for row in query_job.result()]

    # Fallback mock data
    return [
        {
            "product_id": 3,
            "product_title": "Wireless Noise Cancelling Headphones",
            "category_name": "Electronics",
            "unit_price": 120.0,
            "units_sold": 142,
            "completed_sales_amount": 17040.00,
            "refunded_units": 6,
        },
        {
            "product_id": 4,
            "product_title": "Smart Fitness Watch",
            "category_name": "Electronics",
            "unit_price": 95.0,
            "units_sold": 118,
            "completed_sales_amount": 11210.00,
            "refunded_units": 4,
        },
        {
            "product_id": 5,
            "product_title": "Ergonomic Office Chair",
            "category_name": "Furniture",
            "unit_price": 210.0,
            "units_sold": 48,
            "completed_sales_amount": 10080.00,
            "refunded_units": 2,
        },
    ][:limit]


@mcp.tool()
def get_customer_metrics(
    tier: str | None = None,
    limit: int = 20,
    mock_mode: bool = False,
) -> list[dict[str, Any]]:
    """Retrieve customer lifetime value metrics and segmentation tiers.

    PII Protection: Raw emails and personal details are strictly stripped.

    Args:
        tier: Optional filter by tier ('Platinum', 'Gold', 'Silver', 'Bronze')
        limit: Max records to return (default: 20, max: 100)
        mock_mode: Force synthetic response for offline/testing use
    """
    limit = min(limit, 100)
    client = None if mock_mode else _get_bigquery_client()

    if client:
        project_id = os.getenv("GCP_PROJECT_ID", client.project)
        query = f"""
            SELECT customer_id, first_order_date, last_order_date,
                   total_orders, completed_orders, lifetime_net_revenue, customer_tier
            FROM `{project_id}.{ALLOWED_DATASET}.gold_customer_ltv`
            WHERE 1=1
        """
        if tier:
            query += f" AND customer_tier = '{tier}'"
        query += f" ORDER BY lifetime_net_revenue DESC LIMIT {limit}"

        query_job = client.query(query)
        return [dict(row.items()) for row in query_job.result()]

    # Fallback mock data with zero PII
    mock_customers = [
        {
            "customer_id": 1,
            "first_order_date": "2026-06-15",
            "last_order_date": "2026-09-14",
            "total_orders": 12,
            "completed_orders": 11,
            "lifetime_net_revenue": 845.50,
            "customer_tier": "Platinum",
        },
        {
            "customer_id": 2,
            "first_order_date": "2026-07-01",
            "last_order_date": "2026-09-10",
            "total_orders": 6,
            "completed_orders": 5,
            "lifetime_net_revenue": 380.00,
            "customer_tier": "Gold",
        },
    ]
    if tier:
        mock_customers = [c for c in mock_customers if c["customer_tier"] == tier]
    return mock_customers[:limit]


if __name__ == "__main__":
    # Run FastMCP server over stdio
    mcp.run()
