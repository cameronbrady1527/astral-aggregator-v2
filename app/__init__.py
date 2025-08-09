# ==============================================================================
# app/__init__.py — URL Aggregator Application
# ==============================================================================
# Purpose: Main application package with public API
# ==============================================================================

# Version information
__version__ = "1.0.0"
__author__ = "Astral AI"

# Core application components
from .main import app
from .routers.url_router import router as url_router

# Service layer
from .services import UrlService, OnboardingUrlService, ConfigService

# Models
from .models import (
    UrlInfo, 
    DetectionMethod, 
    OnboardingResult,
    SiteConfig,
    SiteStatus
)

# Utilities
from .utils import JsonWriter

__all__ = [
    # Application
    'app',
    'url_router',
    
    # Services
    'UrlService',
    'OnboardingUrlService', 
    'ConfigService',
    
    # Models
    'UrlInfo',
    'DetectionMethod',
    'OnboardingResult',
    'SiteConfig',
    'SiteStatus',
    
    # Utilities
    'JsonWriter',
    
    # Metadata
    '__version__',
    '__author__',
]
