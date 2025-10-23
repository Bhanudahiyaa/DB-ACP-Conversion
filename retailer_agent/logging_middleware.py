from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from common.log_utils import ActivityLogger

class RetailerLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging retailer agent requests and responses."""

    def __init__(self, app, agent_name: str = "Retailer"):
        super().__init__(app)
        self.activity_logger = ActivityLogger(agent_name)

    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()

        # Log request start
        timer = self.activity_logger.log_request(
            endpoint=str(request.url.path),
            method=request.method,
            agent_id=request.headers.get("X-Agent-ID", "retailer")
        )

        # Process request
        response: Response = await call_next(request)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Determine record count from response if possible
        record_count = 0
        if hasattr(response, 'body') and response.body:
            try:
                # Try to parse as JSON and count items if it's a list
                import json
                body_data = json.loads(response.body.decode())
                if isinstance(body_data, list):
                    record_count = len(body_data)
                elif isinstance(body_data, dict) and "data" in body_data:
                    data = body_data["data"]
                    if isinstance(data, list):
                        record_count = len(data)
            except:
                pass

        # Log completion
        status = "OK" if response.status_code < 400 else "ERROR"
        timer.log_completion(
            record_count=record_count,
            status=status,
            target="client"
        )

        return response