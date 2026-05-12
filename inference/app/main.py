from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response


app = FastAPI(
    title="Hospital Readmission Prediction API",
    version="0.1.0",
)

REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total number of API requests",
)


@app.get("/health")
def health_check():
    REQUEST_COUNT.inc()

    return {
        "status": "ok",
        "service": "hospital-readmission-api",
        "phase": "phase-1",
    }


@app.get("/")
def root():
    REQUEST_COUNT.inc()

    return {
        "message": "Hospital Readmission MLOps API is running",
    }


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )