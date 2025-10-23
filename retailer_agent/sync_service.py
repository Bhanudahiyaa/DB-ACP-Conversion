import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from .config import get_config
from .acp_discovery import discover_supplier, get_supplier_schema, fetch_feed
from .retailer_db import retailer_db

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

            # Step 1: Discover supplier
            discovery = discover_supplier(base_url)
            self.supplier_connected = True

            # Step 2: Get schema
            schema = get_supplier_schema(base_url)

            # Step 3: Initialize local DB with schema
            retailer_db.init_db(schema)

            # Step 4: Fetch and sync data for each table
            total_records = 0
            for table_name in schema.keys():
                try:
                    records = fetch_feed(base_url, table_name)
                    retailer_db.upsert_data(table_name, records)
                    total_records += len(records)
                except Exception as e:
                    logger.error(f"Failed to sync table {table_name}: {e}")

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