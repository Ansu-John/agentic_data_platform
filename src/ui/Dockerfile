# syntax=docker/dockerfile:1
FROM python:3.12-slim as UI_builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace_build
COPY src/pyproject.toml ./
RUN pip install --no-cache-dir --target=/workspace_build/dependencies .

# -------------------------------------------------------------
FROM python:3.12-slim as ui_runtime
WORKDIR /app

ENV PYTHONPATH="/app"

COPY --from=UI_builder /workspace_build/dependencies /usr/local/lib/python3.12/site-packages
COPY src/ /app/src/

RUN useradd -u 10002 ui_user && chown -R ui_user:ui_user /app
USER ui_user

EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "src/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]