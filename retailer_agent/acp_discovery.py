import requests
import logging
import time
from typing import Dict, Any, List
from .config import get_config

logger = logging.getLogger(__name__)

def discover_supplier(base_url: str) -> Dict[str, Any]:
    """Discover supplier agent via .well-known/acp endpoint."""
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/.well-known/acp", timeout=10)
        response.raise_for_status()
        data = response.json()
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[Retailer → Supplier] /.well-known/acp | 1 records | OK | {latency_ms}ms")
        logger.info(f"Discovered supplier at {base_url}: {data}")
        return data
    except requests.RequestException as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[Retailer → Supplier] /.well-known/acp | 0 records | ERROR | {latency_ms}ms")
        logger.error(f"Failed to discover supplier at {base_url}: {e}")
        raise

def get_supplier_schema(base_url: str) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch supplier schema from /acp/schema endpoint."""
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/acp/schema", timeout=10)
        response.raise_for_status()
        schema_response = response.json()
        resources = schema_response.get("resources", [])
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[Retailer → Supplier] /acp/schema | {len(resources)} records | OK | {latency_ms}ms")

        # Fetch detailed schema for each resource
        detailed_schema = {}
        for resource in resources:
            resource_start = time.time()
            resource_response = requests.get(f"{base_url}/acp/schema/{resource}", timeout=10)
            resource_response.raise_for_status()
            resource_data = resource_response.json()
            resource_latency = int((time.time() - resource_start) * 1000)
            logger.info(f"[Retailer → Supplier] /acp/schema/{resource} | 1 records | OK | {resource_latency}ms")
            # Extract column schema from the JSON schema properties
            properties = resource_data.get("schema", {}).get("properties", {})
            columns = []
            for col_name, col_info in properties.items():
                columns.append({
                    "column_name": col_name,
                    "data_type": col_info.get("type", "string"),
                    "is_nullable": "YES" if col_name not in resource_data.get("schema", {}).get("required", []) else "NO"
                })
            detailed_schema[resource] = columns

        logger.info(f"Fetched schema with {len(detailed_schema)} tables from {base_url}")
        return detailed_schema
    except requests.RequestException as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[Retailer → Supplier] /acp/schema | 0 records | ERROR | {latency_ms}ms")
        logger.error(f"Failed to fetch schema from {base_url}: {e}")
        raise

def fetch_feed(base_url: str, feed_name: str) -> List[Dict[str, Any]]:
    """Fetch data from /acp/feed/{feed_name} endpoint."""
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/acp/feed/{feed_name}", timeout=30)
        response.raise_for_status()
        feed_response = response.json()
        data = feed_response.get("data", [])
        # Extract attributes from ACP format
        records = []
        for item in data:
            if "attributes" in item:
                records.append(item["attributes"])
            else:
                records.append(item)
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[Retailer → Supplier] /acp/feed/{feed_name} | {len(records)} records | OK | {latency_ms}ms")
        logger.info(f"Fetched {len(records)} records from {feed_name} feed")
        return records
    except requests.RequestException as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[Retailer → Supplier] /acp/feed/{feed_name} | 0 records | ERROR | {latency_ms}ms")
        logger.error(f"Failed to fetch feed {feed_name} from {base_url}: {e}")
        raise