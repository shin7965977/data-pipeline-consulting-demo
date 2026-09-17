import os
import shutil
import subprocess
import sys

from ingestion.run_ingest import run_pipeline


def test_dbt_models_and_tests_end_to_end(tmp_path):
    """Verify dlt ingestion followed by dbt run and dbt test against local warehouse."""
    # Step 1: Ingest into duckdb main schema
    load_info = run_pipeline(
        destination="duckdb",
        dataset_name="main",
        mock_mode=True,
        days=7,
        orders_per_day=5,
        pipeline_name="test_dbt_pipeline",
        pipelines_dir=str(tmp_path / "dlt_pipelines"),
    )
    assert len(load_info.loads_ids) > 0

    # Step 2: Run dbt run against duckdb
    actual_db = os.path.abspath("test_dbt_pipeline.duckdb")
    assert os.path.exists(actual_db)
    env = {
        "DBT_TARGET": "duckdb",
        "DBT_DUCKDB_PATH": actual_db,
    }

    candidates = [
        shutil.which("dbt"),
        os.path.join(os.path.dirname(sys.executable), "dbt.exe"),
        os.path.join(os.path.dirname(sys.executable), "dbt"),
        "dbt",
    ]
    dbt_bin = next(
        c for c in candidates if c and (os.path.exists(c) if os.path.isabs(c) else True)
    )

    # Test dbt run
    run_res = subprocess.run(
        [
            dbt_bin,
            "run",
            "--project-dir",
            "transform_dbt",
            "--profiles-dir",
            "transform_dbt",
            "--select",
            "platzi_transform",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(os.environ), **env},
    )
    assert run_res.returncode == 0, (
        f"dbt run failed:\n{run_res.stdout}\n{run_res.stderr}"
    )

    # Test dbt test
    test_res = subprocess.run(
        [
            dbt_bin,
            "test",
            "--project-dir",
            "transform_dbt",
            "--profiles-dir",
            "transform_dbt",
            "--select",
            "platzi_transform",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**dict(os.environ), **env},
    )
    assert test_res.returncode == 0, (
        f"dbt test failed:\n{test_res.stdout}\n{test_res.stderr}"
    )

    # Cleanup local test duckdb
    if os.path.exists(actual_db):
        os.remove(actual_db)
