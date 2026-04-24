"""
Audio processing utilities for TTS output.

Handles format conversion (WAV -> MP3) and audio concatenation.
"""

from __future__ import annotations

import io

import torch

# pydub is used for audio format conversion
try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def concatenate_with_gap(
    audio_tensors: list[torch.Tensor],
    sample_rate: int,
    gap_ms: int = 120,
) -> torch.Tensor:
    """
    Concatenate audio tensors with silence gap between them.

    Args:
        audio_tensors: List of audio tensors (1, samples)
        sample_rate: Sample rate of the audio
        gap_ms: Gap in milliseconds between chunks

    Returns:
        Concatenated audio tensor
    """
    if not audio_tensors:
        raise ValueError("No audio tensors to concatenate")

    if len(audio_tensors) == 1:
        return audio_tensors[0]

    # Calculate gap in samples
    gap_samples = max(0, int(sample_rate * (gap_ms / 1000.0)))

    # Create silence tensor
    silence = torch.zeros(
        1,
        gap_samples,
        dtype=audio_tensors[0].dtype,
        device=audio_tensors[0].device,
    )

    # Interleave audio with silence
    pieces: list[torch.Tensor] = []
    for i, tensor in enumerate(audio_tensors):
        pieces.append(tensor)
        if i < len(audio_tensors) - 1 and gap_samples > 0:
            pieces.append(silence)

    return torch.cat(pieces, dim=1)


def wav_bytes_to_mp3_bytes(wav_bytes: bytes, bitrate: str = "128k") -> bytes:
    """
    Convert WAV bytes to MP3 bytes using pydub.

    Args:
        wav_bytes: WAV audio data as bytes
        bitrate: MP3 bitrate (default 128k)

    Returns:
        MP3 audio data as bytes

    Raises:
        RuntimeError: If pydub is not available
    """
    if not PYDUB_AVAILABLE:
        raise RuntimeError(
            "pydub is required for MP3 conversion. "
            "Install with: pip install pydub\n"
            "Also ensure ffmpeg is installed on your system."
        )

    # Load WAV from bytes
    audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))

    # Export to MP3
    mp3_buffer = io.BytesIO()
    audio.export(mp3_buffer, format="mp3", bitrate=bitrate)
    mp3_buffer.seek(0)

    return mp3_buffer.read()


def tensor_to_audio_bytes(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    output_format: str = "mp3",
) -> tuple[bytes, str]:
    """
    Convert audio tensor to audio bytes in the specified format.

    Args:
        audio_tensor: Audio tensor from TTS model (1, samples)
        sample_rate: Sample rate
        output_format: "mp3" or "wav"

    Returns:
        Tuple of (audio_bytes, content_type)
    """
    import torchaudio as ta

    # First, convert to WAV bytes
    wav_buffer = io.BytesIO()

    # Ensure tensor is on CPU for saving
    if hasattr(audio_tensor, "cpu"):
        audio_tensor = audio_tensor.cpu()

    ta.save(wav_buffer, audio_tensor, sample_rate, format="wav")
    wav_buffer.seek(0)
    wav_bytes = wav_buffer.read()

    if output_format.lower() == "wav":
        return wav_bytes, "audio/wav"

    # Convert to MP3
    mp3_bytes = wav_bytes_to_mp3_bytes(wav_bytes)
    return mp3_bytes, "audio/mpeg"
