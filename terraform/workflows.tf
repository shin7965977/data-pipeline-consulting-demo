# Google Cloud Workflows - Visual DAG Orchestration
# Orchestrates: Ingest (dlt) -> Transform (dbt run) -> Test (dbt test / Elementary)

resource "google_workflows_workflow" "pipeline_workflow" {
  name            = "platzi-pipeline-orchestrator"
  region          = var.region
  description     = "Visual DAG Orchestrator for Platzi Data Pipeline with Zero Idle Cost"
  service_account = google_service_account.pipeline_sa.email
  labels          = var.labels

  source_contents = <<-EOF
    main:
      params: [args]
      steps:
        - init:
            assign:
              - project_id: "${var.project_id}"
              - location: "${var.region}"
              - job_name: "${google_cloud_run_v2_job.pipeline_job.name}"
        - log_start:
            call: sys.log
            args:
              text: "Starting Platzi Data Pipeline Visual Orchestration DAG"
              severity: "INFO"
        - run_ingest_step:
            call: googleapis.run.v2.projects.locations.jobs.run
            args:
              name: $${"projects/" + project_id + "/locations/" + location + "/jobs/" + job_name}
              body:
                overrides:
                  containerOverrides:
                    - args: ["--target=ingest"]
            result: ingest_execution
        - log_ingest_complete:
            call: sys.log
            args:
              text: "Step 1 [Ingest] finished successfully"
              severity: "INFO"
        - run_transform_step:
            call: googleapis.run.v2.projects.locations.jobs.run
            args:
              name: $${"projects/" + project_id + "/locations/" + location + "/jobs/" + job_name}
              body:
                overrides:
                  containerOverrides:
                    - args: ["--target=transform"]
            result: transform_execution
        - log_transform_complete:
            call: sys.log
            args:
              text: "Step 2 [Transform] finished successfully"
              severity: "INFO"
        - run_test_step:
            call: googleapis.run.v2.projects.locations.jobs.run
            args:
              name: $${"projects/" + project_id + "/locations/" + location + "/jobs/" + job_name}
              body:
                overrides:
                  containerOverrides:
                    - args: ["--target=test"]
            result: test_execution
        - log_test_complete:
            call: sys.log
            args:
              text: "Step 3 [Test & Observability] finished successfully"
              severity: "INFO"
        - complete_pipeline:
            return:
              status: "SUCCESS"
              ingest_step: $${ingest_execution}
              transform_step: $${transform_execution}
              test_step: $${test_execution}
  EOF

  depends_on = [
    google_project_service.enabled_apis,
    google_cloud_run_v2_job.pipeline_job
  ]
}
