output "bronze_dataset_id" {
  description = "The BigQuery Bronze Dataset ID"
  value       = google_bigquery_dataset.bronze.dataset_id
}

output "silver_dataset_id" {
  description = "The BigQuery Silver Dataset ID"
  value       = google_bigquery_dataset.silver.dataset_id
}

output "gold_dataset_id" {
  description = "The BigQuery Gold Dataset ID"
  value       = google_bigquery_dataset.gold.dataset_id
}

output "artifact_registry_repository_id" {
  description = "The Artifact Registry Docker Repository ID"
  value       = google_artifact_registry_repository.pipeline_repo.repository_id
}

output "artifact_registry_repository_url" {
  description = "Full URL of the Docker repository for docker push/pull tags"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pipeline_repo.repository_id}"
}

output "pipeline_service_account_email" {
  description = "The email address of the pipeline runner Service Account"
  value       = google_service_account.pipeline_sa.email
}

output "workflow_name" {
  description = "The name of the Google Cloud Workflows orchestrator"
  value       = google_workflows_workflow.pipeline_workflow.name
}

output "workflow_id" {
  description = "The unique resource ID of the Google Cloud Workflows DAG"
  value       = google_workflows_workflow.pipeline_workflow.id
}

output "workflow_console_url" {
  description = "GCP Console URL to view and monitor the Workflows visual DAG execution"
  value       = "https://console.cloud.google.com/workflows/workflow/${var.region}/${google_workflows_workflow.pipeline_workflow.name}/executions?project=${var.project_id}"
}

