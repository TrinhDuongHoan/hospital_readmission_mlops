import csv
import json
import os
import time
from typing import Dict, Any

from kafka import KafkaProducer


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC_PATIENT_EVENTS",
    "patient-events",
)

CSV_PATH = os.getenv(
    "CSV_PATH",
    "data/diabetic_data.csv",
)

SLEEP_TIME = float(os.getenv("STREAM_SLEEP_TIME", "0.05"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "100"))


def clean_row(row: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}

    for key, value in row.items():
        if value == "?":
            cleaned[key] = None
        else:
            cleaned[key] = value

    return cleaned


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda key: str(key).encode("utf-8"),
        acks="all",
        retries=3,
    )


def stream_csv_to_kafka(csv_path: str) -> None:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    producer = create_producer()

    sent_count = 0

    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for index, row in enumerate(reader):
            if MAX_ROWS > 0 and sent_count >= MAX_ROWS:
                break

            cleaned_row = clean_row(row)

            key = cleaned_row.get("encounter_id", index)

            producer.send(
                topic=KAFKA_TOPIC,
                key=key,
                value=cleaned_row,
            )

            sent_count += 1

            print(f"Sent row={index}, key={key}, topic={KAFKA_TOPIC}")

            time.sleep(SLEEP_TIME)

    producer.flush()
    producer.close()

    print(f"Finished streaming {sent_count} rows to topic {KAFKA_TOPIC}")


if __name__ == "__main__":
    stream_csv_to_kafka(CSV_PATH)