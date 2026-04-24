"""
Tests for app/api/endpoints/voices.py
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.voices import VoiceLibrary


class TestListVoices:
    """Tests for list voices endpoint."""

    def test_list_voices_empty(self, client: TestClient, temp_voices_dir: Path):
        """Test listing voices when empty."""
        response = client.get("/api/voices")

        assert response.status_code == 200
        data = response.json()
        assert data["voices"] == []
        assert data["count"] == 0

    def test_list_voices_with_voices(
        self, client: TestClient, temp_voices_dir: Path, sample_voice_file: Path
    ):
        """Test listing voices with existing voices."""
        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)
            voice_lib.scan_voices()

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.get("/api/voices")

                assert response.status_code == 200
                data = response.json()
                assert data["count"] >= 1


class TestGetVoiceInfo:
    """Tests for get voice info endpoint."""

    def test_get_voice_info_not_found(self, client: TestClient):
        """Test getting non-existent voice info."""
        response = client.get("/api/voices/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]["error"]["message"].lower()

    def test_get_voice_info_success(
        self, client: TestClient, temp_voices_dir: Path, sample_voice_file: Path
    ):
        """Test getting existing voice info."""
        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)
            voice_lib.scan_voices()

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.get("/api/voices/test_voice")

                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "test_voice"


class TestUploadVoice:
    """Tests for upload voice endpoint."""

    def test_upload_voice_success(self, client: TestClient, temp_voices_dir: Path):
        """Test successful voice upload."""
        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"

        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.post(
                    "/api/voices",
                    data={"voice_name": "new_voice"},
                    files={"voice_file": ("new_voice.wav", io.BytesIO(audio_content), "audio/wav")},
                )

                assert response.status_code == 201
                assert "uploaded successfully" in response.json()["message"].lower()

    def test_upload_voice_unsupported_format(self, client: TestClient):
        """Test upload with unsupported format."""
        response = client.post(
            "/api/voices",
            data={"voice_name": "new_voice"},
            files={"voice_file": ("new_voice.txt", io.BytesIO(b"text"), "text/plain")},
        )

        assert response.status_code == 400
        assert "unsupported format" in response.json()["detail"]["error"]["message"].lower()

    def test_upload_voice_no_filename(self, client: TestClient):
        """Test upload with empty filename."""
        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"

        response = client.post(
            "/api/voices",
            data={"voice_name": "new_voice"},
            files={"voice_file": ("", io.BytesIO(audio_content), "audio/wav")},
        )

        assert response.status_code == 422

    def test_upload_voice_filename_none(self, client: TestClient, temp_voices_dir: Path):
        """Test upload when filename is None."""
        from io import BytesIO

        from fastapi import UploadFile

        from app.api.endpoints.voices import upload_voice

        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"

        mock_upload = UploadFile(file=BytesIO(audio_content), filename=None)

        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                import asyncio

                with pytest.raises(Exception) as exc_info:
                    asyncio.run(upload_voice(voice_name="new_voice", voice_file=mock_upload))

                assert exc_info.value.status_code == 400

    def test_upload_voice_already_exists(
        self, client: TestClient, temp_voices_dir: Path, sample_voice_file: Path
    ):
        """Test upload voice that already exists."""
        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"

        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)
            voice_lib.scan_voices()

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.post(
                    "/api/voices",
                    data={"voice_name": "test_voice"},
                    files={
                        "voice_file": ("test_voice.wav", io.BytesIO(audio_content), "audio/wav")
                    },
                )

                assert response.status_code == 409

    def test_upload_voice_invalid_name(self, client: TestClient, temp_voices_dir: Path):
        """Test upload with invalid voice name."""
        audio_content = b"RIFF" + b"\x00" * 100 + b"WAVE"

        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.post(
                    "/api/voices",
                    data={"voice_name": "voice/name"},
                    files={"voice_file": ("test.wav", io.BytesIO(audio_content), "audio/wav")},
                )

                assert response.status_code == 400


class TestDeleteVoice:
    """Tests for delete voice endpoint."""

    def test_delete_voice_success(
        self, client: TestClient, temp_voices_dir: Path, sample_voice_file: Path
    ):
        """Test successful voice deletion."""
        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)
            voice_lib.scan_voices()

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.delete("/api/voices/test_voice")

                assert response.status_code == 200
                assert "deleted" in response.json()["message"].lower()

    def test_delete_voice_not_found(self, client: TestClient):
        """Test deleting non-existent voice."""
        response = client.delete("/api/voices/nonexistent")

        assert response.status_code == 404


class TestSetDefaultVoice:
    """Tests for set default voice endpoint."""

    def test_set_default_voice_success(
        self, client: TestClient, temp_voices_dir: Path, sample_voice_file: Path
    ):
        """Test setting default voice."""
        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)
            voice_lib.scan_voices()

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.post(
                    "/api/voices/default",
                    data={"voice_name": "test_voice"},
                )

                assert response.status_code == 200
                assert "default voice set" in response.json()["message"].lower()

    def test_set_default_voice_not_found(self, client: TestClient):
        """Test setting non-existent voice as default."""
        response = client.post(
            "/api/voices/default",
            data={"voice_name": "nonexistent"},
        )

        assert response.status_code == 404


class TestDownloadVoice:
    """Tests for download voice endpoint."""

    def test_download_voice_success(
        self, client: TestClient, temp_voices_dir: Path, sample_voice_file: Path
    ):
        """Test downloading a voice file."""
        with patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir):
            voice_lib = VoiceLibrary(voices_dir=temp_voices_dir)
            voice_lib.scan_voices()

            with patch("app.api.endpoints.voices.get_voice_library", return_value=voice_lib):
                response = client.get("/api/voices/test_voice/download")

                assert response.status_code == 200
                assert response.headers["content-type"] == "audio/wav"

    def test_download_voice_not_found(self, client: TestClient):
        """Test downloading non-existent voice."""
        response = client.get("/api/voices/nonexistent/download")

        assert response.status_code == 404
