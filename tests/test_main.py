"""
Tests for app/main.py
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import create_app, lifespan, main


class TestCreateApp:
    """Tests for create_app function."""

    def test_create_app(self):
        """Test that create_app returns a FastAPI app."""
        app = create_app()

        assert app is not None
        assert app.title == "Fast-Chatterbox"

    def test_app_has_cors_middleware(self):
        """Test that CORS middleware is configured."""
        app = create_app()

        from starlette.middleware.cors import CORSMiddleware

        has_cors = any(m.cls == CORSMiddleware for m in app.user_middleware)
        assert has_cors

    def test_app_includes_router(self):
        """Test that API router is included."""
        app = create_app()

        routes = [route.path for route in app.routes]
        assert "/api/synthesize" in routes
        assert "/api/voices" in routes


class TestLifespan:
    """Tests for lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_with_default_voice(self, temp_db):
        """Test lifespan with default voice set."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            voices_dir = Path(tmpdir) / "voices"
            voices_dir.mkdir()

            voice_file = voices_dir / "test_voice.wav"
            voice_file.write_bytes(b"RIFF" + b"\x00" * 100 + b"WAVE")

            from app.core.voices import VoiceLibrary

            mock_voice_lib = MagicMock(spec=VoiceLibrary)
            mock_voice_lib.list_voices.return_value = [{"name": "test_voice"}]
            mock_voice_lib.get_default_voice.return_value = "test_voice"
            mock_voice_lib.set_default_voice.return_value = True

            with (
                patch("app.main.Config") as mock_config,
                patch("app.main.get_voice_library", return_value=mock_voice_lib),
                patch("app.main.init_db"),
                patch("app.main.BookRepository") as mock_repo_cls,
                patch("app.main.initialize_model", new_callable=AsyncMock),
                patch("app.main.book_worker_loop", new_callable=AsyncMock),
            ):
                mock_config.validate = MagicMock()
                mock_config.DEVICE = "cpu"
                mock_config.MAX_CHUNK_CHARS = 320
                mock_config.DEFAULT_OUTPUT_FORMAT = "mp3"
                mock_config.DEFAULT_VOICE = "custom_voice"

                mock_repo = MagicMock()
                mock_repo.reset_processing_chapters.return_value = 0
                mock_repo_cls.return_value = mock_repo

                app = create_app()
                async with lifespan(app):
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_with_reset_count(self, temp_db):
        """Test lifespan with processing chapters to reset."""
        from app.core.voices import VoiceLibrary

        mock_voice_lib = MagicMock(spec=VoiceLibrary)
        mock_voice_lib.list_voices.return_value = []
        mock_voice_lib.get_default_voice.return_value = "dan"

        with (
            patch("app.main.Config") as mock_config,
            patch("app.main.get_voice_library", return_value=mock_voice_lib),
            patch("app.main.init_db"),
            patch("app.main.BookRepository") as mock_repo_cls,
            patch("app.main.initialize_model", new_callable=AsyncMock),
            patch("app.main.book_worker_loop", new_callable=AsyncMock),
        ):
            mock_config.validate = MagicMock()
            mock_config.DEVICE = "cpu"
            mock_config.MAX_CHUNK_CHARS = 320
            mock_config.DEFAULT_OUTPUT_FORMAT = "mp3"
            mock_config.DEFAULT_VOICE = None

            mock_repo = MagicMock()
            mock_repo.reset_processing_chapters.return_value = 5
            mock_repo_cls.return_value = mock_repo

            app = create_app()
            async with lifespan(app):
                pass

    @pytest.mark.asyncio
    async def test_lifespan_cancels_pending_tasks(self, temp_db):
        """Test that lifespan cancels pending tasks on shutdown."""
        from app.core.voices import VoiceLibrary

        mock_voice_lib = MagicMock(spec=VoiceLibrary)
        mock_voice_lib.list_voices.return_value = []
        mock_voice_lib.get_default_voice.return_value = None

        model_task = asyncio.create_task(asyncio.sleep(10))
        worker_task = asyncio.create_task(asyncio.sleep(10))

        with (
            patch("app.main.Config") as mock_config,
            patch("app.main.get_voice_library", return_value=mock_voice_lib),
            patch("app.main.init_db"),
            patch("app.main.BookRepository") as mock_repo_cls,
            patch("app.main.initialize_model", new_callable=AsyncMock, return_value=None),
            patch("app.main.book_worker_loop", new_callable=AsyncMock, return_value=None),
        ):
            mock_config.validate = MagicMock()
            mock_config.DEVICE = "cpu"
            mock_config.MAX_CHUNK_CHARS = 320
            mock_config.DEFAULT_OUTPUT_FORMAT = "mp3"
            mock_config.DEFAULT_VOICE = None

            mock_repo = MagicMock()
            mock_repo.reset_processing_chapters.return_value = 0
            mock_repo_cls.return_value = mock_repo

            app = create_app()

            with patch("asyncio.create_task") as mock_create_task:
                mock_create_task.side_effect = [model_task, worker_task]

                async with lifespan(app):
                    pass

                model_task.cancel()
                worker_task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await model_task
                with pytest.raises(asyncio.CancelledError):
                    await worker_task


class TestMain:
    """Tests for main function."""

    def test_main_calls_uvicorn(self):
        """Test that main calls uvicorn.run."""
        import uvicorn

        with (
            patch.object(uvicorn, "run") as mock_run,
        ):
            from app.config import Config

            with patch.object(Config, "HOST", "0.0.0.0"), patch.object(
                Config, "PORT", 8000
            ):
                main()

                mock_run.assert_called_once()
                call_args = mock_run.call_args
                assert call_args[0][0] == "app.main:app"
                assert call_args[1]["host"] == "0.0.0.0"
                assert call_args[1]["port"] == 8000
                assert call_args[1]["reload"] is True
