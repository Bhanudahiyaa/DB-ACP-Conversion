#!/usr/bin/env python3
"""
Run ACP Supplier Feed
"""

import os
import uvicorn
from supplier_feed import app
from supplier_db import main as setup_db

if __name__ == "__main__":
    # Check for required environment variable
    if not os.environ.get("NEON_DB_URL"):
        print("❌ Error: NEON_DB_URL environment variable is required")
        print("Please set it with: export NEON_DB_URL='your_neon_connection_string'")
        exit(1)
    
    print("🚀 Initializing supplier database...")
    setup_db()
    print("✅ Starting ACP feed at http://127.0.0.1:8000/acp/feed")
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
