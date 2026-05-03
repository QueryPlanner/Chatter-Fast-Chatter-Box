from fastapi import APIRouter, HTTPException
import trafilatura
from app.models.scrape_models import ScrapeRequest, ScrapeResponse

router = APIRouter(tags=["scrape"])

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    """
    Scrape a URL to extract its main content and title.
    """
    downloaded = trafilatura.fetch_url(request.url)
    if downloaded is None:
        raise HTTPException(status_code=400, detail="Failed to fetch URL")
    
    result = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if result is None:
        raise HTTPException(status_code=400, detail="Failed to extract content")
    
    # Optionally get metadata for title
    metadata = trafilatura.extract_metadata(downloaded)
    title = metadata.title if metadata and metadata.title else "Extracted Content"
    
    return ScrapeResponse(title=title, text=result, url=request.url)
