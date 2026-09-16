# Technical Specification

See the canonical specification file under `.scratch/specs/`:
👉 [Spec 0001: Platzi E-Commerce Cloud Data Pipeline & Analytics Platform](file:///c:/Users/shin7/Downloads/CV/data-pipeline-consulting-demo/.scratch/specs/0001-platzi-ecommerce-data-pipeline.md)

### Key Summaries
- **Architecture**: Pluggable Ingestion (`dlt`) + Lakehouse (`BigQuery Bronze/Silver/Gold`) + Transformations (`dbt-core`) + Serverless Orchestration (`Cloud Scheduler` + `Cloud Run Jobs`) + Declarative IaC (`Terraform`) + AI Interface (`FastMCP`).
- **Domain & Language**: Strictly aligned with [`CONTEXT.md`](file:///c:/Users/shin7/Downloads/CV/data-pipeline-consulting-demo/CONTEXT.md).
- **Key ADRs**:
  - [ADR 0001: Serverless Orchestration via Cloud Scheduler and Cloud Run Jobs](file:///c:/Users/shin7/Downloads/CV/data-pipeline-consulting-demo/docs/adr/0001-serverless-orchestration-cloud-run-and-scheduler.md)
  - [ADR 0002: Pluggable Source Adapters, Incremental ELT, and AI Security Boundary](file:///c:/Users/shin7/Downloads/CV/data-pipeline-consulting-demo/docs/adr/0002-pluggable-sources-and-incremental-strategy.md)
