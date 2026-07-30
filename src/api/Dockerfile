# syntax=docker/dockerfile:1
FROM python:3.12-slim as component_builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Use local package resolution patterns from the repository roots
COPY src/pyproject.toml ./

RUN python -m venv /app/.venv
RUN /app/.venv/bin/pip install --no-cache-dir --upgrade pip && \
    /app/.venv/bin/pip install --no-cache-dir .

# -------------------------------------------------------------
FROM python:3.12-slim as api_runtime
WORKDIR /app

ENV PYTHONPATH="/app"

COPY --from=component_builder /app/.venv /app/.venv
COPY src/ /app/src/

RUN useradd -u 10001 api_user && chown -R api_user:api_user /app
USER api_user

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
ENTRYPOINT ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]