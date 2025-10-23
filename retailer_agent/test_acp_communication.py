#!/usr/bin/env python3
"""
Automated test script for Retailer Agent ↔ Supplier Agent ACP Communication
"""
import sys
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import retailer agent modules
sys.path.append('..')
from config import get_config
from acp_discovery import discover_supplier, get_supplier_schema, fetch_feed
from retailer_db import retailer_db
from common.log_utils import ActivityLogger

class ACPCommunicationTester:
    """Automated tester for ACP communication between Retailer and Supplier agents."""

    def __init__(self):
        self.config = get_config()
        self.logger = ActivityLogger("ACP_Tester")
        self.supplier_url = self.config["SUPPLIER_BASE_URL"]
        self.results = {
            "discovery": {"status": "PENDING", "details": None},
            "schema_fetch": {"status": "PENDING", "details": None},
            "products_feed_fetch": {"status": "PENDING", "details": None},
            "db_insert": {"status": "PENDING", "details": None},
            "overall": {"status": "PENDING", "issues": []}
        }

    def log_test_result(self, test_name: str, status: str, details: Any = None, error: str = None):
        """Log test result and update results dict."""
        self.results[test_name]["status"] = status
        self.results[test_name]["details"] = details
        if error:
            self.results[test_name]["error"] = error
            self.results["overall"]["issues"].append(f"{test_name}: {error}")

        print(f"[{datetime.now().isoformat()}] {test_name.upper()}: {status}")
        if details:
            print(f"  Details: {details}")
        if error:
            print(f"  Error: {error}")

    def test_discovery(self) -> bool:
        """Test supplier discovery via .well-known/acp."""
        try:
            timer = self.logger.log_request("/.well-known/acp", "GET", "discovery_test")
            discovery = discover_supplier(self.supplier_url)
            timer.log_completion(record_count=0, status="OK", target="supplier")

            # Validate discovery response
            required_fields = ["acp_version", "agent", "resources_endpoint", "feed_endpoint"]
            missing_fields = [field for field in required_fields if field not in discovery]

            if missing_fields:
                self.log_test_result("discovery", "FAIL",
                                   f"Missing required fields: {missing_fields}")
                return False

            self.log_test_result("discovery", "SUCCESS", discovery)
            return True

        except Exception as e:
            self.log_test_result("discovery", "FAIL", error=str(e))
            return False

    def test_schema_fetch(self) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """Test schema fetching and validation."""
        try:
            timer = self.logger.log_request("/acp/schema", "GET", "schema_test")
            schema = get_supplier_schema(self.supplier_url)
            timer.log_completion(record_count=len(schema), status="OK", target="supplier")

            # Validate schema structure
            if not isinstance(schema, dict):
                self.log_test_result("schema_fetch", "FAIL",
                                   "Schema must be a dictionary")
                return None

            if not schema:
                self.log_test_result("schema_fetch", "FAIL",
                                   "Schema is empty")
                return None

            # Check if products table exists
            if "products" not in schema:
                self.log_test_result("schema_fetch", "FAIL",
                                   "Products table not found in schema")
                return None

            # Validate products schema structure
            products_schema = schema["products"]
            if not isinstance(products_schema, list):
                self.log_test_result("schema_fetch", "FAIL",
                                   "Products schema must be a list of columns")
                return None

            # Check for required columns
            column_names = [col.get("column_name") for col in products_schema if col.get("column_name")]
            required_columns = ["name", "price"]  # At minimum
            missing_columns = [col for col in required_columns if col not in column_names]

            if missing_columns:
                self.log_test_result("schema_fetch", "WARNING",
                                   f"Missing recommended columns: {missing_columns}",
                                   f"Schema has {len(products_schema)} columns: {column_names[:5]}...")

            self.log_test_result("schema_fetch", "SUCCESS",
                               f"Found {len(schema)} tables, products has {len(products_schema)} columns")
            return schema

        except Exception as e:
            self.log_test_result("schema_fetch", "FAIL", error=str(e))
            return None

    def test_products_feed_fetch(self, schema: Dict[str, List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Test products feed fetching and validation."""
        try:
            timer = self.logger.log_request("/acp/feed/products", "GET", "feed_test")
            records = fetch_feed(self.supplier_url, "products")
            timer.log_completion(record_count=len(records), status="OK", target="supplier")

            if not isinstance(records, list):
                self.log_test_result("products_feed_fetch", "FAIL",
                                   "Feed must return a list of records")
                return None

            if not records:
                self.log_test_result("products_feed_fetch", "WARNING",
                                   "Feed returned empty results")
                return []

            # Validate record structure
            sample_record = records[0]
            if not isinstance(sample_record, dict):
                self.log_test_result("products_feed_fetch", "FAIL",
                                   "Each record must be a dictionary")
                return None

            # Check for pricing information
            price_fields = ["price", "wholesale_price", "agent_commission_rate"]
            found_price_fields = [field for field in price_fields if field in sample_record]

            if not found_price_fields:
                self.log_test_result("products_feed_fetch", "WARNING",
                                   "No pricing fields found in records")
            else:
                self.log_test_result("products_feed_fetch", "SUCCESS",
                                   f"Fetched {len(records)} products with pricing: {found_price_fields}")
                return records

            # Even without pricing, consider it success if we got data
            self.log_test_result("products_feed_fetch", "SUCCESS",
                               f"Fetched {len(records)} products")
            return records

        except Exception as e:
            self.log_test_result("products_feed_fetch", "FAIL", error=str(e))
            return None

    def test_db_insert(self, records: List[Dict[str, Any]]) -> bool:
        """Test database insertion of fetched records."""
        try:
            if not records:
                self.log_test_result("db_insert", "SKIP", "No records to insert")
                return True

            # Initialize DB with schema (this should create tables)
            # Note: We need schema for table creation, but we'll assume it's already done
            retailer_db.upsert_data("products", records)

            # Verify insertion
            count_after = retailer_db.get_record_count("products")

            if count_after >= len(records):
                self.log_test_result("db_insert", "SUCCESS",
                                   f"Inserted {len(records)} records, total in DB: {count_after}")
                return True
            else:
                self.log_test_result("db_insert", "FAIL",
                                   f"Expected at least {len(records)} records, found {count_after}")
                return False

        except Exception as e:
            self.log_test_result("db_insert", "FAIL", error=str(e))
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all ACP communication tests."""
        print("=" * 60)
        print("🧪 ACP COMMUNICATION TEST SUITE")
        print("=" * 60)

        # Test 1: Discovery
        if not self.test_discovery():
            self.results["overall"]["status"] = "FAIL"
            return self.results

        # Test 2: Schema Fetch
        schema = self.test_schema_fetch()
        if schema is None:
            self.results["overall"]["status"] = "FAIL"
            return self.results

        # Test 3: Products Feed Fetch
        records = self.test_products_feed_fetch(schema)
        if records is None:
            self.results["overall"]["status"] = "FAIL"
            return self.results

        # Test 4: DB Insert
        if not self.test_db_insert(records):
            self.results["overall"]["status"] = "FAIL"
            return self.results

        # Overall result
        if self.results["overall"]["issues"]:
            self.results["overall"]["status"] = "WARNING"
        else:
            self.results["overall"]["status"] = "SUCCESS"

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        for test, result in self.results.items():
            if test != "overall":
                status = result["status"]
                details = result.get("details", "")
                print(f"{test.upper():20} {status:8} {str(details)[:50]}")

        print(f"\nOVERALL: {self.results['overall']['status']}")
        if self.results["overall"]["issues"]:
            print("Issues found:")
            for issue in self.results["overall"]["issues"]:
                print(f"  - {issue}")

        return self.results

def main():
    """Main test runner."""
    tester = ACPCommunicationTester()
    results = tester.run_all_tests()

    # Exit with appropriate code
    if results["overall"]["status"] == "SUCCESS":
        print("\n✅ All tests passed!")
        sys.exit(0)
    elif results["overall"]["status"] == "WARNING":
        print("\n⚠️  Tests passed with warnings")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()