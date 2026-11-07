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


def recommend_dynamic_charts(
    columns: list[str] | dict[str, str], domain_hint: str = ""
) -> list[dict[str, Any]]:
    """Dynamically recommend high-impact executive charts based on actual data columns.

    Analyzes temporal, categorical, numeric, and lifecycle columns to synthesize
    custom visual blueprints without domain hardcoding.
    """
    col_names = list(columns.keys()) if isinstance(columns, dict) else list(columns)
    low_cols = [c.lower() for c in col_names]

    # 1. Classify columns
    temporal_cols = [
        orig
        for orig, low in zip(col_names, low_cols)
        if any(
            k in low
            for k in [
                "date",
                "time",
                "timestamp",
                "created",
                "updated",
                "year",
                "month",
                "day",
            ]
        )
    ]
    status_cols = [
        orig
        for orig, low in zip(col_names, low_cols)
        if any(k in low for k in ["status", "stage", "phase", "state", "step"])
    ]
    id_cols = [
        orig
        for orig, low in zip(col_names, low_cols)
        if low.endswith("_id") or low in ["id", "uuid", "guid", "key"]
    ]
    numeric_keywords = [
        "amount",
        "price",
        "cost",
        "revenue",
        "sales",
        "gmv",
        "aov",
        "profit",
        "qty",
        "quantity",
        "count",
        "rate",
        "ratio",
        "score",
        "value",
        "val",
        "temp",
        "temperature",
        "voltage",
        "volt",
        "watt",
        "amp",
        "power",
        "energy",
        "pressure",
        "speed",
        "humidity",
        "salary",
        "wage",
        "pay",
        "income",
        "comp",
        "bonus",
        "latency",
        "load",
        "cpu",
        "memory",
        "duration",
        "tenure",
        "age",
        "loss",
        "margin",
        "balance",
        "kpi",
        "metric",
        "index",
    ]

    dtype_map = columns if isinstance(columns, dict) else {}

    def is_numeric_col(orig: str, low: str) -> bool:
        if orig in id_cols or orig in temporal_cols or orig in status_cols:
            return False
        dtype = str(dtype_map.get(orig, "")).lower()
        if any(t in dtype for t in ["int", "float", "double", "num", "decimal"]):
            return True
        return any(k in low for k in numeric_keywords)

    numeric_cols = [
        orig for orig, low in zip(col_names, low_cols) if is_numeric_col(orig, low)
    ]
    categorical_cols = [
        orig
        for orig in col_names
        if orig not in id_cols
        and orig not in temporal_cols
        and orig not in numeric_cols
    ]

    recommendations = []

    # Rule A: Status / Lifecycle Funnel / Waterfall
    if status_cols and numeric_cols:
        status_col = status_cols[0]
        num_col = numeric_cols[0]
        recommendations.append(
            {
                "chart_type": "waterfall",
                "title": f"Lifecycle Conversion & Attrition Waterfall ({status_col})",
                "action_title": f"Quantify drop-offs and realization of {num_col} across {status_col} stages",
                "x": status_col,
                "y": num_col,
                "description": f"Break down total {num_col} across progression states in {status_col} to highlight leakage points.",
            }
        )
    elif status_cols:
        status_col = status_cols[0]
        recommendations.append(
            {
                "chart_type": "funnel",
                "title": f"Process Stage Distribution Funnel ({status_col})",
                "action_title": f"Volume transition through sequential {status_col} states",
                "x": status_col,
                "y": "count",
                "description": f"Examine volumetric distribution across {status_col} stages.",
            }
        )

    # Rule B: Temporal Longitudinal Trend
    if temporal_cols and numeric_cols:
        time_col = temporal_cols[0]
        num_col = numeric_cols[0]
        recommendations.append(
            {
                "chart_type": "line",
                "title": f"Longitudinal Trend Analysis ({num_col} over {time_col})",
                "action_title": f"Track temporal momentum and isolate volatility in {num_col}",
                "x": time_col,
                "y": num_col,
                "description": f"Analyze historical time-series patterns and variance for {num_col}.",
            }
        )

    # Rule C: Strategic 2x2 Quadrant Matrix (if 2+ numeric measures and a categorical entity)
    if len(numeric_cols) >= 2 and (categorical_cols or id_cols):
        cat_col = categorical_cols[0] if categorical_cols else id_cols[0]
        x_metric = numeric_cols[0]
        y_metric = numeric_cols[1]
        recommendations.append(
            {
                "chart_type": "quadrant_2x2",
                "title": f"Strategic 2x2 Decision Matrix ({x_metric} vs. {y_metric})",
                "action_title": f"Quadrant segmentation of {cat_col} by {x_metric} and {y_metric}",
                "x": x_metric,
                "y": y_metric,
                "group": cat_col,
                "description": f"Classify {cat_col} entities into 4 performance quadrants based on {x_metric} and {y_metric}.",
            }
        )

    # Rule D: Pareto Top-N Distribution (Categorical + Numeric)
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        if not any(r["chart_type"] == "pareto_bar" for r in recommendations):
            recommendations.append(
                {
                    "chart_type": "pareto_bar",
                    "title": f"Pareto 80/20 Contribution Ranking ({cat_col} by {num_col})",
                    "action_title": f"Identify concentration and top-tier contributors in {cat_col}",
                    "x": cat_col,
                    "y": num_col,
                    "description": f"Rank top {cat_col} segments by cumulative share of {num_col}.",
                }
            )

    # Rule E: Fallback if few columns or generic data
    if len(recommendations) < 3:
        target_col = (
            numeric_cols[0]
            if numeric_cols
            else (col_names[0] if col_names else "metric")
        )
        group_col = (
            categorical_cols[0]
            if categorical_cols
            else (temporal_cols[0] if temporal_cols else "entity")
        )
        recommendations.append(
            {
                "chart_type": "bar",
                "title": f"Comparative Distribution Analysis ({group_col} vs. {target_col})",
                "action_title": f"Comparative breakdown of {target_col} across {group_col}",
                "x": group_col,
                "y": target_col,
                "description": f"Directly compare magnitude of {target_col} partitioned by {group_col}.",
            }
        )

    return recommendations[:3]


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
    has_gemini_key = bool(
        os.getenv("GEMINI_API_KEY")
        or (
            env_file.exists()
            and "GEMINI_API_KEY" in env_file.read_text(encoding="utf-8")
        )
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
            "has_local_duckdb": has_local_duckdb,
            "has_gcp_key": has_gcp_key,
            "finops_budget_limit_mb": 100,
        },
    }


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
    parser.add_argument(
        "--recommend-charts",
        nargs="+",
        metavar="COL",
        help="Dynamically recommend charts based on a list of column names",
    )
    args = parser.parse_args()

    if args.recommend_charts:
        charts = recommend_dynamic_charts(args.recommend_charts)
        print(json.dumps(charts, indent=2, ensure_ascii=False))
        return

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
    print(f"FinOps Budget Guardrail: {health['finops_budget_limit_mb']} MB")
    print("=" * 60)
    print(
        "To start full conversational onboarding, tell the AI agent: 'setup' or 'start installation'"
    )


if __name__ == "__main__":
    main()
