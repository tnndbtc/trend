"""
FastAPI main application for the Trend Intelligence Platform API.

This module initializes the FastAPI app, configures middleware, error handlers,
and includes all API routers.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import __version__
from api.schemas.common import ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Application state
class AppState:
    """Application state container."""

    def __init__(self):
        self.db_pool = None
        self.redis_cache = None
        self.vector_repo = None
        self.plugin_manager = None
        self.started_at: datetime = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Handles initialization and cleanup of database connections,
    caches, and other resources.
    """
    # Startup
    logger.info("🚀 Starting Trend Intelligence Platform API...")
    app_state.started_at = datetime.utcnow()

    try:
        # Initialize database connection pool
        from trend_agent.storage.postgres import PostgreSQLConnectionPool

        app_state.db_pool = PostgreSQLConnectionPool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5433")),  # Updated to match Docker config
            database=os.getenv("POSTGRES_DB", "trends"),
            user=os.getenv("POSTGRES_USER", "trend_user"),
            password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
            min_size=5,
            max_size=20,
        )
        await app_state.db_pool.connect()
        logger.info("✅ Database connection pool initialized")

    except Exception as e:
        logger.warning(f"⚠️  Database connection failed: {e}")
        logger.info("API will start but database-dependent endpoints may fail")

    try:
        # Initialize Redis cache
        from trend_agent.storage.redis import RedisCacheRepository

        app_state.redis_cache = RedisCacheRepository(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6380")),  # Updated to match Docker config
            password=os.getenv("REDIS_PASSWORD", None),
            default_ttl=3600,
        )
        await app_state.redis_cache.connect()
        logger.info("✅ Redis cache connected")

    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")
        logger.info("API will continue without caching")

    try:
        # Initialize Qdrant vector repository
        from trend_agent.storage.qdrant import QdrantVectorRepository

        app_state.vector_repo = QdrantVectorRepository(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            collection_name="trend_embeddings",
            vector_size=1536,
        )
        logger.info("✅ Qdrant vector repository initialized")

    except Exception as e:
        logger.warning(f"⚠️  Qdrant connection failed: {e}")
        logger.info("Semantic search features may be unavailable")

    try:
        # Initialize plugin manager
        from trend_agent.ingestion.manager import DefaultPluginManager

        app_state.plugin_manager = DefaultPluginManager()
        await app_state.plugin_manager.load_plugins()
        logger.info(f"✅ Loaded {len(app_state.plugin_manager.get_all_plugins())} collector plugins")

    except Exception as e:
        logger.warning(f"⚠️  Plugin manager initialization failed: {e}")
        logger.info("Plugin management features will be unavailable")

    logger.info("✅ API startup complete")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Trend Intelligence Platform API...")

    if app_state.db_pool:
        try:
            await app_state.db_pool.close()
            logger.info("✅ Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")

    if app_state.redis_cache:
        try:
            await app_state.redis_cache.close()
            logger.info("✅ Redis cache disconnected")
        except Exception as e:
            logger.error(f"Error closing Redis cache: {e}")

    logger.info("✅ API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Trend Intelligence Platform API",
    description="""
    ## AI-Powered Trend Intelligence Platform

    Automatically collects, analyzes, and ranks trending topics from multiple sources
    including Reddit, Hacker News, and various news outlets.

    ### Features

    - **Multi-Source Collection**: Aggregates data from 9+ sources
    - **Smart Deduplication**: Removes duplicates using semantic similarity
    - **Intelligent Clustering**: Groups related content using HDBSCAN
    - **AI-Powered Analysis**: Generates summaries and insights with LLMs
    - **Multi-Language Support**: Detects and processes 55+ languages
    - **Real-Time Updates**: WebSocket support for live trend notifications
    - **Semantic Search**: Vector similarity search across all content

    ### Authentication

    Most endpoints require an API key passed via the `X-API-Key` header.
    Contact your administrator for API key access.
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent error response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc.detail),
            code=f"HTTP_{exc.status_code}",
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc),
            code="VALIDATION_ERROR",
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred",
            code="INTERNAL_ERROR",
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    API root endpoint providing basic information.

    Returns information about the API including version, status, and available endpoints.
    """
    return {
        "name": "Trend Intelligence Platform API",
        "version": __version__,
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "trends": "/api/v1/trends",
            "topics": "/api/v1/topics",
            "search": "/api/v1/search",
            "health": "/api/v1/health",
            "admin": "/api/v1/admin",
            "websocket": "/ws",
            "graphql": "/graphql",
        },
    }


# Include routers
# Import routers here to avoid circular imports
try:
    from api.routers import health
    app.include_router(health.router, prefix="/api/v1")
except ImportError as e:
    logger.warning(f"Health router not available: {e}")

try:
    from api.routers import trends
    app.include_router(trends.router, prefix="/api/v1")
except ImportError as e:
    logger.warning(f"Trends router not available: {e}")

try:
    from api.routers import topics
    app.include_router(topics.router, prefix="/api/v1")
except ImportError as e:
    logger.warning(f"Topics router not available: {e}")

try:
    from api.routers import search
    app.include_router(search.router, prefix="/api/v1")
except ImportError as e:
    logger.warning(f"Search router not available: {e}")

try:
    from api.routers import admin
    app.include_router(admin.router, prefix="/api/v1")
except ImportError as e:
    logger.warning(f"Admin router not available: {e}")

try:
    from api.routers import ws
    app.include_router(ws.router)
except ImportError as e:
    logger.warning(f"WebSocket router not available: {e}")


# Make app_state accessible to routers
def get_app_state() -> AppState:
    """Dependency to get application state."""
    return app_state


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
