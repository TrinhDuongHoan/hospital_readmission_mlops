import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mlops:mlops123@postgres:5432/mlops",
)

MIN_NEW_LABELS = int(
    os.getenv(
        "RETRAIN_MIN_NEW_LABELS",
        os.getenv("RETRAIN_MIN_NEW_PREDICTIONS", "50"),
    )
)


default_args = {
    "owner": "hoan",
    "depends_on_past": False,
    "retries": 1,
}


def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def get_current_labeled_patient_count() -> int:
    query = """
    SELECT COUNT(*) AS total
    FROM patients
    WHERE actual_readmitted IS NOT NULL;
    """

    engine = get_engine()

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()

    return int(row["total"] or 0)


def get_last_trained_labeled_patient_count() -> int:
    query = """
    SELECT last_trained_patient_count
    FROM retraining_state
    WHERE id = 1;
    """

    engine = get_engine()

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()

    if row is None:
        return 0

    return int(row["last_trained_patient_count"] or 0)


def insert_retraining_run(
    trigger_type: str,
    new_records: int,
    status: str,
) -> None:
    query = """
    INSERT INTO retraining_runs (
        trigger_type,
        new_records,
        status,
        started_at,
        created_at
    )
    VALUES (
        :trigger_type,
        :new_records,
        :status,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    );
    """

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(query),
            {
                "trigger_type": trigger_type,
                "new_records": new_records,
                "status": status,
            },
        )


def decide_retraining_branch() -> str:
    current_count = get_current_labeled_patient_count()
    last_trained_count = get_last_trained_labeled_patient_count()
    new_records = current_count - last_trained_count

    print(f"Current labeled patient count: {current_count}")
    print(f"Last trained labeled patient count: {last_trained_count}")
    print(f"New labeled records: {new_records}")
    print(f"Minimum new labels required: {MIN_NEW_LABELS}")

    if new_records >= MIN_NEW_LABELS:
        insert_retraining_run(
            trigger_type="database_triggered",
            new_records=new_records,
            status="started",
        )
        return "prepare_training_dataset"

    insert_retraining_run(
        trigger_type="database_triggered",
        new_records=new_records,
        status="skipped",
    )
    return "skip_retraining"


def update_retraining_state_success() -> None:
    current_count = get_current_labeled_patient_count()

    update_state_query = """
    UPDATE retraining_state
    SET
        last_trained_patient_count = :current_count,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = 1;
    """

    update_run_query = """
    UPDATE retraining_runs
    SET
        status = 'success',
        ended_at = CURRENT_TIMESTAMP
    WHERE id = (
        SELECT id
        FROM retraining_runs
        WHERE trigger_type = 'database_triggered'
        ORDER BY created_at DESC
        LIMIT 1
    );
    """

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            text(update_state_query),
            {
                "current_count": current_count,
            },
        )

        connection.execute(text(update_run_query))

    print(f"Updated retraining_state.last_trained_patient_count = {current_count}")


with DAG(
    dag_id="db_triggered_retraining_dag",
    description="Retrain model when PostgreSQL has enough newly labeled patient records",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="*/15 * * * *",
    catchup=False,
    tags=["phase9", "database", "retraining", "mlops", "labels"],
) as dag:

    check_new_prediction_logs = BranchPythonOperator(
        task_id="check_new_prediction_logs",
        python_callable=decide_retraining_branch,
    )

    skip_retraining = EmptyOperator(
        task_id="skip_retraining",
    )

    prepare_training_dataset = BashOperator(
        task_id="prepare_training_dataset",
        bash_command=(
            "cd /opt/project && "
            "DATABASE_URL=postgresql://mlops:mlops123@postgres:5432/mlops "
            "python -m training.prepare_training_from_db"
        ),
    )

    train_new_model = BashOperator(
        task_id="train_new_model",
        bash_command=(
            "cd /opt/project && "
            "MLFLOW_TRACKING_URI=http://mlflow:5000 "
            "MLFLOW_S3_ENDPOINT_URL=http://minio:9000 "
            "AWS_ACCESS_KEY_ID=minio "
            "AWS_SECRET_ACCESS_KEY=minio123 "
            "AWS_DEFAULT_REGION=us-east-1 "
            "CSV_PATH=/opt/project/data/processed/db_training_data.csv "
            "MODEL_LOCAL_PATH=/opt/project/models/model.pkl "
            "METRICS_PATH=/opt/project/reports/metrics.json "
            "python -m training.train"
        ),
    )

    register_best_model = BashOperator(
        task_id="register_best_model",
        bash_command=(
            "cd /opt/project && "
            "MLFLOW_TRACKING_URI=http://mlflow:5000 "
            "MLFLOW_S3_ENDPOINT_URL=http://minio:9000 "
            "AWS_ACCESS_KEY_ID=minio "
            "AWS_SECRET_ACCESS_KEY=minio123 "
            "AWS_DEFAULT_REGION=us-east-1 "
            "METRICS_PATH=/opt/project/reports/metrics.json "
            "REGISTER_METRIC_NAME=recall "
            "REGISTER_METRIC_MODE=max "
            "python -m training.register_model"
        ),
    )

    reload_fastapi_model = BashOperator(
        task_id="reload_fastapi_model",
        bash_command=(
            "TOKEN=$(curl -s -X POST http://fastapi:8000/auth/login "
            "-H 'Content-Type: application/json' "
            "-d \"{\\\"username\\\":\\\"${FASTAPI_RELOAD_USERNAME:-admin01}\\\","
            "\\\"password\\\":\\\"${FASTAPI_RELOAD_PASSWORD:-admin123}\\\"}\" "
            "| python -c 'import json,sys; print(json.load(sys.stdin)[\"access_token\"])') && "
            "curl -X POST http://fastapi:8000/reload-model "
            "-H \"Authorization: Bearer ${TOKEN}\""
        ),
    )

    update_retraining_state = PythonOperator(
        task_id="update_retraining_state",
        python_callable=update_retraining_state_success,
    )

    end_retraining = EmptyOperator(
        task_id="end_retraining",
    )

    check_new_prediction_logs >> skip_retraining

    (
        check_new_prediction_logs
        >> prepare_training_dataset
        >> train_new_model
        >> register_best_model
        >> reload_fastapi_model
        >> update_retraining_state
        >> end_retraining
    )
