import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)

@patch("trafilatura.fetch_url")
@patch("trafilatura.extract")
@patch("trafilatura.extract_metadata")
def test_scrape_endpoint_success(mock_extract_metadata, mock_extract, mock_fetch_url):
    mock_fetch_url.return_value = "<html><body>Some content</body></html>"
    mock_extract.return_value = "Some content"
    
    mock_metadata = MagicMock()
    mock_metadata.title = "Test Title"
    mock_extract_metadata.return_value = mock_metadata
    
    response = client.post("/api/scrape", json={"url": "https://example.com"})
    
    assert response.status_code == 200
    assert response.json() == {
        "title": "Test Title",
        "text": "Some content",
        "url": "https://example.com"
    }

@patch("trafilatura.fetch_url")
def test_scrape_endpoint_fetch_fail(mock_fetch_url):
    mock_fetch_url.return_value = None
    
    response = client.post("/api/scrape", json={"url": "https://example.com"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Failed to fetch URL"

@patch("trafilatura.fetch_url")
@patch("trafilatura.extract")
def test_scrape_endpoint_extract_fail(mock_extract, mock_fetch_url):
    mock_fetch_url.return_value = "<html><body></body></html>"
    mock_extract.return_value = None
    
    response = client.post("/api/scrape", json={"url": "https://example.com"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Failed to extract content"
