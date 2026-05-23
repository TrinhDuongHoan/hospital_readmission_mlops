FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/project

COPY requirements.txt /opt/project/inference/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel

RUN pip install \
    --default-timeout=600 \
    --retries=30 \
    -r /opt/project/inference/requirements.txt

RUN pip install \
    --default-timeout=600 \
    --retries=30 \
    --no-deps \
    xgboost==3.1.3

COPY app /opt/project/inference/app

CMD ["uvicorn", "inference.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
