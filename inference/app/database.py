import json
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mlops:mlops123@postgres:5432/mlops",
)

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def init_db() -> None:
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        role VARCHAR(50) NOT NULL DEFAULT 'doctor',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    add_user_is_active_column = """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
    """

    create_patients_table = """
    CREATE TABLE IF NOT EXISTS patients (
        id SERIAL PRIMARY KEY,
        doctor_id INT NULL,

        race VARCHAR(100),
        gender VARCHAR(50),
        age VARCHAR(50),

        admission_type_id INT,
        discharge_disposition_id INT,
        admission_source_id INT,

        time_in_hospital INT,
        num_lab_procedures INT,
        num_procedures INT,
        num_medications INT,

        number_outpatient INT,
        number_emergency INT,
        number_inpatient INT,

        diag_1 VARCHAR(100),
        diag_2 VARCHAR(100),
        diag_3 VARCHAR(100),

        number_diagnoses INT,

        max_glu_serum VARCHAR(100),
        a1c_result VARCHAR(100),

        metformin VARCHAR(50),
        repaglinide VARCHAR(50),
        nateglinide VARCHAR(50),
        chlorpropamide VARCHAR(50),
        glimepiride VARCHAR(50),
        acetohexamide VARCHAR(50),
        glipizide VARCHAR(50),
        glyburide VARCHAR(50),
        tolbutamide VARCHAR(50),
        pioglitazone VARCHAR(50),
        rosiglitazone VARCHAR(50),
        acarbose VARCHAR(50),
        miglitol VARCHAR(50),
        troglitazone VARCHAR(50),
        tolazamide VARCHAR(50),
        examide VARCHAR(50),
        citoglipton VARCHAR(50),
        insulin VARCHAR(50),

        glyburide_metformin VARCHAR(50),
        glipizide_metformin VARCHAR(50),
        glimepiride_pioglitazone VARCHAR(50),
        metformin_rosiglitazone VARCHAR(50),
        metformin_pioglitazone VARCHAR(50),

        change VARCHAR(50),
        diabetes_med VARCHAR(50),

        actual_readmitted INT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT fk_patient_doctor
            FOREIGN KEY(doctor_id)
            REFERENCES users(id)
            ON DELETE SET NULL
    );
    """

    create_prediction_logs_table = """
    CREATE TABLE IF NOT EXISTS prediction_logs (
        id SERIAL PRIMARY KEY,

        patient_id INT NULL,
        doctor_id INT NULL,

        request_json JSONB NOT NULL,

        prediction INT NOT NULL,
        readmission_probability FLOAT NOT NULL,
        risk_level VARCHAR(50) NOT NULL,

        model_name VARCHAR(255) NOT NULL,
        model_version VARCHAR(100),
        model_run_id VARCHAR(255),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT fk_prediction_patient
            FOREIGN KEY(patient_id)
            REFERENCES patients(id)
            ON DELETE SET NULL,

        CONSTRAINT fk_prediction_doctor
            FOREIGN KEY(doctor_id)
            REFERENCES users(id)
            ON DELETE SET NULL
    );
    """

    add_prediction_model_run_id_column = """
    ALTER TABLE prediction_logs
    ADD COLUMN IF NOT EXISTS model_run_id VARCHAR(255);
    """

    create_retraining_state_table = """
    CREATE TABLE IF NOT EXISTS retraining_state (
        id SERIAL PRIMARY KEY,
        last_trained_prediction_count INT DEFAULT 0,
        last_trained_patient_count INT DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_retraining_runs_table = """
    CREATE TABLE IF NOT EXISTS retraining_runs (
        id SERIAL PRIMARY KEY,
        trigger_type VARCHAR(100),
        new_records INT DEFAULT 0,
        status VARCHAR(50),
        metric_name VARCHAR(100),
        metric_value FLOAT,
        started_at TIMESTAMP,
        ended_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    seed_retraining_state = """
    INSERT INTO retraining_state (
        id,
        last_trained_prediction_count,
        last_trained_patient_count
    )
    VALUES (1, 0, 0)
    ON CONFLICT (id) DO NOTHING;
    """

    with engine.begin() as connection:
        connection.execute(text(create_users_table))
        connection.execute(text(add_user_is_active_column))
        connection.execute(text(create_patients_table))
        connection.execute(text(create_prediction_logs_table))
        connection.execute(text(add_prediction_model_run_id_column))
        connection.execute(text(create_retraining_state_table))
        connection.execute(text(create_retraining_runs_table))
        connection.execute(text(seed_retraining_state))


def save_prediction_log(
    request_json: Dict[str, Any],
    response_json: Dict[str, Any],
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    model_version: Optional[str] = None,
    model_run_id: Optional[str] = None,
) -> None:
    query = """
    INSERT INTO prediction_logs (
        patient_id,
        doctor_id,
        request_json,
        prediction,
        readmission_probability,
        risk_level,
        model_name,
        model_version,
        model_run_id
    )
    VALUES (
        :patient_id,
        :doctor_id,
        CAST(:request_json AS JSONB),
        :prediction,
        :readmission_probability,
        :risk_level,
        :model_name,
        :model_version,
        :model_run_id
    );
    """

    with engine.begin() as connection:
        connection.execute(
            text(query),
            {
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "request_json": json.dumps(request_json),
                "prediction": response_json["prediction"],
                "readmission_probability": response_json["readmission_probability"],
                "risk_level": response_json["risk_level"],
                "model_name": response_json["model_name"],
                "model_version": model_version,
                "model_run_id": model_run_id,
            },
        )


def get_prediction_logs(limit: int = 50) -> List[Dict[str, Any]]:
    query = """
    SELECT
        pl.id,
        pl.patient_id,
        pl.doctor_id,
        u.username AS doctor_username,
        u.full_name AS doctor_full_name,
        pl.request_json,
        pl.prediction,
        pl.readmission_probability,
        pl.risk_level,
        pl.model_name,
        pl.model_version,
        pl.model_run_id,
        pl.created_at
    FROM prediction_logs pl
    LEFT JOIN users u ON u.id = pl.doctor_id
    ORDER BY pl.created_at DESC
    LIMIT :limit;
    """

    with engine.begin() as connection:
        rows = connection.execute(
            text(query),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]


def get_prediction_logs_for_patient(
    patient_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    query = """
    SELECT
        pl.id,
        pl.patient_id,
        pl.doctor_id,
        u.username AS doctor_username,
        u.full_name AS doctor_full_name,
        pl.request_json,
        pl.prediction,
        pl.readmission_probability,
        pl.risk_level,
        pl.model_name,
        pl.model_version,
        pl.model_run_id,
        pl.created_at
    FROM prediction_logs pl
    LEFT JOIN users u ON u.id = pl.doctor_id
    WHERE pl.patient_id = :patient_id
    ORDER BY pl.created_at DESC
    LIMIT :limit;
    """

    with engine.begin() as connection:
        rows = connection.execute(
            text(query),
            {
                "patient_id": patient_id,
                "limit": limit,
            },
        ).mappings().all()

    return [dict(row) for row in rows]


def get_high_risk_patients(
    doctor_id: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    doctor_filter = ""
    params: Dict[str, Any] = {
        "limit": limit,
    }

    if doctor_id is not None:
        doctor_filter = "WHERE p.doctor_id = :doctor_id"
        params["doctor_id"] = doctor_id

    query = f"""
    WITH latest_predictions AS (
        SELECT DISTINCT ON (pl.patient_id)
            pl.id AS prediction_log_id,
            pl.patient_id,
            pl.doctor_id,
            pl.prediction,
            pl.readmission_probability,
            pl.risk_level,
            pl.model_name,
            pl.model_version,
            pl.model_run_id,
            pl.created_at AS predicted_at
        FROM prediction_logs pl
        WHERE pl.patient_id IS NOT NULL
        ORDER BY pl.patient_id, pl.created_at DESC
    )
    SELECT
        p.id,
        p.doctor_id,
        u.username AS doctor_username,
        u.full_name AS doctor_full_name,
        p.race,
        p.gender,
        p.age,
        p.admission_type_id,
        p.discharge_disposition_id,
        p.admission_source_id,
        p.time_in_hospital,
        p.num_lab_procedures,
        p.num_procedures,
        p.num_medications,
        p.number_outpatient,
        p.number_emergency,
        p.number_inpatient,
        p.diag_1,
        p.diag_2,
        p.diag_3,
        p.number_diagnoses,
        p.max_glu_serum,
        p.a1c_result,
        p.change,
        p.diabetes_med,
        p.created_at,
        p.updated_at,
        lp.prediction_log_id,
        lp.prediction,
        lp.readmission_probability,
        lp.risk_level,
        lp.model_name,
        lp.model_version,
        lp.model_run_id,
        lp.predicted_at
    FROM latest_predictions lp
    JOIN patients p ON p.id = lp.patient_id
    LEFT JOIN users u ON u.id = p.doctor_id
    {doctor_filter}
    ORDER BY lp.readmission_probability DESC, lp.predicted_at DESC
    LIMIT :limit;
    """

    with engine.begin() as connection:
        rows = connection.execute(
            text(query),
            params,
        ).mappings().all()

    return [row_to_patient_response(dict(row)) for row in rows]


def get_dashboard_stats() -> Dict[str, Any]:
    query = """
    SELECT
        COUNT(*) AS total_predictions,
        AVG(readmission_probability) AS avg_probability,
        SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS positive_predictions,
        SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk_count,
        SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END) AS medium_risk_count,
        SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END) AS low_risk_count
    FROM prediction_logs;
    """

    patients_query = """
    SELECT COUNT(*) AS total_patients
    FROM patients;
    """

    doctors_query = """
    SELECT COUNT(*) AS total_doctors
    FROM users
    WHERE role = 'doctor';
    """

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()
        patients_row = connection.execute(text(patients_query)).mappings().first()
        doctors_row = connection.execute(text(doctors_query)).mappings().first()

    data = dict(row) if row else {}

    return {
        "total_predictions": data.get("total_predictions") or 0,
        "avg_probability": float(data.get("avg_probability") or 0),
        "positive_predictions": data.get("positive_predictions") or 0,
        "high_risk_count": data.get("high_risk_count") or 0,
        "medium_risk_count": data.get("medium_risk_count") or 0,
        "low_risk_count": data.get("low_risk_count") or 0,
        "total_patients": patients_row["total_patients"] if patients_row else 0,
        "total_doctors": doctors_row["total_doctors"] if doctors_row else 0,
    }


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT
        id,
        username,
        password_hash,
        full_name,
        role,
        is_active,
        created_at
    FROM users
    WHERE username = :username;
    """

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            {"username": username},
        ).mappings().first()

    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    query = """
    SELECT
        id,
        username,
        full_name,
        role,
        is_active,
        created_at
    FROM users
    WHERE id = :user_id;
    """

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            {"user_id": user_id},
        ).mappings().first()

    return dict(row) if row else None


def list_users(limit: int = 100) -> List[Dict[str, Any]]:
    query = """
    SELECT
        id,
        username,
        full_name,
        role,
        is_active,
        created_at
    FROM users
    ORDER BY created_at DESC, id DESC
    LIMIT :limit;
    """

    with engine.begin() as connection:
        rows = connection.execute(
            text(query),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]


def create_user(
    username: str,
    password_hash: str,
    full_name: Optional[str],
    role: str,
) -> Dict[str, Any]:
    query = """
    INSERT INTO users (
        username,
        password_hash,
        full_name,
        role,
        is_active
    )
    VALUES (
        :username,
        :password_hash,
        :full_name,
        :role,
        TRUE
    )
    ON CONFLICT (username)
    DO NOTHING
    RETURNING
        id,
        username,
        full_name,
        role,
        is_active,
        created_at;
    """

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            {
                "username": username,
                "password_hash": password_hash,
                "full_name": full_name,
                "role": role,
            },
        ).mappings().first()

    if row is None:
        return get_user_by_username(username)

    return dict(row)


def update_user(
    user_id: int,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    existing_user = get_user_by_id(user_id)

    if existing_user is None:
        return None

    updates = []
    params: Dict[str, Any] = {"user_id": user_id}

    if full_name is not None:
        updates.append("full_name = :full_name")
        params["full_name"] = full_name

    if role is not None:
        updates.append("role = :role")
        params["role"] = role

    if password_hash is not None:
        updates.append("password_hash = :password_hash")
        params["password_hash"] = password_hash

    if not updates:
        return existing_user

    query = f"""
    UPDATE users
    SET {", ".join(updates)}
    WHERE id = :user_id
    RETURNING
        id,
        username,
        full_name,
        role,
        is_active,
        created_at;
    """

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            params,
        ).mappings().first()

    return dict(row) if row else None


def set_user_active(user_id: int, is_active: bool) -> Optional[Dict[str, Any]]:
    existing_user = get_user_by_id(user_id)

    if existing_user is None:
        return None

    query = """
    UPDATE users
    SET is_active = :is_active
    WHERE id = :user_id
    RETURNING
        id,
        username,
        full_name,
        role,
        is_active,
        created_at;
    """

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            {
                "user_id": user_id,
                "is_active": is_active,
            },
        ).mappings().first()

    return dict(row) if row else None


def create_patient(
    doctor_id: int,
    patient_data: Dict[str, Any],
) -> Dict[str, Any]:
    query = """
    INSERT INTO patients (
        doctor_id,

        race,
        gender,
        age,

        admission_type_id,
        discharge_disposition_id,
        admission_source_id,

        time_in_hospital,
        num_lab_procedures,
        num_procedures,
        num_medications,

        number_outpatient,
        number_emergency,
        number_inpatient,

        diag_1,
        diag_2,
        diag_3,

        number_diagnoses,

        max_glu_serum,
        a1c_result,

        metformin,
        repaglinide,
        nateglinide,
        chlorpropamide,
        glimepiride,
        acetohexamide,
        glipizide,
        glyburide,
        tolbutamide,
        pioglitazone,
        rosiglitazone,
        acarbose,
        miglitol,
        troglitazone,
        tolazamide,
        examide,
        citoglipton,
        insulin,

        glyburide_metformin,
        glipizide_metformin,
        glimepiride_pioglitazone,
        metformin_rosiglitazone,
        metformin_pioglitazone,

        change,
        diabetes_med,
        actual_readmitted
    )
    VALUES (
        :doctor_id,

        :race,
        :gender,
        :age,

        :admission_type_id,
        :discharge_disposition_id,
        :admission_source_id,

        :time_in_hospital,
        :num_lab_procedures,
        :num_procedures,
        :num_medications,

        :number_outpatient,
        :number_emergency,
        :number_inpatient,

        :diag_1,
        :diag_2,
        :diag_3,

        :number_diagnoses,

        :max_glu_serum,
        :a1c_result,

        :metformin,
        :repaglinide,
        :nateglinide,
        :chlorpropamide,
        :glimepiride,
        :acetohexamide,
        :glipizide,
        :glyburide,
        :tolbutamide,
        :pioglitazone,
        :rosiglitazone,
        :acarbose,
        :miglitol,
        :troglitazone,
        :tolazamide,
        :examide,
        :citoglipton,
        :insulin,

        :glyburide_metformin,
        :glipizide_metformin,
        :glimepiride_pioglitazone,
        :metformin_rosiglitazone,
        :metformin_pioglitazone,

        :change,
        :diabetes_med,
        :actual_readmitted
    )
    RETURNING *;
    """

    params = normalize_patient_data(patient_data)
    params["doctor_id"] = doctor_id

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            params,
        ).mappings().first()

    return dict(row)


def normalize_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(patient_data)

    if "A1Cresult" in data:
        data["a1c_result"] = data.pop("A1Cresult")

    if "diabetesMed" in data:
        data["diabetes_med"] = data.pop("diabetesMed")

    defaults = {
        "diag_1": "Unknown",
        "diag_2": "Unknown",
        "diag_3": "Unknown",
        "max_glu_serum": "None",
        "a1c_result": "None",

        "metformin": "No",
        "repaglinide": "No",
        "nateglinide": "No",
        "chlorpropamide": "No",
        "glimepiride": "No",
        "acetohexamide": "No",
        "glipizide": "No",
        "glyburide": "No",
        "tolbutamide": "No",
        "pioglitazone": "No",
        "rosiglitazone": "No",
        "acarbose": "No",
        "miglitol": "No",
        "troglitazone": "No",
        "tolazamide": "No",
        "examide": "No",
        "citoglipton": "No",
        "insulin": "No",

        "glyburide_metformin": "No",
        "glipizide_metformin": "No",
        "glimepiride_pioglitazone": "No",
        "metformin_rosiglitazone": "No",
        "metformin_pioglitazone": "No",

        "actual_readmitted": None,
    }

    for key, value in defaults.items():
        if key not in data:
            data[key] = value

    return data


def row_to_patient_response(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)

    data["A1Cresult"] = data.pop("a1c_result")
    data["diabetesMed"] = data.pop("diabetes_med")

    return data


def get_patient_by_id(patient_id: int) -> Optional[Dict[str, Any]]:
    query = """
    SELECT *
    FROM patients
    WHERE id = :patient_id;
    """

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            {"patient_id": patient_id},
        ).mappings().first()

    if row is None:
        return None

    return row_to_patient_response(dict(row))


def get_patients_for_doctor(
    doctor_id: int,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query = """
    SELECT *
    FROM patients
    WHERE doctor_id = :doctor_id
    ORDER BY created_at DESC
    LIMIT :limit;
    """

    with engine.begin() as connection:
        rows = connection.execute(
            text(query),
            {
                "doctor_id": doctor_id,
                "limit": limit,
            },
        ).mappings().all()

    return [row_to_patient_response(dict(row)) for row in rows]


def get_all_patients(limit: int = 200) -> List[Dict[str, Any]]:
    query = """
    SELECT
        p.*,
        u.username AS doctor_username,
        u.full_name AS doctor_full_name
    FROM patients p
    LEFT JOIN users u ON u.id = p.doctor_id
    ORDER BY p.created_at DESC
    LIMIT :limit;
    """

    with engine.begin() as connection:
        rows = connection.execute(
            text(query),
            {"limit": limit},
        ).mappings().all()

    return [row_to_patient_response(dict(row)) for row in rows]


def update_patient(
    patient_id: int,
    doctor_id: int,
    patient_data: Dict[str, Any],
    is_admin: bool = False,
) -> Optional[Dict[str, Any]]:
    existing_patient = get_patient_by_id(patient_id)

    if existing_patient is None:
        return None

    if not is_admin and existing_patient["doctor_id"] != doctor_id:
        return None

    query = """
    UPDATE patients
    SET
        race = :race,
        gender = :gender,
        age = :age,

        admission_type_id = :admission_type_id,
        discharge_disposition_id = :discharge_disposition_id,
        admission_source_id = :admission_source_id,

        time_in_hospital = :time_in_hospital,
        num_lab_procedures = :num_lab_procedures,
        num_procedures = :num_procedures,
        num_medications = :num_medications,

        number_outpatient = :number_outpatient,
        number_emergency = :number_emergency,
        number_inpatient = :number_inpatient,

        diag_1 = :diag_1,
        diag_2 = :diag_2,
        diag_3 = :diag_3,

        number_diagnoses = :number_diagnoses,

        max_glu_serum = :max_glu_serum,
        a1c_result = :a1c_result,

        metformin = :metformin,
        repaglinide = :repaglinide,
        nateglinide = :nateglinide,
        chlorpropamide = :chlorpropamide,
        glimepiride = :glimepiride,
        acetohexamide = :acetohexamide,
        glipizide = :glipizide,
        glyburide = :glyburide,
        tolbutamide = :tolbutamide,
        pioglitazone = :pioglitazone,
        rosiglitazone = :rosiglitazone,
        acarbose = :acarbose,
        miglitol = :miglitol,
        troglitazone = :troglitazone,
        tolazamide = :tolazamide,
        examide = :examide,
        citoglipton = :citoglipton,
        insulin = :insulin,

        glyburide_metformin = :glyburide_metformin,
        glipizide_metformin = :glipizide_metformin,
        glimepiride_pioglitazone = :glimepiride_pioglitazone,
        metformin_rosiglitazone = :metformin_rosiglitazone,
        metformin_pioglitazone = :metformin_pioglitazone,

        change = :change,
        diabetes_med = :diabetes_med,
        actual_readmitted = :actual_readmitted,

        updated_at = CURRENT_TIMESTAMP
    WHERE id = :patient_id
    RETURNING *;
    """

    params = normalize_patient_data(patient_data)
    params["patient_id"] = patient_id

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            params,
        ).mappings().first()

    if row is None:
        return None

    return row_to_patient_response(dict(row))


def delete_patient(
    patient_id: int,
    doctor_id: int,
    is_admin: bool = False,
) -> bool:
    existing_patient = get_patient_by_id(patient_id)

    if existing_patient is None:
        return False

    if not is_admin and existing_patient["doctor_id"] != doctor_id:
        return False

    query = """
    DELETE FROM patients
    WHERE id = :patient_id;
    """

    with engine.begin() as connection:
        connection.execute(
            text(query),
            {"patient_id": patient_id},
        )

    return True
