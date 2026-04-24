"""
TTS model initialization and management.

Based on generate_turbo.py - uses ChatterboxTurboTTS for faster generation.
"""

from __future__ import annotations

import asyncio
from typing import Optional, List

import torch
from chatterbox.tts_turbo import ChatterboxTurboTTS

from app.core.text import split_text_into_chunks
from app.core.audio import concatenate_with_gap, tensor_to_audio_bytes


# Global model instance
_model: Optional[ChatterboxTurboTTS] = None
_device: Optional[str] = None
_initialization_error: Optional[str] = None


def resolve_device(explicit: Optional[str] = None) -> str:
    """
    Determine the best available device for TTS.

    Priority: cuda > mps > cpu

    Args:
        explicit: Optional explicit device override

    Returns:
        Device string: "cuda", "mps", or "cpu"
    """
    if explicit and explicit.lower() != "auto":
        return explicit.lower()

    if torch.cuda.is_available():
        return "cuda"

    # Check for MPS (Apple Silicon)
    mps_available = (
        hasattr(torch.backends, "mps") and
        torch.backends.mps.is_available()
    )
    if mps_available:
        return "mps"

    return "cpu"


async def initialize_model(device: Optional[str] = None) -> ChatterboxTurboTTS:
    """
    Initialize the ChatterboxTurboTTS model asynchronously.

    Args:
        device: Optional device override ("cuda", "mps", "cpu", or "auto")

    Returns:
        The initialized model instance
    """
    global _model, _device, _initialization_error

    try:
        _device = resolve_device(device)
        print(f"Loading ChatterboxTurboTTS on device={_device!r} ...")

        # Run model loading in executor to avoid blocking
        loop = asyncio.get_event_loop()
        _model = await loop.run_in_executor(
            None,
            lambda: ChatterboxTurboTTS.from_pretrained(device=_device)
        )

        _initialization_error = None
        print(f"Model loaded successfully on {_device}")
        return _model

    except Exception as e:
        _initialization_error = str(e)
        print(f"Failed to initialize model: {e}")
        raise


def get_model() -> Optional[ChatterboxTurboTTS]:
    """Get the current model instance."""
    return _model


def get_device() -> Optional[str]:
    """Get the current device."""
    return _device


def get_initialization_error() -> Optional[str]:
    """Get initialization error if any."""
    return _initialization_error


def is_ready() -> bool:
    """Check if the model is ready for use."""
    return _model is not None


def generate_speech(
    text: str,
    reference_audio_path: Optional[str] = None,
    max_sentences_per_chunk: int = 5,
    max_chunk_chars: int = 320,
    chunk_gap_ms: int = 120,
    output_format: str = "mp3",
) -> tuple[bytes, str]:
    """
    Generate speech from text using ChatterboxTurboTTS.

    This function handles:
    - Text chunking for long inputs
    - Reference audio for voice cloning
    - Audio concatenation with gaps
    - Format conversion (WAV to MP3)

    Args:
        text: Input text to synthesize
        reference_audio_path: Optional path to reference audio for voice cloning
        max_sentences_per_chunk: Maximum sentences per chunk
        max_chunk_chars: Maximum characters per chunk
        chunk_gap_ms: Gap between chunks in milliseconds
        output_format: "mp3" or "wav"

    Returns:
        Tuple of (audio_bytes, content_type)

    Raises:
        RuntimeError: If model is not initialized
    """
    if _model is None:
        raise RuntimeError("Model not initialized. Call initialize_model() first.")

    # Split text into chunks
    chunks = split_text_into_chunks(text, max_sentences_per_chunk=max_sentences_per_chunk, max_chunk_chars=max_chunk_chars)

    print(f"Synthesizing {len(text)} characters in {len(chunks)} chunk(s) ...")

    # Generate audio for each chunk
    audio_tensors: List[torch.Tensor] = []

    for index, chunk in enumerate(chunks):
        print(f"  Chunk {index + 1}/{len(chunks)} ({len(chunk)} chars) ...")

        # Only use reference audio for the first chunk (voice consistency)
        ref_path = None
        if reference_audio_path is not None and index == 0:
            ref_path = reference_audio_path

        # Generate audio
        with torch.no_grad():
            if ref_path is not None:
                audio_tensor = _model.generate(chunk, audio_prompt_path=ref_path)
            else:
                # Use model's built-in voice (conds.pt from checkpoint)
                audio_tensor = _model.generate(chunk)

        audio_tensors.append(audio_tensor)

    # Concatenate chunks with gap
    final_audio = concatenate_with_gap(
        audio_tensors,
        _model.sr,
        gap_ms=chunk_gap_ms,
    )

    # Convert to output format
    return tensor_to_audio_bytes(final_audio, _model.sr, output_format)
