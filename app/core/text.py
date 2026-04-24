"""
Text chunking utilities for TTS.

Ported from generate_turbo.py - uses sentence-based chunking at punctuation boundaries.
"""

from __future__ import annotations

import re

from app.config import Config

# Split at sentence boundaries (after .!?)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_text_into_chunks(
    text: str,
    max_sentences_per_chunk: int | None = None,
    max_chunk_chars: int | None = None,
) -> list[str]:
    """
    Split text into chunks suitable for TTS generation.

    Uses sentence-based chunking to avoid cutting mid-sentence.
    Turbo often predicts speech EOS early on long inputs, so chunking
    by sentences keeps each generation short enough to finish.

    Args:
        text: The input text to split
        max_sentences_per_chunk: Maximum sentences per chunk (default from Config)
        max_chunk_chars: Maximum characters per chunk (default from Config)

    Returns:
        List of text chunks
    """
    if max_sentences_per_chunk is None:
        max_sentences_per_chunk = Config.MAX_SENTENCES_PER_CHUNK
    if max_chunk_chars is None:
        max_chunk_chars = Config.MAX_CHUNK_CHARS

    text = text.strip()
    if not text:
        return []

    # Split into sentences
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:  # pragma: no cover
        return [text]

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_parts, current_len
        if current_parts:
            chunks.append(" ".join(current_parts))
        current_parts = []
        current_len = 0

    for part in sentences:
        # If single sentence exceeds max characters, split it at max_chunk_chars
        if len(part) > max_chunk_chars:
            flush()
            for start in range(0, len(part), max_chunk_chars):
                segment = part[start : start + max_chunk_chars].strip()
                if segment:
                    chunks.append(segment)
            continue

        # Check if adding this sentence would exceed the limit (either sentences or chars)
        extra_chars = len(part) + (1 if current_parts else 0)
        would_exceed_sentences = len(current_parts) >= max_sentences_per_chunk
        would_exceed_chars = current_len + extra_chars > max_chunk_chars

        # It's better to flush if we hit sentence limit, but for backwards compat / safety
        # we still respect max_chunk_chars if it's set very strictly. We prioritize sentence count.
        if would_exceed_sentences or would_exceed_chars:
            flush()

        current_parts.append(part)
        current_len += extra_chars

    flush()
    return chunks
