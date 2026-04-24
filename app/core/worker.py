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
from app.core.tts import generate_speech, is_ready
from app.core.voices import get_voice_library

logger = logging.getLogger(__name__)

WORKER_POLL_INTERVAL = int(getattr(Config, "WORKER_POLL_INTERVAL", 2))
MAX_CHAPTER_RETRIES = int(getattr(Config, "MAX_CHAPTER_RETRIES", 3))


def get_book_output_dir(book_id: str) -> Path:
    """Get the directory where audiobook chapters are saved."""
    output_dir = Path("outputs") / "books" / book_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


async def process_chapter(repo: BookRepository, chapter: dict) -> None:
    """Process a single chapter: generate speech and save to disk."""
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

    max_sentences = metadata.get("max_sentences_per_chunk", 5)
    max_chars = metadata.get("max_chunk_chars", 320)
    gap_ms = metadata.get("chunk_gap_ms", 120)

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
        raise ValueError(f"Voice '{voice_alias}' not found in library.")

    # Run generation in a thread to not block the asyncio loop
    loop = asyncio.get_event_loop()

    # generate_speech handles the TTS and format conversion
    audio_bytes, _ = await loop.run_in_executor(
        None,
        lambda: generate_speech(
            text=text,
            reference_audio_path=reference_audio_path,
            max_sentences_per_chunk=max_sentences,
            max_chunk_chars=max_chars,
            chunk_gap_ms=gap_ms,
            output_format=output_format,
        ),
    )

    # Save to disk
    output_dir = get_book_output_dir(book_id)
    filename = f"chapter_{chapter_num:03d}.{output_format}"
    file_path = output_dir / filename

    # Ensure it's streamed/saved efficiently
    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    # Estimate duration roughly based on bytes (for MP3/WAV this is just a proxy,
    # a real duration check would require pydub or similar, but we keep it simple here)
    # Just storing 0.0 or a dummy value since real duration calculation requires parsing the audio frame
    duration_secs = 0.0

    repo.mark_chapter_completed(chapter_id, str(file_path), duration_secs)


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

                if retry_count < MAX_CHAPTER_RETRIES:
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
