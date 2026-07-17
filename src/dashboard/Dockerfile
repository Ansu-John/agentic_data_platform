# Use a lightweight Python base image
FROM python:3.12-slim-bookworm

# Install the uv binary directly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /home/hadoop/app

# Ensure uv output is not buffered and virtual environment is in the project
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/home/hadoop/app/.venv

# Step 1: Copy ONLY the dependency files first to leverage Docker layer caching
COPY src/pyproject.toml src/uv.lock ./

# Step 2: Install dependencies (without installing the project source code yet)
RUN uv sync --frozen --no-dev --no-install-project

# Step 3: Copy the actual application code
COPY  src/ ./src/

# Step 4: Final sync to link the application code
RUN uv sync --frozen --no-dev

# Expose the port Streamlit runs on
EXPOSE 8501

# Start Streamlit using uv to ensure it runs inside the virtual environment
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]