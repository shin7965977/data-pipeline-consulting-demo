"""Lakehouse Cockpit Interactive Onboarding & Codebase Introspection Engine.

Provides dynamic codebase introspection to power the conversational onboarding skill
and standalone terminal setup wizard without hardcoded schemas or static catalogs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


def introspect_codebase(base_dir: str | Path | None = None) -> dict[str, Any]:
    """Dynamically scan the repository to extract all available lakehouse capabilities.

    Discovers:
    - Ingestion sources and domain adapters
    - dbt Gold marts models and schemas
    - Storage destinations supported by pipeline runners
    - Available deliverables (pitch decks, discovery reports)
    - Local environment health and credentials
    """
    root = Path(base_dir) if base_dir else Path(__file__).resolve().parent

    # 1. Discover Ingestion Sources
    sources = []
    sources_dir = root / "ingestion" / "sources"
    if sources_dir.exists():
        for py_file in sorted(sources_dir.glob("*.py")):
            if py_file.name.startswith("__"):
                continue
            stem = py_file.stem
            sources.append(
                {
                    "name": stem,
                    "path": str(py_file.relative_to(root)),
                    "type": "source",
                }
            )

    # 2. Discover Domain Adapters
    adapters = []
    domain_dir = root / "domain"
    if domain_dir.exists():
        for py_file in sorted(domain_dir.glob("*_adapter.py")):
            adapters.append(
                {
                    "name": py_file.stem,
                    "path": str(py_file.relative_to(root)),
                    "type": "adapter",
                }
            )
    # Also check root-level adapters (e.g. platzi_adapter.py)
    for py_file in sorted(root.glob("*_adapter.py")):
        adapters.append(
            {
                "name": py_file.stem,
                "path": str(py_file.relative_to(root)),
                "type": "adapter",
            }
        )

    # 3. Discover dbt Marts (Gold Layer)
    marts = []
    marts_dir = root / "transform_dbt" / "models" / "marts"
    if marts_dir.exists():
        for sql_file in sorted(marts_dir.glob("gold_*.sql")):
            stem = sql_file.stem
            human_title = stem.replace("gold_", "").replace("_", " ").title() + " Mart"
            marts.append(
                {
                    "model_name": stem,
                    "title": human_title,
                    "path": str(sql_file.relative_to(root)),
                }
            )

    # 4. Discover Storage Destinations from pipeline_runner.py
    destinations = ["duckdb", "bigquery"]  # Default baseline
    runner_file = root / "pipeline_runner.py"
    if runner_file.exists():
        try:
            content = runner_file.read_text(encoding="utf-8")
            choices_match = re.search(
                r"choices=\[([^\]]+)\]",
                content,
            )
            if (
                choices_match
                and "destination"
                in content[max(0, choices_match.start() - 200) : choices_match.start()]
            ):
                extracted = [
                    c.strip().strip("'\"") for c in choices_match.group(1).split(",")
                ]
                if extracted:
                    destinations = extracted
        except Exception:
            pass

    # 5. Discover Deliverable Generators
    deliverables = []
    for script_name, title in [
        ("generate_pitch_deck.py", "Executive C-Level Pitch Deck"),
        ("generate_discovery_pdf.py", "SME Transformation Discovery Guide"),
        ("chart_generator.py", "Natural Language Text-to-Chart Engine"),
        ("powerbi_builder.py", "Power BI-Style Custom Visualization Builder"),
    ]:
        script_path = root / script_name
        if script_path.exists():
            deliverables.append(
                {
                    "name": script_name,
                    "title": title,
                    "path": str(script_path.relative_to(root)),
                }
            )

    # 6. Environment & Credential Health
    env_file = root / ".env"
    env_text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY") or "GEMINI_API_KEY" in env_text)
    has_looker_embed = bool(
        os.getenv("LOOKER_STUDIO_EMBED_URL") or "LOOKER_STUDIO_EMBED_URL" in env_text
    )
    has_local_duckdb = (root / "local_warehouse.duckdb").exists()
    has_gcp_key = (root / "gcp-key.json").exists()

    return {
        "sources": sources,
        "adapters": adapters,
        "gold_marts": marts,
        "destinations": destinations,
        "deliverables": deliverables,
        "health": {
            "has_gemini_key": has_gemini_key,
            "has_looker_embed": has_looker_embed,
            "has_local_duckdb": has_local_duckdb,
            "has_gcp_key": has_gcp_key,
            "finops_budget_limit_mb": 100,
            "default_bi_engine": "Looker Studio (Embedded in Streamlit)",
        },
    }


def synthesize_dynamic_chart_proposals(
    columns: list[str] | dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Dynamically formulate consultant-grade chart proposals based on actual data columns.

    Analyzes continuous measures, categorical dimensions, and temporal axes to construct
    C-T-D-S-A (Context, Type, Data, Styling, Action Title) proposals with Looker Studio
    as the primary default BI engine embedded directly within Streamlit.
    """
    col_list = []
    if isinstance(columns, dict):
        for table_cols in columns.values():
            col_list.extend(table_cols)
    else:
        col_list = list(columns)

    normalized_cols = [c.lower() for c in col_list]

    # 1. Classify column semantics
    time_cols = [
        c
        for c in normalized_cols
        if any(
            t in c
            for t in [
                "date",
                "time",
                "timestamp",
                "year",
                "month",
                "day",
                "created",
                "period",
            ]
        )
    ]
    measure_cols = [
        c
        for c in normalized_cols
        if any(
            m in c
            for m in [
                "amount",
                "revenue",
                "price",
                "gmv",
                "cost",
                "total",
                "count",
                "orders",
                "units",
                "quantity",
                "sales",
                "profit",
                "rate",
                "pct",
                "ratio",
                "score",
                "churn",
                "clicks",
                "impressions",
                "value",
                "ltv",
                "margin",
                "salary",
                "headcount",
                "spend",
                "budget",
            ]
        )
        and c not in time_cols
    ]
    # Any column that is not temporal or measure is classified as a dimension
    dim_cols = [
        c for c in normalized_cols if c not in time_cols and c not in measure_cols
    ]

    # Fallback defaults if columns are generic
    primary_measure = measure_cols[0] if measure_cols else "record_count"
    secondary_measure = measure_cols[1] if len(measure_cols) > 1 else primary_measure
    primary_dim = dim_cols[0] if dim_cols else "category"
    primary_time = time_cols[0] if time_cols else "timestamp"

    proposals = []

    # Proposal 1: Time Series Trend & Volatility
    proposals.append(
        {
            "proposal_id": 1,
            "title": f"Temporal Performance & Trend ({primary_measure} over {primary_time})",
            "framework": {
                "C_Tool_Engine": "Google Looker Studio (Embedded in Streamlit Cockpit)",
                "T_Chart_Type": "Dual-Axis Time Series / Trend Line with 30-Day Moving Average",
                "D_Data_Specs": {
                    "x_axis": primary_time,
                    "y_axis": primary_measure,
                    "secondary_y": secondary_measure
                    if secondary_measure != primary_measure
                    else None,
                    "sort": f"Chronological ({primary_time} ASC)",
                },
                "S_Styling_Focus": "Corporate Navy & Emerald; suppress background clutter, highlight period peaks",
                "A_Action_Title": f"Trajectory and cyclical patterns in {primary_measure} indicate core demand elasticity",
            },
        }
    )

    # Proposal 2: Dimensional Pareto / Contribution
    proposals.append(
        {
            "proposal_id": 2,
            "title": f"Concentration & Pareto Breakdown ({primary_dim} vs {primary_measure})",
            "framework": {
                "C_Tool_Engine": "Google Looker Studio (Embedded in Streamlit Cockpit)",
                "T_Chart_Type": "Horizontal Ranked Bar Chart / Treemap",
                "D_Data_Specs": {
                    "dimension": primary_dim,
                    "metric": primary_measure,
                    "sort": f"Descending ({primary_measure} DESC)",
                    "top_n": 10,
                },
                "S_Styling_Focus": "Monochrome slate with accent color on top 20% contributors (80/20 Rule)",
                "A_Action_Title": f"Top {primary_dim} segments drive majority of {primary_measure}, revealing structural dependency",
            },
        }
    )

    # Proposal 3: Correlation, Ratio, or Funnel
    proposals.append(
        {
            "proposal_id": 3,
            "title": f"Efficiency & Diagnostic Variance ({primary_dim} cross-analyzed by {secondary_measure})",
            "framework": {
                "C_Tool_Engine": "Google Looker Studio (Embedded in Streamlit Cockpit)",
                "T_Chart_Type": "2x2 Quadrant Matrix / Conversion Funnel / Variance Waterfall",
                "D_Data_Specs": {
                    "primary_dimension": primary_dim,
                    "x_metric": primary_measure,
                    "y_metric": secondary_measure,
                },
                "S_Styling_Focus": "Crimson highlight for leakages/underperformers; neutral gray baseline",
                "A_Action_Title": f"Variance between {primary_measure} and {secondary_measure} reveals actionable optimization margin",
            },
        }
    )

    return proposals


def main():
    parser = argparse.ArgumentParser(
        description="Lakehouse Cockpit Onboarding & Codebase Introspection"
    )
    parser.add_argument(
        "--introspect",
        action="store_true",
        help="Perform dynamic introspection and output structured JSON",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Format output as formatted JSON string",
    )
    args = parser.parse_args()

    result = introspect_codebase()

    if args.introspect or args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Lightweight interactive summary for terminal users
    print("=" * 60)
    print("[*] Lakehouse Cockpit Dynamic Capability Introspection")
    print("=" * 60)
    print(f"Discovered Sources: {[s['name'] for s in result['sources']]}")
    print(f"Discovered Adapters: {[a['name'] for a in result['adapters']]}")
    print(f"Discovered Gold Marts: {[m['model_name'] for m in result['gold_marts']]}")
    print(f"Supported Storage Destinations: {result['destinations']}")
    print(f"Deliverables: {[d['name'] for d in result['deliverables']]}")
    print("-" * 60)
    health = result["health"]
    print(
        f"Gemini API Key configured: {'[YES]' if health['has_gemini_key'] else '[NO]'}"
    )
    print(f"Local DuckDB existing: {'[YES]' if health['has_local_duckdb'] else '[NO]'}")
    print(f"GCP Service Account key: {'[YES]' if health['has_gcp_key'] else '[NO]'}")
    print(
        f"Looker Studio Embed configured: {'[YES]' if health['has_looker_embed'] else '[NO]'}"
    )
    print(f"Default BI Visualization Engine: {health['default_bi_engine']}")
    print(f"FinOps Budget Guardrail: {health['finops_budget_limit_mb']} MB")
    print("=" * 60)
    print(
        "To start full conversational onboarding, tell the AI agent: 'setup' or 'start installation'"
    )


if __name__ == "__main__":
    main()
