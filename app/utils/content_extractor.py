# ==============================================================================
# content_extractor.py — Content Extraction Pipeline
# ==============================================================================
# Purpose: Extract article URLs and content from paginated pages
# ==============================================================================

import re
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

from app.models.pagination_models import ContentType, ContentIndicators

# ==============================================================================
# Article URL Pattern Definitions
# ==============================================================================

class ArticlePatterns:
    """Patterns for identifying article URLs."""
    
    # Common article URL patterns
    URL_PATTERNS = [
        # News and articles
        r'/(?:news|articles|blog|posts|stories?)/[^/]+',
        r'/(?:news|articles|blog|posts|stories?)/\d{4}/\d{2}/[^/]+',
        r'/(?:news|articles|blog|posts|stories?)/\d{4}/[^/]+',
        
        # Date-based patterns
        r'/\d{4}/\d{2}/\d{2}/[^/]+',
        r'/\d{4}/\d{2}/[^/]+',
        r'/\d{4}/[^/]+',
        
        # Generic content patterns
        r'/[a-z-]+/[^/]+(?:-[^/]+)*',
        r'/[a-z-]+/\d+/[^/]+',
        
        # Government-specific patterns (for gov.uk)
        r'/government/news/[^/]+',
        r'/government/publications/[^/]+',
        r'/government/announcements/[^/]+',
        r'/government/speeches/[^/]+',
        r'/government/statements/[^/]+',
    ]
    
    # HTML content patterns for article identification
    CONTENT_PATTERNS = {
        'article_containers': [
            'article',
            '[class*="article"]',
            '[class*="post"]',
            '[class*="news"]',
            '[class*="content"]',
            '[class*="item"]',
        ],
        'article_links': [
            'a[href*="/news/"]',
            'a[href*="/articles/"]',
            'a[href*="/blog/"]',
            'a[href*="/posts/"]',
            'a[href*="/stories/"]',
            'a[href*="/government/"]',
        ],
        'article_titles': [
            'h1',
            'h2',
            'h3',
            '[class*="title"]',
            '[class*="headline"]',
        ]
    }

# ==============================================================================
# Main Content Extractor
# ==============================================================================

class ContentExtractor:
    """Main class for extracting content from web pages."""
    
    def __init__(self):
        self.patterns = ArticlePatterns()
    
    def extract_article_urls(self, page_content: str, base_url: str) -> List[str]:
        """Extract article URLs from a page."""
        soup = BeautifulSoup(page_content, 'html.parser')
        article_urls = set()
        
        # Method 1: Extract from article containers
        container_urls = self._extract_from_containers(soup, base_url)
        article_urls.update(container_urls)
        
        # Method 2: Extract from article links
        link_urls = self._extract_from_links(soup, base_url)
        article_urls.update(link_urls)
        
        # Method 3: Extract from article titles
        title_urls = self._extract_from_titles(soup, base_url)
        article_urls.update(title_urls)
        
        # Method 4: Pattern-based extraction
        pattern_urls = self._extract_by_patterns(page_content, base_url)
        article_urls.update(pattern_urls)
        
        # Filter and validate URLs
        valid_urls = self._filter_valid_urls(list(article_urls), base_url)
        
        return valid_urls
    
    def _extract_from_containers(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Extract URLs from article containers."""
        urls = set()
        
        for selector in self.patterns.CONTENT_PATTERNS['article_containers']:
            containers = soup.select(selector)
            for container in containers:
                # Look for links within containers
                links = container.find_all('a', href=True)
                for link in links:
                    url = self._process_link(link, base_url)
                    if url and self._is_likely_article_url(url):
                        urls.add(url)
        
        return urls
    
    def _extract_from_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Extract URLs from article-specific links."""
        urls = set()
        
        for selector in self.patterns.CONTENT_PATTERNS['article_links']:
            links = soup.select(selector)
            for link in links:
                url = self._process_link(link, base_url)
                if url and self._is_likely_article_url(url):
                    urls.add(url)
        
        return urls
    
    def _extract_from_titles(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Extract URLs from article titles."""
        urls = set()
        
        for selector in self.patterns.CONTENT_PATTERNS['article_titles']:
            titles = soup.select(selector)
            for title in titles:
                # Look for parent links
                parent_link = title.find_parent('a', href=True)
                if parent_link:
                    url = self._process_link(parent_link, base_url)
                    if url and self._is_likely_article_url(url):
                        urls.add(url)
                
                # Look for sibling links
                sibling_link = title.find_next_sibling('a', href=True)
                if sibling_link:
                    url = self._process_link(sibling_link, base_url)
                    if url and self._is_likely_article_url(url):
                        urls.add(url)
        
        return urls
    
    def _extract_by_patterns(self, page_content: str, base_url: str) -> Set[str]:
        """Extract URLs using regex patterns."""
        urls = set()
        
        for pattern in self.patterns.URL_PATTERNS:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                # Construct full URL
                full_url = urljoin(base_url, match)
                if self._is_likely_article_url(full_url):
                    urls.add(full_url)
        
        return urls
    
    def _process_link(self, link: Tag, base_url: str) -> Optional[str]:
        """Process a link tag and return the URL."""
        href = link.get('href')
        if not href:
            return None
        
        # Skip empty or fragment-only links
        if not href or href.startswith('#'):
            return None
        
        # Resolve relative URLs
        if href.startswith('http'):
            url = href
        else:
            url = urljoin(base_url, href)
        
        return url
    
    def _is_likely_article_url(self, url: str) -> bool:
        """Determine if a URL is likely to be an article."""
        
        # Skip if no URL
        if not url:
            return False
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        
        # Skip external domains (for now)
        base_domain = urlparse(url).netloc
        if not base_domain:
            return False
        
        # Check for article indicators in path
        path = parsed.path.lower()
        
        # Positive indicators
        positive_patterns = [
            r'/news/',
            r'/articles/',
            r'/blog/',
            r'/posts/',
            r'/stories/',
            r'/government/news/',
            r'/government/publications/',
            r'/government/announcements/',
            r'/government/speeches/',
            r'/government/statements/',
        ]
        
        for pattern in positive_patterns:
            if re.search(pattern, path):
                return True
        
        # Negative indicators (skip these)
        negative_patterns = [
            r'/search',
            r'/admin',
            r'/login',
            r'/register',
            r'/contact',
            r'/about',
            r'/privacy',
            r'/terms',
            r'/sitemap',
            r'/rss',
            r'/feed',
            r'/api',
        ]
        
        for pattern in negative_patterns:
            if re.search(pattern, path):
                return False
        
        # Check for date patterns (good indicator of articles)
        date_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',
            r'/\d{4}/\d{2}/',
            r'/\d{4}/',
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, path):
                return True
        
        # Check for meaningful path length (articles usually have longer paths)
        path_segments = [seg for seg in path.split('/') if seg]
        if len(path_segments) >= 3:
            return True
        
        return False
    
    def _filter_valid_urls(self, urls: List[str], base_url: str) -> List[str]:
        """Filter and validate extracted URLs."""
        valid_urls = []
        base_domain = urlparse(base_url).netloc
        
        for url in urls:
            try:
                parsed = urlparse(url)
                
                # Must have valid scheme and domain
                if not parsed.scheme or not parsed.netloc:
                    continue
                
                # Must be same domain (for now)
                if parsed.netloc != base_domain:
                    continue
                
                # Must have meaningful path
                if not parsed.path or parsed.path == '/':
                    continue
                
                # Skip common non-article paths
                if self._is_common_non_article_path(parsed.path):
                    continue
                
                valid_urls.append(url)
                
            except Exception:
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in valid_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    def _is_common_non_article_path(self, path: str) -> bool:
        """Check if path is a common non-article path."""
        path_lower = path.lower()
        
        non_article_paths = [
            '/',
            '/search',
            '/admin',
            '/login',
            '/register',
            '/contact',
            '/about',
            '/privacy',
            '/terms',
            '/sitemap',
            '/rss',
            '/feed',
            '/api',
            '/help',
            '/support',
            '/faq',
            '/feedback',
            '/accessibility',
            '/cookies',
        ]
        
        return path_lower in non_article_paths

# ==============================================================================
# Content Type Classifier
# ==============================================================================

class ContentClassifier:
    """Classify the type of content on a page."""
    
    def classify_content(self, page_content: str, url: str) -> ContentType:
        """Classify the content type of a page."""
        
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

# ==============================================================================
# Utility Functions
# ==============================================================================

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""

def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    domain1 = extract_domain(url1)
    domain2 = extract_domain(url2)
    return domain1 == domain2

def normalize_url_for_comparison(url: str) -> str:
    """Normalize URL for comparison purposes."""
    try:
        parsed = urlparse(url)
        # Remove fragments and normalize scheme
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.lower()
    except Exception:
        return url.lower()
