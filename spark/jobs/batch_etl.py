from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, when
from pyspark.sql.types import DoubleType, IntegerType


INPUT_PATH = "/opt/project/data/diabetic_data.csv"
OUTPUT_PATH = "/opt/project/data/gold/diabetic_gold.parquet"


NUMERIC_COLUMNS = [
    "admission_type_id",
    "discharge_disposition_id",
    "admission_source_id",
    "time_in_hospital",
    "num_lab_procedures",
    "num_procedures",
    "num_medications",
    "number_outpatient",
    "number_emergency",
    "number_inpatient",
    "number_diagnoses",
]


DROP_COLUMNS = [
    "weight",
    "payer_code",
    "medical_specialty",
]


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("HospitalReadmissionBatchETL")
        .getOrCreate()
    )


def clean_dataframe(df):
    # Dataset dùng "?" để biểu diễn missing value
    df = df.replace("?", None)

    # Tạo target nhị phân:
    # readmitted = <30 => 1
    # readmitted = >30 hoặc NO => 0
    df = df.withColumn(
        "readmitted_binary",
        when(col("readmitted") == "<30", lit(1)).otherwise(lit(0)),
    )

    # Thêm timestamp phục vụ Feature Store / streaming style
    df = df.withColumn("event_timestamp", current_timestamp())

    # Ép kiểu numeric
    for column_name in NUMERIC_COLUMNS:
        if column_name in df.columns:
            df = df.withColumn(column_name, col(column_name).cast(DoubleType()))

    # Ép kiểu ID nếu có
    if "encounter_id" in df.columns:
        df = df.withColumn("encounter_id", col("encounter_id").cast("string"))

    if "patient_nbr" in df.columns:
        df = df.withColumn("patient_nbr", col("patient_nbr").cast("string"))

    # Drop các cột thiếu quá nhiều hoặc ít hữu ích trong MVP
    for column_name in DROP_COLUMNS:
        if column_name in df.columns:
            df = df.drop(column_name)

    # Drop cột target gốc sau khi tạo target binary
    if "readmitted" in df.columns:
        df = df.drop("readmitted")

    # Bỏ dòng thiếu các cột quan trọng
    df = df.dropna(
        subset=[
            "race",
            "gender",
            "age",
        ]
    )

    # Fill categorical missing bằng Unknown
    for column_name, dtype in df.dtypes:
        if dtype == "string" and column_name != "event_timestamp":
            df = df.fillna({column_name: "Unknown"})

    # Fill numeric missing bằng 0 ở tầng ETL.
    # Khi train vẫn có thể dùng imputer median trong sklearn pipeline.
    for column_name in NUMERIC_COLUMNS:
        if column_name in df.columns:
            df = df.fillna({column_name: 0.0})

    return df


def main():
    spark = create_spark_session()

    print(f"Reading raw CSV from: {INPUT_PATH}")

    df = spark.read.csv(
        INPUT_PATH,
        header=True,
        inferSchema=True,
    )

    print("Raw schema:")
    df.printSchema()

    cleaned_df = clean_dataframe(df)

    print("Cleaned schema:")
    cleaned_df.printSchema()

    print("Sample cleaned data:")
    cleaned_df.show(5, truncate=False)

    print(f"Writing gold data to: {OUTPUT_PATH}")

    cleaned_df.write.mode("overwrite").parquet(OUTPUT_PATH)

    print("Batch ETL completed successfully.")

    spark.stop()


if __name__ == "__main__":
    main()