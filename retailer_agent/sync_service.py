import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from .config import get_config
from .acp_discovery import discover_supplier, get_supplier_schema, fetch_feed
from .retailer_db import retailer_db
from .a2a_client import fetch_supplier_catalog

logger = logging.getLogger(__name__)

class SyncService:
    """Service for syncing data from supplier to retailer database."""

    def __init__(self):
        self.config = get_config()
        self.last_sync_time = None
        self.last_record_count = 0
        self.supplier_connected = False

    async def run_sync(self) -> None:
        """Run the complete sync process."""
        try:
            base_url = self.config["SUPPLIER_BASE_URL"]

            # Step 1: Discover supplier via ACP discovery
            discovery = discover_supplier(base_url)
            self.supplier_connected = True

            # Extract A2A endpoint from discovery
            a2a_endpoint = discovery.get("a2a_endpoint", "http://localhost:8090")
            logger.info(f"Using A2A endpoint: {a2a_endpoint}")

            # Step 2: Get schema from ACP endpoint
            schema = get_supplier_schema(base_url)

            # Step 3: Initialize local DB with schema
            retailer_db.init_db(schema)

            # Step 4: Use A2A skill for catalog data
            total_records = 0
            try:
                # Use A2A FetchCatalog skill with retry logic
                records = await self._fetch_catalog_with_retry(a2a_endpoint)
                if records:  # If A2A returned data
                    # Validate ACP data format
                    self._validate_acp_data(records)
                    # Extract attributes from ACP records for database insertion
                    product_data = [record["attributes"] for record in records]
                    # Records are ACP-compliant, insert into products table
                    retailer_db.upsert_data("products", product_data)
                    total_records += len(records)
                    logger.info(f"A2A sync successful: {len(records)} records")
                else:
                    # No fallback - A2A must work
                    logger.error("A2A FetchCatalog returned no data - cannot proceed without catalog data")
                    raise RuntimeError("Supplier A2A skill returned zero records")
            except Exception as e:
                logger.error(f"A2A sync failed: {e}")
                raise

            self.last_sync_time = datetime.now()
            self.last_record_count = total_records
            logger.info(f"Sync completed successfully. Total records: {total_records}")

        except Exception as e:
            self.supplier_connected = False
            logger.error(f"Sync failed: {e}")
            raise

    async def start_periodic_sync(self) -> None:
        """Start periodic syncing based on config interval."""
        interval_minutes = self.config["FETCH_INTERVAL_MINUTES"]
        interval_seconds = interval_minutes * 60

        while True:
            await self.run_sync()
            await asyncio.sleep(interval_seconds)

    async def _fetch_catalog_with_retry(self, a2a_endpoint: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Fetch catalog data with retry logic."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                logger.info(f"A2A FetchCatalog attempt {attempt + 1}/{max_retries} to {a2a_endpoint}")
                records = await fetch_supplier_catalog(a2a_endpoint, 1)  # Single attempt per call

                if records and len(records) > 0:
                    logger.info(f"A2A FetchCatalog successful: {len(records)} records on attempt {attempt + 1}")
                    return records
                else:
                    logger.warning(f"A2A FetchCatalog returned empty records (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Brief pause before retry
                        continue
                    else:
                        logger.error("A2A FetchCatalog returned empty records after all retries")
                        return []

            except Exception as e:
                last_exception = e
                logger.error(f"A2A FetchCatalog failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Longer pause before retry for network issues
                    continue

        # All retries exhausted
        if last_exception:
            raise last_exception
        else:
            # Return empty list if all attempts returned empty data
            return []

    def _validate_acp_data(self, records: List[Dict[str, Any]]) -> None:
        """Validate that records conform to ACP format."""
        if not records:
            raise ValueError("No records to validate")

        required_fields = ["id", "type", "attributes"]
        required_attributes = ["price"]

        for i, record in enumerate(records):
            # Check required top-level fields
            for field in required_fields:
                if field not in record:
                    raise ValueError(f"Record {i} missing required field '{field}'")

            # Check that id is a string
            if not isinstance(record["id"], str):
                raise ValueError(f"Record {i} id must be a string, got {type(record['id'])}")

            # Check that type is a string
            if not isinstance(record["type"], str):
                raise ValueError(f"Record {i} type must be a string, got {type(record['type'])}")

            # Check that attributes is a dict
            if not isinstance(record["attributes"], dict):
                raise ValueError(f"Record {i} attributes must be a dict, got {type(record['attributes'])}")

            # Check required attributes
            for attr in required_attributes:
                if attr not in record["attributes"]:
                    raise ValueError(f"Record {i} missing required attribute '{attr}'")

        logger.info(f"ACP validation successful: {len(records)} records validated")

    def get_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "last_record_count": self.last_record_count,
            "supplier_connected": self.supplier_connected,
            "next_sync_in_minutes": self.config["FETCH_INTERVAL_MINUTES"]
        }

# Global sync service instance
sync_service = SyncService()