FROM python:3.10-slim

WORKDIR /opt/project

RUN pip install \
    fastapi==0.111.0 \
    uvicorn==0.29.0 \
    prometheus-client==0.20.0

COPY app /opt/project/inference/app

CMD ["uvicorn", "inference.app.main:app", "--host", "0.0.0.0", "--port", "8000"]