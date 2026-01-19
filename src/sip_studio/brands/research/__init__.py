"""Brand creation research module - models for website scraping and job management."""

from .deep_research import (
    BrandResearchError,
    BrandResearchWrapper,
    research_brand,
)
from .evaluation import (
    EvaluationError,
    ResearchEvaluator,
    evaluate_research,
)
from .job_storage import (
    cancel_job,
    cleanup_on_startup,
    clear_job,
    complete_job,
    create_job,
    fail_job,
    get_job_path,
    get_jobs_dir,
    has_active_job,
    is_cancellation_requested,
    load_job,
    request_cancellation,
    save_job,
    update_job_progress,
)
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
    "BrandResearchError",
    "BrandResearchWrapper",
    "EvaluationError",
    "ResearchEvaluator",
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
    "cancel_job",
    "cleanup_on_startup",
    "clear_job",
    "complete_job",
    "create_job",
    "evaluate_research",
    "fail_job",
    "get_job_path",
    "get_jobs_dir",
    "has_active_job",
    "is_cancellation_requested",
    "load_job",
    "request_cancellation",
    "research_brand",
    "save_job",
    "update_job_progress",
]
