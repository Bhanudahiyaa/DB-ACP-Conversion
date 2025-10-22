#!/usr/bin/env python3
"""
Run ACP Supplier Agent

This script initializes the database and starts the new ACP-compliant Supplier Agent.
"""

import os
import sys
import uvicorn
from supplier_agent.main import main as supplier_agent_main
from supplier_agent.legacy_supplier_db import main as setup_db

def main():
    """Main entry point for running the Supplier Agent."""
    print("🚀 Starting Supplier Agent...")
    
    # Check for required environment variable
    if not os.environ.get("NEON_DB_URL"):
        print("❌ Error: NEON_DB_URL environment variable is required")
        print("Please set it with: export NEON_DB_URL='your_neon_connection_string'")
        return 1
    
    try:
        print("📊 Initializing supplier database...")
        setup_db()
        print("✅ Database initialized successfully")
        
        print("🌐 Starting ACP Agent...")
        return supplier_agent_main()
        
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal, shutting down...")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())