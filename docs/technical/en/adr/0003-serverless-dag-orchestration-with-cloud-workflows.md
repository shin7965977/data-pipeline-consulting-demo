# 3. Serverless Visual DAG Orchestration with Cloud Workflows and Cloud Run Jobs

Date: 2026-09-17
Status: accepted

## Context
In ADR 0001, we established an ultra-lean serverless architecture using Cloud Scheduler to directly trigger a single Cloud Run Job. While this achieved true $0 idle cost and NoOps maintenance, as the pipeline matured to incorporate automated data quality tests and Elementary Data observability, several operational limitations emerged:
1. **Single-Container Black Box**: Running Ingest, Transform, and Test sequentially within a monolithic container made it difficult to determine in GCP Console exactly which phase failed during an outage.
2. **Lack of Visual DAG Flow**: Operational engineers and stakeholders rely on clear Directed Acyclic Graph (DAG) visualizations (similar to Apache Airflow) to inspect execution progress, runtimes, and step dependencies.
3. **High Airflow / Cloud Composer Costs**: Managed Airflow environments require dedicated compute instances or GKE clusters (Cloud Composer starts at $300+/month), violating the economic principles of SME lightweight architectures.

## Decision
We decided to upgrade the orchestration layer to a **Google Cloud Scheduler + Google Cloud Workflows + Cloud Run Jobs** hybrid serverless architecture:
1. **Decoupled Pipeline Stages**:
   - `pipeline_runner.py` supports stage-level execution via `--target=ingest|transform|test`.
2. **Cloud Workflows as the Serverless DAG Orchestration Center**:
   - Codify workflow logic as a declarative state machine in YAML (`platzi-pipeline-orchestrator`).
   - Workflows invokes the official Cloud Run Admin API Connector (`googleapis.run.v2.projects.locations.jobs.run`) sequentially:
     - **Step 1: `run_ingest_step`** (`dlt` ingestion writing to BigQuery Bronze)
     - **Step 2: `run_transform_step`** (`dbt run` building Silver and Gold dimensional models)
     - **Step 3: `run_test_step`** (`dbt test` verifying data contract rules and Elementary telemetry)
   - The Workflows Connector manages long-polling and automated retries natively without manual polling scripts.
3. **Cloud Scheduler Triggers Workflows**:
   - Cloud Scheduler dispatches scheduled daily HTTP POST calls to the Cloud Workflows Executions API, triggering the DAG run.
4. **100% Terraform Automation**:
   - Defined in `terraform/workflows.tf`, managing Workflows state machines, Cloud Run Jobs, and IAM bindings under unified Infrastructure as Code (IaC).

## Consequences
- **Advantages**:
  - **Native Visual DAG**: Delivers step-by-step graphical workflow visualization in Google Cloud Console matching Airflow's user experience, providing real-time visibility into stage durations and step status.
  - **Maintains True $0 Idle Cost**: Cloud Workflows includes 5,000 internal steps per month free; when inactive, zero VM or container compute costs are incurred ($0/mo idle cost).
  - **Modularity & Maintainability**: Downstream failures (e.g., failed tests) do not invalidate successful upstream ingestion batches, and individual stages can be retried independently via Console or CLI.
  - **Seamless Elementary Integration**: The test stage functions as a dedicated terminal node in the DAG, producing automated data observability alerts and lineage telemetry.
- **Trade-offs**:
  - Cloud Workflows employs declarative YAML/JSON syntax rather than Python code, offering slightly less dynamic metaprogramming flexibility than Airflow; however, for modern ELT pipelines (`Ingest -> Transform -> Test`), its declarative simplicity and zero-idle cost are unmatched.
