import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from training.train import (
    build_estimator,
    build_model,
    get_config_value,
    get_model_candidates,
    is_better_metric,
    load_data,
)


def test_get_config_value_returns_nested_value_or_default():
    config = {
        "model": {
            "random_state": 42,
        }
    }

    assert get_config_value(config, ["model", "random_state"]) == 42
    assert get_config_value(config, ["model", "missing"], "fallback") == "fallback"
    assert get_config_value(config, ["missing", "value"], 123) == 123


def test_load_data_cleans_dataset_and_builds_binary_target(tmp_path):
    csv_path = tmp_path / "diabetic_sample.csv"
    pd.DataFrame(
        [
            {
                "encounter_id": 1,
                "patient_nbr": 11,
                "race": "Caucasian",
                "gender": "Female",
                "age": "[50-60)",
                "weight": "?",
                "payer_code": "?",
                "medical_specialty": "?",
                "time_in_hospital": "3",
                "num_medications": "12",
                "diag_1": "?",
                "readmitted": "<30",
            },
            {
                "encounter_id": 2,
                "patient_nbr": 12,
                "race": None,
                "gender": "Male",
                "age": "[60-70)",
                "weight": "?",
                "payer_code": "?",
                "medical_specialty": "?",
                "time_in_hospital": "4",
                "num_medications": "15",
                "diag_1": "250",
                "readmitted": "NO",
            },
            {
                "encounter_id": 3,
                "patient_nbr": 13,
                "race": "Asian",
                "gender": "Male",
                "age": "[70-80)",
                "weight": "?",
                "payer_code": "?",
                "medical_specialty": "?",
                "time_in_hospital": "5",
                "num_medications": "18",
                "diag_1": "401",
                "readmitted": ">30",
            },
        ]
    ).to_csv(csv_path, index=False)

    data = load_data(str(csv_path))

    assert len(data) == 2
    assert "readmitted_binary" in data.columns
    assert data["readmitted_binary"].tolist() == [1, 0]
    assert "encounter_id" not in data.columns
    assert "patient_nbr" not in data.columns
    assert "readmitted" not in data.columns
    assert data["diag_1"].tolist() == ["Unknown", "401"]
    assert pd.api.types.is_numeric_dtype(data["time_in_hospital"])


def test_get_model_candidates_uses_configured_candidates_or_default():
    configured = {
        "model": {
            "candidates": [
                {
                    "name": "logreg",
                    "type": "logistic_regression",
                    "params": {"C": 0.5},
                }
            ]
        }
    }

    assert get_model_candidates(configured) == configured["model"]["candidates"]

    default_candidates = get_model_candidates({"model": {"n_estimators": 10}})

    assert default_candidates[0]["name"] == "random_forest"
    assert default_candidates[0]["params"]["n_estimators"] == 10


def test_build_estimator_supports_configured_model_types():
    config = {"model": {"random_state": 7}}

    random_forest = build_estimator(
        {
            "type": "random_forest",
            "params": {"n_estimators": 5},
        },
        config,
    )
    logistic_regression = build_estimator(
        {
            "type": "logistic_regression",
            "params": {"max_iter": 200},
        },
        config,
    )

    assert isinstance(random_forest, RandomForestClassifier)
    assert random_forest.random_state == 7
    assert isinstance(logistic_regression, LogisticRegression)
    assert logistic_regression.random_state == 7


def test_build_estimator_rejects_unknown_model_type():
    with pytest.raises(ValueError, match="Unsupported model candidate type"):
        build_estimator({"type": "unsupported", "params": {}}, {"model": {}})


def test_build_model_creates_sklearn_pipeline():
    data = pd.DataFrame(
        {
            "race": ["Asian", "Caucasian"],
            "time_in_hospital": [3, 5],
        }
    )

    pipeline = build_model(
        data,
        {"model": {"random_state": 42}},
        {
            "type": "random_forest",
            "params": {"n_estimators": 5},
        },
    )

    assert isinstance(pipeline, Pipeline)
    assert list(pipeline.named_steps) == ["preprocessor", "model"]


def test_is_better_metric_handles_modes_and_invalid_mode():
    assert is_better_metric(0.8, None, "max")
    assert is_better_metric(0.8, 0.7, "max")
    assert not is_better_metric(0.6, 0.7, "max")
    assert is_better_metric(0.2, 0.3, "min")
    assert not is_better_metric(0.4, 0.3, "min")

    with pytest.raises(ValueError, match="selection.mode"):
        is_better_metric(1.0, 0.5, "median")
