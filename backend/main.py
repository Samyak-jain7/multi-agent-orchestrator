"""
Multi-Agent Orchestrator - FastAPI Backend
"""
import os
import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from core.database import init_db, close_db
from agents.queue import task_queue
from api import agents_router, workflows_router, tasks_router, execution_router


# ---------------------------------------------------------------------------
# Structured Logging Setup
# ---------------------------------------------------------------------------
class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for production readability."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data)


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    # Reduce noise from third-party libs
    for lib in ["uvicorn.access", "sqlalchemy.engine", "httpx"]:
        logging.getLogger(lib).setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Multi-Agent Orchestrator", extra={"version": "1.0.0"})
    await init_db()
    logger.info("Database initialized")
    await task_queue.start()
    logger.info("Task queue started with max_concurrent=10")
    yield
    logger.info("Shutting down...")
    await task_queue.stop()
    await close_db()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# App Creation
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Multi-Agent Orchestrator",
    description="A platform to visually configure and run multiple AI agents for complex tasks",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

if frontend_url == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Optional API key authentication for all /api/* endpoints."""
    allowed_paths = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
    if request.url.path in allowed_paths:
        return await call_next(request)

    app_api_key = os.getenv("APP_API_KEY")
    if app_api_key:
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != app_api_key:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or missing API Key"},
            )

    return await call_next(request)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Structured logging for all incoming requests."""
    start = datetime.utcnow()
    method = request.method
    path = request.url.path

    response = await call_next(request)

    duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
    logger.info(
        "HTTP request",
        extra={
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else None,
        },
    )
    return response


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"X-Content-Type-Options": "nosniff"},
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(agents_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(execution_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["root"])
async def root():
    return {
        "name": "Multi-Agent Orchestrator",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Liveness probe – returns 200 if the service is up.
    Used by Docker healthchecks and orchestrators.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "connected",
            "task_queue": "running" if task_queue._running else "stopped",
        },
    }


@app.get("/ready", tags=["health"])
async def readiness_check():
    """
    Readiness probe – checks that dependent services are ready.
    """
    checks = {
        "database": True,
        "task_queue": task_queue._running,
    }
    all_ready = all(checks.values())
    return JSONResponse(
        status_code=200 if all_ready else 503,
        content={
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "development") == "development",
    )
