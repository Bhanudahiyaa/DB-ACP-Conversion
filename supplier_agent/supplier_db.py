import asyncpg
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import time
from functools import lru_cache
from .config import get_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and schema caching."""
    
    def __init__(self):
        self.config = get_config()
        self.pool: Optional[asyncpg.Pool] = None
        self.schema_cache: Dict[str, Any] = {}
        self.last_cache_update: float = 0
        
    async def get_connection_pool(self) -> asyncpg.Pool:
        """Create and return a connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=self.config["DB_URL"],
                min_size=1,
                max_size=10,
                command_timeout=60
            )
        return self.pool
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        pool = await self.get_connection_pool()
        async with pool.acquire() as conn:
            yield conn
    
    async def get_tables(self) -> List[str]:
        """Get all table names from the database."""
        async with self.get_connection() as conn:
            rows = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
            )
            return [r["table_name"] for r in rows]
    
    async def get_table_schema(self, table: str) -> List[Dict[str, Any]]:
        """Get schema information for a specific table."""
        async with self.get_connection() as conn:
            q = """
            SELECT column_name, data_type, is_nullable, column_default, udt_name
            FROM information_schema.columns
            WHERE table_name=$1
            ORDER BY ordinal_position;
            """
            rows = await conn.fetch(q, table)
            return [dict(r) for r in rows]
    
    async def get_primary_key(self, table: str) -> Optional[str]:
        """Get the primary key column for a table."""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT k.column_name
                FROM information_schema.table_constraints t
                JOIN information_schema.key_column_usage k
                    ON t.constraint_name = k.constraint_name
                    AND t.table_schema = k.table_schema
                WHERE t.constraint_type = 'PRIMARY KEY'
                AND t.table_name = $1;
            """, table)
            return rows[0]["column_name"] if rows else None
    
    async def get_table_data(self, table: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get data from a specific table with pagination."""
        async with self.get_connection() as conn:
            # Use parameterized query to prevent SQL injection
            query = f"SELECT * FROM {table} LIMIT $1 OFFSET $2"
            rows = await conn.fetch(query, limit, offset)
            return [dict(r) for r in rows]
    
    async def get_cached_schema(self, table: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached schema if available and not expired."""
        current_time = time.time()
        cache_ttl = self.config["CACHE_TTL"]
        
        # Check if cache exists and is still valid
        if (table in self.schema_cache and 
            current_time - self.last_cache_update < cache_ttl):
            return self.schema_cache[table]
        
        # Cache is expired or doesn't exist, fetch fresh data
        try:
            schema = await self.get_table_schema(table)
            self.schema_cache[table] = schema
            self.last_cache_update = current_time
            return schema
        except Exception as e:
            logger.error(f"Failed to fetch schema for table {table}: {e}")
            return None
    
    async def refresh_schema_cache(self) -> None:
        """Refresh the entire schema cache."""
        try:
            tables = await self.get_tables()
            self.schema_cache = {}
            
            for table in tables:
                schema = await self.get_table_schema(table)
                self.schema_cache[table] = schema
            
            self.last_cache_update = time.time()
            logger.info(f"Schema cache refreshed for {len(tables)} tables")
        except Exception as e:
            logger.error(f"Failed to refresh schema cache: {e}")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
async def get_connection_pool(db_url: str):
    """Legacy function for backward compatibility."""
    return await db_manager.get_connection_pool()

async def get_tables(conn) -> List[str]:
    """Legacy function for backward compatibility."""
    return await db_manager.get_tables()

async def get_table_schema(conn, table: str) -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility."""
    return await db_manager.get_table_schema(table)