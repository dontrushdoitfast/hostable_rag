import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.router import router as api_router, sync_engine

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting R2R SharePoint Retrieval Service...")
    sync_engine.start_scheduled_sync()
    yield
    logger.info("Shutting down R2R SharePoint Retrieval Service...")


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "mode": settings.CONNECTOR_MODE,
        "uptime_seconds": round(time.time() - start_time, 2),
    }


@app.get("/metrics", status_code=status.HTTP_200_OK, tags=["Metrics"])
async def get_metrics():
    """Service metrics and diagnostic information."""
    return {
        "uptime_seconds": round(time.time() - start_time, 2),
        "sync_stats": sync_engine.sync_stats,
        "connector_mode": settings.CONNECTOR_MODE,
    }
