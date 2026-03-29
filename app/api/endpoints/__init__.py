"""API endpoints."""

from app.api.endpoints.speech import router as speech_router
from app.api.endpoints.voices import router as voices_router
from app.api.endpoints.health import router as health_router

__all__ = ["speech_router", "voices_router", "health_router"]
