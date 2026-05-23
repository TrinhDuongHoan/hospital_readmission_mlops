import json
import os
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.artifacts import download_artifacts


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "HospitalReadmissionModel")
METRICS_PATH = os.getenv("METRICS_PATH", "reports/metrics.json")

REGISTER_METRIC_NAME = os.getenv("REGISTER_METRIC_NAME")
REGISTER_METRIC_MODE = os.getenv("REGISTER_METRIC_MODE")
MIN_IMPROVEMENT = float(os.getenv("MIN_IMPROVEMENT", "0.001"))


def load_candidate_from_metrics_file():
    if not Path(METRICS_PATH).exists():
        raise FileNotFoundError(
            f"Không tìm thấy {METRICS_PATH}. Hãy chạy training.train trước."
        )

    with open(METRICS_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    run_id = data.get("run_id")
    model_uri = data.get("model_uri")
    metrics = data.get("metrics", {})
    selection = data.get("selection", {})
    metric_name = REGISTER_METRIC_NAME or selection.get("metric") or "roc_auc"
    metric_mode = REGISTER_METRIC_MODE or selection.get("mode") or "max"

    if not run_id:
        raise ValueError("metrics.json thiếu run_id.")

    if not model_uri:
        model_uri = f"runs:/{run_id}/model"

    if metric_name not in metrics:
        raise ValueError(f"metrics.json không có metric: {metric_name}")

    return run_id, model_uri, float(metrics[metric_name]), metric_name, metric_mode


def verify_model_artifact(model_uri: str):
    local_path = download_artifacts(artifact_uri=model_uri)

    required_files = ["MLmodel", "model.pkl"]
    for file_name in required_files:
        file_path = Path(local_path) / file_name
        if not file_path.exists():
            raise RuntimeError(f"Missing artifact file: {file_path}")

    print(f"Verified model artifact: {local_path}")


def get_production_model(client: MlflowClient, metric_name: str):
    versions = client.search_model_versions(f"name='{MODEL_NAME}'")

    production_versions = [
        version
        for version in versions
        if version.current_stage == "Production"
    ]

    if not production_versions:
        return None, None

    latest_production = sorted(
        production_versions,
        key=lambda version: int(version.version),
        reverse=True,
    )[0]

    try:
        run = client.get_run(latest_production.run_id)
    except Exception as exc:
        print(
            "Cannot read current Production run "
            f"{latest_production.run_id}. Treating the new model as better. "
            f"Reason: {exc}"
        )
        return latest_production, None

    metric = run.data.metrics.get(metric_name)

    return latest_production, metric


def is_better(candidate_metric, production_metric, metric_mode: str):
    if production_metric is None:
        return True

    if metric_mode == "max":
        return candidate_metric > production_metric + MIN_IMPROVEMENT

    if metric_mode == "min":
        return candidate_metric < production_metric - MIN_IMPROVEMENT

    raise ValueError("REGISTER_METRIC_MODE chỉ được là 'max' hoặc 'min'.")


def main():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    client = MlflowClient()

    (
        run_id,
        model_uri,
        candidate_metric,
        metric_name,
        metric_mode,
    ) = load_candidate_from_metrics_file()

    print(f"Candidate run_id: {run_id}")
    print(f"Candidate model_uri: {model_uri}")
    print(f"Selection metric: {metric_name} ({metric_mode})")
    print(f"Candidate {metric_name}: {candidate_metric}")

    verify_model_artifact(model_uri)

    production_version, production_metric = get_production_model(client, metric_name)

    if production_version is None:
        print("Chưa có Production model. Sẽ register model đầu tiên.")
    else:
        print(
            f"Current Production version: {production_version.version}, "
            f"run_id: {production_version.run_id}, "
            f"{metric_name}: {production_metric}"
        )

    if not is_better(candidate_metric, production_metric, metric_mode):
        print("Model mới không tốt hơn Production model. Bỏ qua register/promote.")
        return

    registered_model = mlflow.register_model(
        model_uri=model_uri,
        name=MODEL_NAME,
    )

    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=registered_model.version,
        stage="Production",
        archive_existing_versions=True,
    )

    print(
        f"Promoted {MODEL_NAME} version {registered_model.version} "
        f"to Production. Metric {metric_name} = {candidate_metric}"
    )


if __name__ == "__main__":
    main()
