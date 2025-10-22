from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import logging
from .supplier_db import db_manager
from .acp_mapper import get_table_acp_schema, convert_table_to_acp
from .config import get_config

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supplier ACP Agent",
    description="Dynamic ACP-compliant Supplier Agent exposing NeonDB data",
    version="1.0.0"
)

# Global state for database connection
app.state.pool = None
app.state.tables = None

@app.on_event("startup")
async def startup():
    """Initialize database connection and refresh schema cache on startup."""
    try:
        cfg = get_config()
        app.state.pool = await db_manager.get_connection_pool()
        await db_manager.refresh_schema_cache()
        logger.info("ACP Agent started successfully")
    except Exception as e:
        logger.error(f"Failed to start ACP Agent: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    """Clean up database connections on shutdown."""
    if app.state.pool:
        await app.state.pool.close()
        logger.info("Database connections closed")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for better error responses."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

@app.get("/.well-known/acp", response_model=Dict[str, Any])
async def get_acp_info():
    """Return ACP discovery metadata."""
    return {
        "acp_version": "1.0",
        "agent": "supplier",
        "resources_endpoint": "/acp/schema",
        "feed_endpoint": "/acp/feed",
        "description": "Supplier Agent exposing Neon DB data via ACP"
    }

@app.get("/acp/schema", response_model=Dict[str, List[str]])
async def list_resources():
    """List all available resources (tables)."""
    try:
        tables = await db_manager.get_tables()
        return {"resources": tables}
    except Exception as e:
        logger.error(f"Failed to list resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to list resources")

@app.get("/acp/schema/{resource}", response_model=Dict[str, Any])
async def get_resource_schema(resource: str):
    """Return JSON Schema for a specific resource (table)."""
    try:
        # Check if table exists
        tables = await db_manager.get_tables()
        if resource not in tables:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        schema = await get_table_acp_schema(resource)
        if not schema:
            raise HTTPException(status_code=500, detail="Failed to generate schema")
        
        return {
            "resource": resource,
            "schema": schema
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for {resource}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource schema")

@app.get("/acp/feed/{resource}", response_model=Dict[str, Any])
async def get_resource_feed(
    resource: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination")
):
    """Return paginated ACP feed for a specific resource."""
    try:
        # Check if table exists
        tables = await db_manager.get_tables()
        if resource not in tables:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # Convert table data to ACP format
        result = await convert_table_to_acp(resource, limit, offset)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "resource": resource,
            "data": result["data"],
            "pagination": result["pagination"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feed for {resource}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource feed")

@app.get("/acp/resource/{resource}/{resource_id}", response_model=Dict[str, Any])
async def get_single_resource(resource: str, resource_id: str):
    """Return a single ACP resource by ID."""
    try:
        # Check if table exists
        tables = await db_manager.get_tables()
        if resource not in tables:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # Get primary key for the table
        pk = await db_manager.get_primary_key(resource)
        if not pk:
            raise HTTPException(status_code=500, detail="No primary key found for resource")
        
        # Extract the actual ID from the resource_id (format: table:actual_id)
        if ":" in resource_id:
            _, actual_id_str = resource_id.split(":", 1)
        else:
            actual_id_str = resource_id

        # Try to convert to int, fallback to string
        try:
            actual_id = int(actual_id_str)
        except ValueError:
            actual_id = actual_id_str

        # Query the specific resource
        async with db_manager.get_connection() as conn:
            query = f"SELECT * FROM {resource} WHERE {pk} = $1"
            row = await conn.fetch(query, actual_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Resource not found")
            
            # Convert to ACP resource
            acp_resource = {
                "id": f"{resource}:{actual_id}",
                "type": resource,
                "attributes": dict(row[0]),
                "links": {
                    "self": f"/acp/resource/{resource}/{actual_id}"
                }
            }
            
            return acp_resource
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource {resource_id} from {resource}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        async with db_manager.get_connection() as conn:
            await conn.fetch("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "cached_tables": len(db_manager.schema_cache)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )