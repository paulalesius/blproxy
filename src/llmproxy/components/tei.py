"""TEI-compatible rerank component. YAML config only."""

import logging
import time
from typing import List, Optional, Any
from pydantic import BaseModel
import httpx

from ..config import get_config

logger = logging.getLogger(__name__)


class RerankRequest(BaseModel):
    model: Optional[str] = None
    query: str
    documents: Optional[List[str]] = None
    texts: Optional[List[str]] = None          # Hindsight compat
    top_n: Optional[int] = None
    max_chunks_per_doc: Optional[int] = None
    return_documents: Optional[bool] = None
    return_text: Optional[bool] = None         # Hindsight compat


class RerankResult(BaseModel):
    index: int
    score: float
    document: Optional[str] = None


class RerankResponse(BaseModel):
    model: str
    results: List[RerankResult]


class TEIComponent:
    """Proxy component for TEI rerank API."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        config = get_config()
        backend = config.backends.get("rerank")

        self.base_url = backend.url if backend else "http://127.0.0.1:8082"
        self.api_key = backend.api_key if backend else ""
        timeout = backend.timeout if backend else 30
        read_timeout = getattr(backend, "read_timeout", 120) if backend else 120

        if client is not None:
            self.client = client
        else:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(timeout, read=read_timeout)
            )
        logger.info(f"TEIComponent ready → {self.base_url}")

    async def rerank(self, request: RerankRequest) -> RerankResponse:
        start = time.time()

        # Hindsight compatibility
        documents = request.documents or request.texts or []
        if not documents:
            documents = ["no documents provided"]

        model = request.model or "reranker"
        return_documents = request.return_documents if request.return_documents is not None else (request.return_text or False)

        payload = {
            "model": model,
            "query": request.query,
            "documents": documents,
        }
        if request.top_n is not None:
            payload["top_n"] = request.top_n
        if request.max_chunks_per_doc is not None:
            payload["max_chunks_per_doc"] = request.max_chunks_per_doc
        if return_documents:
            payload["return_documents"] = True

        try:
            resp = await self.client.post("/rerank", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Rerank backend error: {e}")
            raise

        results = []
        for i, item in enumerate(data.get("results", [])):
            results.append(RerankResult(
                index=item.get("index", i),
                score=item.get("score", 0.0),
                document=item.get("document") or item.get("text") if return_documents else None
            ))

        logger.info(f"Rerank completed in {time.time()-start:.2f}s → {len(results)} results")
        return RerankResponse(model=model, results=results)

    async def close(self):
        await self.client.aclose()
