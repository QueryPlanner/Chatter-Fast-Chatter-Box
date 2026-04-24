"""
Tests for app/core/worker.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.database import BookRepository
from app.core.worker import (
    PermanentChapterError,
    book_worker_loop,
    get_book_output_dir,
    process_chapter,
)


class TestGetBookOutputDir:
    """Tests for get_book_output_dir function."""

    def test_creates_directory(self, temp_output_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that output directory is created."""
        monkeypatch.chdir(temp_output_dir)

        output_dir = get_book_output_dir("test-book-id")

        assert output_dir.exists()
        assert output_dir.name == "test-book-id"
        assert output_dir.parent.name == "books"


class TestProcessChapter:
    """Tests for process_chapter function."""

    @pytest.mark.asyncio
    async def test_process_chapter_success(
        self, temp_db: Path, temp_output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test successful chapter processing."""
        monkeypatch.chdir(temp_output_dir)

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        chapter_row = repo.get_next_pending_chapter()
        repo.mark_chapter_processing(chapter_row["id"], book_id)

        chapter_dict = dict(chapter_row)

        with (
            patch("app.core.worker.generate_speech") as mock_gen,
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.get_voice_library") as mock_voice_lib,
        ):
            mock_gen.return_value = (b"audio_data", "audio/mpeg")
            mock_voice_lib.return_value.get_voice_path.return_value = None
            mock_voice_lib.return_value.get_default_voice.return_value = None

            await process_chapter(repo, chapter_dict)

        updated = repo.get_chapter(book_id, 1)
        assert updated["status"] == "completed"
        assert updated["audio_path"] is not None

    @pytest.mark.asyncio
    async def test_process_chapter_with_voice(
        self, temp_db: Path, temp_output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test chapter processing with voice."""
        monkeypatch.chdir(temp_output_dir)

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice="test_voice",
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        chapter_row = repo.get_next_pending_chapter()
        repo.mark_chapter_processing(chapter_row["id"], book_id)

        chapter_dict = dict(chapter_row)

        with (
            patch("app.core.worker.generate_speech") as mock_gen,
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.get_voice_library") as mock_voice_lib,
        ):
            mock_gen.return_value = (b"audio_data", "audio/mpeg")
            mock_voice_lib.return_value.get_voice_path.return_value = "/path/to/voice.wav"

            await process_chapter(repo, chapter_dict)

            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["reference_audio_path"] == "/path/to/voice.wav"

    @pytest.mark.asyncio
    async def test_process_chapter_voice_not_found(
        self, temp_db: Path, temp_output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test chapter processing when voice not found."""
        monkeypatch.chdir(temp_output_dir)

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice="nonexistent_voice",
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        chapter_row = repo.get_next_pending_chapter()
        repo.mark_chapter_processing(chapter_row["id"], book_id)

        chapter_dict = dict(chapter_row)

        with (
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.get_voice_library") as mock_voice_lib,
        ):
            mock_voice_lib.return_value.get_voice_path.return_value = None

            with pytest.raises(ValueError, match="not found in library"):
                await process_chapter(repo, chapter_dict)

    @pytest.mark.asyncio
    async def test_process_chapter_custom_metadata(
        self, temp_db: Path, temp_output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test chapter processing with custom metadata."""
        monkeypatch.chdir(temp_output_dir)

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="wav",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={
                "max_sentences_per_chunk": 10,
                "max_chunk_chars": 500,
                "chunk_gap_ms": 200,
            },
        )

        chapter_row = repo.get_next_pending_chapter()
        repo.mark_chapter_processing(chapter_row["id"], book_id)

        chapter_dict = dict(chapter_row)

        with (
            patch("app.core.worker.generate_speech") as mock_gen,
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.get_voice_library") as mock_voice_lib,
        ):
            mock_gen.return_value = (b"audio_data", "audio/wav")
            mock_voice_lib.return_value.get_voice_path.return_value = None
            mock_voice_lib.return_value.get_default_voice.return_value = None

            await process_chapter(repo, chapter_dict)

            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["max_sentences_per_chunk"] == 10
            assert call_kwargs["max_chunk_chars"] == 500
            assert call_kwargs["chunk_gap_ms"] == 200

    @pytest.mark.asyncio
    async def test_process_chapter_empty_metadata_json(
        self, temp_db: Path, temp_output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test chapter processing with empty metadata_json string."""
        monkeypatch.chdir(temp_output_dir)

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        conn = repo._get_conn()
        conn.execute("UPDATE books SET metadata_json = ? WHERE id = ?", ("", book_id))
        conn.commit()

        chapter_row = repo.get_next_pending_chapter()
        repo.mark_chapter_processing(chapter_row["id"], book_id)

        chapter_dict = dict(chapter_row)

        with (
            patch("app.core.worker.generate_speech") as mock_gen,
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.get_voice_library") as mock_voice_lib,
        ):
            mock_gen.return_value = (b"audio_data", "audio/mpeg")
            mock_voice_lib.return_value.get_voice_path.return_value = None
            mock_voice_lib.return_value.get_default_voice.return_value = None

            await process_chapter(repo, chapter_dict)

            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["max_sentences_per_chunk"] == 3

    @pytest.mark.asyncio
    async def test_process_chapter_default_voice_none(
        self, temp_db: Path, temp_output_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test chapter processing when default voice path is None."""
        monkeypatch.chdir(temp_output_dir)

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        chapter_row = repo.get_next_pending_chapter()
        repo.mark_chapter_processing(chapter_row["id"], book_id)

        chapter_dict = dict(chapter_row)

        with (
            patch("app.core.worker.generate_speech") as mock_gen,
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.get_voice_library") as mock_voice_lib,
        ):
            mock_gen.return_value = (b"audio_data", "audio/mpeg")
            mock_voice_lib.return_value.get_voice_path.return_value = None
            mock_voice_lib.return_value.get_default_voice.return_value = "missing_voice"

            await process_chapter(repo, chapter_dict)

            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["reference_audio_path"] is None


class TestBookWorkerLoop:
    """Tests for book_worker_loop function."""

    @pytest.mark.asyncio
    async def test_worker_waits_when_model_not_ready(self, temp_db: Path):
        """Test that worker waits when model not ready."""
        sleep_count = 0

        async def mock_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                raise asyncio.CancelledError()

        with (
            patch("app.core.worker.is_ready", return_value=False),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await book_worker_loop()
            assert sleep_count >= 2

    @pytest.mark.asyncio
    async def test_worker_waits_when_no_pending_chapters(self, temp_db: Path):
        """Test that worker waits when no pending chapters."""
        sleep_count = 0

        async def mock_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                raise asyncio.CancelledError()

        with (
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.BookRepository") as mock_repo_cls,
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            mock_repo = MagicMock()
            mock_repo.get_next_pending_chapter.return_value = None
            mock_repo_cls.return_value = mock_repo

            await book_worker_loop()

            assert sleep_count >= 2

    @pytest.mark.asyncio
    async def test_worker_handles_cancel(self, temp_db: Path):
        """Test that worker handles cancellation gracefully."""

        async def mock_sleep(seconds):
            raise asyncio.CancelledError()

        with (
            patch("app.core.worker.is_ready", return_value=False),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await book_worker_loop()

    @pytest.mark.asyncio
    async def test_worker_handles_exceptions(self, temp_db: Path):
        """Test that worker handles exceptions gracefully."""
        sleep_count = 0

        async def mock_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                raise asyncio.CancelledError()

        with (
            patch("app.core.worker.is_ready", side_effect=RuntimeError("Test error")),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await book_worker_loop()
            assert sleep_count >= 2

    @pytest.mark.asyncio
    async def test_worker_processes_chapter_successfully(self, temp_db: Path):
        """Test that worker processes a chapter successfully."""
        sleep_count = 0

        async def mock_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 1:
                raise asyncio.CancelledError()

        repo = BookRepository()
        _book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        _chapter = repo.get_next_pending_chapter()

        with (
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.BookRepository", return_value=repo),
            patch("app.core.worker.process_chapter", new_callable=AsyncMock) as mock_process,
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await book_worker_loop()

            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_retries_failed_chapter(self, temp_db: Path):
        """Test that worker retries a failed chapter."""
        process_count = 0

        async def mock_process(repo, chapter):
            nonlocal process_count
            process_count += 1
            if process_count == 1:
                raise RuntimeError("Failed first time")
            raise asyncio.CancelledError()

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        with (
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.BookRepository", return_value=repo),
            patch("app.core.worker.process_chapter", side_effect=mock_process),
        ):
            await book_worker_loop()

        chapter = repo.get_chapter(book_id, 1)
        assert chapter["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_worker_exhausts_retries(self, temp_db: Path):
        """Test that worker marks chapter as failed after exhausting retries."""
        sleep_count = 0

        async def mock_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 1:
                raise asyncio.CancelledError()

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        chapter = repo.get_next_pending_chapter()
        for _ in range(3):
            repo.mark_chapter_failed(chapter["id"], "error", retry=True)

        with (
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.BookRepository", return_value=repo),
            patch("app.core.worker.process_chapter", side_effect=RuntimeError("Failed")),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await book_worker_loop()

        chapter = repo.get_chapter(book_id, 1)
        assert chapter["status"] == "failed"

    @pytest.mark.asyncio
    async def test_worker_permanent_error_skips_retries(self, temp_db: Path):
        """Test that PermanentChapterError marks the chapter failed without retry."""

        async def mock_sleep(_seconds):
            raise asyncio.CancelledError()

        repo = BookRepository()
        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Test text"}],
            metadata={},
        )

        with (
            patch("app.core.worker.is_ready", return_value=True),
            patch("app.core.worker.BookRepository", return_value=repo),
            patch(
                "app.core.worker.process_chapter",
                side_effect=PermanentChapterError("Unknown voice name"),
            ),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await book_worker_loop()

        chapter = repo.get_chapter(book_id, 1)
        assert chapter["status"] == "failed"
        assert chapter["retry_count"] == 0
