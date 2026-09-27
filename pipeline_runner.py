import argparse
import os
import shutil
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
    parser.add_argument(
        "--report-bucket",
        default=os.getenv("ELEMENTARY_REPORT_BUCKET"),
        help="Optional GCS bucket to automatically publish Elementary Observability HTML report",
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


def generate_and_publish_elementary_report(
    project_dir: str = "transform_dbt",
    profiles_dir: str = "transform_dbt",
    report_file: str = "elementary_report.html",
    gcs_bucket: str | None = None,
) -> str | None:
    """Generate Elementary Observability HTML report and optionally upload to GCS."""
    print("-" * 60)
    print("[Elementary] Generating automated Observability report...")
    bucket_name = gcs_bucket or os.getenv(
        "ELEMENTARY_REPORT_BUCKET", "de-consulting-508822_cloudbuild"
    )

    edr_bin = shutil.which("edr") or os.path.join(os.path.dirname(sys.executable), "edr")
    if sys.platform == "win32" and not edr_bin.endswith(".exe") and os.path.exists(edr_bin + ".exe"):
        edr_bin += ".exe"

    cmd_edr = [
        edr_bin,
        "report",
        "--project-dir",
        project_dir,
        "--profiles-dir",
        profiles_dir,
        "--file-path",
        report_file,
    ]
    try:
        res = subprocess.run(cmd_edr, check=False)
        if res.returncode != 0:
            print(f"[Elementary] edr report exited with returncode {res.returncode}")
        else:
            print(f"[Elementary] Report successfully generated at: {report_file}")
    except Exception as e:
        print(f"[Elementary] Warning: Failed to execute edr report: {e}")
        return None

    # Upload to Google Cloud Storage if bucket name is specified
    if bucket_name and os.path.exists(report_file):
        try:
            print(f"[Elementary] Uploading report to GCS bucket: {bucket_name}...")
            from google.cloud import storage

            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob_name = os.path.basename(report_file)
            blob = bucket.blob(blob_name)
            blob.cache_control = "no-cache, max-age=0"
            blob.upload_from_filename(report_file, content_type="text/html")
            public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
            print(f"[Elementary] Report is live at: {public_url}")
            return public_url
        except Exception as e:
            print(f"[Elementary] Note: GCS upload skipped or failed: {e}")
            return None

    return report_file


def run_testing_step(
    dbt_target: str | None = None,
    project_dir: str = "transform_dbt",
    profiles_dir: str = "transform_dbt",
    gcs_bucket: str | None = None,
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

    # Always generate/update Elementary report so latest test runs are reflected
    generate_and_publish_elementary_report(
        project_dir=project_dir,
        profiles_dir=profiles_dir,
        gcs_bucket=gcs_bucket,
    )

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
    report_bucket: str | None = None,
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
        ret = run_testing_step(dbt_target=dbt_target, gcs_bucket=report_bucket)
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
        report_bucket=args.report_bucket,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
