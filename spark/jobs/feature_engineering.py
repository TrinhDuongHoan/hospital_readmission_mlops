from pyspark.sql import SparkSession
from pyspark.sql.functions import col


INPUT_PATH = "/opt/project/data/gold/diabetic_gold.parquet"
OUTPUT_PATH = "/opt/project/data/features/offline/patient_features.parquet"


FEATURE_COLUMNS = [
    "encounter_id",
    "patient_nbr",
    "event_timestamp",

    "race",
    "gender",
    "age",

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

    "readmitted_binary",
]


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


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("HospitalReadmissionFeatureEngineering")
        .getOrCreate()
    )


def main():
    spark = create_spark_session()

    print(f"Reading gold data from: {INPUT_PATH}")

    df = spark.read.parquet(INPUT_PATH)

    print("Gold schema:")
    df.printSchema()

    existing_feature_columns = [
        column_name
        for column_name in FEATURE_COLUMNS
        if column_name in df.columns
    ]

    feature_df = df.select(existing_feature_columns)

    # Ép kiểu numeric chắc chắn
    for column_name in NUMERIC_COLUMNS:
        if column_name in feature_df.columns:
            feature_df = feature_df.withColumn(
                column_name,
                col(column_name).cast("double"),
            )

    print("Feature schema:")
    feature_df.printSchema()

    print("Sample features:")
    feature_df.show(5, truncate=False)

    print(f"Writing offline features to: {OUTPUT_PATH}")

    feature_df.write.mode("overwrite").parquet(OUTPUT_PATH)

    print("Feature engineering completed successfully.")

    spark.stop()


if __name__ == "__main__":
    main()