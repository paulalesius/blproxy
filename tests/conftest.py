"""Shared fixtures for llmproxy tests - Mocked by default for reliability."""

import pytest
import httpx
import respx
from fastapi.testclient import TestClient
from pathlib import Path


# ============================================================
# MOCKED APP (DEFAULT - Recommended)
# ============================================================

@pytest.fixture(scope="session")
def app():
    """FastAPI app with all backends mocked. Used by default."""
    from src.llmproxy.app import create_app

    with respx.mock:
        # LLM backend (8080)
        respx.post("http://127.0.0.1:8080/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "Mocked response"}}]
            })
        )
        respx.post("http://127.0.0.1:8080/v1/completions").mock(
            return_value=httpx.Response(200, json={
                "id": "cmpl-mock", "object": "text_completion",
                "choices": [{"text": "Mocked completion"}]
            })
        )
        respx.get("http://127.0.0.1:8080/v1/models").mock(
            return_value=httpx.Response(200, json={"data": [{"id": "mock-llm"}]})
        )

        # Embeddings backend (8081)
        respx.post("http://127.0.0.1:8081/v1/embeddings").mock(
            return_value=httpx.Response(200, json={
                "object": "list",
                "data": [{"embedding": [0.1]*1024, "index": 0}]
            })
        )

        # Rerank backend (8082)
        respx.post("http://127.0.0.1:8082/rerank").mock(
            return_value=httpx.Response(200, json={"results": [{"index": 0, "score": 0.95}]})
        )
        respx.get("http://127.0.0.1:8082/v1/models").mock(
            return_value=httpx.Response(200, json=[{"id": "mock-reranker"}])
        )

        app = create_app()
        yield app


@pytest.fixture
def sync_client(app):
    """Sync client that uses the mocked app by default."""
    with TestClient(app) as client:
        yield client


# ============================================================
# Real server (only when you explicitly want live backends)
# ============================================================

@pytest.fixture(scope="session")
def llmproxy_server():
    """Real server with real backends. Only use when needed."""
    import os
    import subprocess
    import time

    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "config.test.yaml"

    proc = subprocess.Popen(
        ["python3", "-m", "src.llmproxy.main", "-c", str(config_path)],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    base_url = "http://127.0.0.1:4002"
    for _ in range(15):
        try:
            if httpx.get(f"{base_url}/health", timeout=2).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("Real server failed to start")

    yield base_url
    proc.terminate()
