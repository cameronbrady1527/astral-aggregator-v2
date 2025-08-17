from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SiteStatus(str, Enum):
    """Status of site onboarding"""
    NOT_ONBOARDED = "not_onboarded"
    ONBOARDED = "onboarded"
    FAILED = "failed"

class SiteConfig(BaseModel):
    """Configuration for a single site"""
    name: str
    url: str
    sitemap_url: str
    is_sitemap_index: bool = False
    is_sitemap: bool = True  # New field: True if site has a sitemap, False if no sitemap
    onboarded: bool = False
    top_urls: List[str] = Field(default_factory=list)
    onboarding_datetime: Optional[datetime] = None
    status: SiteStatus = SiteStatus.NOT_ONBOARDED
    last_processed: Optional[datetime] = None
    
    # Pagination configuration
    pagination_enabled: bool = Field(default=True, description="Enable pagination detection and handling")
    pagination_max_pages: int = Field(default=1000, description="Maximum pages to crawl for pagination")
    pagination_rate_limit: float = Field(default=2.0, description="Seconds between batch requests")
    pagination_concurrent_batches: int = Field(default=10, description="Pages per batch for concurrent crawling")
    pagination_custom_patterns: List[str] = Field(default_factory=list, description="Custom pagination patterns for this site")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class SitesConfig(BaseModel):
    """Complete sites configuration"""
    sites: dict[str, SiteConfig] = Field(default_factory=dict)

class SiteUpdate(BaseModel):
    """Model for updating site configuration"""
    name: Optional[str] = None
    url: Optional[str] = None
    sitemap_url: Optional[str] = None  # can be a sitemap index: if so, set below to True
    is_sitemap_index: Optional[bool] = None
    is_sitemap: Optional[bool] = None  # New field: True if site has a sitemap, False if no sitemap
    onboarded: Optional[bool] = None
    top_urls: Optional[List[str]] = None
    onboarding_datetime: Optional[datetime] = None
    status: Optional[SiteStatus] = None
    last_processed: Optional[datetime] = None
    
    # Pagination configuration updates
    pagination_enabled: Optional[bool] = None
    pagination_max_pages: Optional[int] = None
    pagination_rate_limit: Optional[float] = None
    pagination_concurrent_batches: Optional[int] = None
    pagination_custom_patterns: Optional[List[str]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }