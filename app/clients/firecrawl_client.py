# ==============================================================================
# firecrawl_client.py — Firecrawl SDK client
# ==============================================================================
# Purpose: Handle Firecrawl SDK communication and authentication
# Sections: Imports, Public API, Main Classes
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
import asyncio
from typing import List, Optional

# Third Party -----
from firecrawl import AsyncFirecrawlApp

# Astral AI ----
from app.services.config_service import config_service

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = ["FirecrawlClient"]

# ==============================================================================
# Main Classes
# ==============================================================================

class FirecrawlClient:
    """Client for Firecrawl SDK communication."""
    
    def __init__(self):
        self.api_key = config_service.firecrawl_api_key
        self._app: Optional[AsyncFirecrawlApp] = None
        
    async def __aenter__(self):
        """Async context manager for SDK client lifecycle."""
        self._app = AsyncFirecrawlApp(api_key=self.api_key)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up SDK client."""
        if self._app:
            # SDK handles cleanup automatically
            pass
    
    async def map_site(self, url: str, include_subdomains: bool = True) -> List[str]:
        """
        Raw SDK call to Firecrawl map_url endpoint.
        
        Args:
            url: Base URL of the site to map
            include_subdomains: Whether to include subdomains
            
        Returns:
            List of discovered URLs from SDK response
        """
        if not self._app:
            raise RuntimeError("Client must be used as async context manager")
            
        try:
            response = await self._app.map_url(
                url=url,
                limit=30000,
                include_subdomains=include_subdomains
            )
            
            # extract URLs from response
            # assuming response has a structure with URLs
            if hasattr(response, 'links'):
                return response.links
            elif hasattr(response, 'urls'):
                return response.urls
            elif isinstance(response, dict):
                return response.get('links', []) or response.get('urls', [])
            else:
                # fallback - try to extract URLs from response
                return self._extract_urls_from_response(response)
            
        except Exception as e:
            raise Exception(f"Firecrawl map SDK call failed: {str(e)}")
    
    async def crawl_urls(self, urls: List[str], max_depth: int = 2, limit: int = 1) -> List[str]:
        """
        Raw SDK call to Firecrawl crawl_urls endpoint.
        
        Args:
            urls: List of URLs to crawl
            max_depth: Maximum crawl depth
            limit: Limit per URL
            
        Returns:
            List of discovered URLs from SDK response
        """
        if not self._app:
            raise RuntimeError("Client must be used as async context manager")
            
        all_discovered_urls = []
        
        # process URLs in batches to avoid overwhelming the API
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            
            tasks = [
                self._crawl_single_url(url, max_depth, limit)
                for url in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, list):
                    all_discovered_urls.extend(result)
        
        return list(set(all_discovered_urls))  # remove duplicates

    async def _crawl_single_url(self, url: str, max_depth: int, limit: int) -> List[str]:
        """
        Raw SDK call to crawl a single URL.
        
        Args:
            url: URL to crawl
            max_depth: Maximum crawl depth
            limit: Limit for this URL
            
        Returns:
            List of discovered URLs
        """
        try:
            response = await self._app.crawl_url(
                url=url,
                max_depth=max_depth,
                limit=limit
            )
            
            # extract URLs from response
            if hasattr(response, 'links'):
                return response.links
            elif hasattr(response, 'urls'):
                return response.urls
            elif isinstance(response, dict):
                return response.get('links', []) or response.get('urls', [])
            else:
                return self._extract_urls_from_response(response)
            
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return []
    
    def _extract_urls_from_response(self, response) -> List[str]:
        """
        Extract URLs from SDK response object.
        
        Args:
            response: SDK response object
            
        Returns:
            List of URLs extracted from response
        """
        # try different ways to extract URLs from the response
        if hasattr(response, '__dict__'):
            # check common attributes
            for attr in ['links', 'urls', 'pages', 'results']:
                if hasattr(response, attr):
                    value = getattr(response, attr)
                    if isinstance(value, list):
                        return value
                    elif isinstance(value, dict) and 'url' in value:
                        return [value['url']]
        
        # if response is a list, assume it contains URLs
        if isinstance(response, list):
            return response
        
        # if response is a dict, look for URL-like keys
        if isinstance(response, dict):
            for key in ['links', 'urls', 'pages', 'results']:
                if key in response:
                    value = response[key]
                    if isinstance(value, list):
                        return value
        
        # fallback - return empty list
        print(f"Could not extract URLs from response type: {type(response)}")
        return [] 
    