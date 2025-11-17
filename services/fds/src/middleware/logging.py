"""
Structured Logging Middleware for ShopFDS Ecommerce Service
Provides JSON-formatted logs with request context for ELK Stack integration
"""

import json
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Configure structured logger
logger = logging.getLogger("shopfds.fds")
logger.setLevel(logging.INFO)

# JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "@timestamp": self.formatTime(record, self.datefmt),
            "service": "fds",
            "environment": "development",  # Override with env var in production
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "http_method"):
            log_data["http_method"] = record.http_method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "response_time"):
            log_data["response_time"] = record.response_time
        if hasattr(record, "client_ip"):
            log_data["client_ip"] = record.client_ip
        if hasattr(record, "user_agent"):
            log_data["user_agent"] = record.user_agent
        
        # Add exception info if present
        if record.exc_info:
            log_data["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stack_trace": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add structured logging with request context
    
    Features:
    - Request ID generation
    - Request/response logging
    - Response time tracking
    - User context extraction
    - Client IP and User-Agent logging
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Setup JSON handler if not already configured
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            logger.addHandler(handler)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Extract user ID from JWT if authenticated
        user_id = None
        if hasattr(request.state, "user"):
            user_id = str(request.state.user.id)
        
        # Log incoming request
        start_time = time.time()
        
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "endpoint": request.url.path,
                "http_method": request.method,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "query_params": dict(request.query_params),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Log outgoing response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": request.url.path,
                    "http_method": request.method,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "client_ip": client_ip,
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate response time even for errors
            response_time = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": request.url.path,
                    "http_method": request.method,
                    "status_code": 500,
                    "response_time": response_time,
                    "client_ip": client_ip,
                }
            )
            
            # Re-raise exception to be handled by FastAPI exception handlers
            raise


def get_logger() -> logging.Logger:
    """Get the configured structured logger"""
    return logger


def log_with_context(level: str, message: str, request: Request = None, **extra):
    """
    Log a message with request context
    
    Args:
        level: Log level (info, warning, error, etc.)
        message: Log message
        request: Optional FastAPI Request object
        **extra: Additional fields to include in log
    """
    context = {}
    
    if request:
        if hasattr(request.state, "request_id"):
            context["request_id"] = request.state.request_id
        if hasattr(request.state, "user"):
            context["user_id"] = str(request.state.user.id)
        context["endpoint"] = request.url.path
        context["http_method"] = request.method
    
    # Merge extra fields
    context.update(extra)
    
    # Get logger method
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=context)
