import pytest
from unittest.mock import AsyncMock, MagicMock
from supplier_agent.supplier_db import DatabaseManager

class TestDatabaseManager:
    def test_init(self):
        db_manager = DatabaseManager()
        assert db_manager.config is not None
        assert db_manager.pool is None
        assert db_manager.schema_cache == {}
        assert db_manager.last_cache_update == 0
    
    @pytest.mark.asyncio
    async def test_get_connection_pool(self):
        # Mock asyncpg.create_pool
        mock_pool = AsyncMock()
        mock_create_pool = AsyncMock(return_value=mock_pool)
        
        # Patch the create_pool function
        import supplier_agent.supplier_db
        original_create_pool = supplier_agent.supplier_db.asyncpg.create_pool
        supplier_agent.supplier_db.asyncpg.create_pool = mock_create_pool
        
        try:
            db_manager = DatabaseManager()
            pool = await db_manager.get_connection_pool()
            
            assert pool == mock_pool
            mock_create_pool.assert_called_once()
            
        finally:
            # Restore original function
            supplier_agent.supplier_db.asyncpg.create_pool = original_create_pool
    
    @pytest.mark.asyncio
    async def test_get_tables(self):
        # Mock connection and query result
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"table_name": "products"},
            {"table_name": "variants"}
        ]
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        db_manager = DatabaseManager()
        db_manager.pool = mock_pool
        
        tables = await db_manager.get_tables()
        
        assert tables == ["products", "variants"]
        mock_conn.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_table_schema(self):
        # Mock connection and query result
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None, "udt_name": "int4"},
            {"column_name": "name", "data_type": "varchar", "is_nullable": "NO", "column_default": None, "udt_name": "varchar"}
        ]
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        db_manager = DatabaseManager()
        db_manager.pool = mock_pool
        
        schema = await db_manager.get_table_schema("products")
        
        assert len(schema) == 2
        assert schema[0]["column_name"] == "id"
        assert schema[0]["data_type"] == "integer"
        assert schema[1]["column_name"] == "name"
        assert schema[1]["data_type"] == "varchar"
    
    @pytest.mark.asyncio
    async def test_get_primary_key(self):
        # Mock connection and query result
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [{"column_name": "id"}]
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        db_manager = DatabaseManager()
        db_manager.pool = mock_pool
        
        pk = await db_manager.get_primary_key("products")
        
        assert pk == "id"
        mock_conn.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_table_data(self):
        # Mock connection and query result
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"id": 1, "name": "Test Product"},
            {"id": 2, "name": "Another Product"}
        ]
        
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        db_manager = DatabaseManager()
        db_manager.pool = mock_pool
        
        data = await db_manager.get_table_data("products", limit=5, offset=0)
        
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Test Product"
        mock_conn.fetch.assert_called_once_with("SELECT * FROM products LIMIT $1 OFFSET $2", 5, 0)
    
    @pytest.mark.asyncio
    async def test_get_cached_schema(self):
        # Mock the get_table_schema method
        mock_schema = [
            {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None, "udt_name": "int4"},
            {"column_name": "name", "data_type": "varchar", "is_nullable": "NO", "column_default": None, "udt_name": "varchar"}
        ]
        
        db_manager = DatabaseManager()
        db_manager.get_table_schema = AsyncMock(return_value=mock_schema)
        
        # First call should fetch and cache
        result1 = await db_manager.get_cached_schema("products")
        assert result1 == mock_schema
        assert db_manager.schema_cache["products"] == mock_schema
        assert db_manager.last_cache_update > 0
        
        # Second call should use cache
        import time
        time.sleep(0.01)  # Small delay to ensure cache is still valid
        result2 = await db_manager.get_cached_schema("products")
        assert result2 == mock_schema
        
        # get_table_schema should only be called once due to caching
        db_manager.get_table_schema.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_schema_cache(self):
        # Mock get_tables and get_table_schema
        mock_tables = ["products", "variants"]
        db_manager.get_tables = AsyncMock(return_value=mock_tables)
        
        mock_schema1 = [{"column_name": "id", "data_type": "integer"}]
        mock_schema2 = [{"column_name": "product_id", "data_type": "integer"}]
        
        db_manager.get_table_schema = AsyncMock(side_effect=[mock_schema1, mock_schema2])
        
        await db_manager.refresh_schema_cache()
        
        assert len(db_manager.schema_cache) == 2
        assert "products" in db_manager.schema_cache
        assert "variants" in db_manager.schema_cache
        assert db_manager.schema_cache["products"] == mock_schema1
        assert db_manager.schema_cache["variants"] == mock_schema2
        assert db_manager.last_cache_update > 0
        
        # Verify both get_table_schema calls were made
        db_manager.get_table_schema.assert_any_call("products")
        db_manager.get_table_schema.assert_any_call("variants")