from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "hoan",
    "depends_on_past": False,
    "retries": 1,
}


with DAG(
    dag_id="retraining_dag",
    description="Weekly retraining pipeline: ETL, train, register, reload FastAPI",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@weekly",
    catchup=False,
    tags=["phase6", "retraining", "mlops"],
) as dag:

    batch_etl = BashOperator(
        task_id="spark_batch_etl",
        bash_command=(
            "docker exec spark-master "
            "/opt/spark/bin/spark-submit "
            "/opt/project/spark/jobs/batch_etl.py"
        ),
    )

    feature_engineering = BashOperator(
        task_id="spark_feature_engineering",
        bash_command=(
            "docker exec spark-master "
            "/opt/spark/bin/spark-submit "
            "/opt/project/spark/jobs/feature_engineering.py"
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
            "CSV_PATH=/opt/project/data/diabetic_data.csv "
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

    batch_etl >> feature_engineering >> train_new_model >> register_best_model >> reload_fastapi_model
