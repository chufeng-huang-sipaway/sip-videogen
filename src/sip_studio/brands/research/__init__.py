"""Brand creation research module - models for website scraping and job management."""

from .models import (
    BrandCreationJob,
    BrandResearchBundle,
    JobPhase,
    JobStatus,
    ResearchCompleteness,
    WebsiteAssets,
)
from .website_scraper import (
    ContentTooLargeError,
    InvalidContentTypeError,
    MaxRetriesError,
    SSRFError,
    scrape_website,
    validate_url_for_scraping,
)

__all__ = [
    "BrandCreationJob",
    "BrandResearchBundle",
    "JobPhase",
    "JobStatus",
    "ResearchCompleteness",
    "WebsiteAssets",
    "SSRFError",
    "MaxRetriesError",
    "ContentTooLargeError",
    "InvalidContentTypeError",
    "scrape_website",
    "validate_url_for_scraping",
]
