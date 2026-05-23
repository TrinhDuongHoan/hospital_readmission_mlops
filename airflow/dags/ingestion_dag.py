import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

TOPIC_NAME = os.getenv(
    "KAFKA_TOPIC",
    "patient-events",
)


default_args = {
    "owner": "hoan",
    "depends_on_past": False,
    "retries": 1,
}


def create_kafka_topic():
    admin_client = KafkaAdminClient(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        client_id="airflow-topic-admin",
    )

    topic = NewTopic(
        name=TOPIC_NAME,
        num_partitions=3,
        replication_factor=1,
    )

    try:
        admin_client.create_topics(
            new_topics=[topic],
            validate_only=False,
        )
        print(f"Created Kafka topic: {TOPIC_NAME}")
    except TopicAlreadyExistsError:
        print(f"Kafka topic already exists: {TOPIC_NAME}")
    finally:
        admin_client.close()


with DAG(
    dag_id="ingestion_dag",
    description="Stream CSV data to Kafka topic patient-events",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["ingestion", "kafka", "mlops"],
) as dag:

    create_kafka_topics = PythonOperator(
        task_id="create_kafka_topics",
        python_callable=create_kafka_topic,
    )

    stream_csv_to_kafka = BashOperator(
        task_id="stream_csv_to_kafka",
        bash_command=(
            "cd /opt/project && "
            "KAFKA_BOOTSTRAP_SERVERS=kafka:9092 "
            "KAFKA_TOPIC=patient-events "
            "CSV_PATH=/opt/project/data/diabetic_data.csv "
            "MAX_ROWS=100 "
            "STREAM_SLEEP_TIME=0.05 "
            "python kafka/producer.py"
        ),
    )

    create_kafka_topics >> stream_csv_to_kafka