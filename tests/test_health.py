"""Integration tests for health endpoint."""

import pytest


class TestHealth:
    """Test health check endpoint."""
    
    def test_health_endpoint(self, sync_client):
        """Test 1: Health endpoint returns healthy status."""
        response = sync_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, sync_client):
        """Test root endpoint returns service info."""
        response = sync_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "llmproxy"
        assert "status" in data
        assert data["status"] == "running"
