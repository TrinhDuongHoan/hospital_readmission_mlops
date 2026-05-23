import pandas as pd

from training.prepare_training_from_bronze import load_bronze_dataset
from training.prepare_training_from_db import normalize_prediction_logs


def test_normalize_prediction_logs_maps_request_json_and_label():
    logs = pd.DataFrame(
        [
            {
                "request_json": {
                    "race": "Asian",
                    "a1c_result": ">8",
                    "diabetes_med": "Yes",
                    "glyburide_metformin": "Steady",
                },
                "actual_readmitted": 1,
            },
            {
                "request_json": '{"race":"Caucasian","A1Cresult":"None","diabetesMed":"No"}',
                "actual_readmitted": 0,
            },
        ]
    )

    normalized = normalize_prediction_logs(logs)

    assert normalized.loc[0, "A1Cresult"] == ">8"
    assert normalized.loc[0, "diabetesMed"] == "Yes"
    assert normalized.loc[0, "glyburide-metformin"] == "Steady"
    assert normalized.loc[0, "readmitted"] == "<30"
    assert normalized.loc[1, "readmitted"] == "NO"


def test_load_bronze_dataset_maps_binary_target_and_drops_streaming_columns(
    tmp_path,
    monkeypatch,
):
    bronze_path = tmp_path / "bronze"
    bronze_path.mkdir()

    (bronze_path / "part-00000.parquet").touch()

    parquet_data = pd.DataFrame(
        [
            {
                "kafka_key": "1",
                "kafka_timestamp": "2026-01-01T00:00:00",
                "event_timestamp": "2026-01-01T00:00:01",
                "race": "Asian",
                "readmitted_binary": 1,
            },
            {
                "kafka_key": "2",
                "kafka_timestamp": "2026-01-01T00:00:02",
                "event_timestamp": "2026-01-01T00:00:03",
                "race": "Caucasian",
                "readmitted_binary": 0,
            },
        ]
    )

    monkeypatch.setattr(
        "training.prepare_training_from_bronze.BRONZE_PATH",
        str(bronze_path),
    )
    monkeypatch.setattr(
        "training.prepare_training_from_bronze.pd.read_parquet",
        lambda parquet_file: parquet_data,
    )

    bronze = load_bronze_dataset()

    assert bronze["readmitted"].tolist() == ["<30", "NO"]
    assert "readmitted_binary" not in bronze.columns
    assert "kafka_key" not in bronze.columns
    assert "event_timestamp" not in bronze.columns
