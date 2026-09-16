# Terraform GCP Baseline for Platzi Data Pipeline

This module provisions the core GCP cloud foundation for the Platzi E-Commerce Data Pipeline.

## Resources Provisioned
1. **Google APIs**: Automatically enables `bigquery.googleapis.com`, `artifactregistry.googleapis.com`, `run.googleapis.com`, `cloudscheduler.googleapis.com`, and `iam.googleapis.com`.
2. **BigQuery Medallion Datasets**:
   - `platzi_bronze`: Raw ingested JSON data (managed by `dlt`).
   - `platzi_silver`: Cleaned and normalized Star Schema dimension/fact tables (managed by `dbt`).
   - `platzi_gold`: Business metrics and KPI analytical marts (for Looker Studio & FastMCP).
3. **Artifact Registry**: Docker repository (`platzi-pipeline-repo`) for pipeline container images.
4. **Service Account**: Dedicated runner identity (`platzi-pipeline-sa`) with least-privilege roles (`BigQuery Data Editor`, `BigQuery Job User`, `Artifact Registry Writer`).

---

## Quickstart Guide

### 1. Prerequisites
- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and logged in.
- [Terraform](https://www.terraform.io/) (v1.5+) installed.

### 2. Authenticate GCP
```bash
# Authenticate your Google user account
gcloud auth login

# Set Application Default Credentials (ADC) for Terraform
gcloud auth application-default login
```

### 3. Configure Variables
Copy `terraform.tfvars.example` to `terraform.tfvars`:
```bash
cp terraform.tfvars.example terraform.tfvars
```
Edit `terraform.tfvars` with your actual GCP Project ID:
```hcl
project_id = "your-actual-gcp-project-id"
region     = "asia-east1"
```

### 4. Deploy Infrastructure
```bash
# Initialize Terraform and download providers
terraform init

# Validate configuration syntax
terraform validate

# Review proposed changes
terraform plan

# Apply changes to provision resources in GCP
terraform apply
```

### 5. Tear Down (Clean up demo resources)
```bash
terraform destroy
```
