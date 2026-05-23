from datetime import datetime
from pathlib import Path

import pandas as pd

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator


BRONZE_PATH = "/opt/project/data/bronze/patient_events"
STATE_PATH = "/opt/project/reports/retraining_state.txt"

MIN_NEW_RECORDS = 50


default_args = {
    "owner": "hoan",
    "depends_on_past": False,
    "retries": 1,
}


def count_bronze_records() -> int:
    bronze_dir = Path(BRONZE_PATH)

    if not bronze_dir.exists():
        return 0

    parquet_files = list(bronze_dir.glob("*.parquet"))

    if not parquet_files:
        return 0

    total_records = 0

    for parquet_file in parquet_files:
        try:
            df = pd.read_parquet(parquet_file)
            total_records += len(df)
        except Exception as exc:
            print(f"Skip file {parquet_file}: {exc}")

    return total_records


def load_last_trained_count() -> int:
    state_file = Path(STATE_PATH)

    if not state_file.exists():
        return 0

    try:
        return int(state_file.read_text().strip())
    except Exception:
        return 0


def decide_retraining_branch():
    current_count = count_bronze_records()
    last_trained_count = load_last_trained_count()
    new_records = current_count - last_trained_count

    print(f"Current bronze records: {current_count}")
    print(f"Last trained records: {last_trained_count}")
    print(f"New records: {new_records}")
    print(f"Minimum new records required: {MIN_NEW_RECORDS}")

    if new_records >= MIN_NEW_RECORDS:
        return "spark_batch_etl"

    return "skip_retraining"


def update_retraining_state():
    current_count = count_bronze_records()

    state_file = Path(STATE_PATH)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(str(current_count))

    print(f"Updated retraining state to: {current_count}")


with DAG(
    dag_id="data_triggered_retraining_dag",
    description="Retrain only when enough new streaming data is available",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="*/30 * * * *",
    catchup=False,
    tags=["retraining", "data-triggered"],
) as dag:

    check_new_data = BranchPythonOperator(
        task_id="check_new_data",
        python_callable=decide_retraining_branch,
    )

    skip_retraining = EmptyOperator(
        task_id="skip_retraining",
    )

    spark_batch_etl = BashOperator(
        task_id="spark_batch_etl",
        bash_command=(
            "docker exec spark-master "
            "/opt/spark/bin/spark-submit "
            "/opt/project/spark/jobs/batch_etl.py"
        ),
    )

    spark_feature_engineering = BashOperator(
        task_id="spark_feature_engineering",
        bash_command=(
            "docker exec spark-master "
            "/opt/spark/bin/spark-submit "
            "/opt/project/spark/jobs/feature_engineering.py"
        ),
    )

    prepare_training_dataset = BashOperator(
        task_id="prepare_training_dataset",
        bash_command=(
            "cd /opt/project && "
            "BRONZE_PATH=/opt/project/data/bronze/patient_events "
            "BASE_CSV_PATH=/opt/project/data/diabetic_data.csv "
            "STREAMING_TRAINING_OUTPUT_PATH=/opt/project/data/processed/streaming_training_data.csv "
            "python -m training.prepare_training_from_bronze"
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
            "CSV_PATH=/opt/project/data/processed/streaming_training_data.csv "
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
            "REGISTER_METRIC_NAME=roc_auc "
            "REGISTER_METRIC_MODE=max "
            "MIN_IMPROVEMENT=0.001 "
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

    update_state = PythonOperator(
        task_id="update_retraining_state",
        python_callable=update_retraining_state,
    )

    end_retraining = EmptyOperator(
        task_id="end_retraining",
    )

    check_new_data >> skip_retraining

    (
        check_new_data
        >> spark_batch_etl
        >> spark_feature_engineering
        >> prepare_training_dataset
        >> train_new_model
        >> register_best_model
        >> reload_fastapi_model
        >> update_state
        >> end_retraining
    )
