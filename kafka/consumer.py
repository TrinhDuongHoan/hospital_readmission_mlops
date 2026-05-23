import json
import os

from kafka import KafkaConsumer


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC_PATIENT_EVENTS",
    "patient-events",
)

GROUP_ID = os.getenv(
    "KAFKA_CONSUMER_GROUP",
    "hospital-readmission-debug-group",
)


def create_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        key_deserializer=lambda key: key.decode("utf-8") if key else None,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def consume_messages() -> None:
    consumer = create_consumer()

    print(f"Listening topic={KAFKA_TOPIC}")
    print("Press Ctrl+C to stop.")

    try:
        for message in consumer:
            print("-" * 80)
            print("topic:", message.topic)
            print("partition:", message.partition)
            print("offset:", message.offset)
            print("key:", message.key)
            print("value:", message.value)
    except KeyboardInterrupt:
        print("Stopped consumer.")
    finally:
        consumer.close()


if __name__ == "__main__":
    consume_messages()