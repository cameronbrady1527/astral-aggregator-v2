# ==============================================================================
# pagination_detector.py — Pagination Detection Engine
# ==============================================================================
# Purpose: Detect various pagination patterns on web pages
# ==============================================================================

import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup

from app.models.pagination_models import (
    PaginationInfo, 
    PaginationType, 
    ContentType,
    ContentIndicators,
    PaginationPattern
)

# ==============================================================================
# Pagination Pattern Definitions
# ==============================================================================

class PaginationPatterns:
    """Predefined pagination patterns for detection."""
    
    # URL parameter patterns
    PARAMETER_PATTERNS = {
        'page_based': [
            r'page=(\d+)',           # ?page=1, ?page=2
            r'p=(\d+)',              # ?p=1, ?p=2
            r'pg=(\d+)',             # ?pg=1, ?pg=2
            r'pageno=(\d+)',         # ?pageno=1, ?pageno=2
        ],
        'offset_based': [
            r'start=(\d+)',          # ?start=0, ?start=20
            r'offset=(\d+)',         # ?offset=0, ?offset=20
            r'from=(\d+)',           # ?from=0, ?from=20
            r'begin=(\d+)',          # ?begin=0, ?begin=20
        ],
        'limit_based': [
            r'limit=(\d+)',          # ?limit=20, ?limit=50
            r'per_page=(\d+)',       # ?per_page=20, ?per_page=50
            r'items_per_page=(\d+)', # ?items_per_page=20
        ]
    }
    
    # URL path patterns
    PATH_PATTERNS = [
        r'/page/(\d+)',              # /page/1, /page/2
        r'/p/(\d+)',                 # /p/1, /p/2
        r'/pg/(\d+)',                # /pg/1, /pg/2
        r'/page-(\d+)',              # /page-1, /page-2
        r'/p-(\d+)',                 # /p-1, /p-2
    ]
    
    # HTML content patterns
    CONTENT_PATTERNS = {
        'page_indicators': [
            r'page\s+(\d+)\s+of\s+(\d+)',           # "page 1 of 50"
            r'(\d+)\s+of\s+(\d+)',                   # "1 of 50"
            r'showing\s+(\d+)-(\d+)\s+of\s+(\d+)',  # "showing 1-20 of 1000"
            r'(\d+)\s*-\s*(\d+)\s+of\s+(\d+)',      # "1-20 of 1000"
            r'page\s+(\d+)\s*/\s*(\d+)',            # "page 1 / 50"
        ],
        'result_counts': [
            r'(\d+)\s+results?',                     # "1000 results"
            r'(\d+)\s+items?',                       # "1000 items"
            r'(\d+)\s+articles?',                    # "1000 articles"
            r'(\d+)\s+posts?',                       # "1000 posts"
        ],
        'gov_uk_specific': [
            r'Next page\s*:\s*(\d+)\s+of\s+(\d+)',  # "Next page : 2 of 6,801"
            r'(\d+)\s+results sorted by',            # "136,019 results sorted by"
            r'(\d+)\s+results',                      # "136,019 results"
        ]
    }
    
    # Navigation link patterns
    NAVIGATION_PATTERNS = [
        r'<a[^>]*href=[^>]*>.*?next.*?</a>',
        r'<a[^>]*href=[^>]*>.*?previous.*?</a>',
        r'<a[^>]*href=[^>]*>.*?older.*?</a>',
        r'<a[^>]*href=[^>]*>.*?newer.*?</a>',
        r'<a[^>]*href=[^>]*>.*?earlier.*?</a>',
        r'<a[^>]*href=[^>]*>.*?later.*?</a>',
        r'<a[^>]*href=[^>]*>.*?first.*?</a>',
        r'<a[^>]*href=[^>]*>.*?last.*?</a>',
    ]

# ==============================================================================
# Main Detection Engine
# ==============================================================================

class PaginationDetector:
    """Main engine for detecting pagination patterns."""
    
    def __init__(self):
        self.patterns = PaginationPatterns()
    
    def detect_pagination(self, page_content: str, url: str) -> PaginationInfo:
        """Main method to detect pagination on a page."""
        
        # Initialize pagination info
        pagination_info = PaginationInfo(
            source_url=url,
            base_url=self._extract_base_url(url)
        )
        
        # Step 1: Detect URL-based pagination
        url_patterns = self._detect_url_patterns(url)
        if url_patterns:
            pagination_info.pagination_patterns.extend(url_patterns)
            pagination_info.has_pagination = True
        
        # Step 2: Detect content-based pagination (MUST come before navigation links)
        content_patterns = self._detect_content_patterns(page_content)
        if content_patterns:
            pagination_info.pagination_patterns.extend(content_patterns)
            pagination_info.has_pagination = True
        
        # Step 3: Extract pagination numbers (MUST come before classification)
        self._extract_pagination_numbers(pagination_info, page_content, url)
        
        # Step 4: Classify pagination type (MUST come before navigation links)
        pagination_info.pagination_type = self._classify_pagination_type(pagination_info)
        
        # Step 5: Detect navigation links (MUST come after classification)
        nav_info = self._detect_navigation_links(page_content, url)
        if nav_info:
            pagination_info.has_next_prev_links = True
            pagination_info.next_url = nav_info.get('next_url')
            pagination_info.previous_url = nav_info.get('previous_url')
            pagination_info.has_pagination = True
        
        # Step 6: Calculate confidence score
        pagination_info.confidence_score = self._calculate_confidence(pagination_info)
        
        return pagination_info
    
    def _detect_url_patterns(self, url: str) -> List[str]:
        """Detect pagination patterns in the URL."""
        detected_patterns = []
        
        # Check parameter-based patterns
        for pattern_type, patterns in self.patterns.PARAMETER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    detected_patterns.append(f"URL_PARAM_{pattern_type}: {pattern}")
        
        # Check path-based patterns
        for pattern in self.patterns.PATH_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                detected_patterns.append(f"URL_PATH: {pattern}")
        
        return detected_patterns
    
    def _detect_content_patterns(self, page_content: str) -> List[str]:
        """Detect pagination patterns in the page content."""
        detected_patterns = []
        
        # Check page indicators
        for pattern in self.patterns.CONTENT_PATTERNS['page_indicators']:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                detected_patterns.append(f"CONTENT_PAGE_INDICATOR: {pattern} (found {len(matches)} matches)")
        
        # Check result counts
        for pattern in self.patterns.CONTENT_PATTERNS['result_counts']:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                detected_patterns.append(f"CONTENT_RESULT_COUNT: {pattern} (found {len(matches)} matches)")
        
        # Check GOV.UK specific patterns
        for pattern in self.patterns.CONTENT_PATTERNS['gov_uk_specific']:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                detected_patterns.append(f"CONTENT_GOV_UK: {pattern} (found {len(matches)} matches)")
        
        return detected_patterns
    
    def _detect_navigation_links(self, page_content: str, base_url: str) -> Optional[Dict[str, str]]:
        """Detect next/previous navigation links."""
        soup = BeautifulSoup(page_content, 'html.parser')
        nav_info = {}
        
        # Look for next/previous links
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
            next_link = soup.select_one(selector)
            if next_link and next_link.get('href'):
                nav_info['next_url'] = self._resolve_relative_url(next_link['href'], base_url)
                break
        
        # Find previous link
        for selector in prev_selectors:
            prev_link = soup.select_one(selector)
            if prev_link and prev_link.get('href'):
                nav_info['previous_url'] = self._resolve_relative_url(prev_link['href'], base_url)
                break
        
        # Fallback: Look for GOV.UK specific pagination format
        if not nav_info.get('next_url'):
            gov_uk_next = self._detect_gov_uk_pagination(page_content, base_url)
            if gov_uk_next:
                nav_info['next_url'] = gov_uk_next
        
        return nav_info if nav_info else None
    
    def _detect_gov_uk_pagination(self, page_content: str, base_url: str) -> Optional[str]:
        """Detect GOV.UK specific pagination format."""
        # Look for "Next page : X of Y" pattern
        next_page_pattern = r'Next page\s*:\s*(\d+)\s+of\s+(\d+)'
        match = re.search(next_page_pattern, page_content, re.IGNORECASE)
        
        if match:
            try:
                current_page = int(match.group(1))
                total_pages = int(match.group(2))
                
                # GOV.UK uses ?page=X format for pagination
                if current_page < total_pages:
                    # Construct next page URL
                    parsed_url = urlparse(base_url)
                    query_params = parse_qs(parsed_url.query)
                    
                    # Add or update page parameter
                    query_params['page'] = [str(current_page + 1)]
                    
                    # Rebuild URL
                    new_query = urlencode(query_params, doseq=True)
                    next_url = urlunparse((
                        parsed_url.scheme, 
                        parsed_url.netloc, 
                        parsed_url.path, 
                        parsed_url.params, 
                        new_query, 
                        parsed_url.fragment
                    ))
                    
                    return next_url
                    
            except (ValueError, IndexError):
                pass
        
        return None
    
    def _classify_pagination_type(self, pagination_info: PaginationInfo) -> PaginationType:
        """Classify the type of pagination detected."""
        
        # Check for content indicators with total pages (ABSOLUTE HIGHEST priority)
        # This MUST come first to ensure GOV.UK is classified as INDICATOR_BASED
        content_patterns = [p for p in pagination_info.pagination_patterns if 'CONTENT' in p]
        if content_patterns and pagination_info.total_pages:
            # If we have content patterns AND total pages, this is indicator-based
            # GOV.UK shows "136,019 results" which is a clear content indicator
            print(f"🔍 Classification: Content indicators with {pagination_info.total_pages} total pages detected - using INDICATOR_BASED strategy")
            return PaginationType.INDICATOR_BASED
        
        # Check for parameter-based patterns (second priority)
        param_patterns = [p for p in pagination_info.pagination_patterns if 'URL_PARAM' in p]
        if param_patterns:
            if any('offset_based' in p for p in param_patterns):
                return PaginationType.OFFSET_BASED
            else:
                return PaginationType.PARAMETER_BASED
        
        # Check for navigation links (lowest priority)
        if pagination_info.has_next_prev_links:
            print(f"🔍 Classification: Navigation links detected - using LINK_BASED strategy")
            return PaginationType.LINK_BASED
        
        # Check for content indicators without total pages (lowest priority)
        if content_patterns:
            return PaginationType.INDICATOR_BASED
        
        return PaginationType.NONE
    
    def _extract_pagination_numbers(self, pagination_info: PaginationInfo, page_content: str, url: str):
        """Extract current page, total pages, and item counts."""
        
        # Extract from URL parameters
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Check for page number
        for param in ['page', 'p', 'pg', 'pageno']:
            if param in query_params:
                try:
                    pagination_info.current_page = int(query_params[param][0])
                    break
                except (ValueError, IndexError):
                    pass
        
        # Check for offset
        for param in ['start', 'offset', 'from', 'begin']:
            if param in query_params:
                try:
                    offset = int(query_params[param][0])
                    pagination_info.current_page = (offset // 20) + 1  # Assume 20 per page
                    break
                except (ValueError, IndexError):
                    pass
        
        # Extract from content
        self._extract_numbers_from_content(pagination_info, page_content)
    
    def _extract_numbers_from_content(self, pagination_info: PaginationInfo, page_content: str):
        """Extract pagination numbers from page content."""
        
        # Look for "page X of Y" patterns
        page_pattern = r'page\s+(\d+)\s+of\s+(\d+)'
        page_match = re.search(page_pattern, page_content, re.IGNORECASE)
        if page_match:
            try:
                pagination_info.current_page = int(page_match.group(1))
                pagination_info.total_pages = int(page_match.group(2))
            except ValueError:
                pass
        
        # Look for "showing X-Y of Z" patterns
        showing_pattern = r'showing\s+(\d+)-(\d+)\s+of\s+(\d+)'
        showing_match = re.search(showing_pattern, page_content, re.IGNORECASE)
        if showing_match:
            try:
                start = int(showing_match.group(1))
                end = int(showing_match.group(2))
                total = int(showing_match.group(3))
                
                pagination_info.current_items = end - start + 1
                pagination_info.total_items = total
                pagination_info.items_per_page = end - start + 1
                
                # Calculate current page if not already set
                if pagination_info.current_page is None:
                    pagination_info.current_page = (start // pagination_info.items_per_page) + 1
                
                # Calculate total pages if not already set
                if pagination_info.total_pages is None:
                    pagination_info.total_pages = (total + pagination_info.items_per_page - 1) // pagination_info.items_per_page
                    
            except ValueError:
                pass
        
        # Look for GOV.UK specific patterns
        gov_uk_page_pattern = r'Next page\s*:\s*(\d+)\s+of\s+(\d+)'
        gov_uk_page_match = re.search(gov_uk_page_pattern, page_content, re.IGNORECASE)
        if gov_uk_page_match:
            try:
                pagination_info.current_page = int(gov_uk_page_match.group(1))
                pagination_info.total_pages = int(gov_uk_page_match.group(2))
            except ValueError:
                pass
        
        # Also look for the more general "X of Y" pattern that GOV.UK uses
        general_page_pattern = r'(\d+)\s+of\s+(\d+)'
        general_page_match = re.search(general_page_pattern, page_content, re.IGNORECASE)
        if general_page_match and pagination_info.total_pages is None:
            try:
                current_page = int(general_page_match.group(1))
                total_pages = int(general_page_match.group(2))
                # Only set if it looks like a reasonable pagination (current < total and total > 1)
                if 1 <= current_page < total_pages and total_pages > 1:
                    pagination_info.current_page = current_page
                    pagination_info.total_pages = total_pages
            except ValueError:
                pass
        
        # Look for GOV.UK result count patterns
        gov_uk_results_pattern = r'(\d{1,3}(?:,\d{3})*)\s+results'
        gov_uk_results_match = re.search(gov_uk_results_pattern, page_content, re.IGNORECASE)
        if gov_uk_results_match:
            try:
                # Remove commas and convert to int
                total_results = int(gov_uk_results_match.group(1).replace(',', ''))
                pagination_info.total_items = total_results
                print(f"🔍 GOV.UK: Found {total_results} total results")
                
                # Set default items per page for GOV.UK (they typically show 20 results per page)
                if pagination_info.items_per_page is None:
                    pagination_info.items_per_page = 20
                
                # ALWAYS calculate total pages from total results when we have both
                # This overrides any navigation-based total pages that might be incorrect
                if pagination_info.items_per_page:
                    calculated_total_pages = (total_results + pagination_info.items_per_page - 1) // pagination_info.items_per_page
                    pagination_info.total_pages = calculated_total_pages
                    print(f"🔍 GOV.UK: Calculated {calculated_total_pages} total pages from {total_results} results ÷ {pagination_info.items_per_page} per page")
                    print(f"🔍 GOV.UK: This overrides any navigation-based total pages")
                    
            except ValueError as e:
                print(f"⚠️ GOV.UK: Error parsing results: {e}")
                pass
    
    def _calculate_confidence(self, pagination_info: PaginationInfo) -> float:
        """Calculate confidence score for pagination detection."""
        confidence = 0.0
        
        # Base confidence for having pagination
        if pagination_info.has_pagination:
            confidence += 0.3
        
        # URL pattern confidence
        if pagination_info.pagination_patterns:
            confidence += 0.2
        
        # Navigation links confidence
        if pagination_info.has_next_prev_links:
            confidence += 0.2
        
        # Number extraction confidence
        if pagination_info.current_page is not None:
            confidence += 0.1
        if pagination_info.total_pages is not None:
            confidence += 0.1
        if pagination_info.total_items is not None:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_base_url(self, url: str) -> str:
        """Extract base URL without pagination parameters."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Remove pagination parameters
        pagination_params = ['page', 'p', 'pg', 'pageno', 'start', 'offset', 'from', 'begin', 'limit', 'per_page']
        for param in pagination_params:
            query_params.pop(param, None)
        
        # Rebuild URL without pagination parameters
        new_query = urlencode(query_params, doseq=True) if query_params else ''
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    
    def _resolve_relative_url(self, href: str, base_url: str) -> str:
        """Resolve relative URLs to absolute URLs."""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            parsed_base = urlparse(base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
        else:
            return f"{base_url.rstrip('/')}/{href.lstrip('/')}"

# ==============================================================================
# Content Type Detection
# ==============================================================================

class ContentTypeDetector:
    """Detect the type of content on a page."""
    
    def detect_content_type(self, page_content: str, url: str) -> ContentType:
        """Detect the type of content on the page."""
        
        indicators = self._analyze_content_indicators(page_content, url)
        
        # Determine content type based on indicators
        if indicators.has_search_box and indicators.has_result_count:
            return ContentType.SEARCH_RESULTS
        elif indicators.has_item_list and indicators.has_pagination_controls:
            return ContentType.LISTING
        elif indicators.has_title and indicators.has_content_body:
            return ContentType.ARTICLE
        elif indicators.has_pagination_controls:
            return ContentType.PAGINATION
        else:
            return ContentType.UNKNOWN
    
    def _analyze_content_indicators(self, page_content: str, url: str) -> ContentIndicators:
        """Analyze page content for content type indicators."""
        soup = BeautifulSoup(page_content, 'html.parser')
        
        indicators = ContentIndicators()
        
        # Check for article indicators
        indicators.has_title = bool(soup.find(['h1', 'h2']) and soup.find(['p', 'div'], class_=re.compile(r'content|body|article')))
        indicators.has_author = bool(soup.find(text=re.compile(r'by|author|written by', re.IGNORECASE)))
        indicators.has_publish_date = bool(soup.find(text=re.compile(r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', re.IGNORECASE)))
        indicators.has_content_body = bool(soup.find(['article', 'main', 'div'], class_=re.compile(r'content|body|article|post')))
        
        # Check for listing indicators
        indicators.has_item_list = bool(soup.find(['ul', 'ol', 'div'], class_=re.compile(r'list|items|results')))
        indicators.has_pagination_controls = bool(soup.find(text=re.compile(r'next|previous|page|pagination', re.IGNORECASE)))
        indicators.has_search_filters = bool(soup.find(['select', 'input'], class_=re.compile(r'filter|sort|category')))
        
        # Check for search indicators
        indicators.has_search_box = bool(soup.find('input', {'type': 'search'}) or soup.find('input', {'placeholder': re.compile(r'search', re.IGNORECASE)}))
        indicators.has_result_count = bool(soup.find(text=re.compile(r'\d+\s+results?|\d+\s+items?', re.IGNORECASE)))
        indicators.has_sort_options = bool(soup.find('select', {'name': re.compile(r'sort|order', re.IGNORECASE)}))
        
        return indicators
