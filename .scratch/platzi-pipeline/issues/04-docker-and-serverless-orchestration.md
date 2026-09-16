# 04: Docker Packaging and Serverless Orchestration

**What to build:** Unified containerization and serverless orchestration eliminating dedicated server maintenance costs. An optimized multi-stage Dockerfile packages the Python ingestion engine and dbt transformation project, controlled by a parameterized entrypoint CLI (`--target=all|ingest|transform`). A local `docker-compose.yml` allows one-command end-to-end execution. Terraform definitions deploy the container as a GCP Cloud Run Job triggered automatically via GCP Cloud Scheduler on a daily cron schedule (`0 2 * * *`).

**Blocked by:** 03: Medallion Transformations and Data Observability via dbt-core

**Status:** ready-for-agent

- [x] Multi-stage Dockerfile packages Python dependencies, dlt runner, and dbt project with non-root security.
- [x] Container entrypoint CLI supports `--target=ingest`, `--target=transform`, and `--target=all`.
- [x] `docker-compose.yml` enables developers to run the entire pipeline locally with one command: `docker compose run pipeline --target=all`.
- [x] Terraform definitions provision the GCP Cloud Run Job with memory/CPU limits and execution timeouts.
- [x] Terraform definitions provision the GCP Cloud Scheduler job with cron schedule `0 2 * * *` calling Cloud Run via OIDC Service Account token.
- [x] Manual execution can be triggered on demand via GCP Cloud Console or gcloud CLI without waiting for the scheduled trigger.
