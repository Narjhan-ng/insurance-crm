"""
FastAPI main application - Insurance CRM
Event-driven architecture with async processing
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.database import engine, Base
from app.core.redis_client import get_redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Startup: Initialize database tables, test Redis connection
    Shutdown: Close connections gracefully
    """
    logger.info("🚀 Starting Insurance CRM Application...")

    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    # Test Redis connection
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.warning("⚠️  Event system will not work without Redis")

    logger.info("✅ Application startup complete")

    yield  # Application runs here

    # Shutdown
    logger.info("🛑 Shutting down Insurance CRM Application...")
    logger.info("✅ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Insurance CRM API",
    description="""
    Event-driven Insurance CRM with AI-powered features.

    ## Features
    * **Prospect Management** - Track leads and customers
    * **Eligibility Checking** - Multi-provider comparison
    * **Quote Generation** - AI-powered recommendations
    * **Policy Management** - Complete lifecycle handling
    * **Commission Tracking** - Automated calculations

    ## Architecture
    Built with event-driven architecture for scalability:
    - Events published to Redis Streams
    - ARQ workers process events asynchronously
    - Complete audit trail in Event Store
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "healthy",
        "service": "Insurance CRM API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check endpoint.
    Verifies database and Redis connectivity.
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
    }

    # Check database
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


# Import and include API routers
from app.api.v1 import auth, dashboard, prospects, quotes, policies, eligibility

# Authentication router (no authentication required for login/register)
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

# Dashboard router (requires authentication)
app.include_router(
    dashboard.router,
    prefix="/api/v1/dashboard",
    tags=["Dashboard"]
)

app.include_router(
    prospects.router,
    prefix="/api/v1/prospects",
    tags=["Prospects"]
)

# Eligibility check router
app.include_router(
    eligibility.router,
    prefix="/api/v1/eligibility",
    tags=["Eligibility"]
)

app.include_router(
    quotes.router,
    prefix="/api/v1/quotes",
    tags=["Quotes"]
)

app.include_router(
    policies.router,
    prefix="/api/v1/policies",
    tags=["Policies"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
