import os

import mlflow
import mlflow.sklearn

from training.train import (
    configure_mlflow_artifact_store,
    get_config_value,
    load_data,
    load_config,
)

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


MODEL_STAGE = os.getenv("MODEL_STAGE", "Production")


def main():
    config = load_config()

    csv_path = os.getenv(
        "CSV_PATH",
        get_config_value(config, ["data", "csv_path"], "data/diabetic_data.csv"),
    )

    mlflow_tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        get_config_value(config, ["mlflow", "tracking_uri"], "http://localhost:5000"),
    )

    model_name = os.getenv(
        "MLFLOW_MODEL_NAME",
        get_config_value(config, ["model", "name"], "HospitalReadmissionModel"),
    )

    configure_mlflow_artifact_store(config)
    mlflow.set_tracking_uri(mlflow_tracking_uri)

    df = load_data(csv_path)

    X = df.drop(columns=["readmitted_binary"])
    y = df["readmitted_binary"]

    _, X_test, _, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model_uri = f"models:/{model_name}/{MODEL_STAGE}"

    model = mlflow.sklearn.load_model(model_uri)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("Model URI:", model_uri)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Precision:", precision_score(y_test, y_pred, zero_division=0))
    print("Recall:", recall_score(y_test, y_pred, zero_division=0))
    print("F1:", f1_score(y_test, y_pred, zero_division=0))
    print("ROC-AUC:", roc_auc_score(y_test, y_proba))


if __name__ == "__main__":
    main()
