"""
supplier_agent/a2a_server.py
Wraps existing ACP logic inside an A2A SDK server.
"""

from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication, AgentCard
from a2a.server.skills.skill import Skill
from a2a.server.skills.skill_registry import SkillRegistry
from a2a.types import AgentID, SkillID
from fastapi import FastAPI, Request, Response
from .acp_mapper import convert_table_to_acp
import logging
import asyncio
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Create A2A FastAPI application
app = A2ARESTFastAPIApplication(
    agent_card=AgentCard(
        agent_id=AgentID("supplier-agent"),
        name="Supplier Agent",
        description="ACP-compliant Supplier Agent exposing NeonDB data via A2A protocol",
        version="1.0.0"
    )
)

# Skill Registry
skill_registry = SkillRegistry()

# Custom logging middleware for A2A requests
@app.middleware("http")
async def a2a_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = datetime.now()

    # Log incoming request
    logger.info(f"[{start_time.isoformat()}] {request_id} | {request.method} {request.url.path} | START")

    response = await call_next(request)

    end_time = datetime.now()
    latency_ms = int((end_time - start_time).total_seconds() * 1000)

    # Log response
    logger.info(f"[{start_time.isoformat()}] {request_id} | {request.method} {request.url.path} | {response.status_code} | {latency_ms}ms")

    return response

# Register FetchCatalog skill
@skill_registry.skill(SkillID("FetchCatalog"))
async def fetch_catalog_skill(params: dict = None) -> dict:
    """
    A2A Skill: Fetch catalog data in ACP-compliant format.
    Returns ACP data with id, type, attributes (including price).
    """
    if params is None:
        params = {}

    agent_id = params.get("agent_id", "unknown")
    request_id = params.get("request_id", str(uuid.uuid4()))
    start_time = datetime.now()

    try:
        # Log skill invocation
        logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchCatalog | INVOKED")

        # Fetch actual catalog data from database
        result = await convert_table_to_acp("products", limit=100)  # Fetch up to 100 catalog items

        if "error" in result:
            logger.error(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchCatalog | ERROR | {result['error']}")
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchCatalog | 0 records | FAILURE | {latency_ms}ms")
            return {
                "status": "error",
                "error": result["error"],
                "records": [],
                "count": 0,
                "request_id": request_id
            }

        # Return full ACP-compliant records
        records = result["data"]
        count = len(records)

        # Log success
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchCatalog | {count} records | SUCCESS | {latency_ms}ms")

        return {
            "status": "ok",
            "records": records,
            "count": count,
            "request_id": request_id
        }
    except Exception as e:
        # Log failure
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchCatalog | 0 records | FAILURE | {latency_ms}ms")

        logger.error(f"Error in FetchCatalog skill: {e}")
        return {
            "status": "error",
            "error": str(e),
            "records": [],
            "count": 0,
            "request_id": request_id
        }

# Register FetchProductPrice skill
@skill_registry.skill(SkillID("FetchProductPrice"))
async def fetch_product_price_skill(params: dict = None) -> dict:
    """
    A2A Skill: Fetch product prices in ACP-compliant format.
    Returns ACP data with id, type, attributes (name, price, currency).
    """
    if params is None:
        params = {}

    agent_id = params.get("agent_id", "unknown")
    request_id = params.get("request_id", str(uuid.uuid4()))
    start_time = datetime.now()

    try:
        # Log skill invocation
        logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchProductPrice | INVOKED")

        # Fetch actual product data from database
        result = await convert_table_to_acp("products", limit=100)  # Fetch up to 100 products

        if "error" in result:
            logger.error(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchProductPrice | ERROR | {result['error']}")
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchProductPrice | 0 records | FAILURE | {latency_ms}ms")
            return {
                "status": "error",
                "error": result["error"],
                "records": [],
                "count": 0,
                "request_id": request_id
            }

        # Return full ACP-compliant records
        records = result["data"]
        count = len(records)

        # Log success
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchProductPrice | {count} records | SUCCESS | {latency_ms}ms")

        return {
            "status": "ok",
            "records": records,
            "count": count,
            "request_id": request_id
        }
    except Exception as e:
        # Log failure
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        logger.info(f"[{start_time.isoformat()}] {request_id} | {agent_id} | FetchProductPrice | 0 records | FAILURE | {latency_ms}ms")

        logger.error(f"Error in FetchProductPrice skill: {e}")
        return {
            "status": "error",
            "error": str(e),
            "records": [],
            "count": 0,
            "request_id": request_id
        }

# Register skills with the A2A application
app.register_skill_registry(skill_registry)

async def run_a2a_server():
    """Run the A2A server using uvicorn."""
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8090, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_a2a_server())