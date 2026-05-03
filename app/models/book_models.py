"""
Pydantic models for the audiobook jobs API.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ChapterInput(BaseModel):
    """Input model for a single chapter."""
    chapter_number: int = Field(..., ge=1, description="1-indexed chapter number")
    title: Optional[str] = Field(None, description="Optional chapter title")
    text: str = Field(..., min_length=1, description="Full chapter text")


class BookConfig(BaseModel):
    """Configuration overrides for TTS generation of a book."""
    max_sentences_per_chunk: int = Field(5, ge=1, le=50, description="Max sentences per chunk")
    max_chunk_chars: int = Field(320, ge=50, le=1000, description="Max characters per chunk")
    chunk_gap_ms: int = Field(120, ge=0, le=1000, description="Gap between chunks in ms")


class CreateBookRequest(BaseModel):
    """Request payload to create a new audiobook job."""
    title: str = Field(..., min_length=1, max_length=200, description="Book title")
    voice: Optional[str] = Field(None, description="Voice alias (defaults to server default if null)")
    output_format: str = Field("mp3", description="Output format: mp3 or wav")
    folder_id: Optional[str] = Field(None, description="Optional folder ID")
    chapters: List[ChapterInput] = Field(..., min_length=1, description="List of chapters to process")
    config: BookConfig = Field(default_factory=BookConfig)  # type: ignore[arg-type]


class ChapterStatus(BaseModel):
    """Status of a specific chapter."""
    chapter_number: int
    title: Optional[str] = None
    status: str
    duration_secs: Optional[float] = None
    error: Optional[str] = None
    retry_count: int = 0
    completed_chunks: int = 0
    total_chunks: int = 0


class BookProgress(BaseModel):
    """Aggregated progress statistics for a book."""
    total_chapters: int
    completed: int
    failed: int
    pending: int
    processing: int
    percent_complete: float


class BookResponse(BaseModel):
    """Full details of a book job including all chapters."""
    id: str
    title: str
    status: str
    voice: Optional[str] = None
    output_format: str
    folder_id: Optional[str] = None
    progress: BookProgress
    chapters: List[ChapterStatus]
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class BookListItem(BaseModel):
    """Summary of a book job for list views."""
    id: str
    title: str
    status: str
    total_chapters: int
    folder_id: Optional[str] = None
    created_at: str
    updated_at: str


class BooksListResponse(BaseModel):
    """Response payload for listing books."""
    books: List[BookListItem]
    count: int
