# ==============================================================================
# pagination_orchestrator.py — Intelligent Crawling Orchestration
# ==============================================================================
# Purpose: Orchestrate pagination detection, strategy selection, and content extraction
# ==============================================================================

import asyncio
import time
from typing import List, Dict, Optional, Callable, Any
from urllib.parse import urlparse

from app.models.pagination_models import (
    PaginationInfo, 
    PaginationStrategy, 
    PaginationType,
    ContentType,
    CrawlResult,
    PaginationSettings
)
from app.utils.pagination_detector import PaginationDetector, ContentTypeDetector
from app.utils.pagination_strategies import PaginationStrategyFactory
from app.utils.content_extractor import ContentExtractor

# ==============================================================================
# Main Orchestrator Class
# ==============================================================================

class PaginationOrchestrator:
    """Main orchestrator for intelligent pagination handling."""
    
    def __init__(self, settings: Optional[PaginationSettings] = None):
        self.settings = settings or PaginationSettings()
        self.detector = PaginationDetector()
        self.content_detector = ContentTypeDetector()
        self.content_extractor = ContentExtractor()
        self.strategy_factory = PaginationStrategyFactory()
        
        # Performance tracking
        self.total_pages_crawled = 0
        self.total_urls_found = 0
        self.start_time = None
    
    async def process_site_with_pagination(
        self, 
        initial_url: str, 
        crawl_function: Callable[[str], str],
        max_pages: Optional[int] = None
    ) -> CrawlResult:
        """
        Main method to process a site with pagination support.
        
        Args:
            initial_url: Starting URL to analyze
            crawl_function: Function to fetch page content (should return HTML string)
            max_pages: Maximum pages to crawl (overrides settings)
        
        Returns:
            CrawlResult with comprehensive crawling information
        """
        self.start_time = time.time()
        
        # Initialize crawl result
        crawl_result = CrawlResult(
            source_url=initial_url,
            urls_discovered=[],
            article_urls=[],
            listing_urls=[]
        )
        
        try:
            print(f"🚀 Starting pagination analysis for: {initial_url}")
            
            # Step 1: Initial page analysis
            print("🔍 Step 1: Analyzing initial page for pagination...")
            initial_content = await self._safe_crawl(initial_url, crawl_function)
            if not initial_content:
                crawl_result.errors.append(f"Failed to fetch initial page: {initial_url}")
                return crawl_result
            
            # Detect pagination on initial page
            pagination_info = self.detector.detect_pagination(initial_content, initial_url)
            crawl_result.pagination_info = pagination_info
            
            # Classify content type
            content_type = self.content_detector.detect_content_type(initial_content, initial_url)
            crawl_result.content_type = content_type
            
            print(f"📊 Pagination detected: {pagination_info.has_pagination}")
            print(f"📊 Pagination type: {pagination_info.pagination_type}")
            print(f"📊 Content type: {content_type}")
            print(f"📊 Confidence: {pagination_info.confidence_score:.2f}")
            
            # Step 2: Handle pagination if detected
            if pagination_info.has_pagination and self.settings.enabled:
                print("🔄 Step 2: Processing pagination...")
                await self._handle_paginated_content(
                    pagination_info, 
                    crawl_function, 
                    crawl_result,
                    max_pages or self.settings.max_pages
                )
            else:
                print("📄 Step 2: No pagination detected, processing single page...")
                await self._process_single_page(
                    initial_url, 
                    initial_content, 
                    crawl_result
                )
            
            # Step 3: Finalize results
            self._finalize_crawl_result(crawl_result)
            
            print(f"✅ Crawling complete!")
            print(f"📊 Total pages crawled: {crawl_result.total_pages_crawled}")
            print(f"📊 Total URLs found: {crawl_result.total_urls_found}")
            print(f"📊 Article URLs: {len(crawl_result.article_urls)}")
            print(f"📊 Time taken: {crawl_result.crawling_time_seconds:.2f}s")
            
            return crawl_result
            
        except Exception as e:
            error_msg = f"Error during pagination orchestration: {str(e)}"
            print(f"❌ {error_msg}")
            crawl_result.errors.append(error_msg)
            return crawl_result
    
    async def _handle_paginated_content(
        self, 
        pagination_info: PaginationInfo, 
        crawl_function: Callable[[str], str],
        crawl_result: CrawlResult,
        max_pages: int
    ):
        """Handle content with pagination."""
        
        # Create strategy for this pagination type
        strategy = self.strategy_factory.create_strategy_from_info(pagination_info)
        crawl_result.pagination_strategy = strategy
        
        print(f"🎯 Using {pagination_info.pagination_type} strategy")
        
        # Generate page URLs based on strategy
        if pagination_info.pagination_type == PaginationType.LINK_BASED:
            # Link-based requires discovery
            await self._handle_link_based_pagination(
                strategy, 
                crawl_function, 
                crawl_result, 
                max_pages
            )
        else:
            # Parameter/offset/indicator-based can generate URLs
            await self._handle_parameter_based_pagination(
                strategy, 
                crawl_function, 
                crawl_result, 
                max_pages
            )
    
    async def _handle_link_based_pagination(
        self, 
        strategy, 
        crawl_function: Callable[[str], str],
        crawl_result: CrawlResult,
        max_pages: int
    ):
        """Handle link-based pagination by following navigation."""
        
        print("🔗 Following navigation links to discover pages...")
        
        discovered_urls = await strategy.discover_all_pages(crawl_function, max_pages)
        print(f"🔗 Discovered {len(discovered_urls)} pages via navigation")
        
        # Process each discovered page
        await self._process_page_batch(
            discovered_urls, 
            crawl_function, 
            crawl_result,
            batch_size=1  # Process one at a time for link-based
        )
    
    async def _handle_parameter_based_pagination(
        self, 
        strategy, 
        crawl_function: Callable[[str], str],
        crawl_result: CrawlResult,
        max_pages: int
    ):
        """Handle parameter/offset/indicator-based pagination."""
        
        # Generate all page URLs
        strategy_result = strategy.generate_page_urls(max_pages)
        page_urls = strategy_result.page_urls
        
        print(f"📄 Generated {len(page_urls)} page URLs")
        
        # Process pages in batches for efficiency
        await self._process_page_batch(
            page_urls, 
            crawl_function, 
            crawl_result,
            batch_size=self.settings.concurrent_batches
        )
    
    async def _process_page_batch(
        self, 
        page_urls: List[str], 
        crawl_function: Callable[[str], str],
        crawl_result: CrawlResult,
        batch_size: int
    ):
        """Process pages in batches for efficiency."""
        
        total_pages = len(page_urls)
        processed_count = 0
        
        for i in range(0, total_pages, batch_size):
            batch = page_urls[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_pages + batch_size - 1) // batch_size
            
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} pages)")
            
            # Process batch concurrently
            batch_tasks = [
                self._process_single_page_async(url, crawl_function, crawl_result)
                for url in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle any errors from batch
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    error_msg = f"Error processing {batch[j]}: {str(result)}"
                    crawl_result.errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            processed_count += len(batch)
            print(f"📊 Progress: {processed_count}/{total_pages} pages processed")
            
            # Rate limiting between batches
            if i + batch_size < total_pages:
                await asyncio.sleep(self.settings.rate_limit_delay)
    
    async def _process_single_page_async(
        self, 
        url: str, 
        crawl_function: Callable[[str], str],
        crawl_result: CrawlResult
    ):
        """Process a single page asynchronously."""
        
        try:
            # Fetch page content
            content = await self._safe_crawl(url, crawl_function)
            if not content:
                return
            
            # Extract article URLs
            article_urls = self.content_extractor.extract_article_urls(content, url)
            
            # Update crawl result
            crawl_result.article_urls.extend(article_urls)
            crawl_result.urls_discovered.append(url)
            crawl_result.total_pages_crawled += 1
            crawl_result.total_urls_found += len(article_urls)
            
            print(f"📄 {url}: Found {len(article_urls)} article URLs")
            
        except Exception as e:
            print(f"❌ Error processing {url}: {str(e)}")
            raise
    
    async def _process_single_page(
        self, 
        url: str, 
        content: str, 
        crawl_result: CrawlResult
    ):
        """Process a single page (synchronous version)."""
        
        try:
            # Extract article URLs
            article_urls = self.content_extractor.extract_article_urls(content, url)
            
            # Update crawl result
            crawl_result.article_urls.extend(article_urls)
            crawl_result.urls_discovered.append(url)
            crawl_result.total_pages_crawled = 1
            crawl_result.total_urls_found = len(article_urls)
            
            print(f"📄 Single page: Found {len(article_urls)} article URLs")
            
        except Exception as e:
            error_msg = f"Error processing single page {url}: {str(e)}"
            crawl_result.errors.append(error_msg)
            print(f"❌ {error_msg}")
    
    async def _safe_crawl(self, url: str, crawl_function: Callable[[str], str]) -> Optional[str]:
        """Safely crawl a URL with retry logic."""
        
        for attempt in range(self.settings.max_retries):
            try:
                # Handle both sync and async crawl functions
                if asyncio.iscoroutinefunction(crawl_function):
                    content = await crawl_function(url)
                else:
                    content = crawl_function(url)
                
                if content:
                    return content
                    
            except Exception as e:
                print(f"⚠️  Crawl attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < self.settings.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"❌ All retry attempts failed for {url}")
        
        return None
    
    def _finalize_crawl_result(self, crawl_result: CrawlResult):
        """Finalize the crawl result with performance metrics."""
        
        # Calculate total time
        if self.start_time:
            crawl_result.crawling_time_seconds = time.time() - self.start_time
        
        # Update total counts
        crawl_result.total_pages_crawled = self.total_pages_crawled
        crawl_result.total_urls_found = self.total_urls_found
        
        # Remove duplicates from article URLs
        crawl_result.article_urls = list(set(crawl_result.article_urls))
        
        # Update total URLs found
        crawl_result.total_urls_found = len(crawl_result.article_urls)

# ==============================================================================
# Utility Functions
# ==============================================================================

async def create_pagination_orchestrator(
    max_pages: int = 1000,
    rate_limit_delay: float = 2.0,
    concurrent_batches: int = 10
) -> PaginationOrchestrator:
    """Create a configured pagination orchestrator."""
    
    settings = PaginationSettings(
        max_pages=max_pages,
        rate_limit_delay=rate_limit_delay,
        concurrent_batches=concurrent_batches
    )
    
    return PaginationOrchestrator(settings)

def estimate_crawl_time(
    total_pages: int, 
    rate_limit_delay: float = 2.0,
    concurrent_batches: int = 10
) -> float:
    """Estimate total crawl time based on configuration."""
    
    if total_pages <= 0:
        return 0.0
    
    # Calculate batches needed
    total_batches = (total_pages + concurrent_batches - 1) // concurrent_batches
    
    # Time per batch (including rate limiting)
    time_per_batch = (concurrent_batches * 0.5) + rate_limit_delay  # 0.5s per page + delay
    
    # Total estimated time
    total_time = total_batches * time_per_batch
    
    return total_time

def format_crawl_summary(crawl_result: CrawlResult) -> str:
    """Format a human-readable summary of crawl results."""
    
    summary = f"""
🚀 **Crawl Summary**
===================

📊 **Overview**
- Source URL: {crawl_result.source_url}
- Total pages crawled: {crawl_result.total_pages_crawled}
- Total URLs found: {crawl_result.total_urls_found}
- Time taken: {crawl_result.crawling_time_seconds:.2f}s

🔍 **Pagination Analysis**
- Pagination detected: {crawl_result.pagination_info.has_pagination if crawl_result.pagination_info else False}
- Pagination type: {crawl_result.pagination_info.pagination_type if crawl_result.pagination_info else 'N/A'}
- Confidence score: {crawl_result.pagination_info.confidence_score if crawl_result.pagination_info else 0.0:.2f}

📄 **Content Analysis**
- Content type: {crawl_result.content_type}
- Article URLs: {len(crawl_result.article_urls)}
- Listing URLs: {len(crawl_result.listing_urls)}

⚡ **Performance**
- URLs per second: {crawl_result.total_urls_found / max(crawl_result.crawling_time_seconds, 1):.2f}
- Pages per second: {crawl_result.total_pages_crawled / max(crawl_result.crawling_time_seconds, 1):.2f}

"""
    
    if crawl_result.errors:
        summary += f"❌ **Errors ({len(crawl_result.errors)})**\n"
        for error in crawl_result.errors[:5]:  # Show first 5 errors
            summary += f"- {error}\n"
        if len(crawl_result.errors) > 5:
            summary += f"- ... and {len(crawl_result.errors) - 5} more\n"
    
    if crawl_result.warnings:
        summary += f"⚠️  **Warnings ({len(crawl_result.warnings)})**\n"
        for warning in crawl_result.warnings[:3]:  # Show first 3 warnings
            summary += f"- {warning}\n"
        if len(crawl_result.warnings) > 3:
            summary += f"- ... and {len(crawl_result.warnings) - 3} more\n"
    
    return summary
