import os
import time
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from inference.app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    require_role,
)
from inference.app.airflow_service import get_pipeline_status, trigger_dag
from inference.app.database import (
    get_dashboard_stats,
    get_high_risk_patients,
    get_prediction_logs,
    get_prediction_logs_for_patient,
    init_db,
    create_patient,
    create_user,
    delete_patient,
    get_all_patients,
    get_patient_by_id,
    get_patients_for_doctor,
    save_prediction_log,
    update_patient,
)
from inference.app.feature_service import feature_service
from inference.app.model_loader import model_loader
from inference.app.preprocessing import convert_request_to_dataframe, get_risk_level
from inference.app.schemas import (
    DashboardStatsResponse,
    PatientRequest,
    PredictionLogResponse,
    PredictionResponse,
    LoginRequest,
    TokenResponse,
    UserResponse,
    PatientCreateRequest,
    PatientUpdateRequest,
    PatientResponse,
)


logger = logging.getLogger(__name__)


app = FastAPI(
    title="Hospital Readmission Prediction API",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_COUNT = Counter(
    "prediction_requests_total",
    "Total number of prediction requests",
    ["source"],
)

REQUEST_LATENCY = Histogram(
    "prediction_request_latency_seconds",
    "Prediction request latency in seconds",
    ["source"],
)

PREDICTION_ERROR_COUNT = Counter(
    "prediction_errors_total",
    "Total number of failed prediction requests",
    ["source"],
)

PREDICTION_RISK_COUNT = Counter(
    "prediction_risk_level_total",
    "Total number of predictions by risk level",
    ["source", "risk_level"],
)

PREDICTION_PROBABILITY = Histogram(
    "prediction_readmission_probability",
    "Distribution of predicted readmission probabilities",
    ["source"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)

MODEL_RELOAD_COUNT = Counter(
    "model_reload_total",
    "Total number of model reload attempts",
    ["status"],
)


def initialize_metric_labels() -> None:
    for source in ["direct", "patient"]:
        REQUEST_COUNT.labels(source=source).inc(0)
        REQUEST_LATENCY.labels(source=source)
        PREDICTION_ERROR_COUNT.labels(source=source).inc(0)
        PREDICTION_PROBABILITY.labels(source=source)

        for risk_level in ["low", "medium", "high"]:
            PREDICTION_RISK_COUNT.labels(
                source=source,
                risk_level=risk_level,
            ).inc(0)

    for status_label in ["success", "error"]:
        MODEL_RELOAD_COUNT.labels(status=status_label).inc(0)


def build_prediction_result(payload_dict: dict) -> dict:
    dataframe = convert_request_to_dataframe(payload_dict)

    probability = model_loader.predict_probability(dataframe)
    prediction = 1 if probability >= 0.5 else 0
    risk_level = get_risk_level(probability)
    model_metadata = model_loader.get_metadata()

    return {
        "prediction": prediction,
        "readmission_probability": probability,
        "risk_level": risk_level,
        "model_name": model_metadata["model_name"],
        "model_version": model_metadata["model_version"],
        "model_run_id": model_metadata["run_id"],
    }


def raise_prediction_service_error(exc: Exception) -> None:
    logger.exception("Prediction failed because the model service is unavailable.")
    raise HTTPException(
        status_code=503,
        detail=(
            "Cannot load prediction model. "
            "Please check MLflow tracking URI and registered model status."
        ),
    ) from exc


def record_prediction_metrics(result: dict, source: str, start_time: float) -> None:
    REQUEST_COUNT.labels(source=source).inc()
    REQUEST_LATENCY.labels(source=source).observe(time.time() - start_time)
    PREDICTION_RISK_COUNT.labels(
        source=source,
        risk_level=result["risk_level"],
    ).inc()
    PREDICTION_PROBABILITY.labels(source=source).observe(
        result["readmission_probability"]
    )


def seed_default_users() -> None:
    if os.getenv("SEED_DEFAULT_USERS", "true").lower() not in {"1", "true", "yes"}:
        return

    create_user(
        username="doctor01",
        password_hash=hash_password("doctor123"),
        full_name="Doctor User",
        role="doctor",
    )

    create_user(
        username="admin01",
        password_hash=hash_password("admin123"),
        full_name="System Admin",
        role="admin",
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = authenticate_user(
        username=payload.username,
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    access_token = create_access_token(
        data={
            "sub": user["username"],
            "role": user["role"],
            "user_id": user["id"],
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }


@app.get("/auth/me", response_model=UserResponse)
def auth_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
    }


@app.post("/patients", response_model=PatientResponse)
def create_patient_api(
    payload: PatientCreateRequest,
    current_user=Depends(require_role("doctor", "admin")),
):
    doctor_id = current_user["id"]

    patient = create_patient(
        doctor_id=doctor_id,
        patient_data=payload.model_dump(),
    )

    return patient


@app.get("/patients", response_model=list[PatientResponse])
def list_patients_api(
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_role("doctor", "admin")),
):
    if current_user["role"] == "admin":
        return get_all_patients(limit=limit)

    return get_patients_for_doctor(
        doctor_id=current_user["id"],
        limit=limit,
    )


@app.get("/patients/high-risk")
def high_risk_patients_api(
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_role("doctor", "admin")),
):
    doctor_id = None if current_user["role"] == "admin" else current_user["id"]

    return get_high_risk_patients(
        doctor_id=doctor_id,
        limit=limit,
    )


@app.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient_api(
    patient_id: int,
    current_user=Depends(require_role("doctor", "admin")),
):
    patient = get_patient_by_id(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    if current_user["role"] != "admin" and patient["doctor_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this patient.",
        )

    return patient


@app.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient_api(
    patient_id: int,
    payload: PatientUpdateRequest,
    current_user=Depends(require_role("doctor", "admin")),
):
    patient = update_patient(
        patient_id=patient_id,
        doctor_id=current_user["id"],
        patient_data=payload.model_dump(),
        is_admin=current_user["role"] == "admin",
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found or permission denied.",
        )

    return patient


@app.delete("/patients/{patient_id}")
def delete_patient_api(
    patient_id: int,
    current_user=Depends(require_role("doctor", "admin")),
):
    deleted = delete_patient(
        patient_id=patient_id,
        doctor_id=current_user["id"],
        is_admin=current_user["role"] == "admin",
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Patient not found or permission denied.",
        )

    return {
        "status": "deleted",
        "patient_id": patient_id,
    }


@app.post("/patients/{patient_id}/predict", response_model=PredictionResponse)
def predict_patient_api(
    patient_id: int,
    current_user=Depends(require_role("doctor", "admin")),
):
    start_time = time.time()

    patient = get_patient_by_id(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    if current_user["role"] != "admin" and patient["doctor_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this patient.",
        )

    payload_dict = {
        key: value
        for key, value in patient.items()
        if key not in {
            "id",
            "doctor_id",
            "created_at",
            "updated_at",
            "doctor_username",
            "doctor_full_name",
        }
    }

    try:
        result = build_prediction_result(payload_dict)
    except Exception as exc:
        PREDICTION_ERROR_COUNT.labels(source="patient").inc()
        raise_prediction_service_error(exc)

    log_key = f"prediction:{patient_id}:{int(time.time())}"

    feature_service.save_prediction_log(
        key=log_key,
        value={
            "patient_id": patient_id,
            "doctor_id": current_user["id"],
            "request": payload_dict,
            "response": result,
            "timestamp": int(time.time()),
        },
    )

    save_prediction_log(
        request_json=payload_dict,
        response_json=result,
        patient_id=patient_id,
        doctor_id=current_user["id"],
        model_version=result.get("model_version"),
        model_run_id=result.get("model_run_id"),
    )

    record_prediction_metrics(
        result=result,
        source="patient",
        start_time=start_time,
    )

    return result


@app.get("/patients/{patient_id}/predictions", response_model=list[PredictionLogResponse])
def patient_prediction_logs_api(
    patient_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    current_user=Depends(require_role("doctor", "admin")),
):
    patient = get_patient_by_id(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    if current_user["role"] != "admin" and patient["doctor_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this patient.",
        )

    return get_prediction_logs_for_patient(
        patient_id=patient_id,
        limit=limit,
    )


@app.get("/mlops/pipelines")
def mlops_pipelines(current_user=Depends(require_admin)):
    return {
        "pipelines": get_pipeline_status(),
    }


@app.post("/mlops/pipelines/{dag_id}/trigger")
def trigger_mlops_pipeline(
    dag_id: str,
    current_user=Depends(require_admin),
):
    allowed_dags = {
        "ingestion_dag",
        "etl_dag",
        "training_dag",
        "db_triggered_retraining_dag",
    }

    if dag_id not in allowed_dags:
        raise HTTPException(
            status_code=400,
            detail=f"DAG {dag_id} is not allowed.",
        )

    try:
        result = trigger_dag(dag_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Cannot trigger Airflow DAG {dag_id}: {str(exc)}",
        )

    return {
        "status": "triggered",
        "dag_id": dag_id,
        "result": result,
    }


@app.on_event("startup")
def startup_event():
    init_db()
    seed_default_users()
    initialize_metric_labels()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "hospital-readmission-api",
        "phase": "postgres-logging",
    }


@app.post("/reload-model")
def reload_model(current_user=Depends(require_admin)):
    try:
        model_loader.load_model()
    except Exception as exc:
        MODEL_RELOAD_COUNT.labels(status="error").inc()
        raise_prediction_service_error(exc)

    MODEL_RELOAD_COUNT.labels(status="success").inc()

    return {
        "status": "model reloaded",
        "model_uri": model_loader.model_uri,
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(
    payload: PatientRequest,
    current_user=Depends(require_role("doctor", "admin")),
):
    start_time = time.time()

    payload_dict = payload.model_dump()

    try:
        result = build_prediction_result(payload_dict)
    except Exception as exc:
        PREDICTION_ERROR_COUNT.labels(source="direct").inc()
        raise_prediction_service_error(exc)

    log_key = f"prediction:{int(time.time())}"

    feature_service.save_prediction_log(
        key=log_key,
        value={
            "doctor_id": current_user["id"],
            "request": payload_dict,
            "response": result,
            "timestamp": int(time.time()),
        },
    )

    save_prediction_log(
        request_json=payload_dict,
        response_json=result,
        doctor_id=current_user["id"],
        model_version=result.get("model_version"),
        model_run_id=result.get("model_run_id"),
    )

    record_prediction_metrics(
        result=result,
        source="direct",
        start_time=start_time,
    )

    return result


@app.get("/prediction-logs", response_model=list[PredictionLogResponse])
def prediction_logs(
    limit: int = Query(default=50, ge=1, le=500),
    current_user=Depends(require_admin),
):
    return get_prediction_logs(limit=limit)


@app.get("/dashboard-stats", response_model=DashboardStatsResponse)
def dashboard_stats(current_user=Depends(require_admin)):
    return get_dashboard_stats()


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/model-info")
def model_info():
    return model_loader.get_metadata()
