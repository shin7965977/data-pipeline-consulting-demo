import argparse
import os
import subprocess
import sys

from ingestion.run_ingest import run_pipeline
from ingestion.sources.platzi_store import SimulatorConfig


def parse_args():
    parser = argparse.ArgumentParser(
        description="Platzi E-Commerce Data Pipeline Orchestrator"
    )
    parser.add_argument(
        "--target",
        choices=["all", "ingest", "transform", "test"],
        default=os.getenv("PIPELINE_TARGET", "all"),
        help="Pipeline phase to execute (all, ingest, transform, test)",
    )
    parser.add_argument(
        "--destination",
        default=os.getenv("DLT_DESTINATION", "bigquery"),
        help="Storage destination (bigquery or duckdb)",
    )
    parser.add_argument(
        "--dataset",
        default=os.getenv("DLT_DATASET_NAME", "platzi_bronze"),
        help="Bronze target dataset",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.getenv("SIMULATION_DAYS", "90")),
        help="Number of historical days to simulate",
    )
    parser.add_argument(
        "--orders-per-day",
        type=int,
        default=int(os.getenv("ORDERS_PER_DAY", "40")),
        help="Average orders generated per day",
    )
    parser.add_argument(
        "--incremental-days",
        type=int,
        default=int(os.getenv("INCREMENTAL_DAYS", "0")) or None,
        help="Lookback days for incremental run",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=os.getenv("MOCK_MODE", "false").lower() == "true",
        help="Run simulator with mock catalog without hitting external APIs",
    )
    return parser.parse_args()


def run_ingestion_step(
    destination: str = "bigquery",
    dataset: str = "platzi_bronze",
    config: SimulatorConfig | None = None,
    days: int = 90,
    orders_per_day: int = 40,
    incremental_days: int | None = None,
    mock_mode: bool = False,
):
    print("=" * 60)
    print("STEP 1: INGESTION (dlt -> Bronze Layer)")
    print("=" * 60)
    sim_config = config or SimulatorConfig(
        days=days,
        orders_per_day=orders_per_day,
        mock_mode=mock_mode,
    )
    load_info = run_pipeline(
        destination=destination,
        dataset_name=dataset,
        incremental_days=incremental_days,
        config=sim_config,
    )
    return load_info


def run_transformation_step(
    dbt_target: str | None = None,
    project_dir: str = "transform_dbt",
    profiles_dir: str = "transform_dbt",
):
    print("=" * 60)
    print("STEP 2: TRANSFORMATION (dbt run -> Silver & Gold)")
    print("=" * 60)
    target = dbt_target or os.getenv("DBT_TARGET", "bigquery")
    env = {**dict(os.environ), "DBT_TARGET": target}

    # dbt run
    cmd_run = [
        sys.executable,
        "-m",
        "dbt.cli.main",
        "run",
        "--project-dir",
        project_dir,
        "--profiles-dir",
        profiles_dir,
        "--select",
        "platzi_transform",
    ]
    print(f"[dbt] Running models against target: {target}...")
    res_run = subprocess.run(cmd_run, env=env, check=False)
    if res_run.returncode != 0:
        print("[dbt] dbt run failed! Exiting pipeline.")
        return res_run.returncode

    print("[dbt] Transformations completed successfully!")
    return 0


def run_testing_step(
    dbt_target: str | None = None,
    project_dir: str = "transform_dbt",
    profiles_dir: str = "transform_dbt",
) -> int:
    print("=" * 60)
    print("STEP 3: TESTING & OBSERVABILITY (dbt test -> Elementary)")
    print("=" * 60)
    target = dbt_target or os.getenv("DBT_TARGET", "bigquery")
    env = {**dict(os.environ), "DBT_TARGET": target}

    # dbt test
    cmd_test = [
        sys.executable,
        "-m",
        "dbt.cli.main",
        "test",
        "--project-dir",
        project_dir,
        "--profiles-dir",
        profiles_dir,
        "--select",
        "platzi_transform",
    ]
    print(f"[dbt] Running quality tests against target: {target}...")
    res_test = subprocess.run(cmd_test, env=env, check=False)
    if res_test.returncode != 0:
        print("[dbt] dbt test failed! Exiting pipeline.")
        return res_test.returncode

    print("[dbt] Quality tests and Elementary observability completed successfully!")
    return 0


def run_pipeline_orchestrator(
    target: str = "all",
    destination: str = "bigquery",
    dataset: str = "platzi_bronze",
    days: int = 90,
    orders_per_day: int = 40,
    incremental_days: int | None = None,
    mock_mode: bool = False,
) -> int:
    print(f"Starting Platzi Pipeline Orchestrator with target: {target}")

    if target in ("all", "ingest"):
        run_ingestion_step(
            destination=destination,
            dataset=dataset,
            days=days,
            orders_per_day=orders_per_day,
            incremental_days=incremental_days,
            mock_mode=mock_mode,
        )

    dbt_target = "duckdb" if destination == "duckdb" else "bigquery"

    if target in ("all", "transform"):
        ret = run_transformation_step(dbt_target=dbt_target)
        if ret != 0:
            return ret

    if target in ("all", "test"):
        ret = run_testing_step(dbt_target=dbt_target)
        if ret != 0:
            return ret

    print("Pipeline finished successfully.")
    return 0


def main():
    args = parse_args()
    code = run_pipeline_orchestrator(
        target=args.target,
        destination=args.destination,
        dataset=args.dataset,
        days=args.days,
        orders_per_day=args.orders_per_day,
        incremental_days=args.incremental_days,
        mock_mode=args.mock,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
