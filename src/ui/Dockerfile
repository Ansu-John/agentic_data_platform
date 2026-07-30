# syntax=docker/dockerfile:1
FROM python:3.12-slim as UI_builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace_build
COPY src/pyproject.toml ./

RUN python -m venv /workspace_build/.venv
RUN /workspace_build/.venv/bin/pip install --no-cache-dir .

# -------------------------------------------------------------
FROM python:3.12-slim as ui_runtime
WORKDIR /app

ENV PYTHONPATH="/app"

COPY --from=UI_builder /workspace_build/.venv /app/.venv
COPY src/ /app/src/

RUN useradd -u 10002 ui_user && chown -R ui_user:ui_user /app
USER ui_user

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "src/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]