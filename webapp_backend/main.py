"""
FastAPI application for mini app API
"""
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from routers import houses, users, webhook
from core.config import config
from core.db import db
from kafka_consumer import survey_consumer

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Rubkoff House Selection API",
    description="API for Rubkoff house selection mini app",
    version="1.1.0",
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None
)

# Add CORS middleware
allowed_origins = ["*"] if config.DEBUG else [
    config.MINI_APP_URL,
    config.API_BASE_URL,
    "https://web.telegram.org",
    "https://t.me"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Mount static files for frontend (for local testing)
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")
    logger.info(f"📁 Frontend mounted at /frontend from {frontend_path}")

# Include routers
app.include_router(houses.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(webhook.router)  # No prefix for webhook


@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks"""
    try:
        await db.init_db()
        logger.info("API server started successfully")
        
        # Start Kafka consumer
        if config.KAFKA_ENABLED:
            logger.info("Starting Kafka consumer...")
            await survey_consumer.start()
            logger.info("Kafka consumer started successfully")
        else:
            logger.info("Kafka consumer disabled")
        
        logger.info("API running in PRODUCTION MODE")
            
    except Exception as e:
        logger.error(f"Failed to initialize API server: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        if config.KAFKA_ENABLED:
            logger.info("Stopping Kafka consumer...")
            await survey_consumer.stop()
            logger.info("Kafka consumer stopped")
    except Exception as e:
        logger.error(f"Error stopping Kafka consumer: {e}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Rubkoff House Selection API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        db_healthy = await db.check_connection()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint"""
    try:
        # Check database connection
        db_healthy = await db.check_connection()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "version": "1.1.0"
        }
    except Exception as e:
        logger.error(f"API Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/info")
async def server_info():
    """Server information and available endpoints"""
    return {
        "server": "Rubkoff House Selection API",
        "version": "1.1.0",
        "available_endpoints": {
            "root": "/",
            "health": ["/health", "/api/health"],
            "frontend": "/frontend/",
            "api": {
                "houses": "/api/houses",
                "users": "/api/users",
                "docs": "/docs" if config.DEBUG else "disabled"
            },
            "webhook": {
                "telegram": "/webhook",
                "webhook_info": "/webhook (GET)",
                "webhook_health": "/webhook/health"
            }
        },
        "external_urls": {
            "mini_app_url": config.effective_mini_app_url,
            "api_base_url": config.effective_api_base_url
        }
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    ) 