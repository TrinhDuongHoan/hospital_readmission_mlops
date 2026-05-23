import os
from datetime import datetime, timezone

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "HospitalReadmissionModel")


class ModelLoader:
    def __init__(self):
        self.model = None
        self.model_uri = f"models:/{MODEL_NAME}/Production"
        self.model_name = MODEL_NAME
        self.model_version = None
        self.run_id = None
        self.loaded_at = None
        self.metadata_error = None

    def resolve_production_model_metadata(self):
        client = MlflowClient()
        versions = client.get_latest_versions(
            name=MODEL_NAME,
            stages=["Production"],
        )

        if not versions:
            self.model_version = None
            self.run_id = None
            self.metadata_error = None
            return

        latest_version = sorted(
            versions,
            key=lambda version: int(version.version),
            reverse=True,
        )[0]

        self.model_version = latest_version.version
        self.run_id = latest_version.run_id
        self.metadata_error = None

    def refresh_metadata(self):
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        try:
            self.resolve_production_model_metadata()
        except Exception as exc:
            self.metadata_error = str(exc)

    def load_model(self):
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        self.model = mlflow.sklearn.load_model(self.model_uri)
        self.resolve_production_model_metadata()
        self.loaded_at = datetime.now(timezone.utc).isoformat()

        return self.model

    def predict_probability(self, dataframe) -> float:
        if self.model is None:
            self.load_model()

        probability = self.model.predict_proba(dataframe)[0][1]

        return float(probability)

    def get_metadata(self) -> dict:
        if self.model_version is None and self.run_id is None:
            self.refresh_metadata()

        return {
            "model_name": self.model_name,
            "model_uri": self.model_uri,
            "model_version": self.model_version,
            "run_id": self.run_id,
            "loaded_at": self.loaded_at,
            "metadata_error": self.metadata_error,
        }


model_loader = ModelLoader()
