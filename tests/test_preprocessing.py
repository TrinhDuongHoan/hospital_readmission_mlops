from inference.app.preprocessing import (
    TRAINING_COLUMNS,
    convert_request_to_dataframe,
    get_risk_level,
)


def test_convert_request_to_dataframe_orders_training_columns_and_renames_fields():
    payload = {
        "race": "Caucasian",
        "gender": "Female",
        "age": "[50-60)",
        "admission_type_id": 1,
        "discharge_disposition_id": 1,
        "admission_source_id": 7,
        "time_in_hospital": 4,
        "num_lab_procedures": 43,
        "num_procedures": 0,
        "num_medications": 12,
        "number_outpatient": 0,
        "number_emergency": 0,
        "number_inpatient": 1,
        "number_diagnoses": 8,
        "glyburide_metformin": "Steady",
        "glipizide_metformin": "No",
        "glimepiride_pioglitazone": "No",
        "metformin_rosiglitazone": "No",
        "metformin_pioglitazone": "No",
        "change": "Ch",
        "diabetesMed": "Yes",
    }

    dataframe = convert_request_to_dataframe(payload)

    assert dataframe.shape == (1, len(TRAINING_COLUMNS))
    assert dataframe.columns.tolist() == TRAINING_COLUMNS
    assert dataframe.loc[0, "glyburide-metformin"] == "Steady"
    assert dataframe.loc[0, "diag_1"] == "Unknown"
    assert dataframe.loc[0, "max_glu_serum"] == "None"
    assert dataframe.loc[0, "metformin"] == "No"


def test_get_risk_level_uses_expected_thresholds():
    assert get_risk_level(0.39) == "low"
    assert get_risk_level(0.40) == "medium"
    assert get_risk_level(0.69) == "medium"
    assert get_risk_level(0.70) == "high"
