"""Global lock middleware for backend coordination."""

import asyncio
import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import get_config
from ..routing.backends import Backend, get_backend_for_path

logger = logging.getLogger(__name__)


class GlobalLockMiddleware(BaseHTTPMiddleware):
    """Middleware that implements global locking between backends."""
    
    # Lock state
    _locks: dict[str, asyncio.Lock] = {}
    _lock_conditions: dict[str, asyncio.Condition] = {}
    
    def __init__(self, app):
        super().__init__(app)
        self._initialized = False
    
    async def _ensure_lock_initialized(self, backend: str) -> None:
        """Ensure lock and condition exist for backend."""
        if backend not in self._locks:
            self._locks[backend] = asyncio.Lock()
            self._lock_conditions[backend] = asyncio.Condition()
    
    def _get_locking_backends(self, backend: str) -> list[str]:
        """Get list of backends that lock this backend."""
        config = get_config()
        return config.lock.backends.get(backend, [])
    
    async def _acquire_locks(self, backend: str) -> None:
        """Acquire locks for all backends that lock this one."""
        locking_backends = self._get_locking_backends(backend)
        
        for locking_backend in locking_backends:
            await self._ensure_lock_initialized(locking_backend)
            async with self._lock_conditions[locking_backend]:
                await self._locks[locking_backend].acquire()
                logger.debug(f"Acquired lock for {backend} via {locking_backend}")
    
    async def _release_locks(self, backend: str) -> None:
        """Release locks for all backends that lock this one."""
        locking_backends = self._get_locking_backends(backend)
        
        for locking_backend in locking_backends:
            if locking_backend in self._locks:
                try:
                    self._locks[locking_backend].release()
                    logger.debug(f"Released lock for {backend} via {locking_backend}")
                except RuntimeError:
                    logger.warning(f"Lock for {locking_backend} not held by {backend}")
    
    async def dispatch(
        self,
        request: Request,
        call,
    ) -> Response:
        """Handle request with locking."""
        # Skip if locking is disabled
        config = get_config()
        if not config.lock.enabled:
            return await call(request)
        
        # Get backend for this path
        backend = get_backend_for_path(request.url.path)
        
        if backend is None:
            # No backend matched, pass through
            return await call(request)
        
        backend_name = backend.value
        
        try:
            # Acquire locks
            await self._acquire_locks(backend_name)
            
            # Process request
            return await call(request)
        
        finally:
            # Release locks
            await self._release_locks(backend_name)