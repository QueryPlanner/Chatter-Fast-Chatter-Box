"""
Background worker for processing audiobook chapters sequentially.
"""

import asyncio
import contextlib
import json
import logging
from pathlib import Path

from app.config import Config
from app.core.database import BookRepository
from app.core.tts import generate_single_chunk, get_sample_rate, is_ready
from app.core.text import split_text_into_chunks
from app.core.audio import stitch_chunk_files
from app.core.voices import get_voice_library

logger = logging.getLogger(__name__)

WORKER_POLL_INTERVAL = int(getattr(Config, "WORKER_POLL_INTERVAL", 2))
MAX_CHAPTER_RETRIES = int(getattr(Config, "MAX_CHAPTER_RETRIES", 3))


class PermanentChapterError(ValueError):
    """Permanent chapter failure that should not be retried."""


def get_book_output_dir(book_id: str) -> Path:
    """Get the directory where audiobook chapters are saved."""
    output_dir = Path("outputs") / "books" / book_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_chunks_dir(book_id: str) -> Path:
    """Get the directory for intermediate chunk WAV files."""
    chunks_dir = Path("outputs") / "books" / book_id / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    return chunks_dir


async def process_chapter(repo: BookRepository, chapter: dict) -> None:
    """
    Process a single chapter with chunk-level persistence and crash resume.

    Flow:
    1. Split text into chunks
    2. Check DB for existing chunk_segments (crash resume)
    3. Generate only pending chunks → write each to disk → mark in DB
    4. Stitch all chunk WAVs into final chapter audio
    5. Optionally clean up chunk files
    """
    chapter_id = chapter["id"]
    book_id = chapter["book_id"]
    chapter_num = chapter["chapter_number"]
    text = chapter["text"]

    voice_alias = chapter["voice"]
    output_format = chapter["output_format"]
    metadata_json = chapter["metadata_json"]

    metadata = {}
    if metadata_json:
        with contextlib.suppress(json.JSONDecodeError):
            metadata = json.loads(metadata_json)

    max_sentences = metadata.get("max_sentences_per_chunk", Config.MAX_SENTENCES_PER_CHUNK)
    max_chars = metadata.get("max_chunk_chars", Config.MAX_CHUNK_CHARS)
    gap_ms = metadata.get("chunk_gap_ms", Config.CHUNK_GAP_MS)

    # Determine voice path
    reference_audio_path = None
    voice_lib = get_voice_library()

    if voice_alias:
        reference_audio_path = voice_lib.get_voice_path(voice_alias)
    else:
        default_voice = voice_lib.get_default_voice()
        if default_voice:
            reference_audio_path = voice_lib.get_voice_path(default_voice)

    if reference_audio_path is None and voice_alias:
        raise PermanentChapterError(f"Voice '{voice_alias}' not found in library.")

    # ── 1. Split text into chunks ────────────────────────────────────
    chunks = split_text_into_chunks(
        text,
        max_sentences_per_chunk=max_sentences,
        max_chunk_chars=max_chars,
    )

    # ── 2. Check for existing chunk_segments (crash resume) ──────────
    existing_segments = repo.get_chunk_segments(chapter_id)

    if not existing_segments:
        repo.create_chunk_segments(chapter_id, chunks)
        logger.info(
            f"Created {len(chunks)} chunk segments for chapter {chapter_num} "
            f"(book {book_id})"
        )
        existing_segments = repo.get_chunk_segments(chapter_id)
    else:
        completed_count = sum(1 for s in existing_segments if s["status"] == "completed")
        logger.info(
            f"Resuming chapter {chapter_num} (book {book_id}): "
            f"{completed_count}/{len(existing_segments)} chunks already completed"
        )

    # ── 3. Generate pending chunks → disk → DB ───────────────────────
    chunks_dir = get_chunks_dir(book_id)
    total_count = len(existing_segments)

    pending_segments = [
        seg
        for seg in existing_segments
        if seg["status"] != "completed"
        or not (seg["audio_path"] and Path(seg["audio_path"]).exists())
    ]

    logger.info(
        f"Synthesizing chapter {chapter_num}: "
        f"{len(pending_segments)} pending of {total_count} total chunks"
    )

    loop = asyncio.get_event_loop()

    for seg in pending_segments:
        chunk_index = seg["chunk_index"]
        chunk_text = seg["text"]
        chunk_filename = f"chapter_{chapter_num:03d}_chunk_{chunk_index:04d}.wav"
        chunk_path = str(chunks_dir / chunk_filename)

        logger.info(
            f"  Chunk {chunk_index + 1}/{total_count} "
            f"({len(chunk_text)} chars) ..."
        )

        # Only use reference audio for the very first chunk (index 0)
        ref_path = reference_audio_path if chunk_index == 0 else None

        # Run generation in executor to not block asyncio
        await loop.run_in_executor(
            None,
            lambda cp=chunk_path, ct=chunk_text, rp=ref_path: generate_single_chunk(  # type: ignore[misc]
                text=ct,
                output_path=cp,
                reference_audio_path=rp,
            ),
        )

        # Mark chunk as completed in DB immediately
        repo.mark_chunk_segment_completed(seg["id"], chunk_path)

    # ── 4. Stitch all chunks into final chapter audio ────────────────
    updated_segments = repo.get_chunk_segments(chapter_id)
    chunk_paths = [seg["audio_path"] for seg in updated_segments if seg["audio_path"]]

    if not chunk_paths:
        raise RuntimeError(f"No chunk audio files found for chapter {chapter_id}")

    output_dir = get_book_output_dir(book_id)
    filename = f"chapter_{chapter_num:03d}.{output_format}"
    file_path = str(output_dir / filename)
    sample_rate = get_sample_rate()

    logger.info(f"Stitching {len(chunk_paths)} chunks → {filename}")

    await loop.run_in_executor(
        None,
        lambda: stitch_chunk_files(
            chunk_paths=chunk_paths,
            output_path=file_path,
            sample_rate=sample_rate,
            gap_ms=gap_ms,
            output_format=output_format,
        ),
    )

    # ── 5. Cleanup chunk files and DB records ────────────────────────
    if Config.CLEANUP_CHUNK_FILES:
        for path_str in chunk_paths:
            path = Path(path_str)
            path.unlink(missing_ok=True)

        # Remove chunks dir if empty
        try:
            chunks_dir.rmdir()
        except OSError:
            pass  # Not empty (other chapters' chunks may exist)

        repo.delete_chunk_segments(chapter_id)

    # ── 6. Mark chapter as completed ─────────────────────────────────
    duration_secs = 0.0
    repo.mark_chapter_completed(chapter_id, file_path, duration_secs)


async def book_worker_loop() -> None:
    """Main worker loop that runs continuously in the background."""
    logger.info("Starting audiobook background worker loop...")

    repo = BookRepository()

    while True:
        try:
            if not is_ready():
                await asyncio.sleep(WORKER_POLL_INTERVAL)
                continue

            chapter = repo.get_next_pending_chapter()
            if not chapter:
                await asyncio.sleep(WORKER_POLL_INTERVAL)
                continue

            chapter_id = chapter["id"]
            book_id = chapter["book_id"]

            logger.info(f"Processing book {book_id}, chapter {chapter['chapter_number']}")
            repo.mark_chapter_processing(chapter_id, book_id)

            try:
                await process_chapter(repo, dict(chapter))
                logger.info(f"Completed book {book_id}, chapter {chapter['chapter_number']}")
            except Exception as e:
                logger.error(f"Failed to process chapter {chapter_id}: {e}")
                retry_count = chapter["retry_count"]
                is_permanent_error = isinstance(e, PermanentChapterError)

                if is_permanent_error:
                    logger.error(
                        f"Chapter {chapter_id} has a permanent configuration error. "
                        "Skipping retries and marking as failed."
                    )
                    repo.mark_chapter_failed(chapter_id, str(e), retry=False)
                elif retry_count < MAX_CHAPTER_RETRIES:
                    logger.info(
                        f"Retrying chapter {chapter_id} (Attempt {retry_count + 1}/{MAX_CHAPTER_RETRIES})"
                    )
                    repo.mark_chapter_failed(chapter_id, str(e), retry=True)
                else:
                    logger.error(f"Chapter {chapter_id} exhausted all retries. Marking as failed.")
                    repo.mark_chapter_failed(chapter_id, str(e), retry=False)

            # Check if book is fully done
            repo.update_book_status_if_done(book_id)

        except asyncio.CancelledError:
            logger.info("Worker loop cancelled, shutting down.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")
            try:
                await asyncio.sleep(WORKER_POLL_INTERVAL)
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled, shutting down.")
                break
