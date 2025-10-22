import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

# Mock the database manager for testing
class MockDatabaseManager:
    def __init__(self):
        self.tables = ["products", "variants"]
        self.schemas = {
            "products": [
                {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None, "udt_name": "int4"},
                {"column_name": "name", "data_type": "varchar", "is_nullable": "NO", "column_default": None, "udt_name": "varchar"},
                {"column_name": "price", "data_type": "numeric", "is_nullable": "YES", "column_default": "0.00", "udt_name": "numeric"}
            ],
            "variants": [
                {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None, "udt_name": "int4"},
                {"column_name": "product_id", "data_type": "integer", "is_nullable": "NO", "column_default": None, "udt_name": "int4"},
                {"column_name": "name", "data_type": "varchar", "is_nullable": "YES", "column_default": None, "udt_name": "varchar"}
            ]
        }
        self.data = {
            "products": [
                {"id": 1, "name": "Laptop", "price": 999.99},
                {"id": 2, "name": "Smartphone", "price": 699.99}
            ],
            "variants": [
                {"id": 1, "product_id": 1, "name": "Laptop - SSD"},
                {"id": 2, "product_id": 1, "name": "Laptop - HDD"}
            ]
        }
        self.primary_keys = {
            "products": "id",
            "variants": "id"
        }
    
    async def get_tables(self):
        return self.tables
    
    async def get_table_schema(self, table):
        return self.schemas.get(table, [])
    
    async def get_primary_key(self, table):
        return self.primary_keys.get(table)
    
    async def get_table_data(self, table, limit=10, offset=0):
        data = self.data.get(table, [])
        return data[offset:offset+limit]

# Test the ACP server endpoints
class TestAcpServer:
    def setup_method(self):
        # Import and patch the database manager
        import supplier_agent.acp_server
        self.original_db_manager = supplier_agent.acp_server.db_manager
        supplier_agent.acp_server.db_manager = MockDatabaseManager()
        
        # Create test client
        self.client = TestClient(supplier_agent.acp_server.app)
    
    def teardown_method(self):
        # Restore original database manager
        import supplier_agent.acp_server
        supplier_agent.acp_server.db_manager = self.original_db_manager
    
    def test_acp_info(self):
        response = self.client.get("/.well-known/acp")
        assert response.status_code == 200
        
        data = response.json()
        assert data["acp_version"] == "1.0"
        assert data["agent"] == "supplier"
        assert data["resources_endpoint"] == "/acp/schema"
        assert data["feed_endpoint"] == "/acp/feed"
    
    def test_list_resources(self):
        response = self.client.get("/acp/schema")
        assert response.status_code == 200
        
        data = response.json()
        assert "resources" in data
        assert "products" in data["resources"]
        assert "variants" in data["resources"]
    
    def test_get_resource_schema(self):
        response = self.client.get("/acp/schema/products")
        assert response.status_code == 200
        
        data = response.json()
        assert data["resource"] == "products"
        assert "schema" in data
        assert data["schema"]["type"] == "object"
        assert "properties" in data["schema"]
        assert "id" in data["schema"]["properties"]
        assert "name" in data["schema"]["properties"]
        assert "price" in data["schema"]["properties"]
    
    def test_get_resource_schema_not_found(self):
        response = self.client.get("/acp/schema/nonexistent")
        assert response.status_code == 404
    
    def test_get_resource_feed(self):
        response = self.client.get("/acp/feed/products")
        assert response.status_code == 200
        
        data = response.json()
        assert data["resource"] == "products"
        assert "data" in data
        assert "pagination" in data
        
        # Check ACP format
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "products:1"
        assert data["data"][0]["type"] == "products"
        assert data["data"][0]["attributes"]["name"] == "Laptop"
        assert data["data"][0]["links"]["self"] == "/acp/resource/products/1"
        
        # Check pagination
        assert data["pagination"]["total"] == 2
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["has_more"] is False
    
    def test_get_resource_feed_with_pagination(self):
        response = self.client.get("/acp/feed/products?limit=1&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) == 1
        assert data["pagination"]["total"] == 2
        assert data["pagination"]["limit"] == 1
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["has_more"] is True
    
    def test_get_resource_feed_not_found(self):
        response = self.client.get("/acp/feed/nonexistent")
        assert response.status_code == 404
    
    def test_get_single_resource(self):
        response = self.client.get("/acp/resource/products/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "products:1"
        assert data["type"] == "products"
        assert data["attributes"]["name"] == "Laptop"
        assert data["attributes"]["price"] == 999.99
        assert data["links"]["self"] == "/acp/resource/products/1"
    
    def test_get_single_resource_not_found(self):
        response = self.client.get("/acp/resource/products/999")
        assert response.status_code == 404
    
    def test_get_single_resource_invalid_format(self):
        # Test with invalid resource_id format
        response = self.client.get("/acp/resource/products/invalid_id")
        assert response.status_code == 404
    
    def test_health_check(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "cached_tables" in data

class TestAcpFeedIntegration:
    def setup_method(self):
        # Import and patch the database manager
        import supplier_agent.acp_server
        self.original_db_manager = supplier_agent.acp_server.db_manager
        supplier_agent.acp_server.db_manager = MockDatabaseManager()
        
        # Create test client
        self.client = TestClient(supplier_agent.acp_server.app)
    
    def teardown_method(self):
        # Restore original database manager
        import supplier_agent.acp_server
        supplier_agent.acp_server.db_manager = self.original_db_manager
    
    def test_acp_compliance(self):
        """Test that the feed returns ACP-compliant JSON"""
        response = self.client.get("/acp/feed/products")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify ACP structure
        assert "resource" in data
        assert "data" in data
        assert "pagination" in data
        
        # Verify resource structure
        for resource in data["data"]:
            assert "id" in resource
            assert "type" in resource
            assert "attributes" in resource
            assert "links" in resource
            assert "self" in resource["links"]
            
            # Verify ID format
            assert ":" in resource["id"]
            table, resource_id = resource["id"].split(":", 1)
            assert table == "products"
            assert resource_id.isdigit()
    
    def test_multiple_resources(self):
        """Test that multiple resources work correctly"""
        # Test products
        response = self.client.get("/acp/feed/products")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        
        # Test variants
        response = self.client.get("/acp/feed/variants")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2