from datetime import datetime, timedelta, timezone

import pytest

from ingestion.sources.platzi_store import (
    OrderLifecycleStatus,
    PaymentMethod,
    PlatziStoreAdapter,
)


@pytest.fixture
def adapter():
    return PlatziStoreAdapter(mock_mode=True)


def test_order_lifecycle_statuses():
    """Verify order statuses strictly adhere to the domain glossary."""
    valid_statuses = {"completed", "cancelled", "refunded"}
    assert {s.value for s in OrderLifecycleStatus} == valid_statuses


def test_payment_methods():
    """Verify supported payment methods."""
    valid_methods = {"credit_card", "line_pay", "apple_pay"}
    assert {m.value for m in PaymentMethod} == valid_methods


def test_simulator_generates_canonical_records(adapter):
    """Test that generated records strictly match the Canonical Schema."""
    days = 10
    orders_per_day = 5
    data = adapter.generate_synthetic_orders(days=days, orders_per_day=orders_per_day)

    orders = data["raw_orders"]
    order_items = data["raw_order_items"]
    customers = data["raw_customers"]
    products = data["raw_products"]

    assert len(orders) >= days * orders_per_day
    assert len(order_items) >= len(orders)
    assert len(customers) > 0
    assert len(products) > 0

    # Validate Order fields and invariants
    for order in orders:
        assert "order_id" in order
        assert "customer_id" in order
        assert order["order_status"] in {"completed", "cancelled", "refunded"}
        assert order["currency"] == "USD"
        assert order["gross_amount"] > 0
        assert order["discount_amount"] >= 0
        assert order["payment_method"] in {"credit_card", "line_pay", "apple_pay"}
        assert "created_at" in order
        assert "updated_at" in order

        # Mathematical Invariant: gross - discount == net for completed orders
        expected_net = round(order["gross_amount"] - order["discount_amount"], 2)
        assert abs(order["net_amount"] - expected_net) < 0.01

    # Validate Order Items and relation to Orders
    order_item_totals = {}
    for item in order_items:
        assert "item_id" in item
        assert "order_id" in item
        assert "product_id" in item
        assert item["quantity"] >= 1
        assert item["unit_price"] > 0
        assert (
            abs(item["subtotal"] - round(item["unit_price"] * item["quantity"], 2))
            < 0.01
        )
        order_item_totals[item["order_id"]] = (
            order_item_totals.get(item["order_id"], 0.0) + item["subtotal"]
        )

    for order in orders:
        items_total = order_item_totals.get(order["order_id"], 0.0)
        assert abs(items_total - order["gross_amount"]) < 0.02


def test_incremental_watermark_filtering(adapter):
    """Verify that incremental generation with a watermark only returns new/updated records."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    data = adapter.generate_synthetic_orders(
        days=5, orders_per_day=4, since_timestamp=cutoff
    )

    orders = data["raw_orders"]
    assert len(orders) > 0
    for order in orders:
        order_time = datetime.fromisoformat(order["updated_at"])
        assert order_time >= cutoff


def test_simulator_config_dataclass():
    """Verify that SimulatorConfig cleanly encapsulates parameters."""
    from ingestion.sources.platzi_store import SimulatorConfig

    config = SimulatorConfig(days=3, orders_per_day=2, mock_mode=True)
    adapter = PlatziStoreAdapter(config=config)
    data = adapter.generate_synthetic_orders()
    assert len(data["raw_orders"]) >= 6
