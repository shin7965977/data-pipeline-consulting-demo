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


def upload_file_to_gcs(
    local_file: str, bucket_name: str, target_name: str | None = None
) -> str | None:
    """Helper to upload a local HTML file to GCS with no-cache headers."""
    if not (bucket_name and os.path.exists(local_file)):
        return None
    try:
        from google.cloud import storage

        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ and os.path.exists(
            "gcp-key.json"
        ):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(
                "gcp-key.json"
            )

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob_name = target_name or os.path.basename(local_file)
        blob = bucket.blob(blob_name)
        blob.cache_control = "no-cache, max-age=0"
        blob.upload_from_filename(local_file, content_type="text/html")
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    except Exception as e:  # noqa: BLE001
        print(f"[Storage] Warning: Failed to upload {local_file} to GCS: {e}")
        return None


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

    edr_bin = shutil.which("edr") or os.path.join(
        os.path.dirname(sys.executable), "edr"
    )
    if (
        sys.platform == "win32"
        and not edr_bin.endswith(".exe")
        and os.path.exists(edr_bin + ".exe")
    ):
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
    except Exception as e:  # noqa: BLE001
        print(f"[Elementary] Warning: Failed to execute edr report: {e}")
        return None

    if bucket_name and os.path.exists(report_file):
        public_url = upload_file_to_gcs(report_file, bucket_name)
        if public_url:
            print(f"[Elementary] Live Report: {public_url}")
            return public_url

    return report_file


def generate_and_publish_dbt_docs(
    project_dir: str = "transform_dbt",
    profiles_dir: str = "transform_dbt",
    report_file: str = "dbt_docs.html",
    gcs_bucket: str | None = None,
) -> str | None:
    """Generate dbt docs, bundle into a standalone single-file HTML, and upload to GCS."""
    print("-" * 60)
    print("[dbt Docs] Generating Data Catalog & Lineage documentation...")
    bucket_name = gcs_bucket or os.getenv(
        "ELEMENTARY_REPORT_BUCKET", "de-consulting-508822_cloudbuild"
    )

    cmd_docs = [
        sys.executable,
        "-m",
        "dbt.cli.main",
        "docs",
        "generate",
        "--project-dir",
        project_dir,
        "--profiles-dir",
        profiles_dir,
    ]
    try:
        res = subprocess.run(cmd_docs, check=False)
        if res.returncode != 0:
            print(
                f"[dbt Docs] Warning: docs generate exited with code {res.returncode}"
            )
            return None

        # Bundle index.html + manifest.json + catalog.json into standalone HTML
        target_dir = os.path.join(project_dir, "target")
        index_path = os.path.join(target_dir, "index.html")
        manifest_path = os.path.join(target_dir, "manifest.json")
        catalog_path = os.path.join(target_dir, "catalog.json")

        if (
            os.path.exists(index_path)
            and os.path.exists(manifest_path)
            and os.path.exists(catalog_path)
        ):
            with open(index_path, "r", encoding="utf-8") as f:
                html = f.read()
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = f.read()
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = f.read()

            html = html.replace('"MANIFEST.JSON INLINE DATA"', manifest, 1)
            html = html.replace('"CATALOG.JSON INLINE DATA"', catalog, 1)

            with open(report_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[dbt Docs] Standalone Catalog & Lineage bundled: {report_file}")

            if bucket_name:
                public_url = upload_file_to_gcs(report_file, bucket_name)
                if public_url:
                    print(f"[dbt Docs] Live Catalog: {public_url}")
                    return public_url
    except Exception as e:  # noqa: BLE001
        print(f"[dbt Docs] Warning: Failed to bundle dbt docs: {e}")
        return None

    return report_file


def publish_unified_portal(
    portal_source: str = "docs/technical/zh/portal.html",
    gcs_bucket: str | None = None,
) -> str | None:
    """Upload Unified DataOps Portal (portal.html and index.html) to GCS."""
    print("-" * 60)
    print("[Portal] Publishing Unified DataOps Portal...")
    if not os.path.exists(portal_source) and os.path.exists("docs/portal.html"):
        portal_source = "docs/portal.html"

    bucket_name = gcs_bucket or os.getenv(
        "ELEMENTARY_REPORT_BUCKET", "de-consulting-508822_cloudbuild"
    )
    if bucket_name and os.path.exists(portal_source):
        # Upload as both portal.html and index.html
        url_portal = upload_file_to_gcs(portal_source, bucket_name, "portal.html")
        upload_file_to_gcs(portal_source, bucket_name, "index.html")
        if url_portal:
            print(f"[Portal] Live Unified Portal: {url_portal}")
            return url_portal
    return None


def run_testing_step(
    dbt_target: str | None = None,
    project_dir: str = "transform_dbt",
    profiles_dir: str = "transform_dbt",
    gcs_bucket: str | None = None,
) -> int:
    print("=" * 60)
    print("STEP 3: TESTING, OBSERVABILITY & GOVERNANCE PORTAL")
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

    # 1. Elementary Report (Testing & Observability)
    elem_url = generate_and_publish_elementary_report(
        project_dir=project_dir,
        profiles_dir=profiles_dir,
        gcs_bucket=gcs_bucket,
    )

    # 2. dbt Docs (Catalog & Lineage)
    docs_url = generate_and_publish_dbt_docs(
        project_dir=project_dir,
        profiles_dir=profiles_dir,
        gcs_bucket=gcs_bucket,
    )

    # 3. Unified Portal (Executive Dashboard Hub)
    portal_url = publish_unified_portal(gcs_bucket=gcs_bucket)

    print("=" * 60)
    print("[SUCCESS] UNIFIED DATAOPS PLATFORM READY:")
    if portal_url:
        print(f"  * [Portal Hub]      : {portal_url}")
    if elem_url:
        print(f"  * [Elementary Tests]: {elem_url}")
    if docs_url:
        print(f"  * [dbt Catalog & DAG]: {docs_url}")
    print("=" * 60)

    if res_test.returncode != 0:
        print("[dbt] dbt test failed! Exiting pipeline.")
        return res_test.returncode

    print("[dbt] All tests, observability & governance portals completed successfully!")
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
