"""
Tests for app/api/endpoints/speech.py
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestSynthesize:
    """Tests for synthesize endpoint."""

    def test_synthesize_model_not_ready(self, client: TestClient):
        """Test synthesize when model not ready."""
        with patch("app.api.endpoints.speech.is_ready", return_value=False):
            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                },
            )

            assert response.status_code == 503
            assert "initializing" in response.json()["detail"]["error"]["message"].lower()

    def test_synthesize_invalid_format(self, client: TestClient):
        """Test synthesize with invalid output format."""
        with patch("app.api.endpoints.speech.is_ready", return_value=True):
            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                    "output_format": "ogg",
                },
            )

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"]["error"]["type"].lower()

    def test_synthesize_success(self, client: TestClient):
        """Test successful synthesis."""
        mock_audio = b"audio_data"
        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
        ):
            mock_gen.return_value = (mock_audio, "audio/mpeg")

            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                },
            )

            assert response.status_code == 200
            assert response.content == mock_audio
            assert response.headers["content-type"] == "audio/mpeg"

    def test_synthesize_with_default_voice(self, client: TestClient):
        """Test synthesis with default voice from library."""
        mock_voice_lib = MagicMock()
        mock_voice_lib.get_default_voice.return_value = "default_voice"
        mock_voice_lib.get_voice_path.return_value = "/path/to/default.wav"

        mock_audio = b"audio_data"
        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
            patch("app.api.endpoints.speech.get_voice_library", return_value=mock_voice_lib),
        ):
            mock_gen.return_value = (mock_audio, "audio/mpeg")

            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                },
            )

            assert response.status_code == 200
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["reference_audio_path"] == "alba"

    def test_synthesize_no_default_voice(self, client: TestClient):
        """Test synthesis when no default voice is set."""
        mock_voice_lib = MagicMock()
        mock_voice_lib.get_default_voice.return_value = None

        mock_audio = b"audio_data"
        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
            patch("app.api.endpoints.speech.get_voice_library", return_value=mock_voice_lib),
        ):
            mock_gen.return_value = (mock_audio, "audio/mpeg")

            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                },
            )

            assert response.status_code == 200
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["reference_audio_path"] == "alba"
