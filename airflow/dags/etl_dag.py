from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "hoan",
    "depends_on_past": False,
    "retries": 1,
}


with DAG(
    dag_id="etl_dag",
    description="Run Spark batch ETL and feature engineering",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["phase6", "spark", "etl"],
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

    batch_etl >> feature_engineering