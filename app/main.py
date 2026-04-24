"""
FastAPI application entry point for Fast-Chatterbox.

Chatterbox TTS server with:
- Text-to-speech synthesis using ChatterboxTurboTTS
- Voice library management
- MP3/WAV output formats
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import Config
from app.core.database import BookRepository, init_db
from app.core.tts import initialize_model
from app.core.voices import get_voice_library
from app.core.worker import book_worker_loop

logger = logging.getLogger(__name__)

ASCII_BANNER = r"""
  ╭──────────────────────────╮
  │  FAST-CHATTERBOX SERVER  │
  │     ıllılı.ılılı.ılı     │
  ╰─╮ ╭──────────────────────╯
    ╰─╯ Powered by Chatterbox
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(ASCII_BANNER)

    Config.validate()
    logger.info("Configuration validated:")
    logger.info(f"  - Device: {Config.DEVICE}")
    logger.info(f"  - Max chunk chars: {Config.MAX_CHUNK_CHARS}")
    logger.info(f"  - Default output format: {Config.DEFAULT_OUTPUT_FORMAT}")

    logger.info("Initializing voice library...")
    voice_lib = get_voice_library()
    voices = voice_lib.list_voices()
    logger.info(f"  - Found {len(voices)} voices")
    default_voice = voice_lib.get_default_voice()
    if default_voice:
        logger.info(f"  - Default voice: {default_voice}")

    if Config.DEFAULT_VOICE:
        voice_lib.set_default_voice(Config.DEFAULT_VOICE)

    logger.info("Starting model initialization...")
    model_init_task = asyncio.create_task(initialize_model(Config.DEVICE))

    logger.info("Initializing SQLite database...")
    init_db()

    logger.info("Running crash recovery for jobs...")
    repo = BookRepository()
    reset_count = repo.reset_processing_chapters()
    if reset_count > 0:
        logger.info(f"  - Reset {reset_count} chapters from 'processing' to 'pending'")

    logger.info("Starting background book worker...")
    worker_task = asyncio.create_task(book_worker_loop())

    yield

    logger.info("Shutting down...")

    if not model_init_task.done():
        model_init_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await model_init_task

    if not worker_task.done():
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Fast-Chatterbox",
        description=(
            "FastAPI server for Chatterbox TTS with voice cloning support. "
            "Generate speech from text using ChatterboxTurboTTS with support for "
            "voice cloning, MP3/WAV output, and long text chunking."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router)

    return app


# Create the application instance
app = create_app()


def main() -> None:
    """Entry point for the server."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
