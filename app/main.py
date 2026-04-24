"""
FastAPI application entry point for Fast-Chatterbox.

Chatterbox TTS server with:
- Text-to-speech synthesis using ChatterboxTurboTTS
- Voice library management
- MP3/WAV output formats
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Config
from app.api.router import api_router
from app.core.tts import initialize_model, get_model, get_initialization_error
from app.core.voices import get_voice_library
from app.core.database import init_db, BookRepository
from app.core.worker import book_worker_loop


# ASCII art banner
ASCII_BANNER = r"""
  _____     _   _            _            _
 |  ___|_ _| |_| |_ ___ _ __| |__   _____| |_
 | |_ / _` | __| __/ _ \ '__| '_ \ / _ \ __|
 |  _| (_| | |_| ||  __/ |  | |_) |  __/ |_
 |_|  \__,_|\__|\__\___|_|  |_.__/ \___|\__|

  Fast TTS Server powered by Chatterbox
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    print(ASCII_BANNER)

    # Validate configuration
    Config.validate()
    print(f"Configuration validated:")
    print(f"  - Device: {Config.DEVICE}")
    print(f"  - Max chunk chars: {Config.MAX_CHUNK_CHARS}")
    print(f"  - Default output format: {Config.DEFAULT_OUTPUT_FORMAT}")

    # Initialize voice library
    print("Initializing voice library...")
    voice_lib = get_voice_library()
    voices = voice_lib.list_voices()
    print(f"  - Found {len(voices)} voices")
    default_voice = voice_lib.get_default_voice()
    if default_voice:
        print(f"  - Default voice: {default_voice}")

    # Set default voice from config if specified
    if Config.DEFAULT_VOICE:
        voice_lib.set_default_voice(Config.DEFAULT_VOICE)

    # Start model initialization in background
    print("Starting model initialization...")
    model_init_task = asyncio.create_task(initialize_model(Config.DEVICE))

    # Initialize Database
    print("Initializing SQLite database...")
    init_db()

    # Crash recovery for books
    print("Running crash recovery for jobs...")
    repo = BookRepository()
    reset_count = repo.reset_processing_chapters()
    if reset_count > 0:
        print(f"  - Reset {reset_count} chapters from 'processing' to 'pending'")

    # Start book worker
    print("Starting background book worker...")
    worker_task = asyncio.create_task(book_worker_loop())

    # Yield control to the application
    yield

    # Shutdown
    print("Shutting down...")

    # Cancel model initialization if still running
    if not model_init_task.done():
        model_init_task.cancel()
        try:
            await model_init_task
        except asyncio.CancelledError:
            pass

    # Cancel worker task
    if not worker_task.done():
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


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


def main():
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
