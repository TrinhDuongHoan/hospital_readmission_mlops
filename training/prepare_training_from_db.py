import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mlops:mlops123@postgres:5432/mlops",
)

OUTPUT_PATH = os.getenv(
    "DB_TRAINING_OUTPUT_PATH",
    "data/processed/db_training_data.csv",
)

BASE_CSV_PATH = os.getenv(
    "BASE_CSV_PATH",
    "data/diabetic_data.csv",
)


def normalize_prediction_logs(logs_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in logs_df.iterrows():
        request_json = row["request_json"]

        if isinstance(request_json, str):
            payload = dict(json.loads(request_json))
        else:
            payload = dict(request_json)

        rename_map = {
            "A1Cresult": "A1Cresult",
            "a1c_result": "A1Cresult",
            "diabetes_med": "diabetesMed",
            "glyburide_metformin": "glyburide-metformin",
            "glipizide_metformin": "glipizide-metformin",
            "glimepiride_pioglitazone": "glimepiride-pioglitazone",
            "metformin_rosiglitazone": "metformin-rosiglitazone",
            "metformin_pioglitazone": "metformin-pioglitazone",
        }

        payload = {
            rename_map.get(key, key): value
            for key, value in payload.items()
        }

        payload["readmitted"] = "<30" if int(row["actual_readmitted"]) == 1 else "NO"

        rows.append(payload)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def load_base_dataset() -> pd.DataFrame:
    base_path = Path(BASE_CSV_PATH)

    if not base_path.exists():
        print(f"Base dataset not found: {BASE_CSV_PATH}")
        return pd.DataFrame()

    df = pd.read_csv(base_path)

    return df


def load_prediction_logs() -> pd.DataFrame:
    query = """
    WITH latest_labeled_predictions AS (
        SELECT DISTINCT ON (pl.patient_id)
            pl.id,
            pl.request_json,
            p.actual_readmitted,
            pl.created_at
        FROM prediction_logs pl
        JOIN patients p ON p.id = pl.patient_id
        WHERE p.actual_readmitted IS NOT NULL
        ORDER BY pl.patient_id, pl.created_at DESC
    )
    SELECT
        id,
        request_json,
        actual_readmitted,
        created_at
    FROM latest_labeled_predictions
    ORDER BY created_at ASC;
    """

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    with engine.begin() as connection:
        rows = connection.execute(text(query)).mappings().all()

    df = pd.DataFrame(rows)

    return df


def main():
    print("Preparing training dataset from PostgreSQL labeled prediction_logs...")

    base_df = load_base_dataset()
    logs_df = load_prediction_logs()

    print(f"Base dataset rows: {len(base_df)}")
    print(f"Labeled prediction log rows: {len(logs_df)}")

    logs_training_df = normalize_prediction_logs(logs_df)

    print(f"Normalized DB training rows: {len(logs_training_df)}")

    if base_df.empty and logs_training_df.empty:
        raise RuntimeError("No training data available.")

    if base_df.empty:
        final_df = logs_training_df
    elif logs_training_df.empty:
        final_df = base_df
    else:
        common_columns = [
            column
            for column in base_df.columns
            if column in logs_training_df.columns
        ]

        if "readmitted" not in common_columns:
            common_columns.append("readmitted")

        final_df = pd.concat(
            [
                base_df[common_columns],
                logs_training_df[common_columns],
            ],
            ignore_index=True,
        )

    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_df.to_csv(output_path, index=False)

    print(f"Saved DB training dataset to: {output_path}")
    print(f"Final training rows: {len(final_df)}")
    print(f"Final training columns: {list(final_df.columns)}")


if __name__ == "__main__":
    main()
