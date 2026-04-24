"""
API router configuration.
"""

from fastapi import APIRouter

from app.api.endpoints.speech import router as speech_router
from app.api.endpoints.voices import router as voices_router
from app.api.endpoints.health import router as health_router
from app.api.endpoints.books import router as books_router

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health_router)
api_router.include_router(speech_router)
api_router.include_router(voices_router)
api_router.include_router(books_router)
