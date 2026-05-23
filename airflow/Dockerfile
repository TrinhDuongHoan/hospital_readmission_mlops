FROM apache/airflow:2.8.1-python3.10

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER root

RUN apt-get update && \
    apt-get install -y docker.io curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt
    
