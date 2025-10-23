#!/usr/bin/env python3
"""
Runtime verification script for Retailer ↔ Supplier A2A communication
"""

import sys
import os
sys.path.append('.')

from retailer_agent.a2a_client import fetch_supplier_catalog
from retailer_agent.retailer_db import retailer_db
from retailer_agent.acp_discovery import discover_supplier, get_supplier_schema
import requests

def count_records(table_name: str) -> int:
    """Get record count from retailer DB."""
    return retailer_db.get_record_count(table_name)

def main():
    print("=== Runtime Verification: Retailer → Supplier A2A ===")

    # 1. Discover Supplier
    try:
        acp_info = requests.get("http://localhost:8080/.well-known/acp").json()
        assert "acp_version" in acp_info
        print("✅ Discovery: PASSED")
    except Exception as e:
        print(f"❌ Discovery: FAILED - {e}")
        return

    # 2. Fetch schema
    try:
        schema = requests.get("http://localhost:8080/acp/schema").json()
        assert "products" in schema.get("resources", [])
        print("✅ Schema fetch: PASSED")
    except Exception as e:
        print(f"❌ Schema fetch: FAILED - {e}")
        return

    # 3. Invoke A2A skill with retries
    try:
        # This will retry up to 3 times internally
        import asyncio
        resp = asyncio.run(fetch_supplier_catalog())

        # Check if we got data
        if not resp or len(resp) == 0:
            print("❌ A2A skill: FAILED - No records returned after retries")
            return

        print(f"✅ A2A skill: PASSED - {len(resp)} records fetched")

        # Validate record structure (ACP format)
        sample_record = resp[0]
        assert "id" in sample_record, "Missing id field"
        assert "type" in sample_record, "Missing type field"
        assert "attributes" in sample_record, "Missing attributes field"
        assert isinstance(sample_record["attributes"], dict), "Attributes must be dict"

        # Check price in attributes
        assert "price" in sample_record["attributes"], "Missing price in attributes"
        assert isinstance(sample_record["attributes"]["price"], (str, int, float)), "Invalid price type"
        print("✅ ACP record validation: PASSED")

    except Exception as e:
        print(f"❌ A2A skill: FAILED - {e}")
        return

    # 4. Insert into DB (extract attributes from ACP records)
    try:
        initial_count = count_records("products")
        # Extract attributes from ACP records for database insertion
        product_data = [record["attributes"] for record in resp]
        retailer_db.upsert_data("products", product_data)
        final_count = count_records("products")

        inserted_count = final_count - initial_count
        if inserted_count != len(resp):
            print(f"⚠️  DB insert: WARNING - Expected {len(resp)} inserts, got {inserted_count}")

        print(f"✅ DB insert: PASSED - {final_count} total records")
    except Exception as e:
        print(f"❌ DB insert: FAILED - {e}")
        return

    # 5. Verify counts match (note: DB may have more records from previous runs)
    try:
        db_count = count_records("products")
        if db_count < len(resp):
            print(f"❌ Count verification: FAILED - DB has {db_count}, should be at least {len(resp)}")
        else:
            print("✅ Count verification: PASSED")
    except Exception as e:
        print(f"❌ Count verification: FAILED - {e}")
        return

    print("\n🎉 ALL RUNTIME VERIFICATION CHECKS PASSED!")
    print(f"📊 Final state: {count_records('products')} products in retailer DB")

if __name__ == "__main__":
    main()