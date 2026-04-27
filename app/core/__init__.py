"""Core TTS functionality."""

from app.core.audio import concatenate_with_gap, stitch_chunk_files, tensor_to_audio_bytes
from app.core.text import split_text_into_chunks
from app.core.tts import generate_single_chunk, get_model, get_sample_rate, initialize_model, is_ready

__all__ = [
    "split_text_into_chunks",
    "get_model",
    "is_ready",
    "initialize_model",
    "concatenate_with_gap",
    "tensor_to_audio_bytes",
    "stitch_chunk_files",
    "generate_single_chunk",
    "get_sample_rate",
]
