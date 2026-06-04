"""
Store Intelligence System - FastAPI Backend
Run from store-intelligence-system/backend/:
    uvicorn main:app --reload
"""
import asyncio
import logging
import sys
import os

# Ensure backend/ is on path, and parent dir for streaming/
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)
for _p in [_BACKEND_DIR, _ROOT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from routers import stores, cameras, analytics, alerts, events, dashboard
from middleware.logging import RequestLoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def _try_init_db():
    try:
        from database.connection import init_db
        await init_db()
    except Exception as e:
        logger.warning(f"⚠️  MongoDB not available (skipping): {e}")


async def _try_start_consumer():
    try:
        from streaming.consumer import start_consumer
        await start_consumer()
    except Exception as e:
        logger.warning(f"⚠️  Kafka consumer not started (skipping): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Store Intelligence System...")
    await _try_init_db()
    consumer_task = asyncio.create_task(_try_start_consumer())
    logger.info("✅ API ready  →  http://127.0.0.1:8000/docs")
    yield
    logger.info("🛑 Shutting down...")
    consumer_task.cancel()
    try:
        from database.connection import close_db
        await close_db()
    except Exception:
        pass


app = FastAPI(
    title="Purplle Store Intelligence System",
    description="""
## AI-Powered Retail Store Intelligence Platform

### Features
- 🎥 Real-time CCTV analysis via Computer Vision pipeline
- 📊 Live footfall & occupancy tracking
- 🛒 POS sales correlation & conversion analytics
- 🚨 ML-based anomaly detection & alerts
- 🔥 Customer heatmaps & zone intelligence
- 👥 Staff presence & activity monitoring
- 📡 Event streaming via Apache Kafka

### Stores
- **Store 1**: Andheri West, Mumbai (5 cameras)
- **Store 2**: Koramangala, Bangalore (5 cameras)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

app.include_router(stores.router,    prefix="/stores",    tags=["Stores"])
app.include_router(cameras.router,   prefix="/cameras",   tags=["Cameras"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(alerts.router,    prefix="/alerts",    tags=["Alerts"])
app.include_router(events.router,    prefix="/events",    tags=["Events"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


@app.get("/", tags=["Health"])
async def root():
    return {"service": "Purplle Store Intelligence System", "version": "1.0.0", "status": "operational", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "services": {"api": "up", "database": "up", "kafka": "up", "cv_pipeline": "up"}}
