"""
Configuration management for Fast-Chatterbox.

Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


def _logical_cpu_count() -> int:
    """Usable CPU count (respects Linux cgroup/affinity in containers when available)."""
    if hasattr(os, "sched_getaffinity"):
        try:
            return max(1, len(os.sched_getaffinity(0)))
        except (OSError, NotImplementedError, ValueError, RuntimeError):
            pass
    return max(1, os.cpu_count() or 4)


def _coerce_inference_thread_count() -> int:
    """
    PyTorch/OMP default thread budget for CPU inference.

    Set TORCH_NUM_THREADS to 0 (or leave unset) to use all logical CPUs; set a
    positive integer to cap usage.
    """
    raw = os.getenv("TORCH_NUM_THREADS", "0").strip()
    if not raw:
        return _logical_cpu_count()
    try:
        parsed = int(raw)
    except ValueError:
        return _logical_cpu_count()
    if parsed <= 0:
        return _logical_cpu_count()
    return parsed


# Apply before most numerical libraries spin up (PyTorch, NumPy, MKL, OpenMP)
_INFERENCE_THREADS = _coerce_inference_thread_count()
os.environ["OMP_NUM_THREADS"] = str(_INFERENCE_THREADS)
os.environ["MKL_NUM_THREADS"] = str(_INFERENCE_THREADS)
os.environ["NUMEXPR_MAX_THREADS"] = str(_INFERENCE_THREADS)


class Config:
    """Application configuration from environment variables."""

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # TTS settings
    MAX_CHUNK_CHARS: int = int(os.getenv("MAX_CHUNK_CHARS", "320"))
    CHUNK_GAP_MS: int = int(os.getenv("CHUNK_GAP_MS", "120"))
    MAX_SENTENCES_PER_CHUNK: int = int(os.getenv("MAX_SENTENCES_PER_CHUNK", "3"))

    # Device: auto, cuda, mps, or cpu
    DEVICE: str = os.getenv("DEVICE", "auto")

    # PyTorch/OMP thread budget for CPU ops (0 in env = all logical CPUs; see _coerce_inference_thread_count)
    TORCH_NUM_THREADS: int = _INFERENCE_THREADS

    # Default voice
    DEFAULT_VOICE: str | None = os.getenv("DEFAULT_VOICE", "dan")

    # Output format
    DEFAULT_OUTPUT_FORMAT: str = os.getenv("DEFAULT_OUTPUT_FORMAT", "mp3")

    # Database and Background worker
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/jobs.db")
    WORKER_POLL_INTERVAL: int = int(os.getenv("WORKER_POLL_INTERVAL", "2"))
    MAX_CHAPTER_RETRIES: int = int(os.getenv("MAX_CHAPTER_RETRIES", "3"))

    @classmethod
    def validate(cls) -> None:
        """Validate configuration values."""
        if cls.MAX_CHUNK_CHARS < 50 or cls.MAX_CHUNK_CHARS > 1000:
            raise ValueError(
                f"MAX_CHUNK_CHARS must be between 50 and 1000, got {cls.MAX_CHUNK_CHARS}"
            )

        if cls.CHUNK_GAP_MS < 0 or cls.CHUNK_GAP_MS > 1000:
            raise ValueError(f"CHUNK_GAP_MS must be between 0 and 1000, got {cls.CHUNK_GAP_MS}")

        if cls.MAX_SENTENCES_PER_CHUNK < 1 or cls.MAX_SENTENCES_PER_CHUNK > 50:
            raise ValueError(
                f"MAX_SENTENCES_PER_CHUNK must be between 1 and 50, "
                f"got {cls.MAX_SENTENCES_PER_CHUNK}"
            )

        if cls.DEVICE.lower() not in ("auto", "cuda", "mps", "cpu"):
            raise ValueError(f"DEVICE must be auto, cuda, mps, or cpu, got {cls.DEVICE}")

        if cls.TORCH_NUM_THREADS < 1 or cls.TORCH_NUM_THREADS > 256:
            raise ValueError(
                f"TORCH_NUM_THREADS must be between 1 and 256, got {cls.TORCH_NUM_THREADS}"
            )

        if cls.DEFAULT_OUTPUT_FORMAT.lower() not in ("mp3", "wav"):
            raise ValueError(
                f"DEFAULT_OUTPUT_FORMAT must be mp3 or wav, got {cls.DEFAULT_OUTPUT_FORMAT}"
            )
