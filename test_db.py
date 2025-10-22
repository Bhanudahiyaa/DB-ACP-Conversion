#!/usr/bin/env python3
"""
Test script to verify database setup and population
"""

import os
from supplier_db import main as setup_db, show_sample_products, execute_query

def test_database():
    print("🧪 Testing database setup...")
    
    # Check if NEON_DB_URL is set
    if not os.environ.get("NEON_DB_URL"):
        print("❌ NEON_DB_URL environment variable not set")
        print("Please set it with: export NEON_DB_URL='your_neon_connection_string'")
        return False
    
    try:
        # Run the setup
        setup_db()
        
        # Test that products were inserted
        count = execute_query("SELECT COUNT(*) FROM products;", fetch=True)
        if count and count[0][0] > 0:
            print(f"✅ Database populated with {count[0][0]} products")
            show_sample_products(5)
            return True
        else:
            print("❌ No products found in database")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_database()
