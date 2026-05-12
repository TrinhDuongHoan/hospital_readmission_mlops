import json
import os
from pathlib import Path

import mlflow
from dotenv import dotenv_values
from mlflow.tracking import MlflowClient

from training.train import (
    configure_mlflow_artifact_store,
    get_config_value,
    load_config,
)

DEFAULT_ENV_PATH = ".env"


def load_env_values(env_path: str = DEFAULT_ENV_PATH) -> dict:
    if not Path(env_path).exists():
        return {}

    return {
        key: value
        for key, value in dotenv_values(env_path).items()
        if value is not None
    }


def get_env_value(env_values: dict, key: str, default=None):
    return os.getenv(key) or env_values.get(key) or default


def get_mlflow_tracking_uri(config: dict, env_values: dict) -> str:
    return (
        os.getenv("MLFLOW_TRACKING_URI")
        or env_values.get("MLFLOW_EXTERNAL_TRACKING_URI")
        or env_values.get("MLFLOW_TRACKING_URI")
        or get_config_value(config, ["mlflow", "tracking_uri"], "http://localhost:5000")
    )


def get_metric_from_run(client: MlflowClient, run_id: str, metric_name: str):
    run = client.get_run(run_id)
    return run.data.metrics.get(metric_name)


def get_current_production_metric(client: MlflowClient, model_name: str, metric_name: str):
    versions = client.search_model_versions(
        filter_string=f"name='{model_name}'"
    )

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

    production_metric = get_metric_from_run(
        client=client,
        run_id=latest_production.run_id,
        metric_name=metric_name,
    )

    return latest_production, production_metric


def is_better_model(new_metric, old_metric, metric_mode: str, min_improvement: float):
    if old_metric is None:
        return True

    if metric_mode == "max":
        return new_metric > old_metric + min_improvement

    if metric_mode == "min":
        return new_metric < old_metric - min_improvement

    raise ValueError("METRIC_MODE must be 'max' or 'min'")


def get_latest_training_run_from_metrics_file(metrics_path: str, metric_name: str):
    if not Path(metrics_path).exists():
        raise FileNotFoundError(
            f"Metrics file not found: {metrics_path}. "
            f"Run training/train.py first."
        )

    with open(metrics_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    run_id = data.get("run_id")
    model_uri = data.get("model_uri")
    metrics = data.get("metrics", {})

    if not run_id or not model_uri:
        raise ValueError(
            f"{metrics_path} must contain run_id and model_uri."
        )

    if metric_name not in metrics:
        raise ValueError(
            f"Metric {metric_name} not found in {metrics_path}."
        )

    return run_id, model_uri, metrics[metric_name], data.get("candidate_name")


def tag_champion_model(
    client: MlflowClient,
    model_name: str,
    version: str,
    run_id: str,
    candidate_name: str,
    metric_name: str,
    metric_value: float,
) -> None:
    tags = {
        "champion_model": candidate_name or "unknown",
        "champion_metric": metric_name,
        "champion_metric_value": str(metric_value),
        "champion_run_id": run_id,
    }

    for key, value in tags.items():
        client.set_registered_model_tag(model_name, key, value)
        client.set_model_version_tag(model_name, version, key, value)

    client.set_model_version_tag(model_name, version, "role", "champion")
    client.set_tag(run_id, "candidate_role", "champion")

    if hasattr(client, "set_registered_model_alias"):
        client.set_registered_model_alias(model_name, "champion", version)


def main():
    config = load_config()
    env_values = load_env_values()

    mlflow_tracking_uri = get_mlflow_tracking_uri(config, env_values)
    model_name = get_env_value(
        env_values,
        "MLFLOW_MODEL_NAME",
        get_config_value(config, ["model", "name"], "HospitalReadmissionModel"),
    )
    metric_name = get_env_value(
        env_values,
        "REGISTER_METRIC_NAME",
        get_config_value(config, ["selection", "metric"], "roc_auc"),
    )
    metric_mode = get_env_value(
        env_values,
        "REGISTER_METRIC_MODE",
        get_config_value(config, ["selection", "mode"], "max"),
    )
    min_improvement = float(get_env_value(env_values, "MIN_IMPROVEMENT", "0.0"))
    metrics_path = os.getenv(
        "METRICS_PATH",
        get_config_value(config, ["output", "metrics_path"], "reports/metrics.json"),
    )

    configure_mlflow_artifact_store(config)
    mlflow.set_tracking_uri(mlflow_tracking_uri)

    client = MlflowClient()

    run_id, model_uri, new_metric, candidate_name = get_latest_training_run_from_metrics_file(
        metrics_path=metrics_path,
        metric_name=metric_name,
    )

    production_version, production_metric = get_current_production_metric(
        client=client,
        model_name=model_name,
        metric_name=metric_name,
    )

    print(f"Candidate name: {candidate_name}")
    print(f"Candidate run_id: {run_id}")
    print(f"Candidate model_uri: {model_uri}")
    print(f"Candidate {metric_name}: {new_metric}")
    print(f"Minimum improvement: {min_improvement}")

    if production_version is None:
        print("No Production model found. Registering first model.")
    else:
        print(
            f"Current Production version: {production_version.version}, "
            f"{metric_name}: {production_metric}"
        )

    if not is_better_model(new_metric, production_metric, metric_mode, min_improvement):
        if production_version is not None and production_version.run_id == run_id:
            tag_champion_model(
                client=client,
                model_name=model_name,
                version=production_version.version,
                run_id=run_id,
                candidate_name=candidate_name,
                metric_name=metric_name,
                metric_value=new_metric,
            )
            print(
                f"Synced champion tags for {model_name} "
                f"version {production_version.version}."
            )

        print(
            "New model is not better than Production model. "
            "Skip registration."
        )
        return

    registered_model = mlflow.register_model(
        model_uri=model_uri,
        name=model_name,
    )

    client.transition_model_version_stage(
        name=model_name,
        version=registered_model.version,
        stage="Production",
        archive_existing_versions=True,
    )

    tag_champion_model(
        client=client,
        model_name=model_name,
        version=registered_model.version,
        run_id=run_id,
        candidate_name=candidate_name,
        metric_name=metric_name,
        metric_value=new_metric,
    )

    print(
        f"Promoted {model_name} version {registered_model.version} "
        f"to Production because {metric_name} improved."
    )


if __name__ == "__main__":
    main()
