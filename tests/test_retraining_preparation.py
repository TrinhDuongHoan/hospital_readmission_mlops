import pandas as pd

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
