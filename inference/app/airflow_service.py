import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests


AIRFLOW_API_BASE_URL = os.getenv(
    "AIRFLOW_API_BASE_URL",
    "http://airflow-webserver:8080/tools/airflow/api/v1",
)

AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")


DAG_CONFIGS = [
    {
        "dag_id": "ingestion_dag",
        "name": "Ingestion Pipeline",
        "description": "Stream CSV data to Kafka topic patient-events",
    },
    {
        "dag_id": "etl_dag",
        "name": "ETL Pipeline",
        "description": "Run Spark batch ETL and feature engineering",
    },
    {
        "dag_id": "training_dag",
        "name": "Training Pipeline",
        "description": "Train candidate models and register best model",
    },
    {
        "dag_id": "data_triggered_retraining_dag",
        "name": "Streaming Data Retraining",
        "description": "Retrain model when enough new streaming data is available",
    },
    {
        "dag_id": "db_triggered_retraining_dag",
        "name": "DB-triggered Retraining",
        "description": "Retrain when PostgreSQL prediction_logs has at least 50 new records",
    },
]


def airflow_request(method: str, path: str, **kwargs):
    url = f"{AIRFLOW_API_BASE_URL}{path}"

    response = requests.request(
        method=method,
        url=url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        timeout=30,
        **kwargs,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text

        try:
            detail_json = response.json()
            detail = detail_json.get("detail") or detail_json.get("title") or detail
        except ValueError:
            pass

        raise RuntimeError(
            f"Airflow API {method} {path} failed "
            f"with HTTP {response.status_code}: {detail}"
        ) from exc

    if response.content:
        return response.json()

    return {}


def unpause_dag(dag_id: str) -> Dict[str, Any]:
    return airflow_request(
        method="PATCH",
        path=f"/dags/{dag_id}",
        json={
            "is_paused": False,
        },
    )


def trigger_dag(dag_id: str) -> Dict[str, Any]:
    unpause_dag(dag_id)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    payload = {
        "dag_run_id": f"ui_manual__{timestamp}",
        "conf": {
            "triggered_by": "react_ui",
        },
    }

    return airflow_request(
        method="POST",
        path=f"/dags/{dag_id}/dagRuns",
        json=payload,
    )


def get_latest_dag_runs(dag_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    data = airflow_request(
        method="GET",
        path=f"/dags/{dag_id}/dagRuns?order_by=-start_date&limit={limit}",
    )

    return data.get("dag_runs", [])


def get_pipeline_status() -> List[Dict[str, Any]]:
    pipelines = []

    for dag_config in DAG_CONFIGS:
        dag_id = dag_config["dag_id"]

        try:
            dag_runs = get_latest_dag_runs(dag_id, limit=1)
            latest_run = dag_runs[0] if dag_runs else None

            task_instances = []

            if latest_run:
                dag_run_id = latest_run.get("dag_run_id")
                task_instances = get_task_instances(dag_id, dag_run_id)

            pipelines.append(
                {
                    **dag_config,
                    "available": True,
                    "latest_run": latest_run,
                    "tasks": task_instances,
                    "state": latest_run.get("state") if latest_run else "no_runs",
                }
            )
        except Exception as exc:
            pipelines.append(
                {
                    **dag_config,
                    "available": False,
                    "latest_run": None,
                    "tasks": [],
                    "state": "error",
                    "error": str(exc),
                }
            )

    return pipelines


def get_task_instances(dag_id: str, dag_run_id: str) -> List[Dict[str, Any]]:
    data = airflow_request(
        method="GET",
        path=f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
    )

    return data.get("task_instances", [])
