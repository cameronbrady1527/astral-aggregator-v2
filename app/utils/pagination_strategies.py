# ==============================================================================
# pagination_strategies.py — Pagination Strategy Implementations
# ==============================================================================
# Purpose: Implement strategies for handling different pagination types
# ==============================================================================

import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin

from bs4 import BeautifulSoup

from app.models.pagination_models import (
    PaginationType, 
    PaginationStrategy,
    PaginationInfo
)

# ==============================================================================
# Base Strategy Class
# ==============================================================================

class BasePaginationStrategy:
    """Base class for pagination strategies."""
    
    def __init__(self, base_url: str, pagination_info: PaginationInfo):
        self.base_url = base_url
        self.pagination_info = pagination_info
        self.parameters = {}
    
    def generate_page_urls(self, max_pages: int = 1000) -> List[str]:
        """Generate all page URLs for this pagination strategy."""
        raise NotImplementedError("Subclasses must implement generate_page_urls")
    
    def estimate_total_pages(self) -> int:
        """Estimate the total number of pages."""
        raise NotImplementedError("Subclasses must implement estimate_total_pages")
    
    def validate_page_url(self, url: str) -> bool:
        """Validate if a generated page URL is valid."""
        return True

# ==============================================================================
# Parameter-Based Strategy
# ==============================================================================

class ParameterBasedStrategy(BasePaginationStrategy):
    """Handle ?page=1, ?page=2 style pagination."""
    
    def __init__(self, base_url: str, pagination_info: PaginationInfo):
        super().__init__(base_url, pagination_info)
        self.parameter_name = self._detect_parameter_name()
    
    def _detect_parameter_name(self) -> str:
        """Detect the parameter name used for pagination."""
        # Check URL for existing pagination parameters
        parsed_url = urlparse(self.base_url)
        query_params = parse_qs(parsed_url.query)
        
        # Look for common pagination parameter names
        pagination_params = ['page', 'p', 'pg', 'pageno']
        for param in pagination_params:
            if param in query_params:
                return param
        
        # Default to 'page' if none found
        return 'page'
    
    def generate_page_urls(self, max_pages: int = 1000) -> List[str]:
        """Generate page URLs using parameter-based pagination."""
        start_time = time.time()
        
        # Estimate total pages
        total_pages = self.estimate_total_pages()
        if total_pages > max_pages:
            total_pages = max_pages
        
        page_urls = []
        
        for page in range(1, total_pages + 1):
            if page == 1:
                # First page is the base URL
                page_urls.append(self.base_url)
            else:
                # Add page parameter
                page_url = self._add_page_parameter(self.base_url, page)
                page_urls.append(page_url)
        
        # Update strategy parameters
        self.parameters = {
            'parameter_name': self.parameter_name,
            'total_pages': total_pages,
            'max_pages': max_pages
        }
        
        generation_time = time.time() - start_time
        
        return PaginationStrategy(
            strategy_type=PaginationType.PARAMETER_BASED,
            base_url=self.base_url,
            parameters=self.parameters,
            page_urls=page_urls,
            total_pages_generated=len(page_urls),
            generation_time_seconds=generation_time
        )
    
    def _add_page_parameter(self, url: str, page: int) -> str:
        """Add page parameter to URL."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Add page parameter
        query_params[self.parameter_name] = [str(page)]
        
        # Rebuild URL
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    
    def estimate_total_pages(self) -> int:
        """Estimate total pages based on pagination info."""
        if self.pagination_info.total_pages:
            return self.pagination_info.total_pages
        
        # If we have total items and items per page, calculate
        if self.pagination_info.total_items and self.pagination_info.items_per_page:
            return (self.pagination_info.total_items + self.pagination_info.items_per_page - 1) // self.pagination_info.items_per_page
        
        # Default estimate based on confidence
        if self.pagination_info.confidence_score > 0.7:
            return 100  # High confidence - estimate 100 pages
        elif self.pagination_info.confidence_score > 0.4:
            return 50   # Medium confidence - estimate 50 pages
        else:
            return 20   # Low confidence - estimate 20 pages

# ==============================================================================
# Offset-Based Strategy
# ==============================================================================

class OffsetBasedStrategy(BasePaginationStrategy):
    """Handle ?start=0, ?start=20 style pagination."""
    
    def __init__(self, base_url: str, pagination_info: PaginationInfo):
        super().__init__(base_url, pagination_info)
        self.offset_param = self._detect_offset_parameter()
        self.items_per_page = self._detect_items_per_page()
    
    def _detect_offset_parameter(self) -> str:
        """Detect the offset parameter name."""
        parsed_url = urlparse(self.base_url)
        query_params = parse_qs(parsed_url.query)
        
        offset_params = ['start', 'offset', 'from', 'begin']
        for param in offset_params:
            if param in query_params:
                return param
        
        return 'start'
    
    def _detect_items_per_page(self) -> int:
        """Detect items per page from pagination info or URL."""
        if self.pagination_info.items_per_page:
            return self.pagination_info.items_per_page
        
        # Check URL for limit parameters
        parsed_url = urlparse(self.base_url)
        query_params = parse_qs(parsed_url.query)
        
        limit_params = ['limit', 'per_page', 'items_per_page']
        for param in limit_params:
            if param in query_params:
                try:
                    return int(query_params[param][0])
                except (ValueError, IndexError):
                    pass
        
        # Default to 20 items per page
        return 20
    
    def generate_page_urls(self, max_pages: int = 1000) -> List[str]:
        """Generate page URLs using offset-based pagination."""
        start_time = time.time()
        
        # Calculate total pages
        total_items = self.pagination_info.total_items or (max_pages * self.items_per_page)
        total_pages = min((total_items + self.items_per_page - 1) // self.items_per_page, max_pages)
        
        page_urls = []
        
        for page in range(total_pages):
            offset = page * self.items_per_page
            
            if page == 0:
                # First page is the base URL
                page_urls.append(self.base_url)
            else:
                # Add offset parameter
                page_url = self._add_offset_parameter(self.base_url, offset)
                page_urls.append(page_url)
        
        # Update strategy parameters
        self.parameters = {
            'offset_param': self.offset_param,
            'items_per_page': self.items_per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'max_pages': max_pages
        }
        
        generation_time = time.time() - start_time
        
        return PaginationStrategy(
            strategy_type=PaginationType.OFFSET_BASED,
            base_url=self.base_url,
            parameters=self.parameters,
            page_urls=page_urls,
            total_pages_generated=len(page_urls),
            generation_time_seconds=generation_time
        )
    
    def _add_offset_parameter(self, url: str, offset: int) -> str:
        """Add offset parameter to URL."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Add offset parameter
        query_params[self.offset_param] = [str(offset)]
        
        # Rebuild URL
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    
    def estimate_total_pages(self) -> int:
        """Estimate total pages based on pagination info."""
        if self.pagination_info.total_pages:
            return self.pagination_info.total_pages
        
        if self.pagination_info.total_items and self.items_per_page:
            return (self.pagination_info.total_items + self.items_per_page - 1) // self.items_per_page
        
        # Default estimate
        return 50

# ==============================================================================
# Link-Based Strategy
# ==============================================================================

class LinkBasedStrategy(BasePaginationStrategy):
    """Follow next/previous links to discover all pages."""
    
    def __init__(self, base_url: str, pagination_info: PaginationInfo):
        super().__init__(base_url, pagination_info)
        self.discovered_urls = set()
        self.max_discovery_pages = 1000  # Prevent infinite loops
    
    def generate_page_urls(self, max_pages: int = 1000) -> List[str]:
        """Generate page URLs by following navigation links."""
        start_time = time.time()
        
        # This strategy requires actual crawling to discover pages
        # For now, return the base URL and indicate that discovery is needed
        page_urls = [self.base_url]
        
        # Update strategy parameters
        self.parameters = {
            'requires_crawling': True,
            'max_discovery_pages': min(max_pages, self.max_discovery_pages),
            'has_next_prev_links': self.pagination_info.has_next_prev_links
        }
        
        generation_time = time.time() - start_time
        
        return PaginationStrategy(
            strategy_type=PaginationType.LINK_BASED,
            base_url=self.base_url,
            parameters=self.parameters,
            page_urls=page_urls,
            total_pages_generated=len(page_urls),
            generation_time_seconds=generation_time
        )
    
    async def discover_all_pages(self, crawl_function, max_pages: int = 1000) -> List[str]:
        """Discover all pages by following navigation links."""
        discovered_urls = {self.base_url}
        to_visit = [self.base_url]
        visited_count = 0
        
        while to_visit and visited_count < max_pages:
            current_url = to_visit.pop(0)
            if current_url in discovered_urls:
                continue
            
            try:
                # Crawl the page
                page_content = await crawl_function(current_url)
                discovered_urls.add(current_url)
                visited_count += 1
                
                # Extract next/previous links
                next_links = self._extract_navigation_links(page_content, current_url)
                for link in next_links:
                    if link not in discovered_urls and len(discovered_urls) < max_pages:
                        to_visit.append(link)
                        discovered_urls.add(link)
                
            except Exception as e:
                print(f"Error crawling {current_url}: {e}")
                continue
        
        return list(discovered_urls)
    
    def _extract_navigation_links(self, page_content: str, current_url: str) -> List[str]:
        """Extract navigation links from page content."""
        soup = BeautifulSoup(page_content, 'html.parser')
        navigation_links = []
        
        # Look for next/previous links with various selectors
        next_selectors = [
            'a[href*="next"]',
            'a:contains("Next")',
            'a:contains("next")',
            'a[aria-label*="next"]',
            'a[title*="next"]',
            'a[rel="next"]',
            'a.next',
            'a.next-page',
            'a[class*="next"]'
        ]
        
        prev_selectors = [
            'a[href*="previous"]',
            'a:contains("Previous")',
            'a:contains("previous")',
            'a[aria-label*="previous"]',
            'a[title*="previous"]',
            'a[rel="prev"]',
            'a.previous',
            'a.prev-page',
            'a[class*="prev"]'
        ]
        
        # Find next link
        for selector in next_selectors:
            try:
                next_link = soup.select_one(selector)
                if next_link and next_link.get('href'):
                    href = next_link['href']
                    if href.startswith('http'):
                        navigation_links.append(href)
                    else:
                        # Resolve relative URL
                        navigation_links.append(urljoin(current_url, href))
                    break
            except Exception:
                continue
        
        # Find previous link
        for selector in prev_selectors:
            try:
                prev_link = soup.select_one(selector)
                if prev_link and prev_link.get('href'):
                    href = prev_link['href']
                    if href.startswith('http'):
                        navigation_links.append(href)
                    else:
                        # Resolve relative URL
                        navigation_links.append(urljoin(current_url, href))
                    break
            except Exception:
                continue
        
        # Also look for numbered page links (e.g., page 2, page 3)
        page_links = soup.find_all('a', href=True)
        for link in page_links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            
            # Check if this looks like a page number link
            if any(keyword in text for keyword in ['page', 'p.', 'p ']) and any(char.isdigit() for char in text):
                if href.startswith('http'):
                    navigation_links.append(href)
                else:
                    navigation_links.append(urljoin(current_url, href))
        
        return navigation_links
    
    def estimate_total_pages(self) -> int:
        """Cannot estimate without crawling."""
        return 0

# ==============================================================================
# Indicator-Based Strategy
# ==============================================================================

class IndicatorBasedStrategy(BasePaginationStrategy):
    """Handle pagination based on content indicators like "Page 1 of 50"."""
    
    def __init__(self, base_url: str, pagination_info: PaginationInfo):
        super().__init__(base_url, pagination_info)
    
    def generate_page_urls(self, max_pages: int = 1000) -> List[str]:
        """Generate page URLs based on content indicators."""
        start_time = time.time()
        
        # Use the total pages from pagination info
        total_pages = min(self.pagination_info.total_pages or 50, max_pages)
        
        print(f"🔍 IndicatorBasedStrategy: Generating {total_pages} page URLs")
        
        # Generate all page URLs with ?page=X parameter
        page_urls = []
        
        for page in range(1, total_pages + 1):
            if page == 1:
                # First page is the base URL
                page_urls.append(self.base_url)
            else:
                # Add page parameter for all subsequent pages
                page_url = self._add_page_parameter(self.base_url, page)
                page_urls.append(page_url)
        
        print(f"🔍 IndicatorBasedStrategy: Generated {len(page_urls)} URLs (page 1 to {total_pages})")
        
        # Update strategy parameters
        self.parameters = {
            'total_pages': total_pages,
            'pagination_method': 'content_indicator',
            'requires_url_generation': True
        }
        
        generation_time = time.time() - start_time
        
        return PaginationStrategy(
            strategy_type=PaginationType.INDICATOR_BASED,
            base_url=self.base_url,
            parameters=self.parameters,
            page_urls=page_urls,
            total_pages_generated=len(page_urls),
            generation_time_seconds=generation_time
        )
    
    def _add_page_parameter(self, url: str, page: int) -> str:
        """Add page parameter to URL."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Add page parameter
        query_params['page'] = [str(page)]
        
        # Rebuild URL
        new_query = urlencode(query_params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    
    def _has_url_parameters(self) -> bool:
        """Check if the base URL has pagination parameters."""
        parsed = urlparse(self.base_url)
        query_params = parse_qs(parsed.query)
        
        pagination_params = ['page', 'p', 'pg', 'start', 'offset', 'from']
        return any(param in query_params for param in pagination_params)
    
    def estimate_total_pages(self) -> int:
        """Estimate based on pagination info."""
        return self.pagination_info.total_pages or 50

# ==============================================================================
# Strategy Factory
# ==============================================================================

class PaginationStrategyFactory:
    """Factory for creating pagination strategies."""
    
    @staticmethod
    def create_strategy(pagination_type: PaginationType, base_url: str, pagination_info: PaginationInfo) -> BasePaginationStrategy:
        """Create a pagination strategy based on type."""
        
        strategies = {
            PaginationType.PARAMETER_BASED: ParameterBasedStrategy,
            PaginationType.OFFSET_BASED: OffsetBasedStrategy,
            PaginationType.LINK_BASED: LinkBasedStrategy,
            PaginationType.INDICATOR_BASED: IndicatorBasedStrategy,
        }
        
        strategy_class = strategies.get(pagination_type)
        if strategy_class:
            return strategy_class(base_url, pagination_info)
        else:
            # Default to parameter-based strategy
            return ParameterBasedStrategy(base_url, pagination_info)
    
    @staticmethod
    def create_strategy_from_info(pagination_info: PaginationInfo) -> BasePaginationStrategy:
        """Create strategy directly from pagination info."""
        return PaginationStrategyFactory.create_strategy(
            pagination_info.pagination_type,
            pagination_info.base_url,
            pagination_info
        )
