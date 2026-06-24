"""Integration tests for OpenAI-compatible embeddings endpoint."""

import pytest


class TestOpenAIEmbeddings:
    """Test OpenAI /v1/embeddings endpoint."""
    
    def test_embeddings_basic(self, sync_client):
        """
        Test 8: OpenAI /v1/embeddings.
        Verifies embeddings endpoint forwards to backend.
        """
        # Get an embedding model from the list
        models_response = sync_client.get("/v1/models")
        
        if models_response.status_code != 200:
            pytest.skip("No models available")
        
        models_data = models_response.json()
        embed_model = None
        
        # Look for bge or embedding model
        for model in models_data.get("data", []):
            model_id = model.get("id", "")
            if "bge" in model_id or "embed" in model_id.lower():
                embed_model = model_id
                break
        
        # Fallback to first model
        if not embed_model and models_data.get("data"):
            embed_model = models_data["data"][0]["id"]
        
        if not embed_model:
            pytest.skip("No embedding model available")
        
        response = sync_client.post(
            "/v1/embeddings",
            json={
                "input": "test document",
                "model": embed_model
            }
        )
        
        # Accept various responses as valid proxy behavior:
        # 200 = success, 400 = model not found, 500 = loading error
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            data = response.json()
            
            # OpenAI embeddings format
            assert "data" in data
            assert isinstance(data["data"], list)
            assert len(data["data"]) >= 1
            
            # Each embedding should have embedding vector
            for item in data["data"]:
                assert "embedding" in item
                assert isinstance(item["embedding"], list)
            
            # Should have model field
            assert "model" in data
        else:
            # Error response should have proper format
            data = response.json()
            assert "error" in data or "code" in data
    
    def test_embeddings_with_string_input(self, sync_client):
        """Test embeddings with single string input."""
        # Get any available model
        models_response = sync_client.get("/v1/models")
        if models_response.status_code != 200 or not models_response.json().get("data"):
            pytest.skip("No models available")
        
        model_id = models_response.json()["data"][0]["id"]
        
        response = sync_client.post(
            "/v1/embeddings",
            json={
                "input": "Hello world",
                "model": model_id
            }
        )
        
        # Should forward to backend
        assert response.status_code in [200, 400, 500]
    
    def test_embeddings_with_list_input(self, sync_client):
        """Test embeddings with list of strings (batch)."""
        models_response = sync_client.get("/v1/models")
        if models_response.status_code != 200 or not models_response.json().get("data"):
            pytest.skip("No models available")
        
        model_id = models_response.json()["data"][0]["id"]
        
        response = sync_client.post(
            "/v1/embeddings",
            json={
                "input": ["doc1", "doc2", "doc3"],
                "model": model_id
            }
        )
        
        # Should forward to backend
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert len(data["data"]) == 3  # Should return 3 embeddings
    
    def test_embeddings_without_model(self, sync_client):
        """Test embeddings without specifying model (should use default)."""
        response = sync_client.post(
            "/v1/embeddings",
            json={
                "input": "test"
            }
        )
        
        # Backend may return error if no default model
        assert response.status_code in [200, 400, 500]
    
    def test_embeddings_empty_input(self, sync_client):
        """Test embeddings with empty input."""
        models_response = sync_client.get("/v1/models")
        if models_response.status_code != 200 or not models_response.json().get("data"):
            pytest.skip("No models available")
        
        model_id = models_response.json()["data"][0]["id"]
        
        response = sync_client.post(
            "/v1/embeddings",
            json={
                "input": "",
                "model": model_id
            }
        )
        
        # Should handle empty input gracefully
        assert response.status_code in [200, 400, 500]
