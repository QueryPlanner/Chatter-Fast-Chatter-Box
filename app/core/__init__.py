"""Core TTS functionality."""

from app.core.text import split_text_into_chunks
from app.core.tts import get_model, is_ready, initialize_model
from app.core.audio import concatenate_with_gap, tensor_to_audio_bytes

__all__ = [
    "split_text_into_chunks",
    "get_model",
    "is_ready",
    "initialize_model",
    "concatenate_with_gap",
    "tensor_to_audio_bytes",
]
