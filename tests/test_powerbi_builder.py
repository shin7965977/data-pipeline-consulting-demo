import pandas as pd
import pytest

from powerbi_builder import build_custom_chart


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "category": ["Electronics", "Electronics", "Clothes", "Clothes", "Shoes"],
            "product": ["Phone", "Laptop", "Shirt", "Pants", "Sneakers"],
            "sales": [1000.0, 2500.0, 150.0, 200.0, 600.0],
            "units": [10, 5, 15, 10, 6],
        }
    )


def test_build_custom_chart_bar_sum(sample_data):
    fig, agg_df, summary = build_custom_chart(
        df=sample_data,
        chart_type="bar",
        x_col="category",
        y_col="sales",
        agg_func="sum",
        sort_by="y_desc",
    )
    assert fig is not None
    assert len(agg_df) == 3
    # Electronics should be the highest (3500.0)
    assert agg_df.iloc[0]["category"] == "Electronics"
    assert agg_df.iloc[0]["sales"] == 3500.0
    assert "Electronics" in summary


def test_build_custom_chart_with_color_group(sample_data):
    fig, agg_df, _summary = build_custom_chart(
        df=sample_data,
        chart_type="bar",
        x_col="category",
        y_col="sales",
        agg_func="sum",
        color_col="product",
    )
    assert fig is not None
    assert len(agg_df) == 5


def test_build_custom_chart_donut(sample_data):
    fig, agg_df, _summary = build_custom_chart(
        df=sample_data,
        chart_type="donut",
        x_col="category",
        y_col="sales",
        agg_func="sum",
    )
    assert fig is not None
    assert len(agg_df) == 3


def test_build_custom_chart_top_n(sample_data):
    _fig, agg_df, _summary = build_custom_chart(
        df=sample_data,
        chart_type="line",
        x_col="product",
        y_col="sales",
        agg_func="sum",
        sort_by="y_desc",
        top_n=2,
    )
    assert len(agg_df) == 2
    assert agg_df.iloc[0]["product"] == "Laptop"


def test_build_custom_chart_empty_guard():
    empty_df = pd.DataFrame()
    fig, _agg_df, summary = build_custom_chart(
        df=empty_df,
        chart_type="bar",
        x_col="category",
        y_col="sales",
    )
    assert fig is not None
    assert "無足夠數據" in summary or "資料集為空" in summary


def test_build_pygwalker_spec(sample_data):
    from powerbi_builder import build_pygwalker_spec
    import json

    spec_str = build_pygwalker_spec(sample_data, x_col="category", y_col="sales", geom="bar", agg="sum")
    parsed = json.loads(spec_str)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["encodings"]["columns"][0]["fid"] == "category"
    assert parsed[0]["encodings"]["rows"][0]["fid"] == "sales"
    assert parsed[0]["config"]["geoms"] == ["bar"]


def test_generate_pygwalker_spec_from_nl(sample_data):
    from powerbi_builder import generate_pygwalker_spec_from_nl
    import json

    spec_str, msg = generate_pygwalker_spec_from_nl("我想看各類別 sales 長條圖", sample_data)
    assert spec_str is not None
    parsed = json.loads(spec_str)
    assert parsed[0]["encodings"]["columns"][0]["fid"] == "category"
    assert "category" in msg


def test_sanitize_df_for_pygwalker():
    import datetime
    from decimal import Decimal
    from powerbi_builder import sanitize_df_for_pygwalker

    test_df = pd.DataFrame(
        {
            "category": ["A", "B"],
            "amount": [Decimal("100.5"), Decimal("200.75")],
            "first_order_date": [datetime.date(2026, 9, 1), datetime.date(2026, 9, 2)],
        }
    )
    cleaned = sanitize_df_for_pygwalker(test_df)
    assert cleaned["amount"].dtype == float
    assert pd.api.types.is_datetime64_any_dtype(cleaned["first_order_date"])

