# 01: Terraform GCP Infrastructure Baseline

**What to build:** An automated Terraform module that provisions the complete foundational Google Cloud Platform environment. A developer or consultant can run `terraform apply` against an empty GCP project and immediately obtain all BigQuery Medallion datasets (`platzi_bronze`, `platzi_silver`, `platzi_gold`), an Artifact Registry Docker repository for container images, and a dedicated Service Account configured with least-privilege IAM roles.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Terraform code defines provider settings and region configuration (defaulting to `asia-east1` or `us-central1`).
- [x] BigQuery datasets `platzi_bronze`, `platzi_silver`, and `platzi_gold` are created with appropriate labels.
- [x] Artifact Registry repository is created with Docker format to store pipeline container images.
- [x] Pipeline Service Account is provisioned with `roles/bigquery.dataEditor`, `roles/bigquery.jobUser`, and `roles/artifactregistry.writer`.
- [x] Local environment authentication setup instructions and `.tfvars.example` are provided.
- [x] `terraform plan` and `terraform apply` execute cleanly without manual intervention.
