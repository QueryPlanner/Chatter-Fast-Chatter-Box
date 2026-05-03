"""
Book generation API endpoints.
"""

import os
import tempfile
import zipfile
from pathlib import Path

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.database import BookRepository
from app.models.book_models import (
    BookListItem,
    BookProgress,
    BookResponse,
    BooksListResponse,
    ChapterStatus,
    CreateBookRequest,
)

router = APIRouter(prefix="/books", tags=["books"])


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new book job",
    description="Submit a book consisting of multiple chapters for asynchronous TTS generation.",
)
async def create_book(request: CreateBookRequest) -> BookResponse:
    """Submit a new book for processing."""
    repo = BookRepository()

    # Extract config into dict
    metadata = request.config.model_dump()

    book_id = repo.create_book(
        title=request.title,
        voice=request.voice,
        output_format=request.output_format,
        chapters=[ch.model_dump() for ch in request.chapters],
        metadata=metadata,
        folder_id=request.folder_id,
    )

    return await get_book(book_id)


@router.get(
    "",
    response_model=BooksListResponse,
    summary="List all books",
    description="List all submitted book jobs with their current status.",
)
async def list_books(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    folder_id: str | Literal["root"] | None = Query(default=None, description="Filter by folder ID or 'root'"),
) -> BooksListResponse:
    """List all books."""
    repo = BookRepository()
    books_data = repo.get_books(limit=limit, offset=offset, folder_id=folder_id)

    books = [
        BookListItem(
            id=row["id"],
            title=row["title"],
            status=row["status"],
            total_chapters=row["total_chapters"],
            folder_id=row["folder_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in books_data
    ]

    return BooksListResponse(books=books, count=len(books))


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    summary="Get book status",
    description="Get detailed progress and status of a specific book job.",
)
async def get_book(book_id: str) -> BookResponse:
    """Get detailed book status."""
    repo = BookRepository()
    book = repo.get_book(book_id)

    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    chapters_data = repo.get_chapters(book_id)

    chunk_progress = repo.get_chunk_progress_for_book(book_id)

    total_chapters = book["total_chapters"]
    counts = {"completed": 0, "failed": 0, "pending": 0, "processing": 0}
    chapters = []

    for ch in chapters_data:
        counts[ch["status"]] = counts.get(ch["status"], 0) + 1
        completed_chunks, total_chunks = chunk_progress.get(ch["id"], (0, 0))
        chapters.append(
            ChapterStatus(
                chapter_number=ch["chapter_number"],
                title=ch["title"],
                status=ch["status"],
                duration_secs=ch["duration_secs"],
                error=ch["error"],
                retry_count=ch["retry_count"],
                completed_chunks=completed_chunks,
                total_chunks=total_chunks,
            )
        )

    percent_complete = (counts["completed"] / total_chapters) * 100 if total_chapters > 0 else 0

    progress = BookProgress(
        total_chapters=total_chapters,
        completed=counts["completed"],
        failed=counts["failed"],
        pending=counts["pending"],
        processing=counts["processing"],
        percent_complete=round(percent_complete, 2),
    )

    return BookResponse(
        id=book["id"],
        title=book["title"],
        status=book["status"],
        voice=book["voice"],
        output_format=book["output_format"],
        folder_id=book["folder_id"],
        progress=progress,
        chapters=chapters,
        created_at=book["created_at"],
        updated_at=book["updated_at"],
        completed_at=book["completed_at"],
        error=book["error"],
    )


@router.post(
    "/{book_id}/cancel",
    summary="Cancel a book job",
    description="Cancel a queued or processing book.",
)
async def cancel_book(book_id: str) -> dict:
    """Cancel a book job."""
    repo = BookRepository()
    book = repo.get_book(book_id)

    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book["status"] not in ("queued", "processing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel book in status '{book['status']}'",
        )

    repo.mark_book_cancelled(book_id)
    return {"message": f"Book {book_id} cancelled successfully."}


@router.post(
    "/{book_id}/retry",
    summary="Retry failed chapters",
    description="Retry any chapters that failed in a book job.",
)
async def retry_book(book_id: str) -> dict:
    """Retry failed chapters in a book."""
    repo = BookRepository()
    book = repo.get_book(book_id)

    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    repo.retry_failed_chapters(book_id)
    return {"message": f"Retrying failed chapters for book {book_id}."}


@router.get(
    "/{book_id}/chapters/{chapter_number}/audio",
    response_class=FileResponse,
    summary="Download chapter audio",
    description="Download the audio file for a completed chapter.",
)
async def download_chapter(book_id: str, chapter_number: int) -> FileResponse:
    """Download a single chapter's audio."""
    repo = BookRepository()
    chapter = repo.get_chapter(book_id, chapter_number)

    if not chapter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    if chapter["status"] != "completed" or not chapter["audio_path"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chapter {chapter_number} is not completed (status: {chapter['status']})",
        )

    path = Path(chapter["audio_path"])
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing on disk"
        )

    return FileResponse(
        path,
        filename=path.name,
        media_type="audio/mpeg" if path.suffix == ".mp3" else "audio/wav",
    )


@router.get(
    "/{book_id}/download",
    response_class=FileResponse,
    summary="Download full book",
    description="Download all completed chapters as a ZIP file.",
)
async def download_book_zip(book_id: str, background_tasks: BackgroundTasks) -> FileResponse:
    """Download all completed chapters as a ZIP file."""
    repo = BookRepository()
    book = repo.get_book(book_id)

    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    chapters = repo.get_chapters(book_id)
    completed_chapters = [ch for ch in chapters if ch["status"] == "completed" and ch["audio_path"]]

    if not completed_chapters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No completed chapters to download"
        )

    temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    temp_zip_path = Path(temp_zip.name)
    temp_zip.close()

    try:
        with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for ch in completed_chapters:
                path = Path(ch["audio_path"])
                if path.exists():
                    zip_file.write(path, arcname=path.name)
    except Exception:
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        raise

    # Create a safe filename from the title
    safe_title = "".join([c if c.isalnum() else "_" for c in book["title"]]).strip("_")
    if not safe_title:
        safe_title = f"book_{book_id[:8]}"

    background_tasks.add_task(os.remove, str(temp_zip_path))
    return FileResponse(
        path=temp_zip_path,
        filename=f"{safe_title}.zip",
        media_type="application/zip",
    )
