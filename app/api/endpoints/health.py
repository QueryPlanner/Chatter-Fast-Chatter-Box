"""
Health check endpoint.
"""

from fastapi import APIRouter

from app.core.tts import get_device, get_initialization_error, get_model
from app.core.voices import get_voice_library
from app.models.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check API health and model status",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the current status of the server and model.
    """
    model = get_model()
    device = get_device()
    error = get_initialization_error()

    voice_lib = get_voice_library()
    default_voice = voice_lib.get_default_voice()

    if error:
        status = "error"
    elif model is not None:
        status = "healthy"
    else:
        status = "initializing"

    return HealthResponse(
        status=status,
        model_loaded=model is not None,
        device=device,
        default_voice=default_voice,
        error=error,
    )


@router.get(
    "/ping",
    summary="Simple ping",
    description="Basic connectivity test",
)
async def ping() -> dict:
    """
    Simple ping endpoint for connectivity testing.

    Always returns immediately, even during model initialization.
    """
    return {"status": "ok", "message": "Server is running"}
