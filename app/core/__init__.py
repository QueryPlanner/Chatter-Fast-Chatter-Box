"""Core TTS functionality."""

from app.core.text import split_text_into_chunks
from app.core.tts import get_model, is_ready, initialize_model
from app.core.audio import wav_to_mp3, concatenate_with_gap

__all__ = [
    "split_text_into_chunks",
    "get_model",
    "is_ready",
    "initialize_model",
    "wav_to_mp3",
    "concatenate_with_gap",
]
