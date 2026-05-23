import os

import mlflow
import mlflow.sklearn


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "HospitalReadmissionModel")


class ModelLoader:
    def __init__(self):
        self.model = None
        self.model_uri = f"models:/{MODEL_NAME}/Production"

    def load_model(self):
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        self.model = mlflow.sklearn.load_model(self.model_uri)

        return self.model

    def predict_probability(self, dataframe) -> float:
        if self.model is None:
            self.load_model()

        probability = self.model.predict_proba(dataframe)[0][1]

        return float(probability)


model_loader = ModelLoader()