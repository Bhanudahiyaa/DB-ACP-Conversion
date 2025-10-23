import logging
import time
from datetime import datetime
from typing import Optional
import os

def setup_structured_logging(log_file: str = "logs/agent_activity.log") -> logging.Logger:
    """Setup structured logging for agent activities."""
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger("agent_activity")
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler for structured logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Custom formatter for structured logs
    formatter = logging.Formatter(
        "[%(asctime)s] %(agent)s → %(target)s | %(endpoint)s | %(record_count)s records | %(status)s | %(latency)sms"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

class ActivityLogger:
    """Logger for tracking agent activities."""

    def __init__(self, agent_name: str, log_file: str = "logs/agent_activity.log"):
        self.agent_name = agent_name
        self.logger = setup_structured_logging(log_file)

    def log_request(self, endpoint: str, method: str = "GET", agent_id: Optional[str] = None) -> 'ActivityTimer':
        """Log the start of a request and return a timer for completion logging."""
        return ActivityTimer(self.logger, self.agent_name, endpoint, method, agent_id)

class ActivityTimer:
    """Timer for logging request completion with latency."""

    def __init__(self, logger: logging.Logger, agent_name: str, endpoint: str, method: str, agent_id: Optional[str]):
        self.logger = logger
        self.agent_name = agent_name
        self.endpoint = endpoint
        self.method = method
        self.agent_id = agent_id or "unknown"
        self.start_time = time.time()

    def log_completion(self, record_count: int = 0, status: str = "OK", target: str = "unknown"):
        """Log the completion of the request."""
        latency_ms = int((time.time() - self.start_time) * 1000)

        # Create extra dict for structured logging
        extra = {
            "agent": self.agent_name,
            "target": target,
            "endpoint": f"{self.method} {self.endpoint}",
            "record_count": record_count,
            "status": status,
            "latency": latency_ms
        }

        self.logger.info(f"Request completed", extra=extra)