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


def load_candidate_from_metrics_file():
    if not Path(METRICS_PATH).exists():
        raise FileNotFoundError(
            f"Không tìm thấy {METRICS_PATH}. Hãy chạy training.train trước."
        )

    with open(METRICS_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    run_id = data.get("run_id")
    model_uri = data.get("model_uri")
    model_type = data.get("model_type")
    metrics = data.get("metrics", {})
    selection = data.get("selection", {})
    metric_name = REGISTER_METRIC_NAME or selection.get("metric") or "recall"
    metric_mode = REGISTER_METRIC_MODE or selection.get("mode") or "max"

    if not run_id:
        raise ValueError("metrics.json thiếu run_id.")

    if not model_uri:
        model_uri = f"runs:/{run_id}/model"

    if metric_name not in metrics:
        raise ValueError(f"metrics.json không có metric: {metric_name}")

    return run_id, model_uri, model_type, float(metrics[metric_name]), metric_name, metric_mode


def verify_model_artifact(model_uri: str):
    local_path = download_artifacts(artifact_uri=model_uri)

    required_files = ["MLmodel", "model.pkl"]
    for file_name in required_files:
        file_path = Path(local_path) / file_name
        if not file_path.exists():
            raise RuntimeError(f"Missing artifact file: {file_path}")

    print(f"Verified model artifact: {local_path}")


def set_version_metadata(
    client: MlflowClient,
    registered_version,
    model_type: str | None,
    metric_name: str,
    metric_value: float,
) -> str:
    version_label = f"v{registered_version.version}"

    client.set_model_version_tag(
        name=MODEL_NAME,
        version=registered_version.version,
        key="version_label",
        value=version_label,
    )
    client.set_model_version_tag(
        name=MODEL_NAME,
        version=registered_version.version,
        key="selection_metric",
        value=metric_name,
    )
    client.set_model_version_tag(
        name=MODEL_NAME,
        version=registered_version.version,
        key="selection_metric_value",
        value=str(metric_value),
    )

    if model_type:
        client.set_model_version_tag(
            name=MODEL_NAME,
            version=registered_version.version,
            key="model_type",
            value=model_type,
        )
        client.set_tag(
            run_id=registered_version.run_id,
            key="model_type",
            value=model_type,
        )

    client.set_tag(
        run_id=registered_version.run_id,
        key="registered_version_label",
        value=version_label,
    )

    try:
        client.set_registered_model_alias(
            name=MODEL_NAME,
            alias=version_label,
            version=registered_version.version,
        )
    except Exception as exc:
        print(f"Cannot set MLflow alias {version_label}. Tag was still saved. Reason: {exc}")

    return version_label


def main():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    client = MlflowClient()

    (
        run_id,
        model_uri,
        model_type,
        candidate_metric,
        metric_name,
        metric_mode,
    ) = load_candidate_from_metrics_file()

    print(f"Candidate run_id: {run_id}")
    print(f"Candidate model_uri: {model_uri}")
    print(f"Candidate model_type: {model_type}")
    print(f"Selection metric: {metric_name} ({metric_mode})")
    print(f"Candidate {metric_name}: {candidate_metric}")

    verify_model_artifact(model_uri)

    registered_model = mlflow.register_model(
        model_uri=model_uri,
        name=MODEL_NAME,
    )

    version_label = set_version_metadata(
        client=client,
        registered_version=registered_model,
        model_type=model_type,
        metric_name=metric_name,
        metric_value=candidate_metric,
    )

    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=registered_model.version,
        stage="Production",
        archive_existing_versions=True,
    )

    print(
        f"Registered {MODEL_NAME} version {registered_model.version} "
        f"({version_label}) and promoted it "
        f"to Production. Metric {metric_name} = {candidate_metric}"
    )


if __name__ == "__main__":
    main()
