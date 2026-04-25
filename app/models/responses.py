"""
Shared API response models.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ErrorDetails(BaseModel):
    """Structured error payload for business-level API errors."""

    message: str = Field(..., description="Human-readable error message")
    type: str = Field(..., description="Stable machine-readable error code")


class ErrorResponse(BaseModel):
    """Top-level error response wrapper."""

    error: ErrorDetails


class VoiceInfo(BaseModel):
    """Voice metadata returned by voice endpoints."""

    name: str
    filename: str
    file_size: int
    created: Optional[str] = None
    exists: bool = True


class VoicesResponse(BaseModel):
    """Voice list payload."""

    voices: list[VoiceInfo]
    count: int
    default_voice: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check payload with model state details."""

    status: str
    model_loaded: bool
    device: Optional[str] = None
    default_voice: Optional[str] = None
    error: Optional[str] = None
