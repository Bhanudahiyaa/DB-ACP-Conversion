"""
Legacy Supplier DB Compatibility Shim

This module provides backward compatibility for the original supplier_db.py
by importing and re-exporting functions from the new async implementation.
"""

import asyncio
import logging
from typing import Optional, Iterable, Any, List, Dict
from contextlib import contextmanager
from urllib.parse import urlparse
import os

# Import the new async database manager
from .supplier_db import db_manager

logger = logging.getLogger(__name__)

# Legacy configuration (kept for compatibility)
DB_URL = os.environ.get("NEON_DB_URL")
SUPPLIER_API_KEY = os.environ.get("SUPPLIER_API_KEY", "dev-key")

def parse_db_url(db_url: str) -> dict:
    """Parse the database URL and return kwargs (legacy compatibility)."""
    r = urlparse(db_url)
    return {
        "dbname": r.path.lstrip("/"),
        "user": r.username,
        "password": r.password,
        "host": r.hostname,
        "port": r.port or 5432,
        "sslmode": "require",
        "connect_timeout": 10,
    }

def get_connection():
    """Legacy function - use async version instead."""
    logger.warning("get_connection() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

@contextmanager
def get_cursor(commit: bool = False, dict_cursor: bool = False):
    """Legacy function - use async version instead."""
    logger.warning("get_cursor() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def execute_query(query: str, params: Optional[Iterable[Any]] = None, fetch: bool = True, commit: bool = False, dict_cursor: bool = False):
    """Legacy function - use async version instead."""
    logger.warning("execute_query() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def execute_ddl(query: str) -> bool:
    """Legacy function - use async version instead."""
    logger.warning("execute_ddl() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

# Table management functions (simplified for compatibility)
def create_products_table() -> bool:
    """Legacy function - use async version instead."""
    logger.warning("create_products_table() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def create_variants_table() -> bool:
    """Legacy function - use async version instead."""
    logger.warning("create_variants_table() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def insert_sample_products() -> bool:
    """Legacy function - use async version instead."""
    logger.warning("insert_sample_products() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def insert_sample_variants() -> bool:
    """Legacy function - use async version instead."""
    logger.warning("insert_sample_variants() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def alter_products_for_feed() -> bool:
    """Legacy function - use async version instead."""
    logger.warning("alter_products_for_feed() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def alter_variants_for_feed() -> bool:
    """Legacy function - use async version instead."""
    logger.warning("alter_variants_for_feed() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

def migrate_inventory_and_availability() -> bool:
    """Legacy function - use async version instead."""
    logger.warning("migrate_inventory_and_availability() is deprecated. Use async database manager.")
    raise NotImplementedError("Use async database manager instead")

# Utility functions (async versions available)
def list_tables():
    """List tables in the database (async version available)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.run_until_complete(db_manager.get_tables())
                return future.result()
        else:
            # If we're not in an async context, run the async function
            return loop.run_until_complete(db_manager.get_tables())
    except Exception as e:
        logger.error(f"list_tables error: {e}")
        return []

def show_sample_products(limit: int = 5):
    """Show sample products (async version available)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.run_until_complete(
                    db_manager.get_table_data("products", limit)
                )
                products = future.result()
        else:
            # If we're not in an async context, run the async function
            products = loop.run_until_complete(
                db_manager.get_table_data("products", limit)
            )
        
        if not products:
            print("No products found.")
            return
        
        print("Sample products:")
        for product in products:
            print(f" ID:{product.get('id')} SKU:{product.get('sku')} Name:{product.get('name')} Price:{product.get('price')} Stock:{product.get('stock_quantity')} Status:{product.get('status')}")
    except Exception as e:
        logger.error(f"show_sample_products error: {e}")

# Legacy main function (redirects to new implementation)
def main():
    """Legacy main function - redirects to new implementation."""
    logger.warning("Legacy supplier_db.main() called. Use supplier_agent.main instead.")
    from .main import main as new_main
    return new_main()

# Export legacy functions for backward compatibility
__all__ = [
    'parse_db_url',
    'get_connection',
    'get_cursor',
    'execute_query',
    'execute_ddl',
    'create_products_table',
    'create_variants_table',
    'insert_sample_products',
    'insert_sample_variants',
    'alter_products_for_feed',
    'alter_variants_for_feed',
    'migrate_inventory_and_availability',
    'list_tables',
    'show_sample_products',
    'main',
    'DB_URL',
    'SUPPLIER_API_KEY'
]