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
from firecrawl import ScrapeOptions

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
            print(f"🔍 Mapping site: {url}")
            response = await self._app.map_url(
                url=url,
                limit=30000,
                include_subdomains=include_subdomains
            )
            
            print(f"🔍 Map response type: {type(response)}")
            print(f"🔍 Map response: {response}")
            
            # extract URLs from response
            if hasattr(response, 'links'):
                urls = response.links
                print(f"🔍 Found {len(urls)} URLs in response.links")
                return urls
            elif hasattr(response, 'urls'):
                urls = response.urls
                print(f"🔍 Found {len(urls)} URLs in response.urls")
                return urls
            elif isinstance(response, dict):
                urls = response.get('links', []) or response.get('urls', [])
                print(f"🔍 Found {len(urls)} URLs in response dict")
                return urls
            else:
                # fallback - try to extract URLs from response
                urls = self._extract_urls_from_response(response)
                print(f"🔍 Found {len(urls)} URLs using fallback extraction")
                return urls
            
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
                self.crawl_single_url(url, max_depth, limit)
                for url in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, list):
                    all_discovered_urls.extend(result)
        
        return list(set(all_discovered_urls))  # remove duplicates

    async def crawl_single_url(self, url: str, max_depth: int, limit: int) -> List[str]:
        """
        Raw SDK call to crawl a single URL.
        
        Args:
            url: URL to crawl
            max_depth: Maximum crawl depth
            limit: Limit for this URL
            
        Returns:
            List of discovered URLs
        """
        max_retries = 3
        base_delay = 10  # Base delay for rate limit errors
        
        for attempt in range(max_retries):
            try:
                # Use synchronous crawl_url which waits for completion and returns full response
                print(f"🔍 Starting crawl for {url}...")
                crawl_response = await self._app.crawl_url(
                    url=url,
                    max_depth=max_depth,
                    limit=limit,
                    allow_backward_links = True,
                    scrape_options = ScrapeOptions(
                        formats = [ 'links' ],
                        onlyMainContent = True,
                        parsePDF = False,
                        maxAge = 14400000
                    )
                )
                
                print(f"🔍 Crawl response type: {type(crawl_response)}")
                print(f"🔍 Crawl response: {crawl_response}")
                
                # According to docs, synchronous crawl_url should return completed results directly
                # Check if we have data with URLs
                if hasattr(crawl_response, 'data') and crawl_response.data:
                    print(f"🔍 Found data with {len(crawl_response.data)} items")
                    # Extract URLs from the crawled documents
                    urls = []
                    for i, doc in enumerate(crawl_response.data):
                        print(f"🔍 Processing document {i}: {doc}")
                        
                        # Extract URLs from the links field (this is what we actually want)
                        if hasattr(doc, 'links') and doc.links:
                            # Add all valid links from the document
                            for link in doc.links:
                                if isinstance(link, str) and link.strip() and link.startswith('http'):
                                    urls.append(link)
                                    print(f"🔍 Added link: {link}")
                        else:
                            print(f"🔍 Document has no links field: {type(doc)}")
                            if hasattr(doc, '__dict__'):
                                print(f"🔍 Document attributes: {dir(doc)}")
                    
                    print(f"🔍 Total URLs extracted: {len(urls)}")
                    return urls
                else:
                    print(f"🔍 No data found in crawl response")
                    return []
                    
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error
                if "429" in error_str or "rate limit" in error_str.lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        print(f"🔍 Rate limit hit for {url}, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        print(f"🔍 Rate limit error for {url} after {max_retries} attempts, skipping")
                        return []
                else:
                    # Non-rate-limit error, don't retry
                    print(f"Error crawling {url}: {str(e)}")
                    return []
        
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
    