# ==============================================================================
# clients/__init__.py — External API Clients
# ==============================================================================
# Purpose: Client classes for external API interactions
# ==============================================================================

from .firecrawl_client import FirecrawlClient
from .openai_client import OpenAIClient

__all__ = [
    'FirecrawlClient',
    'OpenAIClient',
]
