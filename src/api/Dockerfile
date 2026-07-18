# syntax=docker/dockerfile:1
FROM python:3.12-slim as component_builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace_build

# Use local package resolution patterns from the repository roots
COPY src/pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --target=/workspace_build/dependencies .

# -------------------------------------------------------------
FROM python:3.12-slim as api_runtime
WORKDIR /app

ENV PYTHONPATH="/app"

COPY --from=component_builder /workspace_build/dependencies /usr/local/lib/python3.12/site-packages
COPY src/ /app/src/

RUN useradd -u 10001 api_user && chown -R api_user:api_user /app
USER api_user

EXPOSE 8000
ENTRYPOINT ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]