import os
from typing import Any

import requests


def get_gcp_auth_token() -> tuple[str | None, str | None]:
    """Obtain a valid OAuth2 Bearer token and project_id using google.auth."""
    try:
        import google.auth
        from google.auth.transport.requests import Request

        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        if not credentials.valid:
            credentials.refresh(Request())
        return credentials.token, project
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def trigger_pipeline_workflow(
    project_id: str | None = None,
    location: str = "asia-east1",
    workflow_id: str = "platzi-pipeline-orchestrator",
) -> tuple[bool, dict[str, Any] | str]:
    """Trigger the Google Cloud Workflows orchestrator via REST API.

    Returns (True, response_json) on success, or (False, error_message) on failure.
    """
    token, proj = get_gcp_auth_token()
    if not token:
        return False, f"無法獲取 GCP 認證憑證：{proj}"

    eff_project = project_id or os.getenv("GCP_PROJECT_ID") or proj or "de-consulting-508822"
    url = (
        f"https://workflowexecutions.googleapis.com/v1/"
        f"projects/{eff_project}/locations/{location}/workflows/{workflow_id}/executions"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json={}, timeout=15)
        if response.status_code in (200, 201):
            return True, response.json()
        return False, f"GCP Workflows 回應 HTTP {response.status_code}: {response.text}"
    except Exception as ex:  # noqa: BLE001
        return False, f"連線至 GCP Workflows 失敗: {ex}"


def get_workflow_execution_status(execution_name: str) -> tuple[bool, dict[str, Any] | str]:
    """Query the status of an ongoing Cloud Workflows execution."""
    token, proj = get_gcp_auth_token()
    if not token:
        return False, f"無法獲取 GCP 認證憑證：{proj}"

    url = f"https://workflowexecutions.googleapis.com/v1/{execution_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, response.json()
        return False, f"查詢狀態 HTTP {response.status_code}: {response.text}"
    except Exception as ex:  # noqa: BLE001
        return False, f"查詢失敗: {ex}"
