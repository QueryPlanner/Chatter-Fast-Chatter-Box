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
            assert call_kwargs["reference_audio_path"] == "/path/to/default.wav"

    def test_synthesize_with_voice(self, client: TestClient, temp_voices_dir: Path):
        """Test synthesis with voice from library."""
        from app.core.voices import VoiceLibrary

        voice_path = temp_voices_dir / "test_voice.wav"
        voice_path.write_bytes(b"RIFF" + b"\x00" * 100 + b"WAVE")

        voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)
        voice_lib.scan_voices()

        mock_audio = b"audio_data"
        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
            patch("app.api.endpoints.speech.get_voice_library", return_value=voice_lib),
        ):
            mock_gen.return_value = (mock_audio, "audio/mpeg")

            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                    "voice": "test_voice",
                },
            )

            assert response.status_code == 200
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["reference_audio_path"] is not None

    def test_synthesize_voice_not_found(self, client: TestClient):
        """Test synthesis with non-existent voice."""
        mock_voice_lib = MagicMock()
        mock_voice_lib.get_voice_path.return_value = None

        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.get_voice_library", return_value=mock_voice_lib),
        ):
            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                    "voice": "nonexistent",
                },
            )

            assert response.status_code == 404

    def test_synthesize_with_reference_audio(self, client: TestClient):
        """Test synthesis with uploaded reference audio."""
        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"
        mock_audio = b"generated_audio"

        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
        ):
            mock_gen.return_value = (mock_audio, "audio/mpeg")

            response = client.post(
                "/api/synthesize",
                data={"text": "Hello world"},
                files={"reference_audio": ("ref.wav", io.BytesIO(audio_content), "audio/wav")},
            )

            assert response.status_code == 200
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["reference_audio_path"] is not None

    def test_synthesize_wav_format(self, client: TestClient):
        """Test synthesis with WAV output format."""
        mock_audio = b"wav_audio_data"
        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
        ):
            mock_gen.return_value = (mock_audio, "audio/wav")

            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                    "output_format": "wav",
                },
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/wav"

    def test_synthesize_custom_parameters(self, client: TestClient):
        """Test synthesis with custom parameters."""
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
                    "max_sentences_per_chunk": 10,
                    "max_chunk_chars": 500,
                    "chunk_gap_ms": 200,
                },
            )

            assert response.status_code == 200
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["max_sentences_per_chunk"] == 10
            assert call_kwargs["max_chunk_chars"] == 500
            assert call_kwargs["chunk_gap_ms"] == 200

    def test_synthesize_generation_error(self, client: TestClient):
        """Test synthesis with generation error."""
        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
        ):
            mock_gen.side_effect = RuntimeError("Generation failed")

            response = client.post(
                "/api/synthesize",
                data={
                    "text": "Hello world",
                },
            )

            assert response.status_code == 500
            assert "error" in response.json()["detail"]

    def test_synthesize_temp_file_cleanup(self, client: TestClient):
        """Test that temp file is cleaned up after synthesis."""

        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"
        mock_audio = b"generated_audio"

        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
            patch("tempfile.NamedTemporaryFile") as mock_temp,
        ):
            mock_gen.return_value = (mock_audio, "audio/mpeg")

            mock_tmp_file = MagicMock()
            mock_tmp_file.__enter__ = MagicMock(return_value=mock_tmp_file)
            mock_tmp_file.__exit__ = MagicMock(return_value=False)
            mock_tmp_file.write = MagicMock()
            mock_tmp_file.name = "/tmp/test_temp_audio.wav"
            mock_temp.return_value = mock_tmp_file

            response = client.post(
                "/api/synthesize",
                data={"text": "Hello world"},
                files={"reference_audio": ("ref.wav", io.BytesIO(audio_content), "audio/wav")},
            )

            assert response.status_code == 200

    def test_synthesize_temp_file_cleanup_on_error(self, client: TestClient):
        """Test that temp file is cleaned up even on error."""

        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"

        with (
            patch("app.api.endpoints.speech.is_ready", return_value=True),
            patch("app.api.endpoints.speech.generate_speech") as mock_gen,
            patch("tempfile.NamedTemporaryFile") as mock_temp,
        ):
            mock_gen.side_effect = RuntimeError("Generation failed")

            mock_tmp_file = MagicMock()
            mock_tmp_file.__enter__ = MagicMock(return_value=mock_tmp_file)
            mock_tmp_file.__exit__ = MagicMock(return_value=False)
            mock_tmp_file.write = MagicMock()
            mock_tmp_file.name = "/tmp/test_temp_audio.wav"
            mock_temp.return_value = mock_tmp_file

            response = client.post(
                "/api/synthesize",
                data={"text": "Hello world"},
                files={"reference_audio": ("ref.wav", io.BytesIO(audio_content), "audio/wav")},
            )

            assert response.status_code == 500

    def test_synthesize_default_voice_path_none(self, client: TestClient):
        """Test synthesis when default voice path returns None."""
        mock_voice_lib = MagicMock()
        mock_voice_lib.get_default_voice.return_value = "missing_voice"
        mock_voice_lib.get_voice_path.return_value = None

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
            assert call_kwargs["reference_audio_path"] is None

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
            assert call_kwargs["reference_audio_path"] is None
