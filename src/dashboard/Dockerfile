FROM ghcr.io/astral-sh/uv:0.4.0 AS uv-base
FROM python:3.12-slim AS builder

# Inherit uv binary from the official image
COPY --from=uv-base /uv /uvx /bin/

# Enforce deterministic build flags and Ensure uv output is not buffered and virtual environment is in the project
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/home/hadoop/app/.venv \
    PATH="/home/hadoop/app/.venv/bin:$PATH"

# Set the working directory
WORKDIR /home/hadoop/app

# Step 1: Copy ONLY the dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Step 2: Install dependencies strictly matching the lockfile (no updates allowed in CI)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Step 3: Copy the actual application code
COPY  . .

# Step 4: Final sync to link the application code

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Expose the port Streamlit runs on
EXPOSE 8501

# Start Streamlit using uv to ensure it runs inside the virtual environment
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]