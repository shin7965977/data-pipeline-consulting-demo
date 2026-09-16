import logging
import random
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import requests


class OrderLifecycleStatus(str, Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    LINE_PAY = "line_pay"
    APPLE_PAY = "apple_pay"


class PlatziStoreAdapter:
    """Pluggable adapter for Platzi Fake Store API and synthetic order generation.

    Yields Canonical Schema records:
    - raw_orders
    - raw_order_items
    - raw_customers
    - raw_products
    """

    BASE_URL = "https://api.escuelajs.co/api/v1"

    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode

    def fetch_products(self) -> list[dict[str, Any]]:
        """Fetch products catalog from Platzi API or return mock products."""
        if not self.mock_mode:
            try:
                resp = requests.get(f"{self.BASE_URL}/products?limit=50", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    products = []
                    for item in data:
                        category = item.get("category", {})
                        products.append(
                            {
                                "product_id": item["id"],
                                "title": item["title"],
                                "price": float(item["price"]),
                                "category_id": category.get("id", 1),
                                "category_name": category.get("name", "General"),
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    if products:
                        return products
            except requests.RequestException as e:
                logging.getLogger(__name__).warning(
                    "Platzi API product fetch failed, falling back to mock catalog: %s",
                    e,
                )

        # Fallback mock catalog
        return [
            {
                "product_id": 1,
                "title": "Classic Cotton T-Shirt",
                "price": 25.0,
                "category_id": 1,
                "category_name": "Clothes",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "product_id": 2,
                "title": "Slim Fit Denim Jeans",
                "price": 60.0,
                "category_id": 1,
                "category_name": "Clothes",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "product_id": 3,
                "title": "Wireless Noise Cancelling Headphones",
                "price": 120.0,
                "category_id": 2,
                "category_name": "Electronics",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "product_id": 4,
                "title": "Smart Fitness Watch",
                "price": 95.0,
                "category_id": 2,
                "category_name": "Electronics",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "product_id": 5,
                "title": "Ergonomic Office Chair",
                "price": 210.0,
                "category_id": 3,
                "category_name": "Furniture",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "product_id": 6,
                "title": "Minimalist Wooden Desk",
                "price": 180.0,
                "category_id": 3,
                "category_name": "Furniture",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "product_id": 7,
                "title": "Leather Running Shoes",
                "price": 85.0,
                "category_id": 4,
                "category_name": "Shoes",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "product_id": 8,
                "title": "Retro Canvas Backpack",
                "price": 45.0,
                "category_id": 5,
                "category_name": "Accessories",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

    def fetch_customers(self) -> list[dict[str, Any]]:
        """Fetch users from Platzi API or return mock customer base."""
        if not self.mock_mode:
            try:
                resp = requests.get(f"{self.BASE_URL}/users?limit=30", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    customers = []
                    for u in data:
                        customers.append(
                            {
                                "customer_id": u["id"],
                                "email": u["email"],
                                "name": u["name"],
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    if customers:
                        return customers
            except requests.RequestException as e:
                logging.getLogger(__name__).warning(
                    "Platzi API customer fetch failed, falling back to mock: %s", e
                )

        # Fallback mock customers
        names = [
            "Alex Rivera",
            "Brenda Vance",
            "Charles Stone",
            "Diana Prince",
            "Evan Wright",
            "Fiona Gallagher",
            "George Clark",
            "Hannah Abbott",
        ]
        return [
            {
                "customer_id": i + 1,
                "email": f"customer{i + 1}@example.com",
                "name": name,
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(days=120)
                ).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            for i, name in enumerate(names)
        ]

    def generate_synthetic_orders(
        self,
        days: int = 90,
        orders_per_day: int = 40,
        since_timestamp: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Synthesize historical or incremental orders adhering to the Canonical Schema."""
        products = self.fetch_products()
        customers = self.fetch_customers()

        orders: list[dict[str, Any]] = []
        order_items: list[dict[str, Any]] = []

        now = datetime.now(timezone.utc)
        order_seq = 1000
        item_seq = 5000

        for d in range(days, 0, -1):
            day_date = now - timedelta(days=d)
            # Weekend surge: Saturdays and Sundays produce 50% more orders
            surge = 1.5 if day_date.weekday() in (5, 6) else 1.0
            daily_count = int(orders_per_day * surge)

            for _ in range(daily_count):
                order_time = day_date + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59),
                )

                if since_timestamp and order_time < since_timestamp:
                    continue

                order_id = f"ORD-{order_seq}"
                order_seq += 1
                customer = random.choice(customers)

                # Status machine: 85% completed, 10% cancelled, 5% refunded
                status_roll = random.random()
                if status_roll < 0.85:
                    status = OrderLifecycleStatus.COMPLETED
                elif status_roll < 0.95:
                    status = OrderLifecycleStatus.CANCELLED
                else:
                    status = OrderLifecycleStatus.REFUNDED

                # Line items (1 to 4 distinct items per order)
                num_items = random.randint(1, 4)
                chosen_products = random.sample(products, min(num_items, len(products)))

                gross_amount = 0.0
                for prod in chosen_products:
                    qty = random.randint(1, 3)
                    unit_price = prod["price"]
                    subtotal = round(unit_price * qty, 2)
                    gross_amount += subtotal

                    order_items.append(
                        {
                            "item_id": f"ITEM-{item_seq}",
                            "order_id": order_id,
                            "product_id": prod["product_id"],
                            "unit_price": unit_price,
                            "quantity": qty,
                            "subtotal": subtotal,
                        }
                    )
                    item_seq += 1

                gross_amount = round(gross_amount, 2)

                # 25% chance of discount coupon (between 5% and 20%)
                discount_amount = 0.0
                if random.random() < 0.25 and gross_amount > 30.0:
                    discount_amount = round(
                        gross_amount * random.uniform(0.05, 0.20), 2
                    )

                net_amount = round(max(0.0, gross_amount - discount_amount), 2)

                payment_method = random.choice(list(PaymentMethod)).value
                created_iso = order_time.isoformat()
                updated_iso = (
                    order_time + timedelta(hours=random.randint(1, 48))
                ).isoformat()

                orders.append(
                    {
                        "order_id": order_id,
                        "customer_id": customer["customer_id"],
                        "order_status": status.value,
                        "currency": "USD",
                        "gross_amount": gross_amount,
                        "discount_amount": discount_amount,
                        "net_amount": net_amount,
                        "payment_method": payment_method,
                        "created_at": created_iso,
                        "updated_at": updated_iso,
                    }
                )

        return {
            "raw_orders": orders,
            "raw_order_items": order_items,
            "raw_customers": customers,
            "raw_products": products,
        }
