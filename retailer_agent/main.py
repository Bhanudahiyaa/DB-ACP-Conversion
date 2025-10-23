from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
from .config import get_config
from .sync_service import sync_service
from .logging_middleware import RetailerLoggingMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    config = get_config()
    logger.info(f"Starting Retailer Agent on port {config['PORT']}")

    # Run initial sync
    try:
        await sync_service.run_sync()
        logger.info("Initial sync completed")
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")

    # Start periodic sync
    sync_task = asyncio.create_task(sync_service.start_periodic_sync())
    logger.info("Periodic sync started")

    yield

    # Shutdown
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    logger.info("Retailer Agent shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Retailer Agent",
    description="ACP Network Retailer Agent for syncing supplier data",
    version="1.0.0",
    lifespan=lifespan
)

# Add logging middleware
app.add_middleware(RetailerLoggingMiddleware)

@app.get("/status")
async def get_status():
    """Get current sync status."""
    return sync_service.get_status()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        "retailer_agent.main:app",
        host="0.0.0.0",
        port=config["PORT"],
        reload=True
    )