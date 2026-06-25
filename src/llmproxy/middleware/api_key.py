"""API key authentication middleware."""

import logging

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import get_config

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware that validates API key if configured."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(
        self,
        request: Request,
        call,
    ) -> Response:
        """Handle request with API key validation."""
        config = get_config()
        
        # Skip if no API key configured
        if not config.api_key:
            return await call(request)
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning("Request without API key")
            raise HTTPException(
                status_code=401,
                detail="API key required",
            )
        
        if api_key != config.api_key:
            logger.warning(f"Invalid API key: {api_key}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
            )
        
        logger.debug("API key validated")
        return await call(request)