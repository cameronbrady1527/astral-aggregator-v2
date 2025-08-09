# ==============================================================================
# models/__init__.py — Models Package
# ==============================================================================
# Purpose: Pydantic models for URL processing and configuration
# ==============================================================================

from .url_models import (
    DetectionMethod,
    UrlInfo,
    UrlResolutionResult,
    UrlResolutionMapping,
    UrlDeduplicationResult,
    OutputURLsWithInfo,
    UrlProcessingResult,
    OnboardingResult,
    UrlSet,
    UrlAnalysisRequest,
    UrlAnalysisResponse,
    UrlJudgeRequest,
    UrlJudgeResponse,
    ProcessingSummary,
)

from .config_models import (
    SiteStatus,
    SiteConfig,
    SitesConfig,
    SiteUpdate,
)

__all__ = [
    # URL Models
    'DetectionMethod',
    'UrlInfo',
    'UrlResolutionResult',
    'UrlResolutionMapping',
    'UrlDeduplicationResult',
    'OutputURLsWithInfo',
    'UrlProcessingResult',
    'OnboardingResult',
    'UrlSet',
    'UrlAnalysisRequest',
    'UrlAnalysisResponse',
    'UrlJudgeRequest',
    'UrlJudgeResponse',
    'ProcessingSummary',
    
    # Config Models
    'SiteStatus',
    'SiteConfig',
    'SitesConfig',
    'SiteUpdate',
]
