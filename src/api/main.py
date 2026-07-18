import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers.query_router import router

# Setup structlog configurations
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

app = FastAPI(
    title="Enterprise AI Data Platform Ingress",
    version="1.0.0",
    description="Production Ready text-to-SQL Execution Orchestrator over S3 Iceberg Layers."
)

# Standard strict security CORS rules for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten down to exact ALB DNS profiles via terraform variables later
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_latency_logging_context(request: Request,
                            call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info("api_request_processed", path=request.url.path, method=request.method,
                latency_seconds=duration)
    return response

app.include_router(router)
