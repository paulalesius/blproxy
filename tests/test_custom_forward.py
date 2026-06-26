"""Unit and integration tests for custom forward backends (backends.custom.*).

Uses respx for mocking the target backend HTTP calls, consistent with other tests.
"""

import pytest
import respx
import httpx
from fastapi.testclient import TestClient

from src.llmproxy.config import set_config, reload_config
from src.llmproxy.config.models import AppConfig, BackendConfig, ServerConfig, LockConfig
from src.llmproxy.app import create_app


def make_test_config_with_custom() -> AppConfig:
    """Create a minimal AppConfig with one custom forward backend for testing."""
    custom_backend = BackendConfig(
        name="my_test_service",
        url="http://127.0.0.1:9999",
        type="forward",
        path_prefix="/my-service",
        strip_prefix=True,
        locks=["llm"],  # locks the llm backend while this runs
        timeout=10,
        read_timeout=30,
    )

    # Also include a core backend so locking has something to lock
    llm_backend = BackendConfig(
        name="llm",
        url="http://127.0.0.1:8080",
        locks=["embed"],
    )

    embed_backend = BackendConfig(
        name="embed",
        url="http://127.0.0.1:8081",
    )

    # Build lock.backends map from backend.locks lists (same logic as loader.py)
    lock_backends_map: dict[str, list[str]] = {}
    for backend_name, backend_config in {
        "llm": llm_backend,
        "embed": embed_backend,
        "my_test_service": custom_backend,
    }.items():
        if backend_config.locks:
            lock_backends_map[backend_name] = list(backend_config.locks)

    return AppConfig(
        backends={
            "llm": llm_backend,
            "embed": embed_backend,
            "my_test_service": custom_backend,
        },
        server=ServerConfig(host="127.0.0.1", port=0, log_level="ERROR"),
        lock=LockConfig(enabled=True, locked_error=False, backends=lock_backends_map),
    )


@pytest.fixture
def custom_app(monkeypatch):
    """Create app with custom forward backend configured."""
    cfg = make_test_config_with_custom()
    set_config(cfg)

    app = create_app()
    yield app

    # cleanup
    set_config(None)  # type: ignore


@pytest.fixture
def sync_client(custom_app):
    """Sync client that uses the custom_app with lifespan."""
    with TestClient(custom_app) as client:
        yield client


class TestCustomForwardBasic:
    """Basic forwarding tests using mocked backend."""

    @respx.mock
    def test_custom_forward_get(self, sync_client):
        """GET request to custom path is forwarded (with prefix stripping)."""
        # Mock the target backend
        route = respx.get("http://127.0.0.1:9999/hello").mock(
            return_value=httpx.Response(200, json={"msg": "from backend"})
        )

        resp = sync_client.get("/my-service/hello?foo=bar")

        assert resp.status_code == 200
        assert resp.json() == {"msg": "from backend"}
        assert route.called
        # Verify query params were forwarded
        assert "foo=bar" in str(route.calls.last.request.url)

    @respx.mock
    def test_custom_forward_post_json(self, sync_client):
        """POST with JSON body is forwarded transparently."""
        route = respx.post("http://127.0.0.1:9999/submit").mock(
            return_value=httpx.Response(201, json={"status": "created"})
        )

        payload = {"data": "test payload"}
        resp = sync_client.post("/my-service/submit", json=payload)

        assert resp.status_code == 201
        assert resp.json()["status"] == "created"
        assert route.called
        sent_body = route.calls.last.request.content
        assert b"test payload" in sent_body

    @respx.mock
    def test_custom_forward_streaming_sse(self, sync_client):
        """Streaming SSE response from custom backend is passed through."""
        sse_content = (
            'data: {"chunk": 1}\n\n'
            'data: {"chunk": 2}\n\n'
            "data: [DONE]\n\n"
        )
        route = respx.get("http://127.0.0.1:9999/stream").mock(
            return_value=httpx.Response(
                200,
                content=sse_content,
                headers={"Content-Type": "text/event-stream"},
            )
        )

        resp = sync_client.get("/my-service/stream")

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        assert "chunk" in resp.text
        assert route.called

    @respx.mock
    def test_custom_forward_error_propagation(self, sync_client):
        """Backend errors (4xx/5xx) are propagated to client."""
        route = respx.get("http://127.0.0.1:9999/notfound").mock(
            return_value=httpx.Response(404, json={"error": "not found in backend"})
        )

        resp = sync_client.get("/my-service/notfound")

        assert resp.status_code == 404
        assert "not found in backend" in resp.text
        assert route.called


class TestCustomForwardPathHandling:
    """Test path_prefix and strip_prefix behavior."""

    @respx.mock
    def test_strip_prefix_enabled(self, sync_client):
        """With strip_prefix=True, /my-service/foo → backend /foo."""
        route = respx.get("http://127.0.0.1:9999/foo").mock(
            return_value=httpx.Response(200, json={"stripped": True})
        )

        resp = sync_client.get("/my-service/foo")

        assert resp.status_code == 200
        assert route.called
        # The request to backend should NOT contain /my-service
        assert "/my-service" not in str(route.calls.last.request.url)

    @respx.mock
    def test_no_strip_prefix(self, monkeypatch):
        """When strip_prefix=False, the full path is forwarded."""
        cfg = make_test_config_with_custom()
        # Override to disable stripping
        cfg.backends["my_test_service"].strip_prefix = False
        set_config(cfg)

        app = create_app()
        
        with TestClient(app) as client:
            route = respx.get("http://127.0.0.1:9999/my-service/bar").mock(
                return_value=httpx.Response(200, json={"full_path": True})
            )

            resp = client.get("/my-service/bar")
            assert resp.status_code == 200
            assert route.called


class TestCustomForwardLockingIntegration:
    """Verify that custom backends participate in global locking."""

    def test_custom_backend_locks_configured_backends(self, custom_app):
        """Accessing a custom backend should trigger lock acquisition for its 'locks' list."""
        # This is a lightweight check: we verify the lock config was loaded correctly
        from src.llmproxy.config import get_config

        cfg = get_config()
        assert "my_test_service" in cfg.backends
        assert cfg.backends["my_test_service"].type == "forward"
        assert cfg.backends["my_test_service"].locks == ["llm"]

        # The lock.backends map should contain the mapping
        assert "my_test_service" in cfg.lock.backends
        assert "llm" in cfg.lock.backends["my_test_service"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
