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
    print(f"FinOps Budget Guardrail: {health['finops_budget_limit_mb']} MB")
    print("=" * 60)
    print(
        "To start full conversational onboarding, tell the AI agent: 'setup' or 'start installation'"
    )


if __name__ == "__main__":
    main()
