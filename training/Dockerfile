FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/project

COPY training/requirements.txt /tmp/training-requirements.txt

RUN python -m pip install --upgrade pip wheel && \
    pip install setuptools==80.9.0 && \
    pip install \
    --default-timeout=600 \
    --retries=30 \
    -r /tmp/training-requirements.txt
