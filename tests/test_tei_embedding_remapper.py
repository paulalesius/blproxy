"""Test embedding remapper with exact backend response mocks."""

import pytest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exrouter.hooks import HookContext

# Exact mock responses from live backends (fetched from 8081 and 8082)
# Embedding backend (8081) returns: {"model": "...", "data": [{"embedding": [...1024...], "index": 0}]}
# Reranker backend (8082) returns: {"model": "...", "results": [{"index": 0, "relevance_score": -3.71...}]}
EMBED_MOCK_RESPONSE = {
    "model": "bge-m3",
    "data": [
        {"embedding": [0.0] * 1024, "index": 0}
    ]
}


@pytest.mark.asyncio
async def test_embedding_remapper_returns_list_for_embed_path():
    """Remapper returns raw TEI list for /embed path."""
    
    remapper_path = Path(__file__).parent.parent / "samples" / "llama-server-embedding-tei-remapper.py"
    assert remapper_path.exists()
    
    import importlib.util
    from unittest.mock import AsyncMock, Mock, patch
    
    spec = importlib.util.spec_from_file_location("embedding_remapper", remapper_path)
    remapper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remapper_module)
    
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = Mock(return_value=EMBED_MOCK_RESPONSE)
    
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    
    with patch.object(remapper_module, '_client', mock_client):
        remapper = remapper_module.RequestRemapper()
        
        ctx = HookContext(
            request_path="/embed",
            request_method="POST",
            request_headers={},
            request_body=json.dumps({"inputs": ["test"]}).encode(),
            backend_name="embed"
        )
        
        result = await remapper.remap(ctx)
        
        assert result.status_code == 200
        data = json.loads(result.content)
        assert isinstance(data, list), "Path /embed returns list"
        assert len(data) == 1
        assert isinstance(data[0], list)
        assert len(data[0]) == 1024


@pytest.mark.asyncio
async def test_embedding_remapper_returns_dict_for_embeddings_path():
    """Remapper returns OpenAI dict for /embeddings path."""
    
    remapper_path = Path(__file__).parent.parent / "samples" / "llama-server-embedding-tei-remapper.py"
    assert remapper_path.exists()
    
    import importlib.util
    from unittest.mock import AsyncMock, Mock, patch
    
    spec = importlib.util.spec_from_file_location("embedding_remapper", remapper_path)
    remapper_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(remapper_module)
    
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = Mock(return_value=EMBED_MOCK_RESPONSE)
    
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    
    with patch.object(remapper_module, '_client', mock_client):
        remapper = remapper_module.RequestRemapper()
        
        ctx = HookContext(
            request_path="/embeddings",
            request_method="POST",
            request_headers={},
            request_body=json.dumps({"input": ["test"]}).encode(),
            backend_name="embed"
        )
        
        result = await remapper.remap(ctx)
        
        assert result.status_code == 200
        data = json.loads(result.content)
        assert isinstance(data, dict), "Path /embeddings returns dict"
        assert "data" in data
        assert "model" in data
        assert len(data["data"]) == 1
        assert "embedding" in data["data"][0]
        assert len(data["data"][0]["embedding"]) == 1024
