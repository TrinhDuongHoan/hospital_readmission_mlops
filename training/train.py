import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml

from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DEFAULT_CONFIG_PATH = "training/config.yaml"


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_config_value(config: dict, keys: list[str], default_value=None):
    value = config

    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default_value

        value = value[key]

    return value


def configure_mlflow_artifact_store(config: dict) -> None:
    artifact_env_values = {
        "MLFLOW_S3_ENDPOINT_URL": get_config_value(
            config,
            ["mlflow", "s3_endpoint_url"],
        ),
        "AWS_ACCESS_KEY_ID": get_config_value(
            config,
            ["mlflow", "aws_access_key_id"],
        ),
        "AWS_SECRET_ACCESS_KEY": get_config_value(
            config,
            ["mlflow", "aws_secret_access_key"],
        ),
    }

    for env_name, env_value in artifact_env_values.items():
        if env_value and not os.getenv(env_name):
            os.environ[env_name] = str(env_value)


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.replace("?", pd.NA)
    df["readmitted_binary"] = (df["readmitted"] == "<30").astype(int)

    drop_cols = [
        "encounter_id",
        "patient_nbr",
        "weight",
        "payer_code",
        "medical_specialty",
        "readmitted",
    ]

    existing_drop_cols = [
        column_name
        for column_name in drop_cols
        if column_name in df.columns
    ]

    df = df.drop(columns=existing_drop_cols)

    df = df.dropna(
        subset=[
            "race",
            "gender",
            "age",
        ]
    )

    categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
    numeric_cols = df.select_dtypes(exclude=["object"]).columns.tolist()

    if "readmitted_binary" in numeric_cols:
        numeric_cols.remove("readmitted_binary")

    for column_name in categorical_cols:
        df[column_name] = df[column_name].astype("string").fillna("Unknown").astype(str)

    for column_name in numeric_cols:
        df[column_name] = pd.to_numeric(df[column_name], errors="coerce")

    return df


def get_model_candidates(config: dict) -> list[dict]:
    candidates = get_config_value(config, ["model", "candidates"])

    if candidates:
        return candidates

    return [
        {
            "name": "random_forest",
            "type": "random_forest",
            "params": {
                "n_estimators": get_config_value(config, ["model", "n_estimators"], 150),
                "max_depth": get_config_value(config, ["model", "max_depth"], 12),
                "class_weight": get_config_value(config, ["model", "class_weight"], "balanced"),
            },
        }
    ]


def build_estimator(candidate: dict, config: dict):
    candidate_type = candidate["type"]
    params = candidate.get("params", {})
    random_state = get_config_value(config, ["model", "random_state"], 42)

    if candidate_type == "random_forest":
        return RandomForestClassifier(
            random_state=random_state,
            n_jobs=-1,
            **params,
        )

    if candidate_type == "logistic_regression":
        logistic_params = {
            "max_iter": 1000,
            **params,
        }

        return LogisticRegression(
            random_state=random_state,
            n_jobs=-1,
            **logistic_params,
        )

    if candidate_type == "xgboost":
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError(
                "XGBoost is not installed. Install xgboost or remove the "
                "xgboost candidate from training/config.yaml."
            ) from exc

        xgboost_params = {
            "eval_metric": "logloss",
            "tree_method": "hist",
            **params,
        }

        return XGBClassifier(
            random_state=random_state,
            n_jobs=-1,
            **xgboost_params,
        )

    raise ValueError(f"Unsupported model candidate type: {candidate_type}")


def build_model(X_train: pd.DataFrame, config: dict, candidate: dict) -> Pipeline:
    categorical_cols = X_train.select_dtypes(include=["object"]).columns.tolist()
    numeric_cols = X_train.select_dtypes(exclude=["object"]).columns.tolist()

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", categorical_transformer, categorical_cols),
        ]
    )

    model = build_estimator(candidate, config)

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def calculate_metrics(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }


def is_better_metric(new_value: float, current_value: float | None, mode: str) -> bool:
    if current_value is None:
        return True

    if mode == "max":
        return new_value > current_value

    if mode == "min":
        return new_value < current_value

    raise ValueError("selection.mode must be 'max' or 'min'")


def main():
    config = load_config()

    csv_path = os.getenv(
        "CSV_PATH",
        get_config_value(config, ["data", "csv_path"], "data/diabetic_data.csv"),
    )

    model_path = os.getenv(
        "MODEL_LOCAL_PATH",
        get_config_value(config, ["output", "model_path"], "models/model.pkl"),
    )

    metrics_path = os.getenv(
        "METRICS_PATH",
        get_config_value(config, ["output", "metrics_path"], "reports/metrics.json"),
    )

    mlflow_tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        get_config_value(config, ["mlflow", "tracking_uri"], "http://localhost:5000"),
    )

    experiment_name = os.getenv(
        "MLFLOW_EXPERIMENT_NAME",
        get_config_value(config, ["model", "experiment_name"], "Hospital_Readmission"),
    )

    configure_mlflow_artifact_store(config)

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)

    df = load_data(csv_path)

    X = df.drop(columns=["readmitted_binary"])
    y = df["readmitted_binary"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=get_config_value(config, ["model", "test_size"], 0.2),
        random_state=get_config_value(config, ["model", "random_state"], 42),
        stratify=y,
    )

    candidates = get_model_candidates(config)
    selection_metric = get_config_value(config, ["selection", "metric"], "roc_auc")
    selection_mode = get_config_value(config, ["selection", "mode"], "max")

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_path).parent.mkdir(parents=True, exist_ok=True)

    training_results = []
    champion_result = None
    champion_model = None

    for candidate in candidates:
        candidate_name = candidate["name"]
        pipeline = build_model(X_train, config, candidate)

        with mlflow.start_run(run_name=candidate_name) as run:
            pipeline.fit(X_train, y_train)
            metrics = calculate_metrics(pipeline, X_test, y_test)

            params = {
                "candidate_name": candidate_name,
                "model_type": candidate["type"],
                **candidate.get("params", {}),
            }

            mlflow.log_params(params)
            mlflow.set_tags(
                {
                    "candidate_name": candidate_name,
                    "model_type": candidate["type"],
                    "candidate_role": "candidate",
                }
            )

            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, float(metric_value))

            mlflow.sklearn.log_model(
                sk_model=pipeline,
                artifact_path="model",
            )

            result = {
                "run_id": run.info.run_id,
                "model_uri": f"runs:/{run.info.run_id}/model",
                "candidate_name": candidate_name,
                "model_type": candidate["type"],
                "metrics": metrics,
                "params": params,
            }

            training_results.append(result)

            candidate_metric = metrics[selection_metric]
            champion_metric = (
                None
                if champion_result is None
                else champion_result["metrics"][selection_metric]
            )

            if is_better_metric(candidate_metric, champion_metric, selection_mode):
                champion_result = result
                champion_model = pipeline

            print(f"Candidate: {candidate_name}")
            print("Run ID:", run.info.run_id)
            print("Model URI:", result["model_uri"])
            print("Metrics:", metrics)

    joblib.dump(champion_model, model_path)

    output = {
        "selection": {
            "metric": selection_metric,
            "mode": selection_mode,
        },
        "run_id": champion_result["run_id"],
        "model_uri": champion_result["model_uri"],
        "candidate_name": champion_result["candidate_name"],
        "model_type": champion_result["model_type"],
        "metrics": champion_result["metrics"],
        "params": champion_result["params"],
        "all_candidates": training_results,
    }

    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=4)

    print("\nChampion:", champion_result["candidate_name"])
    print("Champion Run ID:", champion_result["run_id"])
    print("Champion Model URI:", champion_result["model_uri"])
    print(f"Champion {selection_metric}:", champion_result["metrics"][selection_metric])
    print(f"Saved champion local model to {model_path}")
    print(f"Saved training report to {metrics_path}")


if __name__ == "__main__":
    main()
