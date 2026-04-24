"""
Tests for app/api/endpoints/health.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_healthy(self, client: TestClient):
        """Test health check when model is loaded."""
        mock_model = MagicMock()
        with (
            patch("app.api.endpoints.health.get_model", return_value=mock_model),
            patch("app.api.endpoints.health.get_device", return_value="cuda"),
            patch("app.api.endpoints.health.get_initialization_error", return_value=None),
        ):
            mock_voice_lib = MagicMock()
            mock_voice_lib.get_default_voice.return_value = "test_voice"
            with patch("app.api.endpoints.health.get_voice_library", return_value=mock_voice_lib):
                response = client.get("/api/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["model_loaded"] is True
                assert data["device"] == "cuda"

    def test_health_initializing(self, client: TestClient):
        """Test health check when model is initializing."""
        with (
            patch("app.api.endpoints.health.get_model", return_value=None),
            patch("app.api.endpoints.health.get_device", return_value=None),
            patch("app.api.endpoints.health.get_initialization_error", return_value=None),
        ):
            mock_voice_lib = MagicMock()
            mock_voice_lib.get_default_voice.return_value = "default"
            with patch("app.api.endpoints.health.get_voice_library", return_value=mock_voice_lib):
                response = client.get("/api/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "initializing"
                assert data["model_loaded"] is False

    def test_health_error(self, client: TestClient):
        """Test health check with initialization error."""
        with (
            patch("app.api.endpoints.health.get_model", return_value=None),
            patch("app.api.endpoints.health.get_device", return_value="cpu"),
            patch("app.api.endpoints.health.get_initialization_error", return_value="Load failed"),
        ):
            mock_voice_lib = MagicMock()
            mock_voice_lib.get_default_voice.return_value = None
            with patch("app.api.endpoints.health.get_voice_library", return_value=mock_voice_lib):
                response = client.get("/api/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "error"
                assert data["error"] == "Load failed"


class TestPing:
    """Tests for ping endpoint."""

    def test_ping(self, client: TestClient):
        """Test ping endpoint."""
        response = client.get("/api/ping")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "running" in data["message"].lower()
