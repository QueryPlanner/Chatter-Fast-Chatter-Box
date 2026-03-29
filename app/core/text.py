"""
Text chunking utilities for TTS.

Ported from generate_turbo.py - uses sentence-based chunking at punctuation boundaries.
"""

from __future__ import annotations

import re
from typing import List

# Split at sentence boundaries (after .!?)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_text_into_chunks(text: str, max_chunk_chars: int = 320) -> List[str]:
    """
    Split text into chunks suitable for TTS generation.

    Uses sentence-based chunking to avoid cutting mid-sentence.
    Turbo often predicts speech EOS early on long inputs, so chunking
    by sentences keeps each generation short enough to finish.

    Args:
        text: The input text to split
        max_chunk_chars: Maximum characters per chunk (default 320)

    Returns:
        List of text chunks
    """
    text = text.strip()
    if not text:
        return []

    # Split into sentences
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return [text]

    chunks: List[str] = []
    current_parts: List[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_parts, current_len
        if current_parts:
            chunks.append(" ".join(current_parts))
        current_parts = []
        current_len = 0

    for part in sentences:
        # If single sentence exceeds max, split it at max_chunk_chars
        if len(part) > max_chunk_chars:
            flush()
            for start in range(0, len(part), max_chunk_chars):
                segment = part[start : start + max_chunk_chars].strip()
                if segment:
                    chunks.append(segment)
            continue

        # Check if adding this sentence would exceed the limit
        extra = len(part) + (1 if current_parts else 0)
        if current_len + extra > max_chunk_chars:
            flush()

        current_parts.append(part)
        current_len += extra

    flush()
    return chunks
