"""
Main FastAPI application for Project Orchestrator.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database.connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Application starting up...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Application shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI agent that helps non-coders build software projects",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "app": settings.app_name,
        "status": "healthy",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "version": "0.1.0",
    }


# Register API routers
from src.api.projects import router as projects_router
from src.api.documents import router as documents_router
from src.api.websocket import router as websocket_router
from src.api.sse import router as sse_router

app.include_router(projects_router, prefix="/api", tags=["Projects"])
app.include_router(documents_router, prefix="/api", tags=["Documents"])
app.include_router(websocket_router, prefix="/api", tags=["WebSocket"])
app.include_router(sse_router, prefix="/api", tags=["SSE"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
