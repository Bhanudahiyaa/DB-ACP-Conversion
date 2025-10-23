from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import logging
from .supplier_db import db_manager
from .acp_mapper import get_table_acp_schema, convert_table_to_acp
from .config import get_config
from common.log_utils import ActivityLogger

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supplier ACP Agent",
    description="Dynamic ACP-compliant Supplier Agent exposing NeonDB data",
    version="1.0.0"
)

# Add logging middleware
activity_logger = ActivityLogger("Supplier")

# Global state for database connection
app.state.pool = None
app.state.tables = None

@app.on_event("startup")
async def startup_event():
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
async def shutdown_event():
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
    timer = activity_logger.log_request("/.well-known/acp", "GET", "discovery")
    result = {
        "acp_version": "1.0",
        "agent": "supplier",
        "resources_endpoint": "/acp/schema",
        "feed_endpoint": "/acp/feed",
        "description": "Supplier Agent exposing Neon DB data via ACP"
    }
    timer.log_completion(record_count=0, status="OK", target="client")
    return result

@app.get("/acp/schema", response_model=Dict[str, List[str]])
async def list_resources():
    """List all available resources (tables)."""
    timer = activity_logger.log_request("/acp/schema", "GET", "schema")
    try:
        tables = await db_manager.get_tables()
        result = {"resources": tables}
        timer.log_completion(record_count=len(tables), status="OK", target="client")
        return result
    except Exception as e:
        logger.error(f"Failed to list resources: {e}")
        timer.log_completion(record_count=0, status="ERROR", target="client")
        raise HTTPException(status_code=500, detail="Failed to list resources")

@app.get("/acp/schema/{resource}", response_model=Dict[str, Any])
async def get_resource_schema(resource: str):
    """Return JSON Schema for a specific resource (table)."""
    timer = activity_logger.log_request(f"/acp/schema/{resource}", "GET", "schema")
    try:
        # Check if table exists
        tables = await db_manager.get_tables()
        if resource not in tables:
            timer.log_completion(record_count=0, status="ERROR", target="client")
            raise HTTPException(status_code=404, detail="Resource not found")
        
        schema = await get_table_acp_schema(resource)
        if not schema:
            timer.log_completion(record_count=0, status="ERROR", target="client")
            raise HTTPException(status_code=500, detail="Failed to generate schema")
        
        result = {
            "resource": resource,
            "schema": schema
        }
        timer.log_completion(record_count=0, status="OK", target="client")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for {resource}: {e}")
        timer.log_completion(record_count=0, status="ERROR", target="client")
        raise HTTPException(status_code=500, detail="Failed to get resource schema")

@app.get("/acp/feed/{resource}", response_model=Dict[str, Any])
async def get_resource_feed(
    resource: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination")
):
    """Return paginated ACP feed for a specific resource."""
    timer = activity_logger.log_request(f"/acp/feed/{resource}", "GET", "feed")
    try:
        # Check if table exists
        tables = await db_manager.get_tables()
        if resource not in tables:
            timer.log_completion(record_count=0, status="ERROR", target="client")
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # Convert table data to ACP format
        result = await convert_table_to_acp(resource, limit, offset)
        
        if "error" in result:
            timer.log_completion(record_count=0, status="ERROR", target="client")
            raise HTTPException(status_code=500, detail=result["error"])
        
        response = {
            "resource": resource,
            "data": result["data"],
            "pagination": result["pagination"]
        }
        timer.log_completion(record_count=len(result["data"]), status="OK", target="client")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feed for {resource}: {e}")
        timer.log_completion(record_count=0, status="ERROR", target="client")
        raise HTTPException(status_code=500, detail="Failed to get resource feed")

@app.get("/acp/resource/{resource}/{resource_id}", response_model=Dict[str, Any])
async def get_single_resource(resource: str, resource_id: str):
    """Return a single ACP resource by ID."""
    timer = activity_logger.log_request(f"/acp/resource/{resource}/{resource_id}", "GET", "resource")
    try:
        # Check if table exists
        tables = await db_manager.get_tables()
        if resource not in tables:
            timer.log_completion(record_count=0, status="ERROR", target="client")
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # Get primary key for the table
        pk = await db_manager.get_primary_key(resource)
        if not pk:
            timer.log_completion(record_count=0, status="ERROR", target="client")
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
                timer.log_completion(record_count=0, status="ERROR", target="client")
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
            
            timer.log_completion(record_count=1, status="OK", target="client")
            return acp_resource
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource {resource_id} from {resource}: {e}")
        timer.log_completion(record_count=0, status="ERROR", target="client")
        raise HTTPException(status_code=500, detail="Failed to get resource")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    timer = activity_logger.log_request("/health", "GET", "health")
    try:
        # Test database connection
        async with db_manager.get_connection() as conn:
            await conn.fetch("SELECT 1")
        
        result = {
            "status": "healthy",
            "database": "connected",
            "cached_tables": len(db_manager.schema_cache)
        }
        timer.log_completion(record_count=0, status="OK", target="client")
        return result
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        timer.log_completion(record_count=0, status="ERROR", target="client")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )