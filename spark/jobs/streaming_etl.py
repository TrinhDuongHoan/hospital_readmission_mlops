from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, from_json, lit, when
from pyspark.sql.types import StringType, StructField, StructType


KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
TOPIC = "patient-events"

OUTPUT_PATH = "/opt/project/data/bronze/patient_events"
CHECKPOINT_PATH = "/opt/project/data/checkpoints/patient_events"


def build_schema() -> StructType:
    columns = [
        "encounter_id",
        "patient_nbr",
        "race",
        "gender",
        "age",
        "weight",
        "admission_type_id",
        "discharge_disposition_id",
        "admission_source_id",
        "time_in_hospital",
        "payer_code",
        "medical_specialty",
        "num_lab_procedures",
        "num_procedures",
        "num_medications",
        "number_outpatient",
        "number_emergency",
        "number_inpatient",
        "diag_1",
        "diag_2",
        "diag_3",
        "number_diagnoses",
        "max_glu_serum",
        "A1Cresult",
        "metformin",
        "repaglinide",
        "nateglinide",
        "chlorpropamide",
        "glimepiride",
        "acetohexamide",
        "glipizide",
        "glyburide",
        "tolbutamide",
        "pioglitazone",
        "rosiglitazone",
        "acarbose",
        "miglitol",
        "troglitazone",
        "tolazamide",
        "examide",
        "citoglipton",
        "insulin",
        "glyburide-metformin",
        "glipizide-metformin",
        "glimepiride-pioglitazone",
        "metformin-rosiglitazone",
        "metformin-pioglitazone",
        "change",
        "diabetesMed",
        "readmitted",
    ]

    return StructType(
        [
            StructField(column_name, StringType(), True)
            for column_name in columns
        ]
    )


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("HospitalReadmissionStreamingETL")
        .getOrCreate()
    )


def main():
    spark = create_spark_session()

    spark.sparkContext.setLogLevel("WARN")

    schema = build_schema()

    print(f"Reading stream from Kafka topic: {TOPIC}")

    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    raw_json_df = kafka_df.selectExpr(
        "CAST(key AS STRING) AS kafka_key",
        "CAST(value AS STRING) AS json_value",
        "timestamp AS kafka_timestamp",
    )

    parsed_df = (
        raw_json_df
        .select(
            col("kafka_key"),
            col("kafka_timestamp"),
            from_json(col("json_value"), schema).alias("data"),
        )
        .select(
            col("kafka_key"),
            col("kafka_timestamp"),
            col("data.*"),
        )
    )

    cleaned_df = (
        parsed_df
        .withColumn("event_timestamp", current_timestamp())
        .withColumn(
            "readmitted_binary",
            when(col("readmitted") == "<30", lit(1)).otherwise(lit(0)),
        )
        .drop("readmitted")
    )

    query = (
        cleaned_df.writeStream
        .format("parquet")
        .option("path", OUTPUT_PATH)
        .option("checkpointLocation", CHECKPOINT_PATH)
        .outputMode("append")
        .trigger(processingTime="10 seconds")
        .start()
    )

    print(f"Writing bronze streaming data to: {OUTPUT_PATH}")
    print(f"Checkpoint path: {CHECKPOINT_PATH}")
    print("Streaming query started. Press Ctrl+C to stop.")

    query.awaitTermination()


if __name__ == "__main__":
    main()
