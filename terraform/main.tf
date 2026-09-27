# 1. Enable Required GCP APIs
locals {
  services = [
    "bigquery.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "cloudscheduler.googleapis.com",
    "workflows.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com"
  ]
}

resource "google_project_service" "enabled_apis" {
  for_each           = toset(local.services)
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. BigQuery Medallion Architecture Datasets
resource "google_bigquery_dataset" "bronze" {
  dataset_id                 = "platzi_bronze"
  friendly_name              = "Platzi Bronze (Raw)"
  description                = "Bronze Layer: Raw ingested e-commerce JSON data (Append-only) managed by dlt"
  location                   = var.region
  delete_contents_on_destroy = var.delete_contents_on_destroy
  labels                     = merge(var.labels, { layer = "bronze" })

  depends_on = [google_project_service.enabled_apis]
}

resource "google_bigquery_dataset" "silver" {
  dataset_id                 = "platzi_silver"
  friendly_name              = "Platzi Silver (Cleaned)"
  description                = "Silver Layer: Cleaned and normalized Star Schema (dim_* and fct_*) managed by dbt"
  location                   = var.region
  delete_contents_on_destroy = var.delete_contents_on_destroy
  labels                     = merge(var.labels, { layer = "silver" })

  depends_on = [google_project_service.enabled_apis]
}

resource "google_bigquery_dataset" "gold" {
  dataset_id                 = "platzi_gold"
  friendly_name              = "Platzi Gold (Marts)"
  description                = "Gold Layer: Business aggregation and KPI marts for Looker Studio and FastMCP"
  location                   = var.region
  delete_contents_on_destroy = var.delete_contents_on_destroy
  labels                     = merge(var.labels, { layer = "gold" })

  depends_on = [google_project_service.enabled_apis]
}

# 3. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "pipeline_repo" {
  location      = var.region
  repository_id = "platzi-pipeline-repo"
  description   = "Docker repository for Platzi Data Pipeline runner container images"
  format        = "DOCKER"
  labels        = var.labels

  depends_on = [google_project_service.enabled_apis]
}

# 4. Pipeline Service Account and IAM Roles
resource "google_service_account" "pipeline_sa" {
  account_id   = "platzi-pipeline-sa"
  display_name = "Service Account for Platzi Data Pipeline Runner"
  description  = "Dedicated runner identity for dlt ingestion, dbt transformation, and Cloud Run"

  depends_on = [google_project_service.enabled_apis]
}

locals {
  pipeline_roles = [
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/artifactregistry.writer",
    "roles/workflows.invoker",
    "roles/run.developer",
    "roles/iam.serviceAccountUser"
  ]
}

resource "google_project_iam_member" "pipeline_sa_roles" {
  for_each = toset(local.pipeline_roles)
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# 5. Cloud Storage Bucket for Elementary Observability Reports
resource "google_storage_bucket" "observability_bucket" {
  name                        = "${var.project_id}-elementary-reports"
  location                    = var.region
  force_destroy               = var.delete_contents_on_destroy
  uniform_bucket_level_access = true
  labels                      = merge(var.labels, { service = "observability" })

  website {
    main_page_suffix = "elementary_report.html"
    not_found_page   = "elementary_report.html"
  }

  depends_on = [google_project_service.enabled_apis]
}

# Grant Pipeline Service Account admin access to the report bucket
resource "google_storage_bucket_iam_member" "pipeline_sa_storage_admin" {
  bucket = google_storage_bucket.observability_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Allow public or internal read access to the HTML report
resource "google_storage_bucket_iam_member" "public_report_viewer" {
  bucket = google_storage_bucket.observability_bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
