from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class DetectionMethod(str, Enum):
    """Detection methods for traceability in output URL set"""
    SITEMAP = "sitemap"
    FIRECRAWL_MAP = "firecrawl_map"
    FIRECRAWL_CRAWL = "firecrawl_crawl"
    TOP_URL_CRAWLING = "top_url_crawling"
    PAGINATION_CRAWLING = "pagination_crawling"
    PAGINATION_DISCOVERY = "pagination_discovery"

class UrlInfo(BaseModel):
    """Metadata for full traceability through URL processing"""
    url: str
    detection_methods: List[DetectionMethod]
    detected_at: datetime
    source_url: Optional[str] = None  # URL where this URL was discovered
    pagination_page: Optional[int] = None  # Page number if discovered via pagination
    pagination_type: Optional[str] = None  # Type of pagination used

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UrlResolutionResult(BaseModel):
    """Result of URL resolution operation"""
    original_url: str
    resolved_url: str
    resolution_success: bool
    error_message: Optional[str] = None
    resolution_time: Optional[float] = None  # Time taken to resolve in seconds

class UrlResolutionMapping(BaseModel):
    """Mapping of original URLs to resolved URLs with metadata"""
    mappings: Dict[str, UrlResolutionResult]
    total_urls: int
    successful_resolutions: int
    failed_resolutions: int
    processing_time_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UrlDeduplicationResult(BaseModel):
    """Result of URL deduplication operation"""
    original_urls: List[str]
    unique_urls: List[str]
    duplicates_removed: List[str]
    duplicate_groups: List[List[str]]  # Groups of URLs that resolve to same page
    total_original: int
    total_unique: int
    total_duplicates: int
    processing_time_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class OutputURLsWithInfo(BaseModel):
    """URLs with metadata for traceability"""
    urls: List[UrlInfo]
    total_count: int
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UrlProcessingResult(BaseModel):
    """Result of URL processing operations with preserved metadata"""
    urls: List[UrlInfo]
    total_count: int
    processing_time_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)
    operation_type: str  # "deduplication", "normalization", "filtering", etc.
    metadata: Dict[str, Union[str, int, float, bool, List[str]]] = Field(default_factory=dict)  # Operation-specific data
    pagination_info: Optional[Any] = None  # Pagination information if applicable

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class PaginationProcessingResult(BaseModel):
    """Result of pagination processing operations"""
    urls: List[UrlInfo]
    total_count: int
    processing_time_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)
    pagination_info: Optional[Any] = None
    pages_crawled: int = 0
    articles_discovered: int = 0
    pagination_type: Optional[str] = None
    confidence_score: Optional[float] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class OnboardingResult(BaseModel):
    """Result set from onboarding"""
    site_id: str
    top_urls: List[str]
    onboarding_time: datetime
    total_urls_analyzed: int
    pagination_enabled: bool = False
    pagination_info: Optional[Any] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UrlSet(BaseModel):
    """Complete set of URLs found for a site"""
    site_id: str
    timestamp: datetime
    urls: List[UrlInfo]
    total_count: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UrlAnalysisRequest(BaseModel):
    """Request for AI LLM newsworthy analysis of URLs"""
    urls: List[str]
    site_name: str
    # analysis_type: str = "change_likelihood"  # do we need this?

class UrlAnalysisResponse(BaseModel):
    """Response from AI LLM newsworthy analysis"""
    urls: List[str]

class UrlJudgeRequest(BaseModel):
    """Request for AI LLM judge to select best URLs"""
    url_suggestions: List[List[str]]
    site_name: str
    selection_count: int = 5

class UrlJudgeResponse(BaseModel):
    """Response from AI LLM judge"""
    selected_urls: List[str]
    rejected_urls: List[str] = Field(default_factory=list)

class ProcessingSummary(BaseModel):
    """Summary of URL processing results"""
    status: str  # "completed", "failed", "partial"
    urls_found: int
    urls_processed: int
    processing_time_seconds: float
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    detection_methods_used: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }