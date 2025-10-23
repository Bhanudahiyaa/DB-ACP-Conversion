#!/usr/bin/env python3
"""
test_retailer_supplier.py
Automated test: Retailer Agent ↔ Supplier Agent ACP communication
"""

import time
import logging
import sys
import os

# Add retailer_agent to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from retailer_agent.acp_discovery import discover_supplier, get_supplier_schema, fetch_feed
from retailer_agent.retailer_db import retailer_db

# Setup logging
logging.basicConfig(
    filename="logs/retailer_sync_test.log",
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s"
)

SUPPLIER_URL = "http://localhost:8080"  # Adjust if needed

def main():
    print("=== Retailer ↔ Supplier ACP Test ===")
    summary = {}

    # 1️⃣ Discovery
    try:
        discover_info = discover_supplier(SUPPLIER_URL)
        logging.info(f"Discovery success: {discover_info}")
        print("Discovery: SUCCESS")
        summary["discovery"] = "SUCCESS"
    except Exception as e:
        logging.error(f"Discovery failed: {e}")
        print(f"Discovery: FAIL ({e})")
        summary["discovery"] = f"FAIL ({e})"
        return

    # 2️⃣ Fetch Schema
    try:
        schema = get_supplier_schema(SUPPLIER_URL)
        logging.info(f"Schema fetched: {list(schema.keys())}")
        print(f"Schema fetch: SUCCESS ({len(schema)} tables)")
        summary["schema_fetch"] = f"SUCCESS ({len(schema)} tables)"
    except Exception as e:
        logging.error(f"Schema fetch failed: {e}")
        print(f"Schema fetch: FAIL ({e})")
        summary["schema_fetch"] = f"FAIL ({e})"
        return

    # 3️⃣ Fetch product feed
    try:
        products = fetch_feed(SUPPLIER_URL, "products")
        logging.info(f"Products feed fetched: {len(products)} records")
        print(f"Products feed fetch: SUCCESS ({len(products)} records)")
        summary["products_feed"] = f"SUCCESS ({len(products)} records)"
    except Exception as e:
        logging.error(f"Products feed fetch failed: {e}")
        print(f"Products feed fetch: FAIL ({e})")
        summary["products_feed"] = f"FAIL ({e})"
        return

    # 4️⃣ Insert into Retailer DB
    try:
        retailer_db.upsert_data("products", products)
        rows_count = retailer_db.get_record_count("products")
        logging.info(f"Inserted records into Retailer DB, total: {rows_count}")
        print(f"DB insert: SUCCESS ({rows_count} total records)")
        summary["db_insert"] = f"SUCCESS ({rows_count} total records)"
    except Exception as e:
        logging.error(f"DB insert failed: {e}")
        print(f"DB insert: FAIL ({e})")
        summary["db_insert"] = f"FAIL ({e})"

    # 5️⃣ Summary
    print("\n=== TEST SUMMARY ===")
    for key, val in summary.items():
        print(f"{key}: {val}")

    print("\nCheck logs at logs/retailer_sync_test.log for full details.")

if __name__ == "__main__":
    main()