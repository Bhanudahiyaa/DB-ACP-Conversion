import pytest
from unittest.mock import AsyncMock, MagicMock
from supplier_agent.acp_mapper import (
    sql_type_to_json_schema,
    row_to_acp_resource,
    generate_acp_schema,
    get_table_acp_schema,
    convert_table_to_acp
)

class TestSqlTypeToJsonSchema:
    def test_integer_types(self):
        assert sql_type_to_json_schema("integer") == {"type": "integer"}
        assert sql_type_to_json_schema("bigint") == {"type": "integer"}
        assert sql_type_to_json_schema("smallint") == {"type": "integer"}
        assert sql_type_to_json_schema("serial") == {"type": "integer"}
    
    def test_string_types(self):
        assert sql_type_to_json_schema("text") == {"type": "string"}
        assert sql_type_to_json_schema("varchar") == {"type": "string"}
        assert sql_type_to_json_schema("character") == {"type": "string"}
    
    def test_numeric_types(self):
        assert sql_type_to_json_schema("numeric") == {"type": "number"}
        assert sql_type_to_json_schema("decimal") == {"type": "number"}
        assert sql_type_to_json_schema("real") == {"type": "number"}
        assert sql_type_to_json_schema("double precision") == {"type": "number"}
    
    def test_boolean_types(self):
        assert sql_type_to_json_schema("boolean") == {"type": "boolean"}
    
    def test_datetime_types(self):
        result = sql_type_to_json_schema("timestamp without time zone")
        assert result["type"] == "string"
        assert result["format"] == "date-time"
    
    def test_unknown_type(self):
        assert sql_type_to_json_schema("unknown_type") == {"type": "string"}

class TestRowToAcpResource:
    def test_valid_row(self):
        row = {"id": 1, "name": "Test Product", "price": 99.99}
        pk = "id"
        
        result = row_to_acp_resource("products", row, pk)
        
        assert result["id"] == "products:1"
        assert result["type"] == "products"
        assert result["attributes"]["name"] == "Test Product"
        assert result["attributes"]["price"] == 99.99
        assert result["links"]["self"] == "/acp/resource/products/1"
    
    def test_missing_primary_key(self):
        row = {"name": "Test Product", "price": 99.99}
        pk = "id"
        
        result = row_to_acp_resource("products", row, pk)
        assert result is None

class TestGenerateAcpSchema:
    def test_schema_generation(self):
        schema_info = [
            {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None, "udt_name": "int4"},
            {"column_name": "name", "data_type": "varchar", "is_nullable": "NO", "column_default": None, "udt_name": "varchar"},
            {"column_name": "price", "data_type": "numeric", "is_nullable": "YES", "column_default": "0.00", "udt_name": "numeric"},
            {"column_name": "active", "data_type": "boolean", "is_nullable": "YES", "column_default": "true", "udt_name": "bool"}
        ]
        
        result = generate_acp_schema("products", schema_info)
        
        assert result["type"] == "object"
        assert result["title"] == "Products Schema"
        assert "id" in result["properties"]
        assert "name" in result["properties"]
        assert "price" in result["properties"]
        assert "active" in result["properties"]
        assert result["properties"]["id"]["type"] == "integer"
        assert result["properties"]["name"]["type"] == "string"
        assert result["properties"]["price"]["type"] == "number"
        assert result["properties"]["active"]["type"] == "boolean"
        assert result["required"] == ["id", "name"]

class TestConvertTableToAcp:
    @pytest.mark.asyncio
    async def test_successful_conversion(self):
        # Mock the database manager
        mock_db_manager = AsyncMock()
        mock_db_manager.get_table_data.return_value = [
            {"id": 1, "name": "Test Product", "price": 99.99},
            {"id": 2, "name": "Another Product", "price": 149.99}
        ]
        mock_db_manager.get_primary_key.return_value = "id"
        
        # Mock the global db_manager
        import supplier_agent.acp_mapper
        original_db_manager = supplier_agent.acp_mapper.db_manager
        supplier_agent.acp_mapper.db_manager = mock_db_manager
        
        try:
            result = await convert_table_to_acp("products", limit=10, offset=0)
            
            assert result["data"] == [
                {
                    "id": "products:1",
                    "type": "products",
                    "attributes": {"name": "Test Product", "price": 99.99},
                    "links": {"self": "/acp/resource/products/1"}
                },
                {
                    "id": "products:2",
                    "type": "products",
                    "attributes": {"name": "Another Product", "price": 149.99},
                    "links": {"self": "/acp/resource/products/2"}
                }
            ]
            assert result["pagination"]["total"] == 2
            assert result["pagination"]["limit"] == 10
            assert result["pagination"]["offset"] == 0
            assert result["pagination"]["has_more"] is False
            
        finally:
            # Restore original db_manager
            supplier_agent.acp_mapper.db_manager = original_db_manager

    @pytest.mark.asyncio
    async def test_no_data(self):
        # Mock the database manager
        mock_db_manager = AsyncMock()
        mock_db_manager.get_table_data.return_value = []
        mock_db_manager.get_primary_key.return_value = "id"
        
        # Mock the global db_manager
        import supplier_agent.acp_mapper
        original_db_manager = supplier_agent.acp_mapper.db_manager
        supplier_agent.acp_mapper.db_manager = mock_db_manager
        
        try:
            result = await convert_table_to_acp("products", limit=10, offset=0)
            
            assert result["data"] == []
            assert result["pagination"]["total"] == 0
            assert result["pagination"]["has_more"] is False
            
        finally:
            # Restore original db_manager
            supplier_agent.acp_mapper.db_manager = original_db_manager