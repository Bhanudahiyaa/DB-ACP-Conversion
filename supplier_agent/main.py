#!/usr/bin/env python3
"""
Supplier Agent Main Entry Point

This is the main entry point for the ACP-compliant Supplier Agent.
It initializes the database and starts the FastAPI server.
"""

import uvicorn
import logging
from .acp_server import app
from .config import get_config
from .supplier_db import db_manager

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Supplier Agent."""
    try:
        # Load configuration
        cfg = get_config()
        
        # Validate required configuration
        if not cfg["DB_URL"]:
            logger.error("NEON_DB_URL environment variable is required")
            return 1
        
        logger.info("🚀 Starting Supplier ACP Agent...")
        logger.info(f"📊 Database URL: {cfg['DB_URL'][:30]}...")
        logger.info(f"🌐 Server port: {cfg['PORT']}")
        logger.info(f"⏱️  Cache TTL: {cfg['CACHE_TTL']} seconds")
        
        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=cfg["PORT"],
            log_level="info"
        )
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal, shutting down...")
        return 0
    except Exception as e:
        logger.error(f"❌ Failed to start Supplier Agent: {e}")
        return 1

if __name__ == "__main__":
    exit(main())