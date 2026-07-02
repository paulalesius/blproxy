"""Test reranker remapper with exact backend response mocks."""

import pytest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exrouter.hooks import HookContext


@pytest.mark.asyncio
async def test_reranker_remapper_normalizes_paths():
    """Reranker remapper normalizes /v1/rerank to /rerank."""
    
    remapper_path = Path(__file__).parent.parent / "samples" / "llama-server-rerank-tei-remapper.py"
    assert remapper_path.exists()
    
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("reranker_remapper", remapper_path)
    remapper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remapper_module)
    
    remapper = remapper_module.RequestRemapper()
    
    # Test path normalization
    for path in ["/v1/rerank", "/v1/reranking", "/reranking"]:
        ctx = HookContext(
            request_path=path,
            request_method="POST",
            request_headers={},
            request_body=json.dumps({
                "query": "test",
                "documents": ["doc1"]
            }).encode(),
            backend_name="rerank"
        )
        
        result = remapper.remap(ctx)
        
        # Remapper should normalize to /rerank
        assert result is not None
        assert result.path == "/rerank"


@pytest.mark.asyncio
async def test_reranker_remapper_handles_texts_field():
    """Reranker remapper converts 'texts' to 'documents' if needed."""
    
    remapper_path = Path(__file__).parent.parent / "samples" / "llama-server-rerank-tei-remapper.py"
    assert remapper_path.exists()
    
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("reranker_remapper", remapper_path)
    remapper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remapper_module)
    
    remapper = remapper_module.RequestRemapper()
    
    # Test with "texts" instead of "documents"
    ctx = HookContext(
        request_path="/rerank",
        request_method="POST",
        request_headers={},
        request_body=json.dumps({
            "query": "test query",
            "texts": ["doc1", "doc2"]  # Use "texts" instead
        }).encode(),
        backend_name="rerank"
    )
    
    result = remapper.remap(ctx)
    
    # Remapper should convert "texts" to "documents"
    assert result is not None
    assert result.body is not None
    
    sent_data = json.loads(result.body.decode('utf-8'))
    assert "documents" in sent_data
    assert "texts" not in sent_data
    assert sent_data["documents"] == ["doc1", "doc2"]


@pytest.mark.asyncio
async def test_reranker_remapper_passes_through_documents():
    """Reranker remapper passes through 'documents' unchanged."""
    
    remapper_path = Path(__file__).parent.parent / "samples" / "llama-server-rerank-tei-remapper.py"
    assert remapper_path.exists()
    
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("reranker_remapper", remapper_path)
    remapper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remapper_module)
    
    remapper = remapper_module.RequestRemapper()
    
    # Test with "documents" (no conversion needed)
    ctx = HookContext(
        request_path="/rerank",
        request_method="POST",
        request_headers={},
        request_body=json.dumps({
            "query": "test query",
            "documents": ["doc1", "doc2"]
        }).encode(),
        backend_name="rerank"
    )
    
    result = remapper.remap(ctx)
    
    # Returns None when no remapping needed
    assert result is None
