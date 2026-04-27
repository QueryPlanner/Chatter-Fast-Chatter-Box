"""
Database persistence layer for audiobook jobs.

Uses SQLite to store book and chapter metadata, ensuring crash recovery.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Config


def utc_now_iso() -> str:
    """Return timezone-aware UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def get_db_path() -> Path:
    """Get the configured database path."""
    db_path = Path(Config.DATABASE_PATH)
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    """Get a configured SQLite connection."""
    conn = sqlite3.connect(get_db_path(), timeout=10.0)
    # Return rows as dictionaries
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency and crash safety
    conn.execute("PRAGMA journal_mode=WAL")
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Initialize the database schema if it doesn't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                voice TEXT,
                output_format TEXT NOT NULL,
                status TEXT NOT NULL,
                total_chapters INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                error TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                title TEXT,
                text TEXT NOT NULL,
                status TEXT NOT NULL,
                audio_path TEXT,
                duration_secs REAL,
                error TEXT,
                started_at TEXT,
                completed_at TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chunk_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                total_chunks INTEGER NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                audio_path TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
                UNIQUE(chapter_id, chunk_index)
            );

            -- Index for quick lookups
            CREATE INDEX IF NOT EXISTS idx_chapters_book_id ON chapters(book_id);
            CREATE INDEX IF NOT EXISTS idx_chapters_status ON chapters(status);
            CREATE INDEX IF NOT EXISTS idx_chunk_segments_chapter_id ON chunk_segments(chapter_id);
        """)
        conn.commit()


class BookRepository:
    """Repository for managing book and chapter data in SQLite."""

    def __init__(self, conn: sqlite3.Connection | None = None):
        """Initialize with an optional connection. If none provided, a new one is created per operation."""
        self._conn = conn

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn:
            return self._conn
        return get_connection()

    def create_book(
        self,
        title: str,
        voice: str | None,
        output_format: str,
        chapters: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> str:
        """
        Create a new book and its chapters.

        Args:
            title: Book title
            voice: Voice alias
            output_format: "mp3" or "wav"
            chapters: List of chapter dicts with 'chapter_number', 'title', 'text'
            metadata: Extra config (e.g. max_chunk_chars)

        Returns:
            The new book ID
        """
        book_id = str(uuid.uuid4())
        now = utc_now_iso()

        with self._get_conn() as conn:
            # Insert book
            conn.execute(
                """
                INSERT INTO books (
                    id, title, voice, output_format, status, total_chapters,
                    created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    book_id,
                    title,
                    voice,
                    output_format,
                    "queued",
                    len(chapters),
                    now,
                    now,
                    json.dumps(metadata),
                ),
            )

            # Insert chapters
            chapter_rows = [
                (book_id, ch["chapter_number"], ch.get("title"), ch["text"], "pending")
                for ch in chapters
            ]
            conn.executemany(
                """
                INSERT INTO chapters (book_id, chapter_number, title, text, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                chapter_rows,
            )
            conn.commit()

        return book_id

    def get_book(self, book_id: str) -> sqlite3.Row | None:
        """Get a book by ID."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row: sqlite3.Row | None = cursor.fetchone()
            return row

    def get_books(self, limit: int = 100, offset: int = 0) -> list[sqlite3.Row]:
        """Get a list of books ordered by creation time."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM books ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
            )
            return cursor.fetchall()

    def get_chapters(self, book_id: str) -> list[sqlite3.Row]:
        """Get all chapters for a book, ordered by chapter_number."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM chapters WHERE book_id = ? ORDER BY chapter_number ASC", (book_id,)
            )
            return cursor.fetchall()

    def get_chapter(self, book_id: str, chapter_number: int) -> sqlite3.Row | None:
        """Get a specific chapter."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM chapters WHERE book_id = ? AND chapter_number = ?",
                (book_id, chapter_number),
            )
            row: sqlite3.Row | None = cursor.fetchone()
            return row

    def get_next_pending_chapter(self) -> sqlite3.Row | None:
        """
        Get the next pending chapter across all books.
        Prioritizes the earliest created book, and its earliest chapter.
        """
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT c.*, b.voice, b.output_format, b.metadata_json
                FROM chapters c
                JOIN books b ON c.book_id = b.id
                WHERE c.status = 'pending' AND b.status IN ('queued', 'processing')
                ORDER BY b.created_at ASC, c.chapter_number ASC
                LIMIT 1
            """)
            row: sqlite3.Row | None = cursor.fetchone()
            return row

    def mark_chapter_processing(self, chapter_id: int, book_id: str) -> None:
        """Mark a chapter as processing, and update book status if needed."""
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE chapters SET status = 'processing', started_at = ? WHERE id = ?",
                (now, chapter_id),
            )
            conn.execute(
                "UPDATE books SET status = 'processing', updated_at = ? WHERE id = ? AND status = 'queued'",
                (now, book_id),
            )
            conn.commit()

    def mark_chapter_completed(
        self, chapter_id: int, audio_path: str, duration_secs: float
    ) -> None:
        """Mark a chapter as completed with its audio path."""
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE chapters
                SET status = 'completed', audio_path = ?, duration_secs = ?, completed_at = ?
                WHERE id = ?
                """,
                (audio_path, duration_secs, now, chapter_id),
            )
            conn.commit()

    def mark_chapter_failed(self, chapter_id: int, error: str, retry: bool = False) -> None:
        """Mark a chapter as failed, optionally incrementing retry count and resetting to pending."""
        now = utc_now_iso()
        with self._get_conn() as conn:
            if retry:
                conn.execute(
                    """
                    UPDATE chapters
                    SET status = 'pending', error = ?, retry_count = retry_count + 1
                    WHERE id = ?
                    """,
                    (error, chapter_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE chapters
                    SET status = 'failed', error = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (error, now, chapter_id),
                )
            conn.commit()

    def update_book_status_if_done(self, book_id: str) -> None:
        """Check if all chapters are done, and update book status accordingly."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT status, COUNT(*) as count FROM chapters WHERE book_id = ? GROUP BY status",
                (book_id,),
            )
            counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            pending = counts.get("pending", 0)
            processing = counts.get("processing", 0)
            failed = counts.get("failed", 0)

            now = utc_now_iso()

            if pending == 0 and processing == 0:
                # Book is finished
                new_status = "failed" if failed > 0 else "completed"
                conn.execute(
                    "UPDATE books SET status = ?, completed_at = ?, updated_at = ? WHERE id = ? AND status IN ('queued', 'processing')",
                    (new_status, now, now, book_id),
                )
                conn.commit()

    def mark_book_cancelled(self, book_id: str) -> None:
        """Cancel a book and its pending/processing chapters."""
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE books SET status = 'cancelled', updated_at = ? WHERE id = ? AND status IN ('queued', 'processing')",
                (now, book_id),
            )
            conn.execute(
                "UPDATE chapters SET status = 'failed', error = 'Cancelled by user' WHERE book_id = ? AND status IN ('pending', 'processing')",
                (book_id,),
            )
            conn.commit()

    def retry_failed_chapters(self, book_id: str) -> None:
        """Set failed chapters back to pending and reset book status."""
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE chapters SET status = 'pending', error = NULL WHERE book_id = ? AND status = 'failed'",
                (book_id,),
            )
            conn.execute(
                "UPDATE books SET status = 'processing', updated_at = ? WHERE id = ?",
                (now, book_id),
            )
            conn.commit()

    def reset_processing_chapters(self) -> int:
        """
        Crash recovery: Reset any 'processing' chapters back to 'pending'.
        Returns the number of chapters reset.
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE chapters SET status = 'pending' WHERE status = 'processing'"
            )
            # Also ensure any 'processing' books are fine.
            conn.commit()
            return cursor.rowcount

    # ── Chunk-segment methods ─────────────────────────────────────────

    def create_chunk_segments(self, chapter_id: int, chunks: list[str]) -> None:
        """Bulk-insert chunk segment rows for a chapter."""
        now = utc_now_iso()
        total = len(chunks)
        rows = [
            (chapter_id, idx, total, text, "pending", now)
            for idx, text in enumerate(chunks)
        ]
        with self._get_conn() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO chunk_segments
                    (chapter_id, chunk_index, total_chunks, text, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

    def get_chunk_segments(self, chapter_id: int) -> list[sqlite3.Row]:
        """Get all chunk segments for a chapter, ordered by index."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM chunk_segments WHERE chapter_id = ? ORDER BY chunk_index ASC",
                (chapter_id,),
            )
            return cursor.fetchall()

    def get_pending_chunk_segments(self, chapter_id: int) -> list[sqlite3.Row]:
        """Get only pending (not yet completed) chunk segments for a chapter."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM chunk_segments WHERE chapter_id = ? AND status = 'pending' ORDER BY chunk_index ASC",
                (chapter_id,),
            )
            return cursor.fetchall()

    def mark_chunk_segment_completed(self, chunk_id: int, audio_path: str) -> None:
        """Mark a single chunk segment as completed with its audio path."""
        now = utc_now_iso()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE chunk_segments SET status = 'completed', audio_path = ?, completed_at = ? WHERE id = ?",
                (audio_path, now, chunk_id),
            )
            conn.commit()

    def delete_chunk_segments(self, chapter_id: int) -> None:
        """Delete all chunk segments for a chapter (cleanup after stitching)."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM chunk_segments WHERE chapter_id = ?", (chapter_id,)
            )
            conn.commit()

    def get_chunk_progress(self, chapter_id: int) -> tuple[int, int]:
        """Return (completed_chunks, total_chunks) for a chapter."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed "
                "FROM chunk_segments WHERE chapter_id = ?",
                (chapter_id,),
            )
            row = cursor.fetchone()
            if row and row["total"] > 0:
                return int(row["completed"]), int(row["total"])
            return 0, 0
