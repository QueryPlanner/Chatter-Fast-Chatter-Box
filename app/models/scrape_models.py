from pydantic import BaseModel, Field

class ScrapeRequest(BaseModel):
    url: str = Field(..., description="The URL to scrape")

class ScrapeResponse(BaseModel):
    title: str = Field(..., description="The title of the page")
    text: str = Field(..., description="The main content text extracted from the page")
    url: str = Field(..., description="The URL that was scraped")
