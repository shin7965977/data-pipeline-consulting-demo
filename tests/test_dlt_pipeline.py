from ingestion.run_ingest import create_platzi_source, run_pipeline


def test_dlt_source_yields_resources():
    """Verify that the dlt source declares the four canonical resources."""
    source = create_platzi_source(mock_mode=True, days=2, orders_per_day=3)
    resource_names = set(source.resources.keys())
    expected_resources = {
        "raw_orders",
        "raw_order_items",
        "raw_customers",
        "raw_products",
    }
    assert resource_names == expected_resources


def test_dlt_pipeline_local_execution(tmp_path):
    """Test full end-to-end dlt execution into duckdb local destination."""
    load_info = run_pipeline(
        destination="duckdb",
        dataset_name="platzi_bronze_test",
        mock_mode=True,
        days=3,
        orders_per_day=4,
        pipeline_name="test_pipeline",
        pipelines_dir=str(tmp_path),
    )
    assert load_info is not None
    # Verify tables were loaded
    assert len(load_info.loads_ids) > 0
