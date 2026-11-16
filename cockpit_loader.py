"""Safe loader for cockpit_core components across local and Streamlit Cloud deployments."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

_COCKPIT_REPO = "https://github.com/shin7965977/lakehouse-cockpit-core.git"


def _ensure_cockpit_core_on_path() -> None:
    """Ensure a populated cockpit_core package is importable even if submodule is empty."""
    repo_root = Path(__file__).resolve().parent
    local_schema_designer = repo_root / "cockpit_core" / "components" / "schema_designer.py"
    if local_schema_designer.exists():
        return

    cache_root = Path(tempfile.gettempdir()) / "cockpit_core_cache"
    cached_pkg = cache_root / "cockpit_core"
    if not (cached_pkg / "components" / "schema_designer.py").exists():
        cache_root.mkdir(parents=True, exist_ok=True)
        if not cached_pkg.exists():
            subprocess.run(
                ["git", "clone", "--depth", "1", _COCKPIT_REPO, str(cached_pkg)],
                check=True,
                capture_output=True,
                text=True,
            )

    if str(cache_root) not in sys.path:
        sys.path.insert(0, str(cache_root))

    # Clear any empty namespace package cached from an uninitialized submodule dir
    for mod_name in list(sys.modules):
        if mod_name == "cockpit_core" or mod_name.startswith("cockpit_core."):
            sys.modules.pop(mod_name, None)


def load_render_schema_designer_view() -> Any:
    """Return render_schema_designer_view with Streamlit Cloud submodule fallback."""
    try:
        _ensure_cockpit_core_on_path()
        from cockpit_core.components.schema_designer import render_schema_designer_view

        return render_schema_designer_view
    except Exception as exc:

        def _fallback_view(
            adapter: Any,
            data_dict: dict[str, pd.DataFrame],
            is_en: bool = True,
        ) -> None:
            st.warning(
                f"Autonomous Schema Designer could not be loaded: {exc}"
                if is_en
                else f"無法載入 Autonomous Schema Designer 模組：{exc}"
            )

        return _fallback_view


render_schema_designer_view = load_render_schema_designer_view()
