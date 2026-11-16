# Spec 0002: Semantic-First Schema Designer & AI Advisor Prompt Fix

## 1. Context & Problem Statement
Previously, `cockpit_core/components/schema_designer.py` followed an inverted **SQL-First** approach:
1. Gemini generated `duckdb_sql` without any awareness of Semantic Layer entities, dimensions, or measures.
2. Python string templates naively guessed `semantic_models.yml` and `LookML` based solely on `pd.api.types.is_numeric_dtype()`, resulting in:
   - `product_title` being selected as `primary` entity instead of `product_id`.
   - Non-additive numeric fields (`unit_price`, `*_rank`, `*_percentage`, `*_id`) being aggregated with `agg: sum`.
   - Core KPIs defaulting to `num_cols[0]` instead of the business-relevant goal metric.
3. Physical dbt Mart SQL included `LIMIT 25`, truncating the persisted warehouse table.
4. When key financial fields (e.g., `cost` / `cogs`) were absent from the database, the system silently substituted proxy metrics (e.g., Net Sales) without alerting the user or anchoring assumptions in the Semantic Layer.
5. In `fastmcp_diagnostic.py` and `cockpit_core/components/ai_drawer.py`, clearing the Prompt Editor (`""`) fell back to the long MBB default system prompt.

## 2. Target Architecture: Semantic-First Flow
1. **Step 1: Database Introspection (`reflection.get_schema_summary()`)**
   - Inspect live DuckDB/BigQuery tables, columns, types, and sample data.
2. **Step 2: Semantic Layer Anchoring (`semantic_spec`)**
   - Gemini (or deterministic heuristic fallback) first identifies:
     - `missing_fields_warning`: explicit alert if required domain fields (e.g., `cost` / `cogs`) are missing, stating the proxy assumption used.
     - `primary_entity`: true identifier key (e.g., `product_id`, `customer_id`).
     - `dimensions`: categorical/time attributes (`product_title`, `category_name`, `order_date`).
     - `measures`: strictly additive metrics with valid aggregation (`sum`, `avg`, `count`, `count_distinct`).
     - `primary_metric`: governed KPI name and description aligned with the user's goal.
   - Python Guardrails enforce strict semantic rules:
     - Never classify `*_id`, `id`, `*_rank`, `*_pct`, `*_percentage`, `unit_price` as `agg: sum` measures.
     - Always bind `model: ref('<model_name>')` to the newly synthesized Mart model.
3. **Step 3: Un-truncated Mart SQL + Preview Table**
   - `dbt_sql` (the persisted Mart table) removes `LIMIT 25` so the full dataset is materialized.
   - UI preview (`_run_duckdb_dry_run`) applies `LIMIT 25` strictly for fast, low-memory UI rendering.
4. **Step 4: Prompt Editor Empty-State Fix**
   - Distinguish between "unset (`None`)" and "explicitly cleared (`""`)".
   - When the user clears the Prompt Editor and applies, use a minimal, concise Q&A system instruction instead of falling back to the verbose MBB template.

## 3. Synchronization Requirement
- All changes to `cockpit_core/` must be developed and committed in `lakehouse-cockpit-core` (`main`), pushed to GitHub, and updated via `git submodule update --remote cockpit_core` in `data-pipeline-consulting-demo`.
