"""
retailer_agent/a2a_client.py
Uses HTTP to query the Supplier Agent for catalog/pricing info.
"""

import httpx
import logging
from common.log_utils import ActivityLogger
import asyncio

logger = logging.getLogger("retailer_agent.a2a")

SUPPLIER_A2A_URL = "http://localhost:8090"  # Supplier's A2A endpoint

# Initialize activity logger for A2A events
activity_logger = ActivityLogger("Retailer", "logs/agent_activity.log")

async def fetch_supplier_catalog(a2a_endpoint: str, max_retries: int = 3):
    """
    Invokes Supplier's FetchCatalog skill and returns ACP-style data.
    Retries up to max_retries times if empty data is returned.
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            # Log A2A attempt
            timer = activity_logger.log_request("A2A FetchCatalog", "TASK", "Supplier")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{a2a_endpoint}/skill/FetchCatalog")
                response.raise_for_status()
                data = response.json()

            record_count = len(data.get('records', []))
            logger.info(f"[Retailer → Supplier] Task: FetchCatalog | {record_count} records | OK")

            # Check if we got actual data
            if record_count > 0:
                timer.log_completion(record_count=record_count, status="OK", target="Supplier")
                return data["records"]
            else:
                logger.warning(f"A2A FetchCatalog returned empty records (attempt {attempt + 1}/{max_retries})")
                timer.log_completion(record_count=0, status="EMPTY", target="Supplier")

                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                else:
                    # All retries exhausted with empty data
                    logger.error("A2A FetchCatalog returned empty records after all retries")
                    return []

        except Exception as e:
            last_exception = e
            logger.error(f"A2A FetchCatalog failed (attempt {attempt + 1}/{max_retries}): {e}")
            # Log failure
            try:
                timer.log_completion(record_count=0, status="ERROR", target="Supplier")
            except:
                pass

            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # Longer pause before retry for network issues
                continue

    # All retries exhausted
    if last_exception:
        raise last_exception
    else:
        # Return empty list if all attempts returned empty data
        return []