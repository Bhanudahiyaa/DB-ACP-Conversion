#!/usr/bin/env python3
"""
Run script for the Retailer Agent.
"""
import uvicorn
from retailer_agent.config import get_config

if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "retailer_agent.main:app",
        host="0.0.0.0",
        port=config["PORT"],
        reload=True
    )