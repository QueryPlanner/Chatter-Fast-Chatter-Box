"""
Shared pytest fixtures for Fast-Chatterbox tests.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.core.database import BookRepository, init_db
from app.core.voices import VoiceLibrary


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    old_path = Config.DATABASE_PATH
    Config.DATABASE_PATH = str(db_path)

    init_db()

    yield db_path

    Config.DATABASE_PATH = old_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def temp_voices_dir() -> Generator[Path, None, None]:
    """Create a temporary voices directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        voices_dir = Path(tmpdir) / "voices"
        voices_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "voices": {},
            "aliases": {},
            "default_voice": "dan",
            "version": "1.0",
        }
        with open(voices_dir / "voices.json", "w") as f:
            json.dump(metadata, f)

        yield voices_dir


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        yield output_dir


@pytest.fixture
def sample_voice_file(temp_voices_dir: Path) -> Path:
    """Create a sample voice file for testing."""
    voice_path = temp_voices_dir / "test_voice.wav"
    voice_path.write_bytes(b"RIFF" + b"\x00" * 100 + b"WAVE")
    return voice_path


@pytest.fixture
def sample_mp3_audio() -> bytes:
    """Create sample MP3 audio bytes for testing."""
    return b"ID3" + b"\x00" * 100 + b"\xff\xfb"


@pytest.fixture
def sample_wav_audio() -> bytes:
    """Create sample WAV audio bytes for testing."""
    return b"RIFF" + b"\x00" * 100 + b"WAVE"


@pytest.fixture
def mock_tts_model():
    """Create a mock TTS model for testing."""
    import torch

    model = MagicMock()
    model.sr = 24000
    model.generate = MagicMock(return_value=torch.randn(1, 24000))
    return model


@pytest.fixture
def mock_chatterbox(mock_tts_model: MagicMock):
    """Mock the ChatterboxTurboTTS module."""
    with patch("app.core.tts.ChatterboxTurboTTS") as mock_cls:
        mock_cls.from_pretrained = MagicMock(return_value=mock_tts_model)
        yield mock_cls


@pytest.fixture
def mock_torch():
    """Mock torch for testing without GPU."""
    mock = MagicMock()
    mock.cuda.is_available = MagicMock(return_value=False)
    mock.backends.mps.is_available = MagicMock(return_value=False)
    mock.no_grad = MagicMock()
    mock.no_grad.return_value.__enter__ = MagicMock(return_value=None)
    mock.no_grad.return_value.__exit__ = MagicMock(return_value=None)
    return mock


@pytest.fixture
def client(temp_db: Path, temp_voices_dir: Path) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""

    with (
        patch("app.main.initialize_model", return_value=AsyncMock()),
        patch("app.main.book_worker_loop", return_value=AsyncMock()),
        patch("app.core.voices.DEFAULT_VOICES_DIR", temp_voices_dir),
    ):
        from app.main import create_app

        app = create_app()
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def book_repo(temp_db: Path) -> BookRepository:
    """Create a BookRepository with a temporary database."""
    return BookRepository()


@pytest.fixture
def voice_lib(temp_voices_dir: Path) -> VoiceLibrary:
    """Create a VoiceLibrary with a temporary voices directory."""
    return VoiceLibrary(voices_dir=temp_voices_dir)


@pytest.fixture
def sample_book_request() -> dict[str, Any]:
    """Create a sample book request payload."""
    return {
        "title": "Test Book",
        "voice": "test_voice",
        "output_format": "mp3",
        "chapters": [
            {
                "chapter_number": 1,
                "title": "Chapter 1",
                "text": "This is the first chapter text.",
            },
            {
                "chapter_number": 2,
                "title": "Chapter 2",
                "text": "This is the second chapter text.",
            },
        ],
        "config": {
            "max_sentences_per_chunk": 3,
            "max_chunk_chars": 320,
            "chunk_gap_ms": 120,
        },
    }


@pytest.fixture
def sample_chapter_data() -> dict[str, Any]:
    """Create sample chapter data for database tests."""
    return {
        "chapter_number": 1,
        "title": "Test Chapter",
        "text": "This is test chapter content.",
    }


@pytest.fixture
def env_config(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set environment variables for testing."""
    env_vars = {
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "DEVICE": "cpu",
        "MAX_CHUNK_CHARS": "320",
        "CHUNK_GAP_MS": "120",
        "DEFAULT_VOICE": "test_voice",
        "DEFAULT_OUTPUT_FORMAT": "mp3",
        "DATABASE_PATH": ":memory:",
        "WORKER_POLL_INTERVAL": "1",
        "MAX_CHAPTER_RETRIES": "3",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars
