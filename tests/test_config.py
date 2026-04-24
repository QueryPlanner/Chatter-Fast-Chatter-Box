"""
Tests for app/config.py
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import Config


class TestConfig:
    """Tests for the Config class."""

    def test_default_values(self):
        """Test default configuration values."""
        assert Config.HOST == "0.0.0.0"
        assert Config.PORT == 8000
        assert Config.MAX_CHUNK_CHARS == 320
        assert Config.CHUNK_GAP_MS == 120
        assert Config.DEVICE == "auto"
        assert Config.DEFAULT_OUTPUT_FORMAT == "mp3"
        assert Config.WORKER_POLL_INTERVAL == 2
        assert Config.MAX_CHAPTER_RETRIES == 3

    def test_validate_valid_config(self):
        """Test validation passes with valid config."""
        with patch.object(Config, "MAX_CHUNK_CHARS", 100):
            with patch.object(Config, "CHUNK_GAP_MS", 100):
                with patch.object(Config, "DEVICE", "cuda"):
                    with patch.object(Config, "DEFAULT_OUTPUT_FORMAT", "wav"):
                        Config.validate()

    def test_validate_invalid_max_chunk_chars_too_low(self):
        """Test validation fails with MAX_CHUNK_CHARS too low."""
        with patch.object(Config, "MAX_CHUNK_CHARS", 10):
            with pytest.raises(ValueError, match="MAX_CHUNK_CHARS must be between 50 and 1000"):
                Config.validate()

    def test_validate_invalid_max_chunk_chars_too_high(self):
        """Test validation fails with MAX_CHUNK_CHARS too high."""
        with patch.object(Config, "MAX_CHUNK_CHARS", 2000):
            with pytest.raises(ValueError, match="MAX_CHUNK_CHARS must be between 50 and 1000"):
                Config.validate()

    def test_validate_invalid_chunk_gap_ms_negative(self):
        """Test validation fails with negative CHUNK_GAP_MS."""
        with patch.object(Config, "CHUNK_GAP_MS", -1):
            with pytest.raises(ValueError, match="CHUNK_GAP_MS must be between 0 and 1000"):
                Config.validate()

    def test_validate_invalid_chunk_gap_ms_too_high(self):
        """Test validation fails with CHUNK_GAP_MS too high."""
        with patch.object(Config, "CHUNK_GAP_MS", 2000):
            with pytest.raises(ValueError, match="CHUNK_GAP_MS must be between 0 and 1000"):
                Config.validate()

    def test_validate_invalid_device(self):
        """Test validation fails with invalid device."""
        with patch.object(Config, "DEVICE", "invalid"):
            with pytest.raises(ValueError, match="DEVICE must be auto, cuda, mps, or cpu"):
                Config.validate()

    def test_validate_invalid_output_format(self):
        """Test validation fails with invalid output format."""
        with patch.object(Config, "DEFAULT_OUTPUT_FORMAT", "ogg"):
            with pytest.raises(ValueError, match="DEFAULT_OUTPUT_FORMAT must be mp3 or wav"):
                Config.validate()

    def test_validate_device_case_insensitive(self):
        """Test device validation is case insensitive."""
        for device in ["CUDA", "Cuda", "cuda"]:
            with patch.object(Config, "DEVICE", device):
                Config.validate()

    def test_validate_output_format_case_insensitive(self):
        """Test output format validation is case insensitive."""
        for fmt in ["MP3", "Mp3", "mp3"]:
            with patch.object(Config, "DEFAULT_OUTPUT_FORMAT", fmt):
                Config.validate()

    def test_environment_variable_override(self, monkeypatch: pytest.MonkeyPatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("HOST", "127.0.0.1")
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("DEVICE", "cpu")
        monkeypatch.setenv("MAX_CHUNK_CHARS", "500")

        import importlib

        import app.config

        importlib.reload(app.config)

        assert app.config.Config.HOST == "127.0.0.1"
        assert app.config.Config.PORT == 9000
        assert app.config.Config.DEVICE == "cpu"
        assert app.config.Config.MAX_CHUNK_CHARS == 500

        monkeypatch.delenv("HOST")
        monkeypatch.delenv("PORT")
        monkeypatch.delenv("DEVICE")
        monkeypatch.delenv("MAX_CHUNK_CHARS")
