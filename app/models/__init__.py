# ==============================================================================
# __init__.py — Model layer exports
# ==============================================================================
# Purpose: Export Pydantic models for easy importing
# Sections: Imports, Public exports
# ==============================================================================

from .url_models import (
    UrlInfo,
    DetectionMethod,
    UrlAnalysisRequest,
    UrlAnalysisResponse,
    UrlJudgeRequest,
    UrlJudgeResponse,
    OutputURLsWithInfo,
    OnboardingResult,
    UrlSet,
    ProcessingSummary,
    UrlResolutionResult,
    UrlResolutionMapping,
    UrlDeduplicationResult,
    UrlProcessingResult
)

from .config_models import (
    SiteStatus,
    SiteConfig,
    SitesConfig,
    SiteUpdate
)

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = [
    # URL Models
    "UrlInfo",
    "DetectionMethod", 
    "UrlAnalysisRequest",
    "UrlAnalysisResponse",
    "UrlJudgeRequest",
    "UrlJudgeResponse",
    "OutputURLsWithInfo",
    "OnboardingResult",
    "UrlSet",
    "ProcessingSummary",
    "UrlResolutionResult",
    "UrlResolutionMapping",
    "UrlDeduplicationResult",
    "UrlProcessingResult",
    
    # Config Models
    "SiteStatus",
    "SiteConfig",
    "SitesConfig",
    "SiteUpdate"
]
