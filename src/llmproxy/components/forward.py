"""Generic forward component for custom/unknown-API backends.

These backends are configured under `backends.custom` in YAML.
They perform transparent HTTP forwarding (no protocol translation)
and participate in the global locking system for resource coordination.
"""

import logging
from typing import Optional

import httpx
from fastapi import Request
from starlette.responses import StreamingResponse, Response as StarletteResponse

from ..config import get_config
from ..config.models import BackendConfig

logger = logging.getLogger(__name__)

HOP_BY_HOP_HEADERS = {
    "host", "content-length", "connection", "keep-alive",
    "proxy-authenticate", "proxy-authorization", "te", "trailers",
    "transfer-encoding", "upgrade", "content-encoding"
}


class ForwardComponent:
    """Transparent HTTP forwarder for custom backends."""

    def __init__(
        self,
        name: str,
        url: str,
        client: httpx.AsyncClient | None = None,
        path_prefix: Optional[str] = None,
        strip_prefix: bool = False,
        timeout: int = 30,
        read_timeout: int = 120,
        api_key: str = "",
    ):
        self.name = name
        self.base_url = url.rstrip("/")
        self.path_prefix = path_prefix
        self.strip_prefix = strip_prefix
        self.api_key = api_key

        if client is not None:
            self.client = client
        else:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(timeout, read=read_timeout),
            )
        logger.info(f"ForwardComponent '{name}' ready → {self.base_url}")

    def _rewrite_path(self, incoming_path: str) -> str:
        """Compute the path to send to the backend."""
        if not self.strip_prefix or not self.path_prefix:
            return incoming_path

        prefix = self.path_prefix.rstrip("/")
        if incoming_path.startswith(prefix):
            new_path = incoming_path[len(prefix):] or "/"
            if not new_path.startswith("/"):
                new_path = "/" + new_path
            return new_path
        return incoming_path

    async def forward(self, request: Request) -> StarletteResponse:
        """Forward the incoming request to the backend and return the response.

        Supports streaming (SSE, chunked, binary) transparently.
        """
        incoming_path = request.url.path
        target_path = self._rewrite_path(incoming_path)

        # Build headers (filter hop-by-hop)
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in HOP_BY_HOP_HEADERS
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Preserve content-type if present
        content_type = request.headers.get("content-type")
        if content_type:
            headers["content-type"] = content_type

        try:
            # Use httpx to forward (supports all methods)
            req = self.client.build_request(
                method=request.method,
                url=target_path,
                content=await request.body(),
                headers=headers,
                params=dict(request.query_params),
            )
            backend_resp = await self.client.send(req, stream=True)

            # Determine if we should stream the response
            content_type = backend_resp.headers.get("content-type", "")
            is_streaming = (
                backend_resp.headers.get("transfer-encoding", "").lower() == "chunked"
                or "stream" in content_type.lower()
                or content_type.startswith("text/event-stream")
                or content_type.startswith("application/x-ndjson")
            )

            if is_streaming:
                async def stream_generator():
                    try:
                        async for chunk in backend_resp.aiter_bytes():
                            yield chunk
                    finally:
                        await backend_resp.aclose()

                return StreamingResponse(
                    stream_generator(),
                    status_code=backend_resp.status_code,
                    headers=dict(backend_resp.headers),
                    media_type=content_type or None,
                )
            else:
                # Non-streaming: read body and return
                body = await backend_resp.aread()
                await backend_resp.aclose()
                return StarletteResponse(
                    content=body,
                    status_code=backend_resp.status_code,
                    headers=dict(backend_resp.headers),
                    media_type=content_type or None,
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"Forward backend error for {self.name} on {target_path}: {e}")
            error_body = e.response.content if e.response else b'{"error": "backend error"}'
            return StarletteResponse(
                content=error_body,
                status_code=e.response.status_code if e.response else 502,
                media_type="application/json",
            )
        except Exception as e:
            logger.error(f"Forward error for {self.name}: {e}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content={"error": {"message": str(e), "type": "forward_error"}},
                status_code=502,
            )

    async def close(self):
        await self.client.aclose()
