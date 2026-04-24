"""
Tests for app/api/endpoints/books.py
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestCreateBook:
    """Tests for create book endpoint."""

    def test_create_book_success(self, client: TestClient, temp_db: Path):
        """Test successful book creation."""
        payload = {
            "title": "Test Book",
            "voice": "test_voice",
            "output_format": "mp3",
            "chapters": [
                {"chapter_number": 1, "title": "Chapter 1", "text": "Text 1"},
                {"chapter_number": 2, "title": "Chapter 2", "text": "Text 2"},
            ],
            "config": {
                "max_sentences_per_chunk": 3,
                "max_chunk_chars": 320,
                "chunk_gap_ms": 120,
            },
        }

        response = client.post("/api/books", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Book"
        assert data["status"] == "queued"
        assert data["progress"]["total_chapters"] == 2

    def test_create_book_without_voice(self, client: TestClient, temp_db: Path):
        """Test creating book without voice."""
        payload = {
            "title": "No Voice Book",
            "output_format": "wav",
            "chapters": [
                {"chapter_number": 1, "title": "Ch1", "text": "Text"},
            ],
        }

        response = client.post("/api/books", json=payload)

        assert response.status_code == 201
        assert response.json()["voice"] is None

    def test_create_book_minimal(self, client: TestClient, temp_db: Path):
        """Test creating book with minimal data."""
        payload = {
            "title": "Minimal Book",
            "chapters": [
                {"chapter_number": 1, "text": "Text"},
            ],
        }

        response = client.post("/api/books", json=payload)

        assert response.status_code == 201
        assert response.json()["output_format"] == "mp3"


class TestListBooks:
    """Tests for list books endpoint."""

    def test_list_books_empty(self, client: TestClient, temp_db: Path):
        """Test listing books when empty."""
        response = client.get("/api/books")

        assert response.status_code == 200
        data = response.json()
        assert data["books"] == []
        assert data["count"] == 0

    def test_list_books_with_books(self, client: TestClient, temp_db: Path):
        """Test listing books with existing books."""
        for i in range(3):
            client.post(
                "/api/books",
                json={
                    "title": f"Book {i}",
                    "chapters": [{"chapter_number": 1, "text": "Text"}],
                },
            )

        response = client.get("/api/books")

        assert response.status_code == 200
        assert response.json()["count"] == 3

    def test_list_books_pagination(self, client: TestClient, temp_db: Path):
        """Test book listing pagination."""
        for i in range(5):
            client.post(
                "/api/books",
                json={
                    "title": f"Book {i}",
                    "chapters": [{"chapter_number": 1, "text": "Text"}],
                },
            )

        response = client.get("/api/books?limit=2&offset=0")
        assert len(response.json()["books"]) == 2

        response = client.get("/api/books?limit=2&offset=2")
        assert len(response.json()["books"]) == 2


class TestGetBook:
    """Tests for get book endpoint."""

    def test_get_book_success(self, client: TestClient, temp_db: Path):
        """Test getting a book."""
        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        response = client.get(f"/api/books/{book_id}")

        assert response.status_code == 200
        assert response.json()["title"] == "Test Book"

    def test_get_book_not_found(self, client: TestClient):
        """Test getting non-existent book."""
        response = client.get("/api/books/nonexistent-id")

        assert response.status_code == 404


class TestCancelBook:
    """Tests for cancel book endpoint."""

    def test_cancel_book_success(self, client: TestClient, temp_db: Path):
        """Test cancelling a book."""
        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        response = client.post(f"/api/books/{book_id}/cancel")

        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()

    def test_cancel_book_not_found(self, client: TestClient):
        """Test cancelling non-existent book."""
        response = client.post("/api/books/nonexistent-id/cancel")

        assert response.status_code == 404

    def test_cancel_book_wrong_status(self, client: TestClient, temp_db: Path):
        """Test cancelling book in wrong status."""
        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        client.post(f"/api/books/{book_id}/cancel")

        response = client.post(f"/api/books/{book_id}/cancel")

        assert response.status_code == 400


class TestRetryBook:
    """Tests for retry book endpoint."""

    def test_retry_book_success(self, client: TestClient, temp_db: Path):
        """Test retrying a book."""
        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        response = client.post(f"/api/books/{book_id}/retry")

        assert response.status_code == 200
        assert "retry" in response.json()["message"].lower()

    def test_retry_book_not_found(self, client: TestClient):
        """Test retrying non-existent book."""
        response = client.post("/api/books/nonexistent-id/retry")

        assert response.status_code == 404


class TestDownloadChapter:
    """Tests for download chapter endpoint."""

    def test_download_chapter_not_found(self, client: TestClient, temp_db: Path):
        """Test downloading non-existent chapter."""
        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        response = client.get(f"/api/books/{book_id}/chapters/1/audio")

        assert response.status_code == 400

    def test_download_chapter_book_not_found(self, client: TestClient):
        """Test downloading chapter from non-existent book."""
        response = client.get("/api/books/nonexistent/chapters/1/audio")

        assert response.status_code == 404

    def test_download_chapter_success(
        self,
        client: TestClient,
        temp_db: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test downloading a completed chapter."""

        from app.core.database import get_connection

        monkeypatch.chdir(temp_output_dir)

        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        book_dir = temp_output_dir / "books" / book_id
        book_dir.mkdir(parents=True, exist_ok=True)
        audio_path = book_dir / "chapter_001.mp3"
        audio_path.write_bytes(b"ID3" + b"\x00" * 100)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 1",
            (str(audio_path), book_id),
        )
        cursor.execute("UPDATE books SET status = 'completed' WHERE id = ?", (book_id,))
        conn.commit()

        response = client.get(f"/api/books/{book_id}/chapters/1/audio")

        assert response.status_code == 200
        assert response.content == b"ID3" + b"\x00" * 100

    def test_download_chapter_file_missing(
        self,
        client: TestClient,
        temp_db: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test downloading chapter when file is missing from disk."""

        from app.core.database import get_connection

        monkeypatch.chdir(temp_output_dir)

        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 1",
            ("/nonexistent/path/audio.mp3", book_id),
        )
        conn.commit()

        response = client.get(f"/api/books/{book_id}/chapters/1/audio")

        assert response.status_code == 404


class TestDownloadBookZip:
    """Tests for download book zip endpoint."""

    def test_download_book_zip_no_chapters(self, client: TestClient, temp_db: Path):
        """Test downloading book with no completed chapters."""
        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [{"chapter_number": 1, "text": "Text"}],
            },
        )
        book_id = create_response.json()["id"]

        response = client.get(f"/api/books/{book_id}/download")

        assert response.status_code == 400

    def test_download_book_zip_not_found(self, client: TestClient):
        """Test downloading non-existent book."""
        response = client.get("/api/books/nonexistent/download")

        assert response.status_code == 404

    def test_download_book_zip_success(
        self,
        client: TestClient,
        temp_db: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test downloading book zip with completed chapters."""
        import zipfile

        from app.core.database import get_connection

        monkeypatch.chdir(temp_output_dir)

        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book!",
                "chapters": [
                    {"chapter_number": 1, "text": "Text 1"},
                    {"chapter_number": 2, "text": "Text 2"},
                ],
            },
        )
        book_id = create_response.json()["id"]

        book_dir = temp_output_dir / "books" / book_id
        book_dir.mkdir(parents=True, exist_ok=True)

        audio1_path = book_dir / "chapter_001.mp3"
        audio1_path.write_bytes(b"ID3" + b"\x00" * 100)
        audio2_path = book_dir / "chapter_002.wav"
        audio2_path.write_bytes(b"RIFF" + b"\x00" * 100 + b"WAVE")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 1",
            (str(audio1_path), book_id),
        )
        cursor.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 2",
            (str(audio2_path), book_id),
        )
        cursor.execute("UPDATE books SET status = 'completed' WHERE id = ?", (book_id,))
        conn.commit()

        response = client.get(f"/api/books/{book_id}/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert 'filename="Test_Book.zip"' in response.headers["content-disposition"]

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            names = zf.namelist()
            assert "chapter_001.mp3" in names
            assert "chapter_002.wav" in names

    def test_download_book_zip_uses_book_id_when_title_sanitizes_to_empty(
        self,
        client: TestClient,
        temp_db: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """When the title is only punctuation, the zip uses book_{id[:8]}."""
        from app.core.database import get_connection

        monkeypatch.chdir(temp_output_dir)

        create_response = client.post(
            "/api/books",
            json={"title": "!@#", "chapters": [{"chapter_number": 1, "text": "T"}]},
        )
        book_id = create_response.json()["id"]
        book_dir = temp_output_dir / "books" / book_id
        book_dir.mkdir(parents=True, exist_ok=True)
        audio_path = book_dir / "chapter_001.mp3"
        audio_path.write_bytes(b"ID3" + b"\x00" * 10)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 1",
            (str(audio_path), book_id),
        )
        cur.execute("UPDATE books SET status = 'completed' WHERE id = ?", (book_id,))
        conn.commit()

        response = client.get(f"/api/books/{book_id}/download")
        assert response.status_code == 200
        expected = f'filename="book_{book_id[:8]}.zip"'
        assert expected in response.headers["content-disposition"]

    @patch("app.api.endpoints.books.zipfile.ZipFile", side_effect=OSError("zip failed"))
    def test_download_book_zip_write_failure(
        self,
        _mock_zip: object,
        client: TestClient,
        temp_db: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """ZipFile creation errors are re-raised to the test client (no partial response)."""
        from app.core.database import get_connection

        monkeypatch.chdir(temp_output_dir)
        create_response = client.post(
            "/api/books",
            json={"title": "Z", "chapters": [{"chapter_number": 1, "text": "T"}]},
        )
        book_id = create_response.json()["id"]
        book_dir = temp_output_dir / "books" / book_id
        book_dir.mkdir(parents=True, exist_ok=True)
        audio_path = book_dir / "chapter_001.mp3"
        audio_path.write_bytes(b"ID3" + b"\x00" * 10)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 1",
            (str(audio_path), book_id),
        )
        cur.execute("UPDATE books SET status = 'completed' WHERE id = ?", (book_id,))
        conn.commit()

        with pytest.raises(OSError, match="zip failed"):
            client.get(f"/api/books/{book_id}/download")

    @patch("app.api.endpoints.books.zipfile.ZipFile", side_effect=OSError("zip failed"))
    def test_download_book_zip_error_skips_unlink_if_zip_missing(
        self,
        _mock_zip: object,
        client: TestClient,
        temp_db: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """In the error handler, skip unlink if the temp zip path no longer exists."""
        from app.core.database import get_connection

        real_exists = Path.exists

        def exists_wrapper(self) -> bool:
            path_str = str(self)
            if path_str.endswith(".zip") and "tmp" in path_str:
                return False
            return real_exists(self)

        monkeypatch.chdir(temp_output_dir)
        create_response = client.post(
            "/api/books",
            json={"title": "Z", "chapters": [{"chapter_number": 1, "text": "T"}]},
        )
        book_id = create_response.json()["id"]
        book_dir = temp_output_dir / "books" / book_id
        book_dir.mkdir(parents=True, exist_ok=True)
        audio_path = book_dir / "chapter_001.mp3"
        audio_path.write_bytes(b"ID3" + b"\x00" * 10)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 1",
            (str(audio_path), book_id),
        )
        cur.execute("UPDATE books SET status = 'completed' WHERE id = ?", (book_id,))
        conn.commit()

        with (
            patch.object(Path, "exists", exists_wrapper),
            pytest.raises(OSError, match="zip failed"),
        ):
            client.get(f"/api/books/{book_id}/download")

    def test_download_book_zip_missing_file(
        self,
        client: TestClient,
        temp_db: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test downloading book zip when some files are missing."""
        import zipfile

        from app.core.database import get_connection

        monkeypatch.chdir(temp_output_dir)

        create_response = client.post(
            "/api/books",
            json={
                "title": "Test Book",
                "chapters": [
                    {"chapter_number": 1, "text": "Text 1"},
                    {"chapter_number": 2, "text": "Text 2"},
                ],
            },
        )
        book_id = create_response.json()["id"]

        book_dir = temp_output_dir / "books" / book_id
        book_dir.mkdir(parents=True, exist_ok=True)

        audio1_path = book_dir / "chapter_001.mp3"
        audio1_path.write_bytes(b"ID3" + b"\x00" * 100)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 1",
            (str(audio1_path), book_id),
        )
        cursor.execute(
            "UPDATE chapters SET status = 'completed', audio_path = ? WHERE book_id = ? AND chapter_number = 2",
            ("/nonexistent/path/audio.mp3", book_id),
        )
        cursor.execute("UPDATE books SET status = 'completed' WHERE id = ?", (book_id,))
        conn.commit()

        response = client.get(f"/api/books/{book_id}/download")

        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            names = zf.namelist()
            assert "chapter_001.mp3" in names
            assert "chapter_002.mp3" not in names
