from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "hoan",
    "depends_on_past": False,
    "retries": 1,
}


with DAG(
    dag_id="training_dag",
    description="Build offline features, train model, and register best model to MLflow Registry",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["phase6", "training", "mlflow"],
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

    train_model = BashOperator(
        task_id="train_model",
        bash_command=(
            "cd /opt/project && "
            "MLFLOW_TRACKING_URI=http://mlflow:5000 "
            "MLFLOW_S3_ENDPOINT_URL=http://minio:9000 "
            "AWS_ACCESS_KEY_ID=minio "
            "AWS_SECRET_ACCESS_KEY=minio123 "
            "AWS_DEFAULT_REGION=us-east-1 "
            "TRAINING_DATA_PATH=/opt/project/data/features/offline/patient_features.parquet "
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

    batch_etl >> feature_engineering >> train_model >> register_best_model
