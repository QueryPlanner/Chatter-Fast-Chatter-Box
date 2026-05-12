"""
TTS model initialization and management.

Supports both ChatterboxTurboTTS and Kyutai Pocket TTS.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import torch
import torchaudio as ta

from app.config import Config
from app.core.audio import stitch_chunk_files
from app.core.text import split_text_into_chunks

logger = logging.getLogger(__name__)

# Global model instance
_model: Any | None = None
_device: str | None = None
_initialization_error: str | None = None
_chunk_counter: int = 0
GC_EVERY_N_CHUNKS: int = 5

_voice_state_cache: dict[str, object] = {}
MAX_VOICE_CACHE_SIZE = 10


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


async def initialize_model(device: str | None = None) -> Any:
    """
    Initialize the TTS model asynchronously based on TTS_ENGINE.

    Args:
        device: Optional device override ("cuda", "mps", "cpu", or "auto")

    Returns:
        The initialized model instance
    """
    global _model, _device, _initialization_error, _voice_state_cache

    try:
        _device = resolve_device(device)
        loop = asyncio.get_event_loop()

        if Config.TTS_ENGINE.lower() == "kyutai":
            from pocket_tts import TTSModel
            print(f"Loading Kyutai Pocket TTS on device={_device!r} ...")
            _model = await loop.run_in_executor(
                None, lambda: TTSModel.load_model()
            )
            _voice_state_cache.clear()
        else:
            from chatterbox.tts_turbo import ChatterboxTurboTTS
            print(f"Loading ChatterboxTurboTTS on device={_device!r} ...")
            _model = await loop.run_in_executor(
                None, lambda: ChatterboxTurboTTS.from_pretrained(device=_device)
            )

            # Performance optimization: Disable CPU-heavy numpy watermarking
            if hasattr(_model, "watermarker") and hasattr(_model.watermarker, "apply_watermark"):
                _model.watermarker.apply_watermark = lambda wav, sample_rate: wav
                logger.info("Disabled audio watermarking for performance optimization")

        _apply_cpu_threading_budget()

        _initialization_error = None
        print(f"Model loaded successfully on {_device}")
        return _model

    except Exception as e:
        _initialization_error = str(e)
        print(f"Failed to initialize model: {e}")
        logger.exception("TTS engine failed to load")
        raise


def get_model() -> Any | None:
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


def get_voice_state(prompt: str) -> object:
    """Retrieve or compute the voice state for Kyutai Pocket TTS."""
    if _model is None:
        raise RuntimeError("Model not initialized. Call initialize_model() first.")
    if prompt not in _voice_state_cache:
        if len(_voice_state_cache) >= MAX_VOICE_CACHE_SIZE:
            # Remove oldest entry to prevent memory leak
            _voice_state_cache.pop(next(iter(_voice_state_cache)))
        _voice_state_cache[prompt] = _model.get_state_for_audio_prompt(prompt)
    return _voice_state_cache[prompt]


def get_sample_rate() -> int:
    """Get the model's sample rate."""
    if _model is None:
        raise RuntimeError("Model not initialized. Call initialize_model() first.")
    
    if Config.TTS_ENGINE.lower() == "kyutai":
        return int(_model.sample_rate)
    return int(_model.sr)


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

    with torch.no_grad():
        if Config.TTS_ENGINE.lower() == "kyutai":
            prompt = reference_audio_path if reference_audio_path else "alba"
            voice_state = get_voice_state(prompt)
            audio_tensor = _model.generate_audio(voice_state, text)
            if len(audio_tensor.shape) == 1:
                audio_tensor = audio_tensor.unsqueeze(0)
        else:
            if reference_audio_path is not None:
                audio_tensor = _model.generate(text, audio_prompt_path=reference_audio_path)
            else:
                audio_tensor = _model.generate(text)

    # Move to CPU and save immediately
    if hasattr(audio_tensor, "cpu"):
        audio_tensor = audio_tensor.cpu()

    ta.save(output_path, audio_tensor, get_sample_rate(), format="wav")
    
    # Explicitly free memory periodically to save time
    del audio_tensor
    _chunk_counter += 1
    if _chunk_counter % GC_EVERY_N_CHUNKS == 0:
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()


def generate_speech(
    text: str,
    reference_audio_path: str | None = None,
    max_sentences_per_chunk: int | None = None,
    max_chunk_chars: int | None = None,
    chunk_gap_ms: int | None = None,
    output_format: str = "mp3",
) -> tuple[bytes, str]:
    """
    Generate speech from text using the configured TTS engine.

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
    import shutil

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
    tmp_dir = tempfile.mkdtemp(prefix="tts_chunks_")

    try:
        for index, chunk in enumerate(chunks):
            print(f"  Chunk {index + 1}/{len(chunks)} ({len(chunk)} chars) ...")

            chunk_path = str(Path(tmp_dir) / f"chunk_{index:04d}.wav")

            # Use the same reference audio for all chunks for voice consistency
            ref_path = reference_audio_path

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
            sample_rate=get_sample_rate(),
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
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def generate_speech_stream(
    text: str,
    reference_audio_path: str | None = None,
    max_sentences_per_chunk: int | None = None,
    max_chunk_chars: int | None = None,
    chunk_gap_ms: int | None = None,
    output_format: str = "mp3",
) -> AsyncGenerator[bytes, None]:
    import asyncio
    
    global _chunk_counter

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

    print(f"Streaming {len(text)} characters in {len(chunks)} chunk(s) ...")

    # Start ffmpeg process for seamless audio streaming
    ffmpeg_cmd = [
        "ffmpeg",
        "-f", "f32le",
        "-ar", str(get_sample_rate()),
        "-ac", "1",
        "-i", "pipe:0",
        "-f", output_format.lower(),
        "pipe:1"
    ]

    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    async def run_inference():
        global _chunk_counter
        try:
            for index, chunk in enumerate(chunks):
                print(f"  Streaming Chunk {index + 1}/{len(chunks)} ({len(chunk)} chars) ...")

                # Use the same reference audio for all chunks in the stream for voice consistency
                prompt = reference_audio_path if reference_audio_path else "alba"

                # Run inference in a separate thread to avoid blocking the event loop
                loop = asyncio.get_event_loop()

                def _generate_tensor(c=chunk, p=prompt):
                    with torch.no_grad():
                        if Config.TTS_ENGINE.lower() == "kyutai":
                            voice_state = get_voice_state(p)
                            audio = _model.generate_audio(voice_state, c)
                            if len(audio.shape) == 1:
                                audio = audio.unsqueeze(0)
                            return audio
                        else:
                            if p != "alba" and p is not None:
                                return _model.generate(c, audio_prompt_path=p)
                            else:
                                return _model.generate(c)

                audio_tensor = await loop.run_in_executor(None, _generate_tensor)

                if hasattr(audio_tensor, "cpu"):
                    audio_tensor = audio_tensor.cpu()

                # Add silence gap to prevent unnatural cutoffs at the end of chunks/sentences
                if resolved_gap_ms > 0:
                    gap_samples = max(0, int(get_sample_rate() * (resolved_gap_ms / 1000.0)))
                    silence = torch.zeros(1, gap_samples, dtype=audio_tensor.dtype, device=audio_tensor.device)
                    audio_tensor = torch.cat([audio_tensor, silence], dim=1)

                # Write raw float32 PCM bytes to ffmpeg
                pcm_bytes = audio_tensor.to(torch.float32).numpy().tobytes()
                process.stdin.write(pcm_bytes)
                await process.stdin.drain()

                # Free memory
                del audio_tensor
                _chunk_counter += 1
                if _chunk_counter % GC_EVERY_N_CHUNKS == 0:
                    if torch.backends.mps.is_available():
                        torch.mps.empty_cache()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    import gc
                    gc.collect()
        except Exception as e:
            logger.error(f"Inference error during stream: {e}")
        finally:
            if process.stdin:
                process.stdin.close()
                await process.stdin.wait_closed()

    inference_task = asyncio.create_task(run_inference())

    try:
        while True:
            out_chunk = await process.stdout.read(4096)
            if not out_chunk:
                break
            yield out_chunk
    finally:
        inference_task.cancel()
        if process.returncode is None:
            import contextlib
            with contextlib.suppress(ProcessLookupError):
                process.terminate()
        
        # Wait for the task to finish cleanup
        try:
            await inference_task
        except asyncio.CancelledError:
            pass
