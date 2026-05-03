"""
Folder management API endpoints.
"""

from sqlite3 import IntegrityError
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.core.database import BookRepository
from app.models.folder_models import (
    CreateFolderRequest,
    FolderResponse,
    FoldersListResponse,
)

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post(
    "",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new folder",
)
async def create_folder(request: CreateFolderRequest) -> FolderResponse:
    repo = BookRepository()
    try:
        folder_id = repo.create_folder(
            name=request.name,
            parent_id=request.parent_id,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder with this name already exists in the specified location",
        )

    return await get_folder(folder_id)


@router.get(
    "",
    response_model=FoldersListResponse,
    summary="List folders",
)
async def list_folders(
    parent_id: str | Literal["root"] | None = Query(default=None, description="Filter by parent folder ID or 'root'"),
) -> FoldersListResponse:
    repo = BookRepository()
    folders_data = repo.get_folders(parent_id=parent_id)

    folders = [
        FolderResponse(
            id=row["id"],
            parent_id=row["parent_id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in folders_data
    ]

    return FoldersListResponse(folders=folders, count=len(folders))


@router.get(
    "/{folder_id}",
    response_model=FolderResponse,
    summary="Get a specific folder",
)
async def get_folder(folder_id: str) -> FolderResponse:
    repo = BookRepository()
    folder = repo.get_folder(folder_id)

    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    return FolderResponse(
        id=folder["id"],
        parent_id=folder["parent_id"],
        name=folder["name"],
        created_at=folder["created_at"],
        updated_at=folder["updated_at"],
    )


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a folder",
)
async def delete_folder(folder_id: str) -> None:
    repo = BookRepository()
    folder = repo.get_folder(folder_id)

    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    repo.delete_folder(folder_id)