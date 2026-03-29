"""
Configuration management for Fast-Chatterbox.

Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Config:
    """Application configuration from environment variables."""

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # TTS settings
    MAX_CHUNK_CHARS: int = int(os.getenv("MAX_CHUNK_CHARS", "320"))
    CHUNK_GAP_MS: int = int(os.getenv("CHUNK_GAP_MS", "120"))

    # Device: auto, cuda, mps, or cpu
    DEVICE: str = os.getenv("DEVICE", "auto")

    # Default voice
    DEFAULT_VOICE: Optional[str] = os.getenv("DEFAULT_VOICE", "dan")

    # Output format
    DEFAULT_OUTPUT_FORMAT: str = os.getenv("DEFAULT_OUTPUT_FORMAT", "mp3")

    @classmethod
    def validate(cls) -> None:
        """Validate configuration values."""
        if cls.MAX_CHUNK_CHARS < 50 or cls.MAX_CHUNK_CHARS > 1000:
            raise ValueError(f"MAX_CHUNK_CHARS must be between 50 and 1000, got {cls.MAX_CHUNK_CHARS}")

        if cls.CHUNK_GAP_MS < 0 or cls.CHUNK_GAP_MS > 1000:
            raise ValueError(f"CHUNK_GAP_MS must be between 0 and 1000, got {cls.CHUNK_GAP_MS}")

        if cls.DEVICE.lower() not in ("auto", "cuda", "mps", "cpu"):
            raise ValueError(f"DEVICE must be auto, cuda, mps, or cpu, got {cls.DEVICE}")

        if cls.DEFAULT_OUTPUT_FORMAT.lower() not in ("mp3", "wav"):
            raise ValueError(f"DEFAULT_OUTPUT_FORMAT must be mp3 or wav, got {cls.DEFAULT_OUTPUT_FORMAT}")
