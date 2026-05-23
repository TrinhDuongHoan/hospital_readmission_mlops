from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class PatientRequest(BaseModel):
    race: str
    gender: str
    age: str

    admission_type_id: int
    discharge_disposition_id: int
    admission_source_id: int

    time_in_hospital: int
    num_lab_procedures: int
    num_procedures: int
    num_medications: int

    number_outpatient: int
    number_emergency: int
    number_inpatient: int

    diag_1: Optional[str] = None
    diag_2: Optional[str] = None
    diag_3: Optional[str] = None

    number_diagnoses: int

    max_glu_serum: Optional[str] = "None"
    A1Cresult: Optional[str] = "None"

    metformin: Optional[str] = "No"
    repaglinide: Optional[str] = "No"
    nateglinide: Optional[str] = "No"
    chlorpropamide: Optional[str] = "No"
    glimepiride: Optional[str] = "No"
    acetohexamide: Optional[str] = "No"
    glipizide: Optional[str] = "No"
    glyburide: Optional[str] = "No"
    tolbutamide: Optional[str] = "No"
    pioglitazone: Optional[str] = "No"
    rosiglitazone: Optional[str] = "No"
    acarbose: Optional[str] = "No"
    miglitol: Optional[str] = "No"
    troglitazone: Optional[str] = "No"
    tolazamide: Optional[str] = "No"
    examide: Optional[str] = "No"
    citoglipton: Optional[str] = "No"
    insulin: Optional[str] = "No"

    glyburide_metformin: Optional[str] = "No"
    glipizide_metformin: Optional[str] = "No"
    glimepiride_pioglitazone: Optional[str] = "No"
    metformin_rosiglitazone: Optional[str] = "No"
    metformin_pioglitazone: Optional[str] = "No"

    change: str
    diabetesMed: str


class PredictionResponse(BaseModel):
    prediction: int
    readmission_probability: float
    risk_level: str
    model_name: str
    model_version: Optional[str] = None
    model_run_id: Optional[str] = None


class PredictionLogResponse(BaseModel):
    id: int
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    user_id: Optional[int] = None
    doctor_username: Optional[str] = None
    doctor_full_name: Optional[str] = None
    request_json: Dict[str, Any]
    prediction: int
    readmission_probability: float
    risk_level: str
    model_name: str
    model_version: Optional[str] = None
    model_run_id: Optional[str] = None
    created_at: datetime


class DashboardStatsResponse(BaseModel):
    total_predictions: int
    avg_probability: float
    positive_predictions: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role: str

class PatientCreateRequest(BaseModel):
    race: str = "Caucasian"
    gender: str = "Female"
    age: str = "[50-60)"

    admission_type_id: int = 1
    discharge_disposition_id: int = 1
    admission_source_id: int = 7

    time_in_hospital: int = 4
    num_lab_procedures: int = 43
    num_procedures: int = 0
    num_medications: int = 12

    number_outpatient: int = 0
    number_emergency: int = 0
    number_inpatient: int = 1

    diag_1: Optional[str] = "250"
    diag_2: Optional[str] = "401"
    diag_3: Optional[str] = "414"

    number_diagnoses: int = 8

    max_glu_serum: Optional[str] = "None"
    A1Cresult: Optional[str] = "None"

    metformin: Optional[str] = "No"
    repaglinide: Optional[str] = "No"
    nateglinide: Optional[str] = "No"
    chlorpropamide: Optional[str] = "No"
    glimepiride: Optional[str] = "No"
    acetohexamide: Optional[str] = "No"
    glipizide: Optional[str] = "No"
    glyburide: Optional[str] = "No"
    tolbutamide: Optional[str] = "No"
    pioglitazone: Optional[str] = "No"
    rosiglitazone: Optional[str] = "No"
    acarbose: Optional[str] = "No"
    miglitol: Optional[str] = "No"
    troglitazone: Optional[str] = "No"
    tolazamide: Optional[str] = "No"
    examide: Optional[str] = "No"
    citoglipton: Optional[str] = "No"
    insulin: Optional[str] = "No"

    glyburide_metformin: Optional[str] = "No"
    glipizide_metformin: Optional[str] = "No"
    glimepiride_pioglitazone: Optional[str] = "No"
    metformin_rosiglitazone: Optional[str] = "No"
    metformin_pioglitazone: Optional[str] = "No"

    change: str = "Ch"
    diabetesMed: str = "Yes"

    actual_readmitted: Optional[int] = None


class PatientUpdateRequest(PatientCreateRequest):
    pass


class PatientResponse(PatientCreateRequest):
    id: int
    doctor_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    doctor_username: Optional[str] = None
    doctor_full_name: Optional[str] = None
