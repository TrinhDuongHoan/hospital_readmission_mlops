from inference.app.database import normalize_patient_data, row_to_patient_response


def test_normalize_patient_data_maps_api_names_to_database_names():
    normalized = normalize_patient_data(
        {
            "race": "Asian",
            "gender": "Male",
            "age": "[60-70)",
            "A1Cresult": ">8",
            "diabetesMed": "Yes",
            "change": "Ch",
        }
    )

    assert "A1Cresult" not in normalized
    assert "diabetesMed" not in normalized
    assert normalized["a1c_result"] == ">8"
    assert normalized["diabetes_med"] == "Yes"
    assert normalized["diag_1"] == "Unknown"
    assert normalized["glyburide_metformin"] == "No"
    assert normalized["actual_readmitted"] is None


def test_row_to_patient_response_maps_database_names_to_api_names():
    response = row_to_patient_response(
        {
            "id": 7,
            "race": "Caucasian",
            "a1c_result": "None",
            "diabetes_med": "No",
        }
    )

    assert response["A1Cresult"] == "None"
    assert response["diabetesMed"] == "No"
    assert "a1c_result" not in response
    assert "diabetes_med" not in response
