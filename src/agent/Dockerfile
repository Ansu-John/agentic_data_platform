# ==============================================================================
# STAGE 1: BUILD ENVIRONMENT
# Utilizes Astral's uv for deterministic, lightning-fast dependency resolution.
# ==============================================================================
FROM ghcr.io/astral-sh/uv:0.4.0 AS uv-base
FROM python:3.12-slim AS builder

# Inherit uv binary from the official image
COPY --from=uv-base /uv /uvx /bin/

# Enforce deterministic build flags
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/home/hadoop/app/.venv/bin:$PATH"

WORKDIR /home/hadoop/app

# Copy lockfiles first to maximize Docker layer caching
COPY src/agent/pyproject.toml src/agent/uv.lock ./

# Install dependencies strictly matching the lockfile (no updates allowed in CI)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application source code
COPY src/ ./src/

# Install the project module itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ==============================================================================
# STAGE 2: HARDENED RUNTIME (ZERO-TRUST)
# ==============================================================================
FROM python:3.12-slim

# Install tini to handle PID 1 zombie reaping and SIGTERM forwarding
RUN apt-get update && \
    apt-get install -y --no-install-recommends tini && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Enforce enterprise container scanning policies (Run as non-root)
ARG UID=10001
ARG GID=10001
RUN groupadd -g "${GID}" agentgroup && \
    useradd -u "${UID}" -g "${GID}" -s /sbin/nologin -m agentuser

WORKDIR /home/hadoop/app
# Copy the compiled virtual environment and code from the builder stage
# Chown exclusively to the unprivileged user
COPY --chown=agentuser:agentgroup --from=builder /home/hadoop/app/.venv /home/hadoop/app/.venv
COPY --chown=agentuser:agentgroup --from=builder /home/hadoop/app/src /home/hadoop/app/src

# Create a highly restricted temporary directory for LangGraph/Boto3 local caching
RUN mkdir -p /tmp/agent_cache && \
    chown agentuser:agentgroup /tmp/agent_cache && \
    chmod 700 /tmp/agent_cache

# Drop root privileges immediately
USER agentuser

# Isolate execution environment variables
ENV PATH="/home/hadoop/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TMPDIR="/tmp/agent_cache" \
    PYTHONPATH="/home/hadoop/app"

# Tini intercepts AWS Fargate SIGTERM and gracefully shuts down the Python process
ENTRYPOINT ["/usr/bin/tini", "--"]

# Execute the EventBridge parsing and graph orchestration entry point
CMD ["python", "-m", "src.agent.main"]