"""
Pydantic models for folders API.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateFolderRequest(BaseModel):
    """Request payload to create a new folder."""
    name: str = Field(..., min_length=1, max_length=200, description="Folder name")
    parent_id: Optional[str] = Field(None, description="Optional parent folder ID")


class FolderResponse(BaseModel):
    """Folder details."""
    id: str
    parent_id: Optional[str] = None
    name: str
    created_at: str
    updated_at: str


class FoldersListResponse(BaseModel):
    """Response payload for listing folders."""
    folders: List[FolderResponse]
    count: int