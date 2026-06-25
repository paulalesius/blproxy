"""Request/response logging middleware."""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import get_config

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs requests and responses."""
    
    def __init__(self, app):
        super().__init__(app)
    
    def _log_request(self, request: Request) -> None:
        """Log incoming request."""
        config = get_config()
        
        if not config.log_requests:
            return
        
        logger.info(
            "%s %s",
            request.method,
            request.url,
        )
        
        # Log headers if debug
        if logger.isEnabledFor(logging.DEBUG):
            for key, value in request.headers.items():
                logger.debug("  %s: %s", key, value)
    
    def _log_response(
        self,
        request: Request,
        response: Response,
        duration: float,
    ) -> None:
        """Log outgoing response."""
        config = get_config()
        
        if not config.log_responses:
            return
        
        logger.info(
            "%s %s -> %s (%.3fs)",
            request.method,
            request.url,
            response.status_code,
            duration,
        )
    
    async def dispatch(
        self,
        request: Request,
        call,
    ) -> Response:
        """Handle request with logging."""
        self._log_request(request)
        
        start_time = time.time()
        
        try:
            response = await call(request)
        finally:
            duration = time.time() - start_time
            self._log_response(request, response, duration)
        
        return response