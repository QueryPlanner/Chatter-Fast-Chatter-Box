"""
Tests for app/core/database.py
"""

from __future__ import annotations

from pathlib import Path

from app.core.database import BookRepository, get_connection, get_db_path, init_db


class TestDatabaseFunctions:
    """Tests for database utility functions."""

    def test_get_db_path(self, temp_db: Path):
        """Test database path generation."""
        db_path = get_db_path()
        assert db_path.exists()
        assert db_path.suffix == ".db"

    def test_get_connection(self, temp_db: Path):
        """Test database connection creation."""
        conn = get_connection()
        assert conn is not None
        conn.close()

    def test_connection_row_factory(self, temp_db: Path):
        """Test that connection returns rows as dictionaries."""
        conn = get_connection()
        cursor = conn.execute("SELECT 1 as value")
        row = cursor.fetchone()
        assert row["value"] == 1
        conn.close()

    def test_init_db_creates_tables(self, temp_db: Path):
        """Test that init_db creates all required tables."""
        init_db()
        conn = get_connection()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('books', 'chapters')"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        conn.close()

        assert "books" in tables
        assert "chapters" in tables

    def test_init_db_creates_indexes(self, temp_db: Path):
        """Test that init_db creates required indexes."""
        init_db()
        conn = get_connection()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = {row["name"] for row in cursor.fetchall()}
        conn.close()

        assert "idx_chapters_book_id" in indexes
        assert "idx_chapters_status" in indexes


class TestBookRepository:
    """Tests for BookRepository class."""

    def test_create_book(self, book_repo: BookRepository):
        """Test creating a new book."""
        chapters = [
            {"chapter_number": 1, "title": "Chapter 1", "text": "Text 1"},
            {"chapter_number": 2, "title": "Chapter 2", "text": "Text 2"},
        ]
        metadata = {"max_chunk_chars": 320}

        book_id = book_repo.create_book(
            title="Test Book",
            voice="test_voice",
            output_format="mp3",
            chapters=chapters,
            metadata=metadata,
        )

        assert book_id is not None
        assert len(book_id) == 36

        book = book_repo.get_book(book_id)
        assert book is not None
        assert book["title"] == "Test Book"
        assert book["voice"] == "test_voice"
        assert book["output_format"] == "mp3"
        assert book["status"] == "queued"
        assert book["total_chapters"] == 2

    def test_create_book_without_voice(self, book_repo: BookRepository):
        """Test creating a book without a voice."""
        chapters = [{"chapter_number": 1, "title": "Ch1", "text": "Text"}]

        book_id = book_repo.create_book(
            title="No Voice Book",
            voice=None,
            output_format="wav",
            chapters=chapters,
            metadata={},
        )

        book = book_repo.get_book(book_id)
        assert book["voice"] is None

    def test_get_book_not_found(self, book_repo: BookRepository):
        """Test getting a non-existent book."""
        book = book_repo.get_book("non-existent-id")
        assert book is None

    def test_get_books(self, book_repo: BookRepository):
        """Test listing books."""
        book_repo.create_book(
            title="Book 1",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )
        book_repo.create_book(
            title="Book 2",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        books = book_repo.get_books(limit=10, offset=0)
        assert len(books) == 2

    def test_get_books_pagination(self, book_repo: BookRepository):
        """Test book listing pagination."""
        for i in range(5):
            book_repo.create_book(
                title=f"Book {i}",
                voice=None,
                output_format="mp3",
                chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
                metadata={},
            )

        page1 = book_repo.get_books(limit=2, offset=0)
        page2 = book_repo.get_books(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

    def test_get_chapters(self, book_repo: BookRepository):
        """Test getting chapters for a book."""
        chapters = [
            {"chapter_number": 1, "title": "Chapter 1", "text": "Text 1"},
            {"chapter_number": 2, "title": "Chapter 2", "text": "Text 2"},
            {"chapter_number": 3, "title": "Chapter 3", "text": "Text 3"},
        ]

        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=chapters,
            metadata={},
        )

        retrieved = book_repo.get_chapters(book_id)
        assert len(retrieved) == 3
        assert retrieved[0]["chapter_number"] == 1
        assert retrieved[1]["chapter_number"] == 2
        assert retrieved[2]["chapter_number"] == 3

    def test_get_chapter(self, book_repo: BookRepository):
        """Test getting a specific chapter."""
        chapters = [
            {"chapter_number": 1, "title": "Chapter 1", "text": "Text 1"},
            {"chapter_number": 2, "title": "Chapter 2", "text": "Text 2"},
        ]

        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=chapters,
            metadata={},
        )

        chapter = book_repo.get_chapter(book_id, 1)
        assert chapter is not None
        assert chapter["title"] == "Chapter 1"

    def test_get_chapter_not_found(self, book_repo: BookRepository):
        """Test getting a non-existent chapter."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_chapter(book_id, 999)
        assert chapter is None

    def test_mark_chapter_processing(self, book_repo: BookRepository):
        """Test marking a chapter as processing."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        assert chapter is not None

        book_repo.mark_chapter_processing(chapter["id"], book_id)

        updated = book_repo.get_chapter(book_id, 1)
        assert updated["status"] == "processing"
        assert updated["started_at"] is not None

        book = book_repo.get_book(book_id)
        assert book["status"] == "processing"

    def test_mark_chapter_completed(self, book_repo: BookRepository):
        """Test marking a chapter as completed."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        assert chapter is not None

        book_repo.mark_chapter_processing(chapter["id"], book_id)
        book_repo.mark_chapter_completed(chapter["id"], "/path/to/audio.mp3", 120.5)

        updated = book_repo.get_chapter(book_id, 1)
        assert updated["status"] == "completed"
        assert updated["audio_path"] == "/path/to/audio.mp3"
        assert updated["duration_secs"] == 120.5

    def test_mark_chapter_failed_no_retry(self, book_repo: BookRepository):
        """Test marking a chapter as failed without retry."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        assert chapter is not None

        book_repo.mark_chapter_failed(chapter["id"], "Error message", retry=False)

        updated = book_repo.get_chapter(book_id, 1)
        assert updated["status"] == "failed"
        assert updated["error"] == "Error message"

    def test_mark_chapter_failed_with_retry(self, book_repo: BookRepository):
        """Test marking a chapter as failed with retry."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        assert chapter is not None

        book_repo.mark_chapter_failed(chapter["id"], "Temporary error", retry=True)

        updated = book_repo.get_chapter(book_id, 1)
        assert updated["status"] == "pending"
        assert updated["error"] == "Temporary error"
        assert updated["retry_count"] == 1

    def test_get_next_pending_chapter_priority(self, book_repo: BookRepository):
        """Test that pending chapters are processed in order."""
        book_id1 = book_repo.create_book(
            title="Book 1",
            voice=None,
            output_format="mp3",
            chapters=[
                {"chapter_number": 1, "title": "Ch1", "text": "Text"},
                {"chapter_number": 2, "title": "Ch2", "text": "Text"},
            ],
            metadata={},
        )
        _book_id2 = book_repo.create_book(
            title="Book 2",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        assert chapter is not None
        assert chapter["book_id"] == book_id1
        assert chapter["chapter_number"] == 1

    def test_update_book_status_if_done_completed(self, book_repo: BookRepository):
        """Test book status update when all chapters complete."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        book_repo.mark_chapter_processing(chapter["id"], book_id)
        book_repo.mark_chapter_completed(chapter["id"], "/path/audio.mp3", 60.0)

        book_repo.update_book_status_if_done(book_id)

        book = book_repo.get_book(book_id)
        assert book["status"] == "completed"
        assert book["completed_at"] is not None

    def test_update_book_status_if_done_failed(self, book_repo: BookRepository):
        """Test book status update when chapters fail."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        book_repo.mark_chapter_processing(chapter["id"], book_id)
        book_repo.mark_chapter_failed(chapter["id"], "Error", retry=False)

        book_repo.update_book_status_if_done(book_id)

        book = book_repo.get_book(book_id)
        assert book["status"] == "failed"

    def test_mark_book_cancelled(self, book_repo: BookRepository):
        """Test cancelling a book."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        book_repo.mark_book_cancelled(book_id)

        book = book_repo.get_book(book_id)
        assert book["status"] == "cancelled"

        chapters = book_repo.get_chapters(book_id)
        assert all(ch["status"] == "failed" for ch in chapters)

    def test_retry_failed_chapters(self, book_repo: BookRepository):
        """Test retrying failed chapters."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        book_repo.mark_chapter_processing(chapter["id"], book_id)
        book_repo.mark_chapter_failed(chapter["id"], "Error", retry=False)

        book_repo.retry_failed_chapters(book_id)

        chapters = book_repo.get_chapters(book_id)
        assert chapters[0]["status"] == "pending"
        assert chapters[0]["error"] is None

    def test_reset_processing_chapters(self, book_repo: BookRepository):
        """Test crash recovery resets processing chapters."""
        book_id = book_repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        chapter = book_repo.get_next_pending_chapter()
        book_repo.mark_chapter_processing(chapter["id"], book_id)

        count = book_repo.reset_processing_chapters()
        assert count == 1

        chapters = book_repo.get_chapters(book_id)
        assert chapters[0]["status"] == "pending"

    def test_repo_with_existing_connection(self, temp_db: Path):
        """Test BookRepository with an existing connection."""
        conn = get_connection()
        repo = BookRepository(conn=conn)

        book_id = repo.create_book(
            title="Test Book",
            voice=None,
            output_format="mp3",
            chapters=[{"chapter_number": 1, "title": "Ch1", "text": "Text"}],
            metadata={},
        )

        assert book_id is not None
        book = repo.get_book(book_id)
        assert book["title"] == "Test Book"
        conn.close()
