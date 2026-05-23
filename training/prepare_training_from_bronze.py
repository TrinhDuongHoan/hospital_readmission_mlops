import os
from pathlib import Path

import pandas as pd


BRONZE_PATH = os.getenv(
    "BRONZE_PATH",
    "data/bronze/patient_events",
)

BASE_CSV_PATH = os.getenv(
    "BASE_CSV_PATH",
    "data/diabetic_data.csv",
)

OUTPUT_PATH = os.getenv(
    "STREAMING_TRAINING_OUTPUT_PATH",
    "data/processed/streaming_training_data.csv",
)


def load_base_dataset() -> pd.DataFrame:
    base_path = Path(BASE_CSV_PATH)

    if not base_path.exists():
        print(f"Base dataset not found: {BASE_CSV_PATH}")
        return pd.DataFrame()

    return pd.read_csv(base_path)


def load_bronze_dataset() -> pd.DataFrame:
    bronze_dir = Path(BRONZE_PATH)

    if not bronze_dir.exists():
        print(f"Bronze path not found: {BRONZE_PATH}")
        return pd.DataFrame()

    parquet_files = sorted(bronze_dir.glob("*.parquet"))

    if not parquet_files:
        print(f"No parquet files found in bronze path: {BRONZE_PATH}")
        return pd.DataFrame()

    dataframes = []

    for parquet_file in parquet_files:
        try:
            dataframes.append(pd.read_parquet(parquet_file))
        except Exception as exc:
            print(f"Skip file {parquet_file}: {exc}")

    if not dataframes:
        return pd.DataFrame()

    bronze_df = pd.concat(dataframes, ignore_index=True)

    if "readmitted_binary" in bronze_df.columns:
        bronze_df["readmitted"] = bronze_df["readmitted_binary"].map(
            {
                1: "<30",
                "1": "<30",
                0: "NO",
                "0": "NO",
            }
        ).fillna("NO")

    drop_columns = [
        "kafka_key",
        "kafka_timestamp",
        "event_timestamp",
        "readmitted_binary",
    ]

    return bronze_df.drop(
        columns=[column for column in drop_columns if column in bronze_df.columns],
    )


def main():
    print("Preparing training dataset from streaming bronze parquet...")

    base_df = load_base_dataset()
    bronze_df = load_bronze_dataset()

    print(f"Base dataset rows: {len(base_df)}")
    print(f"Bronze dataset rows: {len(bronze_df)}")

    if base_df.empty and bronze_df.empty:
        raise RuntimeError("No training data available.")

    if base_df.empty:
        final_df = bronze_df
    elif bronze_df.empty:
        final_df = base_df
    else:
        common_columns = [
            column
            for column in base_df.columns
            if column in bronze_df.columns
        ]

        if "readmitted" not in common_columns:
            raise RuntimeError("Bronze dataset does not contain readmitted target.")

        final_df = pd.concat(
            [
                base_df[common_columns],
                bronze_df[common_columns],
            ],
            ignore_index=True,
        )

    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_df.to_csv(output_path, index=False)

    print(f"Saved streaming training dataset to: {output_path}")
    print(f"Final training rows: {len(final_df)}")
    print(f"Final training columns: {list(final_df.columns)}")


if __name__ == "__main__":
    main()
