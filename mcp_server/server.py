import os
from typing import Any

from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("platzi-ecommerce-analytics")

ALLOWED_DATASET = "platzi_gold"
MAX_BYTES_BILLED = 100 * 1024 * 1024  # 100 MB budget protection limit


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


def _clean_val(v: Any) -> Any:
    from decimal import Decimal

    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _execute_gold_query(
    query: str,
    client: Any,
    fallback_data: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Execute BigQuery analytical query with scan budget caps or fallback to mock data."""
    if client:
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES_BILLED)
        query_job = client.query(query, job_config=job_config)
        return [{k: _clean_val(v) for k, v in row.items()} for row in query_job.result()]

    return fallback_data[:limit]


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
    project_id = os.getenv("GCP_PROJECT_ID", client.project if client else "platzi-demo")

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

    fallback = [
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
    ]
    return _execute_gold_query(query, client, fallback, limit)


@mcp.tool()
def get_top_products(limit: int = 10, mock_mode: bool = False) -> list[dict[str, Any]]:
    """Retrieve top-selling products by completed sales amount and units sold.

    Args:
        limit: Max products to return (default: 10, max: 50)
        mock_mode: Force synthetic response for offline/testing use
    """
    limit = min(limit, 50)
    client = None if mock_mode else _get_bigquery_client()
    project_id = os.getenv("GCP_PROJECT_ID", client.project if client else "platzi-demo")

    query = f"""
        SELECT product_id, product_title, category_name, unit_price,
               units_sold, completed_sales_amount, refunded_units
        FROM `{project_id}.{ALLOWED_DATASET}.gold_product_performance`
        ORDER BY completed_sales_amount DESC
        LIMIT {limit}
    """

    fallback = [
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
    ]
    return _execute_gold_query(query, client, fallback, limit)


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
    project_id = os.getenv("GCP_PROJECT_ID", client.project if client else "platzi-demo")

    query = f"""
        SELECT customer_id, first_order_date, last_order_date,
               total_orders, completed_orders, lifetime_net_revenue, customer_tier
        FROM `{project_id}.{ALLOWED_DATASET}.gold_customer_ltv`
        WHERE 1=1
    """
    if tier:
        query += f" AND customer_tier = '{tier}'"
    query += f" ORDER BY lifetime_net_revenue DESC LIMIT {limit}"

    fallback = [
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
        fallback = [c for c in fallback if c["customer_tier"] == tier]
    return _execute_gold_query(query, client, fallback, limit)


# ==============================================================================
# FastMCP Prompts: MBB Strategy & Management Consulting Intelligence
# Integrated with DogInfantry/claude-skill-management-consultant-B1 methodology
# ==============================================================================


@mcp.prompt()
def mbb_executive_performance_review(
    time_horizon: str = "last 30 days",
    focus_area: str = "profitability and revenue leakage",
) -> str:
    """MBB Senior Partner caliber executive diagnostic prompt for Platzi E-Commerce.

    Enforces Pyramid Principle (SCQA), MECE issue tree decomposition, and actionable prescriptions.
    """
    return f"""
You are operating as an MBB Senior Management Consultant (McKinsey / BCG / Bain Principal caliber)
evaluating Platzi E-Commerce performance over the {time_horizon}, with special focus on {focus_area}.

### Core Methodology & Instructions (from MBB Management Consultant Skill):
1. **Tool Invocation**:
   - Immediately call `get_daily_sales_kpi` and `get_top_products` to extract live data from the BigQuery Gold layer.
2. **Three-Test Standard**:
   - **So What?**: Do not merely recite data numbers. Synthesize the non-obvious business insight.
   - **Why So?**: Provide quantified causal proof (Unit Economics: GMV, AOV, Cancellation Rate, Refund Rate).
   - **Now What?**: Give 3 concrete, prioritized, and high-ROI commercial interventions.
3. **Structured Deliverable Structure**:
   - **[Executive Governing Thought / Action Title]**: One crisp, bold sentence stating the core business finding.
   - **[SCQA Context & Burning Platform]**: Situation, Complication, Question, Answer.
   - **[MECE Issue Tree Decomposition]**:
     * Revenue Equation: GMV = Total Orders × AOV.
     * Leakage Analysis: Net Revenue = GMV - (Cancellations + Refunds). Quantify the dollar value lost.
     * Product Concentration (Pareto 80/20): Identify top-performing and high-refund SKUs.
   - **[Strategic Recommendations & 30-60-90 Day Roadmap]**: Concrete steps with assigned ownership and expected financial impact.
"""


@mcp.prompt()
def profitability_issue_tree_diagnostic(
    target_metric: str = "Net Revenue Leakage and Margin Optimization",
) -> str:
    """MECE profitability and leakage diagnostic prompt analyzing product and order attrition."""
    return f"""
You are an MBB Operations & Strategy Practice Director diagnosing {target_metric} for Platzi E-Commerce.

### Analytical Protocol:
1. Call `get_daily_sales_kpi` to evaluate cancellation and refund trend anomalies.
2. Call `get_top_products` to isolate which categories/products suffer from disproportionate return rates.
3. Apply DuPont and MECE root cause analysis:
   - Is leakage driven by operational fulfillment failures, product quality mismatches, or buyer remorse?
   - Calculate the Net Realization Rate: `Net Revenue / GMV`.
4. Deliver findings in executive slide/memo format with clear Action Titles for each pillar.
"""


@mcp.prompt()
def customer_rfm_growth_strategy(
    segment_focus: str = "Platinum and Gold High-LTV Retention",
) -> str:
    """Customer Lifetime Value (LTV) and RFM segmentation strategy prompt."""
    return f"""
You are an MBB Customer & Growth Strategy Consultant analyzing {segment_focus} for Platzi E-Commerce.

### Analytical Protocol:
1. Call `get_customer_rfm_segments` to retrieve customer tiers, order frequencies, and lifetime net revenue.
2. Perform Pareto Tier Analysis (Platinum, Gold, Silver, Bronze):
   - Measure revenue contribution of top 20% customers vs. bottom 80%.
   - Identify repeat purchase cadence and churn velocity (days between first and last order).
3. Prescribe a high-impact Retention & LTV Expansion Playbook:
   - VIP Concierge / Loyalty incentives for Platinum.
   - Cross-sell and repeat-purchase triggers for Gold.
   - Churn reactivation protocols for at-risk accounts.
"""


if __name__ == "__main__":
    # Run FastMCP server over stdio
    mcp.run()

