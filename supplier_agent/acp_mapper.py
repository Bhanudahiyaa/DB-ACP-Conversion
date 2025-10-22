from typing import Dict, Any, Optional, List
import logging
from .supplier_db import db_manager

logger = logging.getLogger(__name__)

def sql_type_to_json_schema(sql_type: str, udt_name: Optional[str] = None) -> Dict[str, Any]:
    """Convert SQL data type to JSON Schema type."""
    type_mapping = {
        "integer": {"type": "integer"},
        "bigint": {"type": "integer"},
        "smallint": {"type": "integer"},
        "serial": {"type": "integer"},
        "bigserial": {"type": "integer"},
        "text": {"type": "string"},
        "varchar": {"type": "string"},
        "character": {"type": "string"},
        "boolean": {"type": "boolean"},
        "numeric": {"type": "number"},
        "decimal": {"type": "number"},
        "real": {"type": "number"},
        "double precision": {"type": "number"},
        "timestamp without time zone": {"type": "string", "format": "date-time"},
        "timestamp with time zone": {"type": "string", "format": "date-time"},
        "date": {"type": "string", "format": "date"},
        "time without time zone": {"type": "string", "format": "time"},
        "json": {"type": "object"},
        "jsonb": {"type": "object"},
        "array": {"type": "array"},
    }
    
    # Handle PostgreSQL specific types
    if udt_name:
        if udt_name in ["int4", "int8", "int2"]:
            return {"type": "integer"}
        elif udt_name in ["varchar", "text", "bpchar"]:
            return {"type": "string"}
        elif udt_name in ["bool"]:
            return {"type": "boolean"}
        elif udt_name in ["numeric", "float8", "float4"]:
            return {"type": "number"}
        elif udt_name in ["timestamp", "timestamptz", "date"]:
            return {"type": "string", "format": "date-time"}
        elif udt_name in ["json", "jsonb"]:
            return {"type": "object"}
    
    return type_mapping.get(sql_type.lower(), {"type": "string"})

def row_to_acp_resource(table: str, row: Dict[str, Any], pk: str) -> Dict[str, Any]:
    """Convert a database row to an ACP-compatible resource."""
    if pk not in row:
        logger.warning(f"Primary key '{pk}' not found in row for table '{table}'")
        return None
    
    resource_id = f"{table}:{row[pk]}"
    attributes = {k: v for k, v in row.items() if k != pk}
    
    return {
        "id": resource_id,
        "type": table,
        "attributes": attributes,
        "links": {
            "self": f"/acp/resource/{table}/{row[pk]}"
        }
    }

def generate_acp_schema(table: str, schema_info: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate ACP-compatible JSON Schema for a table."""
    properties = {}
    required = []
    
    for column in schema_info:
        col_name = column["column_name"]
        col_type = column["data_type"]
        col_nullable = column["is_nullable"] == "YES"
        col_default = column["column_default"]
        udt_name = column.get("udt_name")
        
        # Add to required list if column is not nullable and has no default
        if not col_nullable and col_default is None:
            required.append(col_name)
        
        # Generate schema for this column
        properties[col_name] = sql_type_to_json_schema(col_type, udt_name)
        
        # Add description if available
        if col_default:
            properties[col_name]["description"] = f"Default: {col_default}"
    
    return {
        "type": "object",
        "properties": properties,
        "required": required if required else [],
        "title": f"{table.capitalize()} Schema"
    }

async def get_table_acp_schema(table: str) -> Optional[Dict[str, Any]]:
    """Get ACP schema for a specific table."""
    try:
        schema_info = await db_manager.get_cached_schema(table)
        if not schema_info:
            return None
        
        return generate_acp_schema(table, schema_info)
    except Exception as e:
        logger.error(f"Failed to generate ACP schema for table {table}: {e}")
        return None

async def convert_table_to_acp(table: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """Convert table data to ACP format with pagination."""
    try:
        # Get table data
        rows = await db_manager.get_table_data(table, limit, offset)
        
        if not rows:
            return {
                "data": [],
                "pagination": {
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "has_more": False
                }
            }
        
        # Get primary key
        pk = await db_manager.get_primary_key(table)
        if not pk:
            logger.warning(f"No primary key found for table {table}")
            return {"data": [], "error": "No primary key found"}
        
        # Convert rows to ACP resources
        resources = []
        for row in rows:
            resource = row_to_acp_resource(table, row, pk)
            if resource:
                resources.append(resource)
        
        # Get total count for pagination
        async with db_manager.get_connection() as conn:
            count_result = await conn.fetch(f"SELECT COUNT(*) FROM {table}")
            total = count_result[0]["count"] if count_result else 0
        
        return {
            "data": resources,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to convert table {table} to ACP format: {e}")
        return {"data": [], "error": str(e)}