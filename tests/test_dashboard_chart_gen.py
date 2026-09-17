import pandas as pd
import pytest

from dashboard import generate_chart_from_nl


@pytest.fixture
def sample_data():
    df_kpi = pd.DataFrame(
        {
            "order_date": pd.to_datetime(["2026-09-15", "2026-09-16"]),
            "gmv": [1000.0, 1500.0],
            "net_revenue": [900.0, 1400.0],
            "total_orders": [20, 30],
            "completed_orders": [18, 28],
            "cancelled_orders": [1, 1],
            "refunded_orders": [1, 1],
            "aov": [50.0, 50.0],
            "cancellation_rate": [0.05, 0.033],
            "refund_rate": [0.05, 0.033],
        }
    )
    df_prod = pd.DataFrame(
        {
            "product_id": [1, 2],
            "product_title": ["Product A", "Product B"],
            "category_name": ["Electronics", "Clothes"],
            "completed_sales_amount": [5000.0, 3000.0],
            "units_sold": [50, 60],
            "unit_price": [100.0, 50.0],
        }
    )
    df_ltv = pd.DataFrame(
        {
            "customer_id": [1, 2, 3],
            "customer_name": ["Alice", "Bob", "Charlie"],
            "customer_tier": ["Platinum", "Gold", "Silver"],
            "total_orders": [10, 5, 2],
            "completed_orders": [10, 5, 2],
            "lifetime_net_revenue": [1000.0, 500.0, 200.0],
        }
    )
    return df_kpi, df_prod, df_ltv


def test_generate_chart_kpi_trend(sample_data):
    df_kpi, df_prod, df_ltv = sample_data
    fig, title, insight, _ = generate_chart_from_nl(
        "請畫出每日 GMV 與實質淨營收趨勢", df_kpi, df_prod, df_ltv
    )
    assert fig is not None
    assert "GMV" in title or "對比" in title
    assert len(insight) > 0


def test_generate_chart_top_products(sample_data):
    df_kpi, df_prod, df_ltv = sample_data
    fig, title, _, _ = generate_chart_from_nl(
        "請用長條圖呈現熱銷商品排行", df_kpi, df_prod, df_ltv
    )
    assert fig is not None
    assert "商品" in title


def test_generate_chart_category_pie(sample_data):
    df_kpi, df_prod, df_ltv = sample_data
    fig, title, _, _ = generate_chart_from_nl(
        "幫我畫各商品品類銷售佔比圓餅圖", df_kpi, df_prod, df_ltv
    )
    assert fig is not None
    assert "品類" in title or "佔比" in title


def test_generate_chart_customer_tier(sample_data):
    df_kpi, df_prod, df_ltv = sample_data
    fig, title, _, _ = generate_chart_from_nl(
        "各會員等級顧客價值分佈圓餅圖", df_kpi, df_prod, df_ltv
    )
    assert fig is not None
    assert "會員" in title or "等級" in title


def test_generate_chart_refund_monitoring(sample_data):
    df_kpi, df_prod, df_ltv = sample_data
    fig, title, _, _ = generate_chart_from_nl(
        "監控每日退款率與取消率", df_kpi, df_prod, df_ltv
    )
    assert fig is not None
    assert "退款" in title or "取消" in title


def test_generate_chart_rejects_irrelevant_query(sample_data):
    """Guardrail test: Non-business questions like politics or weather must be rejected."""
    df_kpi, df_prod, df_ltv = sample_data
    fig, title, insight, _ = generate_chart_from_nl(
        "柯文哲是誰", df_kpi, df_prod, df_ltv
    )
    assert fig is None
    assert "業務範疇" in title or "約束" in title
    assert "無關" in insight

    fig2, _, insight2, _ = generate_chart_from_nl(
        "今天天氣好嗎", df_kpi, df_prod, df_ltv
    )
    assert fig2 is None
    assert "無關" in insight2
