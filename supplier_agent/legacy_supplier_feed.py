"""
Legacy Supplier Feed Compatibility Shim

This module provides backward compatibility for the original supplier_feed.py
by importing and re-exporting functions from the new ACP implementation.
"""

import logging
from fastapi import FastAPI
from .acp_server import app as acp_app

logger = logging.getLogger(__name__)

# Create a legacy FastAPI app that wraps the new ACP endpoints
legacy_app = FastAPI(title="Supplier ACP Feed (Legacy)")

# Legacy endpoint for backward compatibility
@legacy_app.get("/acp/feed")
async def get_legacy_feed():
    """Legacy feed endpoint - redirects to new ACP implementation."""
    logger.warning("Legacy /acp/feed endpoint called. Use /acp/feed/{resource} instead.")
    
    # For backward compatibility, return products feed
    try:
        from .acp_mapper import convert_table_to_acp
        
        # Get products data in ACP format
        result = await convert_table_to_acp("products", limit=100)
        
        if "error" in result:
            return {"error": result["error"]}
        
        # Transform to legacy format if needed
        return {
            "supplier_id": "supplier_001",
            "supplier_name": "ACME Supplier Corp",
            "feed_version": "1.0",
            "feed_type": "agent_commerce_protocol",
            "last_updated": "2024-10-22T22:17:59Z",
            "total_products": len(result["data"]),
            "agent_info": {
                "commission_structure": "tiered",
                "payment_frequency": "monthly",
                "minimum_payout": 100.0,
                "currency": "USD"
            },
            "products": result["data"]
        }
        
    except Exception as e:
        logger.error(f"Legacy feed error: {e}")
        return {"error": f"Database query failed: {e}"}

# Export the legacy app
__all__ = ['legacy_app', 'get_legacy_feed']

# For direct import compatibility
app = legacy_app