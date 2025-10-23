import os
from functools import lru_cache
from typing import Dict, Any

@lru_cache
def get_config() -> Dict[str, Any]:
    """Get configuration from environment variables with defaults."""
    return {
        "SUPPLIER_BASE_URL": os.getenv("SUPPLIER_BASE_URL", "http://localhost:8080"),
        "RETAILER_DB_URL": os.getenv("RETAILER_DB_URL", "sqlite:///retailer.db"),
        "FETCH_INTERVAL_MINUTES": int(os.getenv("FETCH_INTERVAL_MINUTES", "15")),
        "PORT": int(os.getenv("PORT", "8082")),
    }