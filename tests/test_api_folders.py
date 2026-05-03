"""
Tests for folder API endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.endpoints.folders import router
from app.main import app

client = TestClient(app)

class TestCreateFolder:
    @patch("app.api.endpoints.folders.BookRepository")
    def test_create_folder_success(self, mock_repo_class: MagicMock) -> None:
        mock_repo = mock_repo_class.return_value
        mock_repo.create_folder.return_value = "folder-id"
        mock_repo.get_folder.return_value = {
            "id": "folder-id",
            "parent_id": None,
            "name": "My Folder",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        response = client.post("/api/folders", json={"name": "My Folder"})

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "folder-id"
        assert data["name"] == "My Folder"

    @patch("app.api.endpoints.folders.BookRepository")
    def test_create_folder_conflict(self, mock_repo_class: MagicMock) -> None:
        from sqlite3 import IntegrityError
        mock_repo = mock_repo_class.return_value
        mock_repo.create_folder.side_effect = IntegrityError()

        response = client.post("/api/folders", json={"name": "My Folder"})

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

class TestListFolders:
    @patch("app.api.endpoints.folders.BookRepository")
    def test_list_folders_success(self, mock_repo_class: MagicMock) -> None:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_folders.return_value = [
            {
                "id": "folder-id",
                "parent_id": None,
                "name": "My Folder",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]

        response = client.get("/api/folders")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["folders"][0]["name"] == "My Folder"

class TestGetFolder:
    @patch("app.api.endpoints.folders.BookRepository")
    def test_get_folder_success(self, mock_repo_class: MagicMock) -> None:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_folder.return_value = {
            "id": "folder-id",
            "parent_id": None,
            "name": "My Folder",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        response = client.get("/api/folders/folder-id")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Folder"

    @patch("app.api.endpoints.folders.BookRepository")
    def test_get_folder_not_found(self, mock_repo_class: MagicMock) -> None:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_folder.return_value = None

        response = client.get("/api/folders/folder-id")

        assert response.status_code == 404

class TestDeleteFolder:
    @patch("app.api.endpoints.folders.BookRepository")
    def test_delete_folder_success(self, mock_repo_class: MagicMock) -> None:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_folder.return_value = {"id": "folder-id"}

        response = client.delete("/api/folders/folder-id")

        assert response.status_code == 204
        mock_repo.delete_folder.assert_called_once_with("folder-id")

    @patch("app.api.endpoints.folders.BookRepository")
    def test_delete_folder_not_found(self, mock_repo_class: MagicMock) -> None:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_folder.return_value = None

        response = client.delete("/api/folders/folder-id")

        assert response.status_code == 404
