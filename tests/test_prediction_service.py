import pytest
from fastapi import HTTPException

from inference.app import main


class FakeModelLoader:
    def __init__(self, probability):
        self.probability = probability
        self.seen_dataframe = None

    def predict_probability(self, dataframe):
        self.seen_dataframe = dataframe
        return self.probability


def test_build_prediction_result_uses_model_probability_and_risk_level(monkeypatch):
    fake_loader = FakeModelLoader(probability=0.72)

    monkeypatch.setattr(main, "model_loader", fake_loader)
    monkeypatch.setattr(
        main,
        "convert_request_to_dataframe",
        lambda payload: {"dataframe_payload": payload},
    )

    result = main.build_prediction_result({"race": "Asian"})

    assert fake_loader.seen_dataframe == {"dataframe_payload": {"race": "Asian"}}
    assert result == {
        "prediction": 1,
        "readmission_probability": 0.72,
        "risk_level": "high",
        "model_name": "HospitalReadmissionModel",
    }


def test_build_prediction_result_marks_low_probability_as_negative(monkeypatch):
    monkeypatch.setattr(main, "model_loader", FakeModelLoader(probability=0.39))
    monkeypatch.setattr(main, "convert_request_to_dataframe", lambda payload: payload)

    result = main.build_prediction_result({"race": "Asian"})

    assert result["prediction"] == 0
    assert result["risk_level"] == "low"


def test_raise_prediction_service_error_returns_service_unavailable():
    with pytest.raises(HTTPException) as exc_info:
        main.raise_prediction_service_error(RuntimeError("model not found"))

    assert exc_info.value.status_code == 503
    assert "Cannot load prediction model" in exc_info.value.detail
