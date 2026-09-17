import sys
from unittest.mock import patch

from pipeline_runner import parse_args, run_pipeline_orchestrator


def test_parse_args_defaults():
    """Verify default CLI arguments."""
    with patch.object(sys, "argv", ["pipeline_runner.py"]):
        args = parse_args()
        assert args.target == "all"
        assert args.days == 90
        assert args.mock is False


def test_parse_args_custom():
    """Verify customized CLI arguments."""
    with patch.object(
        sys,
        "argv",
        [
            "pipeline_runner.py",
            "--target=ingest",
            "--days=30",
            "--mock",
            "--destination=duckdb",
        ],
    ):
        args = parse_args()
        assert args.target == "ingest"
        assert args.days == 30
        assert args.mock is True
        assert args.destination == "duckdb"


def test_run_orchestrator_target_routing():
    """Verify orchestrator routes execution according to target."""
    with (
        patch("pipeline_runner.run_ingestion_step") as mock_ingest,
        patch("pipeline_runner.run_transformation_step") as mock_transform,
        patch("pipeline_runner.run_testing_step") as mock_test,
    ):
        # Target: ingest only
        res = run_pipeline_orchestrator(target="ingest", mock_mode=True, days=5)
        assert res == 0
        assert mock_ingest.called
        assert not mock_transform.called
        assert not mock_test.called

    with (
        patch("pipeline_runner.run_ingestion_step") as mock_ingest,
        patch(
            "pipeline_runner.run_transformation_step", return_value=0
        ) as mock_transform,
        patch("pipeline_runner.run_testing_step") as mock_test,
    ):
        # Target: transform only
        res = run_pipeline_orchestrator(target="transform", mock_mode=True)
        assert res == 0
        assert not mock_ingest.called
        assert mock_transform.called
        assert not mock_test.called

    with (
        patch("pipeline_runner.run_ingestion_step") as mock_ingest,
        patch("pipeline_runner.run_transformation_step") as mock_transform,
        patch(
            "pipeline_runner.run_testing_step", return_value=0
        ) as mock_test,
    ):
        # Target: test only
        res = run_pipeline_orchestrator(target="test", mock_mode=True)
        assert res == 0
        assert not mock_ingest.called
        assert not mock_transform.called
        assert mock_test.called

    with (
        patch("pipeline_runner.run_ingestion_step") as mock_ingest,
        patch(
            "pipeline_runner.run_transformation_step", return_value=0
        ) as mock_transform,
        patch(
            "pipeline_runner.run_testing_step", return_value=0
        ) as mock_test,
    ):
        # Target: all
        res = run_pipeline_orchestrator(target="all", mock_mode=True)
        assert res == 0
        assert mock_ingest.called
        assert mock_transform.called
        assert mock_test.called

