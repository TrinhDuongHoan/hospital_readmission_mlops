# Hospital Readmission Prediction MLOps

End-to-end MLOps platform for predicting early hospital readmission risk for diabetic patients. The project combines batch and streaming data processing, model training and registry, production inference APIs, a React clinical dashboard, automated retraining workflows, and observability with Prometheus and Grafana.

## Overview

The system predicts whether a patient is likely to be readmitted within 30 days based on clinical and admission features from the diabetes readmission dataset. It is designed as a practical MLOps project rather than a standalone notebook: models are trained, tracked, registered, served, monitored, and refreshed through reproducible pipelines.

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
- Readmission prediction from saved patients or direct clinical form input
- Role-based access with JWT authentication for doctors and admins
- Prediction logging to PostgreSQL and Redis
- Batch ETL and feature generation with Apache Spark
- Streaming ingestion from CSV to Kafka and Spark Streaming bronze storage
- ML training with scikit-learn pipelines and MLflow experiment tracking
- Model registration and Production promotion through MLflow Registry
- Data-triggered and database-triggered retraining DAGs in Airflow
- FastAPI Prometheus metrics and Grafana dashboards
- React dashboard for doctors/admin users

## Architecture

```text
CSV / Patient Events
        |
        v
 Kafka + Spark Streaming  --->  Bronze Parquet
        |
        v
 Spark Batch ETL  --->  Gold Parquet  --->  Feature Dataset
        |
        v
 Training Pipeline  --->  MLflow Tracking + MinIO Artifacts
        |
        v
 MLflow Model Registry: HospitalReadmissionModel/Production
        |
        v
 FastAPI Inference API  --->  PostgreSQL + Redis + Prometheus
        |
        v
 React Frontend + Grafana Dashboards
```

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, Vite, axios, lucide-react |
| API | FastAPI, Pydantic, JWT, passlib |
| ML | pandas, scikit-learn, joblib |
| Tracking | MLflow, MinIO/S3 artifact storage |
| Orchestration | Apache Airflow |
| Data processing | Apache Spark, Spark Streaming |
| Messaging | Kafka, Zookeeper, Kafka UI |
| Storage | PostgreSQL, Redis, Parquet |
| Monitoring | Prometheus, Grafana alert rules/dashboard |
| Deployment | Docker, Docker Compose |

## Repository Structure

```text
.
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
├── training/                # Training, evaluation, model registration scripts
├── docker-compose.yml       # Full local MLOps stack
├── dvc.yaml                 # DVC training stage
├── params.yaml              # Training parameters
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
| PostgreSQL | `mlops` | `mlops123` |

## Common Workflows

### Train and Register the Model

The `trainer` service waits for MLflow, trains candidate models, logs metrics/artifacts, and registers the best model.

```bash
docker compose up trainer
```

Training behavior is controlled by:

- `training/config.yaml`
- `params.yaml`
- `.env`

The champion report is written to:

```text
reports/metrics.json
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

Available retraining workflows:

- `data_triggered_retraining_dag`: retrains when enough new bronze streaming records exist
- `db_triggered_retraining_dag`: retrains when enough labeled patient records exist in PostgreSQL
- `retraining_dag`: manual retraining workflow

Example:

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

Admin-only MLOps endpoints:

```text
GET  /prediction-logs
GET  /dashboard-stats
GET  /mlops/pipelines
POST /mlops/pipelines/{dag_id}/trigger
POST /reload-model
```

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

1. Load `data/diabetic_data.csv`
2. Replace `?` with missing values
3. Create binary target: `readmitted == "<30"`
4. Drop high-missing or identifier columns
5. Split train/test with stratification
6. Apply numeric imputation/scaling and categorical one-hot encoding
7. Train candidate models
8. Select champion by ROC-AUC
9. Log model and metrics to MLflow
10. Register/promote a Production model when it improves over the current version

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
docker compose logs -f spark-streaming
```

Rebuild one service:

```bash
docker compose up -d --build fastapi
```

## Notes

- This repository is intended for local MLOps experimentation and demonstration.
- The current model metrics are suitable for project demonstration, not clinical deployment.
- Before real-world use, the model should be validated with stronger evaluation, calibration, bias analysis, explainability, and clinical governance.

