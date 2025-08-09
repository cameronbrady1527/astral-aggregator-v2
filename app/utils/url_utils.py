# ==============================================================================
# url_utils.py — URL Processing Utilities
# ==============================================================================
# Purpose: URL resolution, deduplication, and validation utilities
# Sections: Imports, Public API, Helper Functions, Main Classes
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
import asyncio
from datetime import datetime
import time
from typing import List, Set, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
import re
from pathlib import Path

# Third Party -----
import httpx
from urllib3.util.retry import Retry

# Astral AI ----
from app.models.url_models import (
    UrlInfo, 
    DetectionMethod,
    UrlResolutionResult,
    UrlResolutionMapping,
    UrlDeduplicationResult,
    OutputURLsWithInfo,
    UrlProcessingResult,
    ProcessingSummary
)

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = [
    'UrlUtils',
    'resolve_urls',
    'find_duplicate_resolutions',
    'create_unique_url_set',
    'filter_resolved_duplicates',
    'normalize_url',
    'validate_url',
    'is_same_page',
    'merge_url_lists',
    'extract_domain',
    'is_valid_url',
    'remove_query_parameters',
    'create_url_info',
    'add_detection_method',
]

# ==============================================================================
# Public API Functions
# ==============================================================================

async def resolve_urls(urls: List[str], timeout: int = 10, max_redirects: int = 5) -> UrlResolutionMapping:
    """
    Resolve URLs and return structured mapping with metadata.
    
    Args:
        urls: List of URLs to resolve
        timeout: HTTP request timeout in seconds
        max_redirects: Maximum number of redirects to follow
        
    Returns:
        UrlResolutionMapping with structured results and metadata
    """
    start_time = time.time()
    async with UrlUtils(timeout=timeout, max_redirects=max_redirects) as url_utils:
        return await url_utils.resolve_urls(urls, start_time)

def find_duplicate_resolutions(url_mapping: Dict[str, str]) -> UrlDeduplicationResult:
    """
    Find URLs that resolve to the same page with structured result.
    
    Args:
        url_mapping: Dictionary mapping original URLs to resolved URLs
        
    Returns:
        UrlDeduplicationResult with structured analysis
    """
    start_time = time.time()
    
    resolved_to_originals: Dict[str, List[str]] = {}

    for original, resolved in url_mapping.items():
        if resolved in resolved_to_originals:
            resolved_to_originals[resolved].append(original)
        else:
            resolved_to_originals[resolved] = [original]

    # find URLs that resolve to the same page (keep first)
    duplicates = set()
    duplicate_groups = []
    for resolved, originals in resolved_to_originals.items():
        if len(originals) > 1:
            duplicates.update(originals[1:])
            duplicate_groups.append(originals)
    
    # create unique URLs list (remove duplicates)
    unique_urls = [url for url in url_mapping.keys() if url not in duplicates]
    
    processing_time = time.time() - start_time
    
    return UrlDeduplicationResult(
        original_urls=list(url_mapping.keys()),
        unique_urls=unique_urls,
        duplicates_removed=list(duplicates),
        duplicate_groups=duplicate_groups,
        total_original=len(url_mapping),
        total_unique=len(unique_urls),
        total_duplicates=len(duplicates),
        processing_time_seconds=processing_time
    )

def create_unique_url_set(url_lists: List[List[UrlInfo]]) -> UrlProcessingResult:
    """
    Create a set of unique URLs from multiple UrlInfo lists, preserving metadata.
    
    Args:
        url_lists: List of UrlInfo lists to merge
        
    Returns:
        UrlProcessingResult with unique URLs and preserved metadata
    """
    start_time = time.time()
    
    # Use the existing merge function which already handles UrlInfo properly
    merged_urls = merge_url_lists(url_lists)
    
    processing_time = time.time() - start_time
    
    return UrlProcessingResult(
        urls=merged_urls,
        total_count=len(merged_urls),
        processing_time_seconds=processing_time,
        operation_type="unique_set_creation",
        metadata={
            "input_lists_count": len(url_lists),
            "total_input_urls": sum(len(url_list) for url_list in url_lists)
        }
    )

def filter_resolved_duplicates(url_infos: List[UrlInfo], resolved_mapping: Dict[str, str]) -> UrlProcessingResult:
    """
    Filter out URLs that resolve to the same page, preserving UrlInfo metadata.
    
    Args:
        url_infos: List of UrlInfo objects to filter
        resolved_mapping: Dictionary mapping URLs to their resolved versions
        
    Returns:
        UrlProcessingResult with duplicates removed and metadata preserved
    """
    start_time = time.time()
    
    # Extract URLs for deduplication analysis
    urls = [url_info.url for url_info in url_infos]
    
    # Find duplicates
    dedup_result = find_duplicate_resolutions(resolved_mapping)
    
    # Create mapping from URL to UrlInfo for quick lookup
    url_to_info = {url_info.url: url_info for url_info in url_infos}
    
    # Filter out duplicates, preserving UrlInfo objects
    unique_url_infos = []
    for url in dedup_result.unique_urls:
        if url in url_to_info:
            unique_url_infos.append(url_to_info[url])
    
    processing_time = time.time() - start_time
    
    return UrlProcessingResult(
        urls=unique_url_infos,
        total_count=len(unique_url_infos),
        processing_time_seconds=processing_time,
        operation_type="duplicate_filtering",
        metadata={
            "original_count": len(url_infos),
            "duplicates_removed": len(dedup_result.duplicates_removed),
            "duplicate_groups": dedup_result.duplicate_groups
        }
    )

def normalize_url(url: str) -> str:
    """
    Normalize URL by removing trailing slashes, normalizing scheme, etc.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    if not url:
        return url

    # parse URL
    parsed = urlparse(url)
    # normalize scheme
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    # normalize domain (netloc)
    netloc = parsed.netloc.lower() if parsed.netloc else ""
    # remove trailing slash from path (aside from root)
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

    # normalize query parameters (sort)
    query_parts = parse_qs(parsed.query, keep_blank_values=True)
    if query_parts:
        sorted_query = sorted(query_parts.items())
        query = urlencode(sorted_query, doseq=True)

    else:
        query = ""

    # reconstruct URL
    normalized = urlunparse((scheme, netloc, path, parsed.params, query, ""))

    return normalized

def validate_url(url: str) -> bool:
    """
    Validate if URL is properly formatted and accessible.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    # for now, just check format - HTTP validation will be done in resolve_urls
    return is_valid_url(url)

def is_same_page(url1: str, url2: str) -> bool:
    """
    Check if two URLs point to the same page.
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        True if URLs point to the same page
    """
    if not url1 or not url2:
        return False

    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)

    # remove common tracking patterns that don't affect content
    tracking_params = ["utm_source", "utm_medium", "utm_utm_campaign", "utm_term", "utm_content", "ref", "source"]
    clean1 = remove_query_parameters(norm1, tracking_params)
    clean2 = remove_query_parameters(norm2, tracking_params)

    return clean1 == clean2

def merge_url_lists(url_lists: List[List[UrlInfo]]) -> List[UrlInfo]:
    """
    Merge multiple lists of UrlInfo objects, combining detection methods.
    
    Args:
        url_lists: List of UrlInfo lists to merge
        
    Returns:
        Merged list of UrlInfo objects with combined detection methods
    """
    url_dict: Dict[str, UrlInfo] = {}

    for url_list in url_lists:
        for url_info in url_list:
            url = url_info.url

            if url in url_dict:
                # URL already exists - merge detection methods
                existing_info = url_dict[url]

                # only update time if methods are identical
                if existing_info.detection_methods == url_info.detection_methods:
                    if url_info.detected_at > existing_info.detected_at:
                        url_dict[url] = UrlInfo(
                            url=url,
                            detection_methods=existing_info.detection_methods,
                            detected_at=url_info.detected_at
                        )
                else:
                    # methods not identical - full merge
                    combined_methods = list(
                        set(existing_info.detection_methods) | set(url_info.detection_methods)
                    )
                    latest_time = max(existing_info.detected_at, url_info.detected_at)

                    url_dict[url] = UrlInfo(
                        url=url,
                        detection_methods=combined_methods,
                        detected_at=latest_time
                    )
            else:
                # new URL - add to dictionary
                url_dict[url] = url_info

    return list(url_dict.values())

def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain string
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""

def is_valid_url(url: str) -> bool:
    """
    Check if URL has valid format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL format is valid
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False

def remove_query_parameters(url: str, params_to_remove: List[str] = None) -> str:
    """
    Remove specific query parameters from URL.
    
    Args:
        url: URL to process
        params_to_remove: List of parameter names to remove (None = remove all)
        
    Returns:
        URL with specified query parameters removed
    """
    if not url:
        return url
    
    try:
        parsed = urlparse(url)
        query_parts = parse_qs(parsed.query, keep_blank_values=True)
        
        if params_to_remove is None:
            # Remove all query parameters
            query = ''
        else:
            # Remove specific parameters
            for param in params_to_remove:
                query_parts.pop(param, None)
            
            if query_parts:
                query = urlencode(query_parts, doseq=True)
            else:
                query = ''
        
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))
    except Exception:
        return url

def create_url_info(url: str, detection_method: DetectionMethod) -> UrlInfo:
    """
    Create a UrlInfo object from a raw URL and detection method.
    
    Args:
        url: URL string
        detection_method: Method used to detect this URL
        
    Returns:
        UrlInfo object with metadata
    """
    return UrlInfo(
        url=url,
        detection_methods=[detection_method],
        detected_at=datetime.now()
    )

def add_detection_method(url_info: UrlInfo, method: DetectionMethod) -> UrlInfo:
    """
    Add detection method to UrlInfo if not already present.
    
    Args:
        url_info: UrlInfo object to update
        method: Detection method to add
        
    Returns:
        Updated UrlInfo object
    """
    if method not in url_info.detection_methods:
        updated_methods = url_info.detection_methods + [method]
        return UrlInfo(
            url=url_info.url,
            detection_methods=updated_methods,
            detected_at=url_info.detected_at
        )
    return url_info

# ==============================================================================
# Main Classes
# ==============================================================================

class UrlUtils:
    """
    Main utility class for URL processing operations.
    Provides methods for URL resolution, deduplication, and validation.
    """
    
    def __init__(self, timeout: int = 10, max_redirects: int = 5, max_concurrent: int = 10):
        """
        Initialize UrlUtils with configuration.
        
        Args:
            timeout: HTTP request timeout in seconds
            max_redirects: Maximum number of redirects to follow
            max_concurrent: Maximum concurrent HTTP requests
        """
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.max_concurrent = max_concurrent
        self._session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            max_redirects=self.max_redirects
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.aclose()
    
    async def resolve_urls(self, urls: List[str], start_time: float = None) -> UrlResolutionMapping:
        """
        Resolve URLs using the configured HTTP client.
        
        Args:
            urls: List of URLs to resolve
            start_time: Start time for processing (used for timing)
            
        Returns:
            UrlResolutionMapping with structured results
        """
        if not self._session:
            raise RuntimeError("UrlUtils must be used as async context manager")
        
        if start_time is None:
            start_time = time.time()

        # use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def resolve_with_semaphore(url: str) -> Tuple[str, UrlResolutionResult]:
            async with semaphore:
                return await self._resolve_single_url(url)

        # resolve all URLs concurrently
        tasks = [resolve_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # build result mapping, handling exceptions
        mappings = {}
        successful = 0
        failed = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # if resolution failed, create error result
                error_result = UrlResolutionResult(
                    original_url=urls[i],
                    resolved_url=urls[i],
                    resolution_success=False,
                    error_message=str(result)
                )
                mappings[urls[i]] = error_result
                failed += 1
            else:
                original, resolution_result = result
                mappings[original] = resolution_result
                if resolution_result.resolution_success:
                    successful += 1
                else:
                    failed += 1
        
        processing_time = time.time() - start_time
        
        return UrlResolutionMapping(
            mappings=mappings,
            total_urls=len(urls),
            successful_resolutions=successful,
            failed_resolutions=failed,
            processing_time_seconds=processing_time
        )
    
    async def _resolve_single_url(self, url: str) -> Tuple[str, UrlResolutionResult]:
        """
        Resolve a single URL.
        
        Args:
            url: URL to resolve
            
        Returns:
            Tuple of (original_url, UrlResolutionResult)
        """
        start_time = time.time()
        try:
            response = await self._session.head(url, allow_redirects=True)
            resolution_time = time.time() - start_time
            
            return url, UrlResolutionResult(
                original_url=url,
                resolved_url=str(response.url),
                resolution_success=True,
                resolution_time=resolution_time
            )
        except Exception as e:
            resolution_time = time.time() - start_time
            return url, UrlResolutionResult(
                original_url=url,
                resolved_url=url,
                resolution_success=False,
                error_message=str(e),
                resolution_time=resolution_time
            )
    
    def find_duplicates(self, url_mapping: Dict[str, str]) -> UrlDeduplicationResult:
        """
        Find duplicate resolutions in URL mapping.
        
        Args:
            url_mapping: Dictionary mapping original URLs to resolved URLs
            
        Returns:
            UrlDeduplicationResult with structured analysis
        """
        return find_duplicate_resolutions(url_mapping)
    
    def merge_url_infos(self, url_lists: List[List[UrlInfo]]) -> UrlProcessingResult:
        """
        Merge multiple lists of UrlInfo objects.
        
        Args:
            url_lists: List of UrlInfo lists to merge
            
        Returns:
            UrlProcessingResult with merged URLs and metadata
        """
        start_time = time.time()
        merged_urls = merge_url_lists(url_lists)
        processing_time = time.time() - start_time
        
        return UrlProcessingResult(
            urls=merged_urls,
            total_count=len(merged_urls),
            processing_time_seconds=processing_time,
            operation_type="url_merge",
            metadata={
                "input_lists_count": len(url_lists),
                "total_input_urls": sum(len(url_list) for url_list in url_lists)
            }
        )
    
    def filter_duplicates(self, url_infos: List[UrlInfo], resolved_mapping: Dict[str, str]) -> UrlProcessingResult:
        """
        Filter out URLs that resolve to duplicate pages.
        
        Args:
            url_infos: List of UrlInfo objects to filter
            resolved_mapping: Dictionary mapping URLs to resolved versions
            
        Returns:
            UrlProcessingResult with duplicates removed and metadata preserved
        """
        return filter_resolved_duplicates(url_infos, resolved_mapping)

# ==============================================================================
# Helper Functions
# ==============================================================================

def _get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent

def _create_retry_strategy() -> Retry:
    """Create retry strategy for HTTP requests."""
    return Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )

def _is_redirect_response(status_code: int) -> bool:
    """Check if HTTP status code indicates a redirect."""
    return status_code in (301, 302, 302, 307, 308)

def _should_follow_redirect(url: str, redirect_url: str) -> bool:
    """Determine if redirect should be followed based on URL patterns."""
    # ensure redirect stays on same domain or trusted domains
    try:
        original_domain = extract_domain(url)
        redirect_domain = extract_domain(redirect_url)

        # allow same domain redirects
        if original_domain == redirect_domain:
            return True

        # CONSIDER ADDING TRUSTED DOMAIN LIST CHECK HERE
        return False
    except Exception:
        return False
