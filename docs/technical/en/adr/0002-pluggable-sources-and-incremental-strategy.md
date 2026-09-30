# 2. Pluggable Source Adapters, Incremental ELT, and AI Security Boundary

Date: 2026-09-16
Status: accepted

## Context
This project is an enterprise-grade commercial prototype designed for consulting engagements with SMEs. To ensure that client data sources can be swapped out seamlessly in future engagements while maintaining strict computational cost controls and data security compliance as data scales, the architecture must decouple source systems, establish automated incremental processing, and strictly enforce security perimeters for AI query interfaces.

## Decision
1. **Pluggable Source Adapter Architecture**:
   - The data extraction layer is abstracted into modular source adapters (`ingestion/sources/`).
   - Adapters normalize heterogeneous source payloads into unified Canonical Schemas (`raw_orders`, `raw_customers`, `raw_products`). When onboarding new client systems (e.g., Shopify, POS), engineers only implement a new adapter; downstream dbt models remain 100% reusable without modification.
2. **End-to-End Incremental Processing (Incremental ELT)**:
   - `dlt` tracks watermark cursors via `updated_at` timestamps, extracting only mutated and new records.
   - `dbt` implements `materialized='incremental'` in both Silver and Gold layers using `order_id` as the primary key for Merge/Upsert operations, drastically reducing warehouse runtimes and BigQuery byte scanning costs.
3. **AI Query Security Boundary (FastMCP Scope & Governance)**:
   - AI tools and LLM agents are granted read-only access exclusively to the `Gold` tier (anonymized, pre-aggregated business marts).
   - Sensitive PII (names, emails) is strictly confined to Bronze/Silver layers with salted cryptographic hashing, never exposed to AI models.
   - FastMCP enforces maximum byte scan quotas per query, preventing runaway cloud costs from exploratory prompts.

## Consequences
- **Advantages**:
  - High asset reusability across consulting client engagements, compressing time-to-delivery from months to days.
  - Compute and storage costs remain predictable and low even as historical volumes grow.
  - Fully compliant with data privacy regulations (GDPR/CCPA standards), eliminating client security concerns regarding AI database access.
