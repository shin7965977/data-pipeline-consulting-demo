import argparse
import os
from datetime import datetime, timedelta, timezone

import dlt
from dotenv import load_dotenv

from ingestion.sources.platzi_store import PlatziStoreAdapter

load_dotenv()


def create_platzi_source(
    mock_mode: bool = False,
    days: int = 90,
    orders_per_day: int = 40,
    since_timestamp: datetime | None = None,
):
    """Declare dlt source and resources for the Platzi Store data pipeline."""
    adapter = PlatziStoreAdapter(mock_mode=mock_mode)
    data = adapter.generate_synthetic_orders(
        days=days,
        orders_per_day=orders_per_day,
        since_timestamp=since_timestamp,
    )

    @dlt.source(name="platzi_store")
    def platzi_source():
        @dlt.resource(
            name="raw_orders", write_disposition="append", primary_key="order_id"
        )
        def orders():
            yield data["raw_orders"]

        @dlt.resource(
            name="raw_order_items", write_disposition="append", primary_key="item_id"
        )
        def order_items():
            yield data["raw_order_items"]

        @dlt.resource(
            name="raw_customers", write_disposition="merge", primary_key="customer_id"
        )
        def customers():
            yield data["raw_customers"]

        @dlt.resource(
            name="raw_products", write_disposition="merge", primary_key="product_id"
        )
        def products():
            yield data["raw_products"]

        return orders, order_items, customers, products

    return platzi_source()


def run_pipeline(
    destination: str = "bigquery",
    dataset_name: str = "platzi_bronze",
    mock_mode: bool = False,
    days: int = 90,
    orders_per_day: int = 40,
    incremental_days: int | None = None,
    pipeline_name: str = "platzi_ecom_pipeline",
    pipelines_dir: str | None = None,
):
    """Execute the dlt pipeline ingestion into target destination."""
    since_timestamp = None
    if incremental_days:
        since_timestamp = datetime.now(timezone.utc) - timedelta(days=incremental_days)
        print(
            f"[dlt] Incremental run: extracting orders since {since_timestamp.isoformat()}"
        )
    else:
        print(
            f"[dlt] Full run: generating {days} days of historical orders ({orders_per_day} orders/day)"
        )

    source = create_platzi_source(
        mock_mode=mock_mode,
        days=days,
        orders_per_day=orders_per_day,
        since_timestamp=since_timestamp,
    )

    kwargs = {
        "pipeline_name": pipeline_name,
        "destination": destination,
        "dataset_name": dataset_name,
    }
    if pipelines_dir:
        kwargs["pipelines_dir"] = pipelines_dir

    pipeline = dlt.pipeline(**kwargs)

    print(f"[dlt] Starting load to {destination}.{dataset_name}...")
    load_info = pipeline.run(source)
    print(f"[dlt] Load completed successfully!\n{load_info}")
    return load_info


def main():
    parser = argparse.ArgumentParser(description="Platzi Store dlt Ingestion Runner")
    parser.add_argument(
        "--destination",
        default=os.getenv("DLT_DESTINATION", "bigquery"),
        help="Destination warehouse (bigquery or duckdb)",
    )
    parser.add_argument(
        "--dataset",
        default=os.getenv("DLT_DATASET_NAME", "platzi_bronze"),
        help="Target dataset name",
    )
    parser.add_argument(
        "--days", type=int, default=90, help="Number of historical days to generate"
    )
    parser.add_argument(
        "--orders-per-day", type=int, default=40, help="Average orders per day"
    )
    parser.add_argument(
        "--incremental-days",
        type=int,
        default=None,
        help="Incremental mode days lookback",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with synthetic fallback catalog (offline mode)",
    )

    args = parser.parse_args()

    run_pipeline(
        destination=args.destination,
        dataset_name=args.dataset,
        mock_mode=args.mock,
        days=args.days,
        orders_per_day=args.orders_per_day,
        incremental_days=args.incremental_days,
    )


if __name__ == "__main__":
    main()
