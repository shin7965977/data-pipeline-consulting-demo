variable "project_id" {
  type        = string
  description = "The GCP Project ID where resources will be provisioned."
}

variable "region" {
  type        = string
  description = "The default GCP region for resources (e.g., us-central1, asia-east1)."
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g., dev, staging, prod)."
  default     = "prod"
}

variable "delete_contents_on_destroy" {
  type        = bool
  description = "Whether to delete all tables in BigQuery datasets when destroying via Terraform. Useful for dev/demo."
  default     = false
}

variable "labels" {
  type        = map(string)
  description = "Common labels to attach to all provisioned resources."
  default = {
    project    = "platzi-data-pipeline"
    managed_by = "terraform"
  }
}
