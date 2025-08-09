# ==============================================================================
# sitemap_crawler.py — Sitemap XML parsing utilities
# ==============================================================================
# Purpose: Handle sitemap XML parsing and URL extraction
# Sections: Imports, Public API, Main Classes
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
import asyncio
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime

# Third Party -----
import aiohttp

# Astral AI ----
from app.models.url_models import UrlInfo, DetectionMethod

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = ["SitemapCrawler"]

# ==============================================================================
# Main Classes
# ==============================================================================

class SitemapCrawler:
    """Thin client for sitemap XML parsing with comprehensive sitemap index support."""
    
    def __init__(self):
        self._client: Optional[aiohttp.ClientSession] = None
        self._timeout = 30
        self._max_concurrent_requests = 10
        
    async def __aenter__(self):
        """Async context manager for HTTP client lifecycle."""
        self._client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up HTTP client."""
        if self._client:
            await self._client.close()
    
    async def parse_sitemap(self, sitemap_url: str) -> List[UrlInfo]:
        """Parse a single sitemap and return URL info objects."""
        if not self._client:
            raise RuntimeError("Crawler must be used as async context manager")
            
        try:
            urls = await self._fetch_sitemap_urls(sitemap_url)
            return [self._create_url_info(url, DetectionMethod.SITEMAP) for url in urls]
            
        except Exception as e:
            raise Exception(f"Sitemap parsing failed for {sitemap_url}: {str(e)}")
    
    async def parse_sitemap_index(self, index_url: str) -> List[UrlInfo]:
        """Parse a sitemap index and return URL info objects from all referenced sitemaps."""
        if not self._client:
            raise RuntimeError("Crawler must be used as async context manager")
            
        try:
            urls = await self._fetch_sitemap_index_urls(index_url)
            return [self._create_url_info(url, DetectionMethod.SITEMAP) for url in urls]
            
        except Exception as e:
            raise Exception(f"Sitemap index parsing failed for {index_url}: {str(e)}")
    
    async def _fetch_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """Fetch and parse a single sitemap to extract URLs."""
        async with self._client.get(sitemap_url) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch sitemap: {response.status}")
            
            content = await response.text()
            
            # Check if this is a sitemap index
            if self._is_sitemap_index(content):
                return await self._fetch_sitemap_index_urls_from_content(content, sitemap_url)
            else:
                return self._parse_sitemap_content(content)
    
    async def _fetch_sitemap_index_urls(self, index_url: str) -> List[str]:
        """Fetch and parse a sitemap index to extract URLs from all referenced sitemaps."""
        async with self._client.get(index_url) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch sitemap index: {response.status}")
            
            content = await response.text()
            return await self._fetch_sitemap_index_urls_from_content(content, index_url)
    
    async def _fetch_sitemap_index_urls_from_content(self, index_content: str, index_url: str) -> List[str]:
        """Fetch URLs from a sitemap index file and all referenced sitemaps."""
        all_urls = []
        
        # Parse the sitemap index
        sitemap_urls = self._parse_sitemap_index_content(index_content)
        
        # Fetch each individual sitemap with concurrency control
        semaphore = asyncio.Semaphore(self._max_concurrent_requests)
        
        async def fetch_single_sitemap(sitemap_url: str) -> List[str]:
            async with semaphore:
                try:
                    return await self._fetch_individual_sitemap_urls(sitemap_url)
                except Exception as e:
                    print(f"Error fetching sitemap {sitemap_url}: {str(e)}")
                    return []
        
        # Create tasks for all sitemaps
        tasks = [fetch_single_sitemap(sitemap_url) for sitemap_url in sitemap_urls]
        
        # Wait for all sitemaps to be fetched
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all URLs
        for result in results:
            if isinstance(result, list):
                all_urls.extend(result)
        
        return list(set(all_urls))  # Remove duplicates
    
    async def _fetch_individual_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """Fetch and parse an individual sitemap."""
        try:
            async with self._client.get(sitemap_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch sitemap {sitemap_url}: {response.status}")
                
                content = await response.text()
                return self._parse_sitemap_content(content)
                
        except Exception as e:
            raise Exception(f"Error fetching sitemap {sitemap_url}: {e}")
    
    def _is_sitemap_index(self, content: str) -> bool:
        """Check if the XML content is a sitemap index."""
        try:
            root = ET.fromstring(content)
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            # Look for sitemap elements (indicating an index)
            sitemap_elements = root.findall('.//sitemap:sitemap', namespaces)
            if not sitemap_elements:
                sitemap_elements = root.findall('.//sitemap')
            
            return len(sitemap_elements) > 0
        except ET.ParseError:
            return False
    
    def _parse_sitemap_index_content(self, content: str) -> List[str]:
        """Parse sitemap index XML to extract sitemap URLs."""
        sitemap_urls = []
        
        try:
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            root = ET.fromstring(content)
            
            sitemap_elements = root.findall('.//sitemap:sitemap', namespaces)
            if not sitemap_elements:
                sitemap_elements = root.findall('.//sitemap')
            
            for sitemap_elem in sitemap_elements:
                loc_elem = sitemap_elem.find('sitemap:loc', namespaces)
                if loc_elem is None:
                    loc_elem = sitemap_elem.find('loc')
                
                if loc_elem is not None and loc_elem.text:
                    sitemap_urls.append(loc_elem.text.strip())
            
        except ET.ParseError as e:
            raise Exception(f"Failed to parse sitemap index XML: {e}")
        
        return sitemap_urls
    
    def _parse_sitemap_content(self, content: str) -> List[str]:
        """Parse sitemap XML content to extract URLs."""
        urls = []
        
        try:
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            root = ET.fromstring(content)
            
            url_elements = root.findall('.//sitemap:url', namespaces)
            if not url_elements:
                url_elements = root.findall('.//url')
            
            for url_elem in url_elements:
                loc_elem = url_elem.find('sitemap:loc', namespaces)
                if loc_elem is None:
                    loc_elem = url_elem.find('loc')
                
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text.strip())
            
        except ET.ParseError as e:
            raise Exception(f"Failed to parse sitemap XML: {e}")
        
        return urls
    
    def _create_url_info(self, url: str, detection_method: DetectionMethod) -> UrlInfo:
        """Create a UrlInfo object with the given URL and detection method."""
        return UrlInfo(
            url=url,
            detection_methods=[detection_method],
            detected_at=datetime.now()
        )
