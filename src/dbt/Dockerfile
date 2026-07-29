FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    dbt-core>=1.7.0 \
    dbt-athena-community>=1.7.1

COPY src/dbt/ /app/src/dbt/

ENTRYPOINT ["sh", "-c", "dbt run --profiles-dir . && dbt test --profiles-dir ."]