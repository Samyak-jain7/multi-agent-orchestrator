from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from core.database import init_db, close_db
from agents.queue import task_queue
from api import agents_router, workflows_router, tasks_router, execution_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Multi-Agent Orchestrator...")

    await init_db()
    logger.info("Database initialized")

    await task_queue.start()
    logger.info("Task queue started")

    yield

    logger.info("Shutting down...")
    await task_queue.stop()
    await close_db()
    logger.info("Shutdown complete")


import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from core.database import init_db, close_db
from agents.queue import task_queue
from api import agents_router, workflows_router, tasks_router, execution_router

# ... (rest of imports)

app = FastAPI(
    title="Multi-Agent Orchestrator",
    description="A platform to visually configure and run multiple AI agents for complex tasks",
    version="1.0.0",
    lifespan=lifespan
)

# Secure CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url] if frontend_url != "*" else ["*"],
    allow_credentials=True if frontend_url != "*" else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API Key Middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    app_api_key = os.getenv("APP_API_KEY")
    if app_api_key:
        api_key = request.headers.get("X-API-Key")
        if api_key != app_api_key:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or missing API Key"}
            )
    
    return await call_next(request)

app.include_router(agents_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(execution_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "Multi-Agent Orchestrator",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
