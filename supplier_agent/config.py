import os
import logging
from functools import lru_cache
from typing import Dict, Any

@lru_cache
def get_config() -> Dict[str, Any]:
    """Get configuration from environment variables with defaults."""
    return {
        "DB_URL": os.getenv("NEON_DB_URL"),
        "PORT": int(os.getenv("PORT", "8080")),
        "CACHE_TTL": int(os.getenv("CACHE_TTL_SECONDS", "60")),
        "SUPPLIER_API_KEY": os.getenv("SUPPLIER_API_KEY", "dev-key"),
    }

def setup_logging() -> None:
    """Setup structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("supplier_agent.log")
        ]
    )

# Initialize logging when module is imported
setup_logging()