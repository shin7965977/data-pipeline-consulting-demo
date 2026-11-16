# Ticket 02: Semantic-First Pipeline, Guardrails & Un-truncated Mart SQL

- **blocked_by**: `01-align-cockpit-core-and-schema-designer.md`

## Description
Refactor `components/schema_designer.py` in `lakehouse-cockpit-core`:
1. Update Gemini prompt to perform **Semantic-First** synthesis: inspect DB -> define `semantic_spec` (`primary_entity`, `dimensions`, `measures`, `primary_metric`, `missing_fields_warning`) -> generate un-truncated `duckdb_sql`.
2. Add deterministic Python **Semantic Guardrails** (`_build_governed_semantic_artifacts`):
   - Enforce `model: ref('<model_name>')` pointing to the newly synthesized model.
   - Block `*_id`, `id`, `*_rank`, `*_pct`, `*_percentage`, `unit_price` from being summed as additive measures.
   - Ensure `primary_entity` prioritizes true identifier keys (`*_id` / `id`) over string names.
   - Render valid MetricFlow YAML (`semantic_models.yml`) and Looker LookML (`*.view.lkml`).
3. Separate physical Mart `dbt_sql` (no `LIMIT 25` truncation) from UI preview query (`LIMIT 25` applied only during preview).
4. Surface `missing_fields_warning` (e.g., missing `cost` / `cogs` when asking for profit) visibly in the UI Observability/Business Takeaway tab.

## Acceptance Criteria
- Unit tests verify Semantic-First YAML/LookML generation, non-additive measure filtering, un-truncated `dbt_sql`, and missing-field warning display.
- Code formatted cleanly with `ruff`.
- Changes committed and pushed to `lakehouse-cockpit-core` `main` and synced to `data-pipeline-consulting-demo`.
