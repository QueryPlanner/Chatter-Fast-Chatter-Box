"""
TTS model initialization and management.

Based on generate_turbo.py - uses ChatterboxTurboTTS for faster generation.
"""

from __future__ import annotations

import asyncio
import gc
import logging

from app.config import Config
import torch
import torchaudio as ta
from chatterbox.tts_turbo import ChatterboxTurboTTS
from app.core.audio import stitch_chunk_files
from app.core.text import split_text_into_chunks

logger = logging.getLogger(__name__)

# Global model instance
_model: ChatterboxTurboTTS | None = None
_device: str | None = None
_initialization_error: str | None = None
_chunk_counter: int = 0
GC_EVERY_N_CHUNKS: int = 5


def resolve_device(explicit: str | None = None) -> str:
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
    mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    if mps_available:
        return "mps"

    return "cpu"


def _apply_cpu_threading_budget() -> None:
    """
    Set PyTorch intra/inter-op threads for CPU-side work (e.g. convolutions, MP3
    prep). OpenMP/MKL were configured from Config at import; this aligns torch.
    """
    num = Config.TORCH_NUM_THREADS
    # Inter-op parallelism: small default keeps overhead low; scales slightly with n.
    interop = max(1, min(8, num // 4 or 1))
    try:
        torch.set_num_interop_threads(interop)
    except (RuntimeError, ValueError):
        logger.debug("torch.set_num_interop_threads not applied (already in use)")

    try:
        torch.set_num_threads(num)
    except (RuntimeError, ValueError) as e:
        logger.warning("Could not set torch.set_num_threads(%s): %s", num, e)

    logger.info("CPU inference thread budget: torch_threads=%s, interop=%s (OMP=%s)", num, interop, num)


async def initialize_model(device: str | None = None) -> ChatterboxTurboTTS:
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
            None, lambda: ChatterboxTurboTTS.from_pretrained(device=_device)
        )

        _apply_cpu_threading_budget()

        # Performance optimization: Disable CPU-heavy numpy watermarking
        if hasattr(_model, "watermarker") and hasattr(_model.watermarker, "apply_watermark"):
            _model.watermarker.apply_watermark = lambda wav, sample_rate: wav
            logger.info("Disabled audio watermarking for performance optimization")

        _initialization_error = None
        print(f"Model loaded successfully on {_device}")
        return _model

    except Exception as e:
        _initialization_error = str(e)
        print(f"Failed to initialize model: {e}")
        logger.exception("ChatterboxTurboTTS failed to load")
        raise


def get_model() -> ChatterboxTurboTTS | None:
    """Get the current model instance."""
    return _model


def get_device() -> str | None:
    """Get the current device."""
    return _device


def get_initialization_error() -> str | None:
    """Get initialization error if any."""
    return _initialization_error


def is_ready() -> bool:
    """Check if the model is ready for use."""
    return _model is not None


def generate_single_chunk(
    text: str,
    output_path: str,
    reference_audio_path: str | None = None,
) -> None:
    """
    Generate audio for a single text chunk and write WAV to disk.

    This writes the result immediately and frees the tensor, keeping
    memory usage proportional to a single chunk rather than the full chapter.

    Args:
        text: Text for this chunk
        output_path: Where to write the WAV file
        reference_audio_path: Optional reference audio for voice cloning

    Raises:
        RuntimeError: If model is not initialized
    """

    global _chunk_counter

    if _model is None:
        raise RuntimeError("Model not initialized. Call initialize_model() first.")

    with torch.inference_mode():
        if reference_audio_path is not None:
            audio_tensor = _model.generate(text, audio_prompt_path=reference_audio_path)
        else:
            audio_tensor = _model.generate(text)

    # Move to CPU and save immediately
    if hasattr(audio_tensor, "cpu"):
        audio_tensor = audio_tensor.cpu()

    ta.save(output_path, audio_tensor, _model.sr, format="wav")
    
    # Explicitly free memory periodically to save time
    del audio_tensor
    _chunk_counter += 1
    if _chunk_counter % GC_EVERY_N_CHUNKS == 0:
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()


def get_sample_rate() -> int:
    """Get the model's sample rate."""
    if _model is None:
        raise RuntimeError("Model not initialized. Call initialize_model() first.")
    return int(_model.sr)


def generate_speech(
    text: str,
    reference_audio_path: str | None = None,
    max_sentences_per_chunk: int | None = None,
    max_chunk_chars: int | None = None,
    chunk_gap_ms: int | None = None,
    output_format: str = "mp3",
) -> tuple[bytes, str]:
    """
    Generate speech from text using ChatterboxTurboTTS.

    This function handles:
    - Text chunking for long inputs
    - Reference audio for voice cloning
    - Audio concatenation with gaps
    - Format conversion (WAV to MP3)

    Uses temp files per-chunk to avoid memory buildup on long inputs.

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
    import tempfile
    from pathlib import Path

    if _model is None:
        raise RuntimeError("Model not initialized. Call initialize_model() first.")

    resolved_max_sentences = (
        max_sentences_per_chunk
        if max_sentences_per_chunk is not None
        else Config.MAX_SENTENCES_PER_CHUNK
    )
    resolved_max_chars = max_chunk_chars if max_chunk_chars is not None else Config.MAX_CHUNK_CHARS
    resolved_gap_ms = chunk_gap_ms if chunk_gap_ms is not None else Config.CHUNK_GAP_MS

    # Split text into chunks
    chunks = split_text_into_chunks(
        text,
        max_sentences_per_chunk=resolved_max_sentences,
        max_chunk_chars=resolved_max_chars,
    )

    print(f"Synthesizing {len(text)} characters in {len(chunks)} chunk(s) ...")

    # Generate each chunk to a temp WAV file
    chunk_paths: list[str] = []
    tmp_dir = tempfile.mkdtemp(prefix="chatterbox_chunks_")

    try:
        for index, chunk in enumerate(chunks):
            print(f"  Chunk {index + 1}/{len(chunks)} ({len(chunk)} chars) ...")

            chunk_path = str(Path(tmp_dir) / f"chunk_{index:04d}.wav")

            # Only use reference audio for the first chunk (voice consistency)
            ref_path = reference_audio_path if index == 0 else None

            generate_single_chunk(
                text=chunk,
                output_path=chunk_path,
                reference_audio_path=ref_path,
            )
            chunk_paths.append(chunk_path)

        # Stitch all chunk files into final output
        final_path = str(Path(tmp_dir) / f"final.{output_format}")
        stitch_chunk_files(
            chunk_paths=chunk_paths,
            output_path=final_path,
            sample_rate=_model.sr,
            gap_ms=resolved_gap_ms,
            output_format=output_format,
        )

        # Read final file into bytes
        with open(final_path, "rb") as f:
            audio_bytes = f.read()

        content_type = "audio/wav" if output_format.lower() == "wav" else "audio/mpeg"
        return audio_bytes, content_type

    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
