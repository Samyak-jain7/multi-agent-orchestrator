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


app = FastAPI(
    title="Multi-Agent Orchestrator",
    description="A platform to visually configure and run multiple AI agents for complex tasks",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
