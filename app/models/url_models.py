from typing import List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class DetectionMethod(str, Enum):
    """Detection methods for traceability in output URL set"""
    SITEMAP = "sitemap"
    FIRECRAWL_MAP = "firecrawl_map"
    FIRECRAWL_CRAWL = "firecrawl_crawl"

class UrlInfo(BaseModel):
    """Metadata for full traceability through URL processing"""
    url: str
    detection_methods: List[DetectionMethod]
    detected_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class OutputURLsWithInfo(BaseModel):
    """URLs with metadata for traceability"""
    urls: List[UrlInfo]

class OutputURLsWithoutInfo(BaseModel):
    """URLS without metadata"""
    urls: List[str]

class OnboardingResult(BaseModel):
    """Result set from onboarding"""
    site_id: str
    top_urls: List[str]
    onboarding_time: datetime
    total_urls_analyzed: int

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