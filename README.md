# Hospital Readmission Prediction MLOps

End-to-end MLOps platform for predicting early hospital readmission risk for diabetic patients. The project combines batch feature engineering, model training and registry, production inference APIs, a React clinical dashboard, database-triggered retraining workflows, optional streaming ingestion, and observability with Prometheus and Grafana.

## Overview

The system predicts whether a patient is likely to be readmitted within 30 days based on clinical and admission features from the diabetes readmission dataset. It is designed as a practical MLOps project rather than a standalone notebook: data is processed into offline features, models are trained and tracked, the champion model is registered, inference is served through an authenticated API, predictions are logged, and retraining workflows can refresh the deployed model.

Current champion model:

| Metric | Value |
| --- | ---: |
| Model | Random Forest |
| Accuracy | 0.6556 |
| Precision | 0.1714 |
| Recall | 0.5394 |
| F1-score | 0.2601 |
| ROC-AUC | 0.6477 |

## Key Features

- Patient CRUD and clinical profile management
- Admin user management for doctor/admin accounts, including temporary disable/enable
- Readmission prediction from saved patients or direct clinical form input
- Role-based access with JWT authentication for doctors and admins
- Prediction logging to PostgreSQL and Redis
- Batch ETL and feature generation with Apache Spark
- Optional streaming ingestion from CSV to Kafka and Spark Streaming bronze storage
- ML training with scikit-learn pipelines and MLflow experiment tracking
- Model registration and Production promotion through MLflow Registry
- Database-triggered retraining DAG in Airflow from newly labeled patients
- FastAPI Prometheus metrics and Grafana dashboards
- React dashboard for doctors/admin users

## Architecture

```text
CSV Training Data
        |
        v
 Spark Batch ETL  --->  Gold Parquet  --->  Offline Feature Parquet
        |
        v
 Training Pipeline  --->  MLflow Tracking + MinIO Artifacts
        |
        v
 MLflow Model Registry: HospitalReadmissionModel/Production
        |
        v
 FastAPI Inference API  --->  PostgreSQL + Redis Cache + Prometheus
        |
        v
 React Frontend + Grafana Dashboards

Optional path:

CSV Patient Events ---> Kafka ---> Spark Streaming ---> Bronze Parquet
```

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, Vite, axios, lucide-react |
| API | FastAPI, Pydantic, JWT, passlib |
| ML | pandas, scikit-learn, joblib |
| Tracking | MLflow, MinIO/S3 artifact storage |
| Orchestration | Apache Airflow |
| Data processing | Apache Spark, optional Spark Streaming |
| Messaging | Kafka, Zookeeper, Kafka UI |
| Storage | PostgreSQL, Redis, Parquet |
| Monitoring | Prometheus, Grafana alert rules/dashboard |
| Deployment | Docker, Docker Compose |

## Repository Structure

```text
.
├── .github/workflows/       # CI/CD workflows for tests, builds, and image release
├── airflow/                 # Airflow image and DAGs
├── data/                    # Raw CSV, bronze/gold/features data
├── docs/                    # Project report and generated diagrams
├── frontend/                # React application
├── inference/               # FastAPI inference service
├── kafka/                   # Producer, consumer, topic setup scripts
├── mlflow/                  # MLflow Docker image
├── monitoring/              # Prometheus config, alert rules, Grafana dashboard
├── models/                  # Local model artifact
├── reports/                 # Metrics and retraining state
├── spark/                   # Spark Docker image and ETL jobs
├── tests/                   # Unit tests for API, training, preprocessing, and helpers
├── training/                # Training, evaluation, model registration scripts
├── docker-compose.yml       # Full local MLOps stack
├── dvc.yaml                 # DVC training stage
├── params.yaml              # Training parameters
├── pytest.ini               # Pytest discovery and warning configuration
└── README.md
```

## Prerequisites

- Docker and Docker Compose
- At least 8 GB RAM recommended for the full stack
- Dataset file at `data/diabetic_data.csv`

The dataset is tracked through DVC metadata at `data/diabetic_data.csv.dvc`. If the CSV is not present locally, restore it from your configured DVC remote before running the full pipeline.

## Quick Start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Start the full stack:

```bash
docker compose up -d --build
```

3. Check service health:

```bash
docker compose ps
```

4. Open the web app:

```text
http://localhost:3001
```

Default users:

| Role | Username | Password |
| --- | --- | --- |
| Doctor | `doctor01` | `doctor123` |
| Admin | `admin01` | `admin123` |

## Local Development

Use a Python virtual environment when running tests, scripts, or API code outside Docker:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Start only the FastAPI service locally:

```bash
uvicorn inference.app.main:app --reload --host 0.0.0.0 --port 8000
```

The local API reads configuration from environment variables or `.env`. For the full dependency stack, prefer Docker Compose.

## Compose Profiles

The default `docker compose up -d --build` command starts the core application, orchestration, batch processing, registry, storage, and monitoring services. Two heavier/demo-only services are kept behind profiles:

| Profile | Service | Purpose |
| --- | --- | --- |
| `training` | `trainer` | One-shot raw CSV training and model registration |
| `streaming` | `spark-streaming` | Continuous Kafka-to-bronze streaming demo |

## Service URLs

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3001 |
| FastAPI | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| MLflow | http://localhost:5000/tools/mlflow/ |
| Airflow | http://localhost:8088/tools/airflow/ |
| Kafka UI | http://localhost:8080 |
| MinIO Console | http://localhost:9001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Spark Master UI | http://localhost:8081 |
| Spark Worker UI | http://localhost:8082 |

Default infrastructure credentials:

| Service | Username | Password |
| --- | --- | --- |
| Airflow | `admin` | `admin` |
| Grafana | `admin` | `admin` |
| MinIO | `minio` | `minio123` |
| App PostgreSQL | `mlops` | `mlops123` |
| Airflow PostgreSQL | `airflow` | `airflow` |

## Common Workflows

### Build Features, Train, and Register the Model

The recommended training path is the Airflow `training_dag`. It runs Spark batch ETL, builds the offline feature parquet, trains candidate models, logs metrics/artifacts, and registers the best model.

```bash
docker compose exec airflow-webserver airflow dags trigger training_dag
```

Training behavior is controlled by:

- `training/config.yaml`
- `params.yaml`
- `.env`

The champion report is written to:

```text
reports/metrics.json
```

For a lightweight baseline run that trains directly from the raw CSV, use the one-shot trainer profile:

```bash
docker compose --profile training up trainer
```

### Run Kafka Ingestion

Create Kafka topics and stream rows from the CSV:

```bash
docker compose up kafka-init
docker compose exec airflow-webserver airflow dags trigger ingestion_dag
```

The producer sends events to:

```text
patient-events
```

The continuous Spark Streaming bronze writer is optional. Start it only when you want to demonstrate the streaming path:

```bash
docker compose --profile streaming up -d spark-streaming
```

### Run ETL and Feature Engineering

Trigger the Airflow ETL DAG:

```bash
docker compose exec airflow-webserver airflow dags trigger etl_dag
```

Outputs:

```text
data/gold/diabetic_gold.parquet
data/features/offline/patient_features.parquet
```

### Trigger Training from Airflow

```bash
docker compose exec airflow-webserver airflow dags trigger training_dag
```

### Trigger Retraining

Retraining is driven by newly labeled patients in PostgreSQL. When enough records have `actual_readmitted`, trigger:

```bash
docker compose exec airflow-webserver airflow dags trigger db_triggered_retraining_dag
```

## API Examples

Login:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"doctor01","password":"doctor123"}'
```

Health check:

```bash
curl http://localhost:8000/health
```

Model info:

```bash
curl http://localhost:8000/model-info
```

Prediction endpoints require a Bearer token:

```text
POST /predict
POST /patients/{patient_id}/predict
GET  /patients/high-risk
GET  /patients/{patient_id}/predictions
```

Admin-only endpoints:

```text
GET    /users
POST   /users
PUT    /users/{user_id}
PATCH  /users/{user_id}/status
GET  /prediction-logs
GET  /dashboard-stats
GET  /mlops/pipelines
POST /mlops/pipelines/{dag_id}/trigger
POST /reload-model
```

User accounts are soft-disabled rather than deleted. Disabled users remain in PostgreSQL for patient/log history integrity, but they cannot log in or continue using existing tokens.

## Monitoring

FastAPI exposes Prometheus metrics at:

```text
http://localhost:8000/metrics
```

Tracked metrics include:

- `prediction_requests_total`
- `prediction_request_latency_seconds`
- `prediction_errors_total`
- `prediction_risk_level_total`
- `prediction_readmission_probability`
- `model_reload_total`

Prometheus alert rules are defined in:

```text
monitoring/alert_rules.yml
```

Grafana dashboard JSON:

```text
monitoring/grafana/dashboards/hospital_readmission_mlops.json
```

## Data and Model Pipeline

The training pipeline performs:

1. Build gold data from `data/diabetic_data.csv` with Spark
2. Write offline features to `data/features/offline/patient_features.parquet`
3. Load either offline feature parquet or raw CSV training data
4. Replace `?` with missing values and normalize feature names
5. Create binary target: `readmitted == "<30"` when needed
6. Drop metadata/high-missing columns that are not model features
7. Split train/test with stratification
8. Apply numeric imputation/scaling and categorical one-hot encoding
9. Train candidate models
10. Select champion by ROC-AUC
11. Log model and metrics to MLflow
12. Register/promote a Production model when it improves over the current version

Retraining is intentionally based on labeled operational data in PostgreSQL. The Kafka/Spark Streaming path remains available as an ingestion demonstration, but it is not used as an automatic retraining trigger.

Configured candidates:

- Random Forest
- Logistic Regression

## Documentation

Generated project report:

```text
docs/Hospital_Readmission_Prediction_Report.docx
```

Report generator:

```text
docs/generate_hospital_readmission_report.py
```

Generated diagrams:

```text
docs/generated_diagrams/
```

## Testing

Run the test suite from the project root:

```bash
pytest
```

The current tests cover:

- Authentication and JWT helper behavior
- Admin user management, including role updates and account disable/enable guards
- Prediction API request handling with mocked model dependencies
- Database helper functions using an in-memory SQLite setup
- Preprocessing and feature preparation logic
- Training pipeline behavior with lightweight fixtures
- Retraining data preparation checks

The tests are designed to run without Docker, PostgreSQL, Kafka, Spark, Airflow, or MLflow services. Test bootstrap code in `tests/conftest.py` provides local environment defaults and lightweight stubs where needed.

Expected result:

```text
28 passed
```

## CI/CD

GitHub Actions workflows are defined in:

```text
.github/workflows/ci.yml
.github/workflows/cd.yml
```

`CI` runs on pull requests and pushes to `main`/`develop`:

- Python dependency installation and `pytest`
- Frontend dependency installation and Vite production build
- Docker Compose configuration validation for default and optional profiles
- Report generator validation from the Word template

`CD` runs on release tags matching `v*` or manually from GitHub Actions:

- Builds FastAPI, frontend, trainer, Airflow, Spark, and MLflow Docker images
- Pushes images to GitHub Container Registry on release tags
- Supports manual image push with the `push_images` workflow input
- Validates the full Compose bundle with `training` and `streaming` profiles

Create a release build:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Useful Commands

Stop the stack:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

View logs:

```bash
docker compose logs -f fastapi
docker compose logs -f airflow-scheduler
docker compose --profile streaming logs -f spark-streaming
```

Rebuild one service:

```bash
docker compose up -d --build fastapi
```

## Troubleshooting

`ModuleNotFoundError: No module named 'jose'`

Install the project dependencies in the active virtual environment:

```bash
pip install -r requirements.txt
```

Or install only the authentication dependencies:

```bash
pip install "python-jose[cryptography]" "passlib[bcrypt]" bcrypt
```

`pytest_asyncio` loop-scope warning

The project includes `pytest.ini` to suppress the known collection warning. If it still appears, make sure you run `pytest` from the project root with the updated file present.

Missing dataset

If `data/diabetic_data.csv` is not available, restore it from DVC before running training or ETL:

```bash
dvc pull data/diabetic_data.csv.dvc
```

## Notes

- This repository is intended for local MLOps experimentation and demonstration.
- The current model metrics are suitable for project demonstration, not clinical deployment.
- Before real-world use, the model should be validated with stronger evaluation, calibration, bias analysis, explainability, and clinical governance.


# Note 
docker compose exec postgres psql -U mlops -d mlops -c "
UPDATE patients
SET actual_readmitted = CASE WHEN id % 2 = 0 THEN 1 ELSE 0 END
WHERE id IN (
  SELECT p.id
  FROM patients p
  JOIN prediction_logs pl ON pl.patient_id = p.id
  GROUP BY p.id
  ORDER BY p.id DESC
  LIMIT 10
);

UPDATE retraining_state
SET last_trained_patient_count = 0,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 1;

SELECT COUNT(*) AS labeled_patients
FROM patients
WHERE actual_readmitted IS NOT NULL;
"
