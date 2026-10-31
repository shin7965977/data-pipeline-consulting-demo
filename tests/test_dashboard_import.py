import py_compile
from pathlib import Path


def test_dashboard_compilation_and_syntax():
    """Ensure dashboard.py has no syntax errors and compiles cleanly."""
    root = Path(__file__).resolve().parent.parent
    dashboard_path = root / "dashboard.py"
    assert dashboard_path.exists(), "dashboard.py must exist"
    py_compile.compile(str(dashboard_path), doraise=True)


def test_dashboard_module_imports():
    """Ensure dashboard.py dependencies resolve without ImportError."""
    # Verifies all top-level imports in dashboard.py exist
    import chart_generator
    import fastmcp_diagnostic
    import mcp_server.server

    assert hasattr(chart_generator, "generate_chart_from_nl")
    assert hasattr(mcp_server.server, "get_daily_sales_kpi")
    assert hasattr(fastmcp_diagnostic, "resolve_active_gemini_model")
