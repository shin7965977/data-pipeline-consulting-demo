# 1. Serverless Orchestration via Cloud Scheduler and Cloud Run Jobs

Date: 2026-09-16
Status: superseded by ADR 0003

## Context
This project serves as an enterprise-grade commercial data pipeline prototype and consulting demonstration tailored for small and medium-sized enterprises (SMEs). Traditional enterprises often deploy Apache Airflow as their orchestration center; however, Airflow requires long-running dedicated virtual machines or managed clusters (such as Cloud Composer), imposing high monthly maintenance costs ($300–$500+/month) and demanding dedicated operations staff to monitor underlying PostgreSQL metadata databases and host OS health. In contrast, typical SME data operations center around scheduled daily batch updates and occasional manual on-demand triggers.

## Decision
We decided to adopt **GCP Cloud Scheduler + Cloud Run Jobs** as the serverless workflow orchestration architecture for this pipeline, completely superseding an always-on Apache Airflow cluster:
1. Package both `dlt` data ingestion and `dbt` transformation models into a unified Docker container image stored in GCP Artifact Registry.
2. Execute batch workloads via Cloud Run Jobs, triggered periodically on a Cron schedule by Cloud Scheduler.
3. Enable granular container CLI parameterization (`--target=all|ingest|transform`), seamlessly accommodating automated daily schedules and manual on-demand runs.

## Consequences
- **Advantages**:
  - Extremely Low Total Cost of Ownership (TCO): Baseline infrastructure cost is virtually $0/month (comfortably within Cloud Scheduler and Cloud Run free tiers).
  - True Serverless / NoOps: Zero risk of VM crashes, disk exhaustion, or operating system patch overhead.
  - 100% Infrastructure as Code (IaC): All infrastructure components—including Cloud Scheduler, Cloud Run Jobs, and IAM policies—are codified and reproducibly managed via Terraform.
- **Trade-offs**:
  - Lacks Airflow's built-in multi-DAG dependency visualization dashboard out-of-the-box; however, for an SME's linear end-to-end batch pipeline, this trade-off provides exceptional economic ROI.
