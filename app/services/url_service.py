# ==============================================================================
# url_service.py — URL processing orchestration
# ==============================================================================
# Purpose: Orchestrate URL discovery, processing, and AI analysis
# Sections: Imports, Public API, Main Classes
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Astral AI ----
from app.models.url_models import (
    UrlInfo, 
    DetectionMethod, 
    UrlProcessingResult, 
    UrlSet,
    ProcessingSummary,
    OutputURLsWithInfo,
    UrlAnalysisRequest,
    UrlJudgeRequest,
    UrlDeduplicationResult
)
from app.models.config_models import SiteConfig
from app.models.pagination_models import PaginationSettings, CrawlResult
from app.clients.firecrawl_client import FirecrawlClient
from app.clients.openai_client import OpenAIClient
from app.crawler.sitemap_crawler import SitemapCrawler
from app.services.config_service import config_service
from app.utils.url_utils import (
    create_url_info, 
    merge_url_lists, 
    resolve_urls, 
)
from app.utils.json_writer import JsonWriter
from app.utils.pagination_orchestrator import PaginationOrchestrator
from app.utils.simple_crawler import AsyncHTTPCrawler
from app.ai.config import AIConfig

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = ["UrlService", "OnboardingUrlService"]

# ==============================================================================
# Main Classes
# ==============================================================================

class UrlService:
    """Main orchestration service for URL processing."""
    
    def __init__(self):
        self.json_writer = JsonWriter()
    
    async def process_site(self, site_id: str) -> Dict[str, Any]:
        """Main orchestration method for processing a single site."""
        start_time = datetime.now()
        
        # Get site configuration using existing config_service
        site_config = config_service.site(site_id)
        if not site_config:
            raise ValueError(f"Site {site_id} not found in configuration")
        
        # Step 1: Get URLs from multiple sources concurrently
        discovery_result = await self._get_urls_from_multiple_sources(site_config)
        
        # Step 2: Check if site needs onboarding
        is_onboarded = config_service.is_site_onboarded(site_id)
        
        if not is_onboarded:
            # Step 3a: Run onboarding process
            onboarding_service = OnboardingUrlService()
            top_urls = await onboarding_service.onboard_site(site_id, discovery_result.urls, site_config.name)
            
            # Step 3b: Get additional URLs from top URLs
            additional_urls = await self._get_additional_urls_from_top_urls(top_urls)
            print(f"🔍 Merging {len(discovery_result.urls)} existing URLs with {len(additional_urls)} additional URLs...")
            all_url_infos = discovery_result.urls + additional_urls
        else:
            # Step 3: Get additional URLs from existing top URLs
            top_urls = site_config.top_urls or []
            additional_urls = await self._get_additional_urls_from_top_urls(top_urls)
            print(f"🔍 Merging {len(discovery_result.urls)} existing URLs with {len(additional_urls)} additional URLs...")
            all_url_infos = discovery_result.urls + additional_urls
        
        # Step 4: Reporting on final URL set size
        print(f"🔍 Final URL set contains {len(all_url_infos)} total URLs")
        if not site_config.is_sitemap:
            print(f"🔍 Note: Site {site_config.name} has no sitemap - URLs discovered via Firecrawl map and top URL crawling only")
        
        # Step 5: Safety check - ensure all items are UrlInfo objects
        all_url_infos = [url for url in all_url_infos if isinstance(url, UrlInfo)]
        print(f"🔍 After safety check: {len(all_url_infos)} valid UrlInfo objects")
        
        # Step 6: Show breakdown by detection method
        method_counts = {}
        for url_info in all_url_infos:
            if hasattr(url_info, 'detection_methods'):
                for method in url_info.detection_methods:
                    method_counts[method.value] = method_counts.get(method.value, 0) + 1
            else:
                print(f"🔍 Warning: url_info {url_info} does not have detection_methods attribute")
                print(f"🔍 Warning: url_info type: {type(url_info)}")
                print(f"🔍 Warning: url_info dir: {dir(url_info)}")
        
        print("🔍 URL breakdown by detection method:")
        for method, count in method_counts.items():
            print(f"  - {method}: {count} URLs")
        
        # Step 7: Create URL set with proper structure
        url_set = UrlSet(
            site_id=site_id,
            timestamp=datetime.now(),
            urls=all_url_infos,
            total_count=len(all_url_infos)
        )
        
        # Step 8: Save results using JsonWriter
        output_path = await self._save_url_set(url_set)
        
        # Step 9: Create processing summary
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Step 10: Collect all detection methods safely
        detection_methods_used = []
        for url_info in all_url_infos:
            if hasattr(url_info, 'detection_methods'):
                for method in url_info.detection_methods:
                    detection_methods_used.append(method.value)
        
        # Step 11: Build processing summary
        summary = ProcessingSummary(
            status="completed",
            urls_found=len(all_url_infos),
            urls_processed=len(all_url_infos),
            processing_time_seconds=processing_time,
            detection_methods_used=list(set(detection_methods_used))
        )
        
        # Step 12: Save the final processing summary with correct timing
        self.json_writer.write_processing_summary(site_id, summary)
        
        return {
            "site_id": site_id,
            "site_name": site_config.name,
            "url_set": url_set.model_dump(),
            "processing_summary": summary.model_dump(),
            "discovery_result": discovery_result.model_dump(),
            "output_path": str(output_path),
            "onboarded": is_onboarded,
            "processing_time": datetime.now().isoformat()
        }
    
    async def process_site_with_pagination(self, site_id: str) -> Dict[str, Any]:
        """
        Enhanced site processing with pagination support.
        
        This method extends the standard process_site method with intelligent
        pagination detection and crawling for sites that have paginated content.
        """
        start_time = datetime.now()
        
        # Get site configuration
        site_config = config_service.site(site_id)
        if not site_config:
            raise ValueError(f"Site {site_id} not found in configuration")
        
        print(f"🚀 Starting enhanced processing with pagination for site: {site_config.name}")
        
        # Check if pagination is enabled for this site
        if not getattr(site_config, 'pagination_enabled', True):
            print(f"📄 Pagination disabled for {site_config.name}, using standard processing")
            return await self.process_site(site_id)
        
        # Step 1: Get URLs from multiple sources (including pagination)
        discovery_result = await self._get_urls_from_multiple_sources_with_pagination(site_config)
        
        # Step 2: Check if site needs onboarding
        is_onboarded = config_service.is_site_onboarded(site_id)
        
        if not is_onboarded:
            # Step 3a: Run onboarding process with pagination awareness
            onboarding_service = OnboardingUrlService()
            top_urls = await onboarding_service.onboard_site_with_pagination(site_id, discovery_result.urls, site_config)
            
            # Step 3b: Get additional URLs from top URLs (with pagination)
            additional_urls = await self._get_additional_urls_from_top_urls_with_pagination(top_urls, site_config)
            print(f"🔍 Merging {len(discovery_result.urls)} existing URLs with {len(additional_urls)} additional URLs...")
            all_url_infos = discovery_result.urls + additional_urls
        else:
            # Step 3: Get additional URLs from existing top URLs (with pagination)
            top_urls = site_config.top_urls or []
            additional_urls = await self._get_additional_urls_from_top_urls_with_pagination(top_urls, site_config)
            print(f"🔍 Merging {len(discovery_result.urls)} existing URLs with {len(additional_urls)} additional URLs...")
            all_url_infos = discovery_result.urls + additional_urls
        
        # Step 4: Reporting on final URL set size
        print(f"🔍 Final URL set contains {len(all_url_infos)} total URLs")
        if hasattr(discovery_result, 'pagination_info') and discovery_result.pagination_info:
            print(f"📄 Pagination detected: {discovery_result.pagination_info.pagination_type}")
            total_pages = discovery_result.pagination_info.total_pages
            print(f"📄 Total pages crawled: {total_pages if total_pages is not None else 'Unknown'}")
        
        # Step 5: Safety check - ensure all items are UrlInfo objects
        all_url_infos = [url for url in all_url_infos if isinstance(url, UrlInfo)]
        print(f"🔍 After safety check: {len(all_url_infos)} valid UrlInfo objects")
        
        # Step 6: Show breakdown by detection method
        method_counts = {}
        for url_info in all_url_infos:
            if hasattr(url_info, 'detection_methods'):
                for method in url_info.detection_methods:
                    method_counts[method.value] = method_counts.get(method.value, 0) + 1
            else:
                print(f"🔍 Warning: url_info {url_info} does not have detection_methods attribute")
        
        print("🔍 URL breakdown by detection method:")
        for method, count in method_counts.items():
            print(f"  - {method}: {count} URLs")
        
        # Step 7: Create URL set with proper structure
        url_set = UrlSet(
            site_id=site_id,
            timestamp=datetime.now(),
            urls=all_url_infos,
            total_count=len(all_url_infos)
        )
        
        # Step 8: Save results using JsonWriter
        output_path = await self._save_url_set(url_set)
        
        # Step 9: Create processing summary
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Step 10: Collect all detection methods safely
        detection_methods_used = []
        for url_info in all_url_infos:
            if hasattr(url_info, 'detection_methods'):
                for method in url_info.detection_methods:
                    detection_methods_used.append(method.value)
        
        # Step 11: Build processing summary
        summary = ProcessingSummary(
            status="completed",
            urls_found=len(all_url_infos),
            urls_processed=len(all_url_infos),
            processing_time_seconds=processing_time,
            detection_methods_used=list(set(detection_methods_used))
        )
        
        # Step 12: Save the final processing summary with correct timing
        self.json_writer.write_processing_summary(site_id, summary)
        
        return {
            "site_id": site_id,
            "site_name": site_config.name,
            "url_set": url_set.model_dump(),
            "processing_summary": summary.model_dump(),
            "discovery_result": discovery_result.model_dump(),
            "output_path": str(output_path),
            "onboarded": is_onboarded,
            "processing_time": datetime.now().isoformat(),
            "pagination_enabled": True,
            "pagination_info": discovery_result.pagination_info.model_dump() if hasattr(discovery_result, 'pagination_info') and discovery_result.pagination_info else None
        }
    
    async def _get_urls_from_multiple_sources(self, site_config: SiteConfig) -> UrlProcessingResult:
        """Orchestrates concurrent URL discovery from sitemap and Firecrawl."""
        start_time = datetime.now()
        
        # Step 1.1: Create tasks for concurrent execution based on site configuration
        tasks = []
        task_descriptions = []
        
        # Always include Firecrawl map
        tasks.append(self._get_urls_from_firecrawl_map(site_config))
        task_descriptions.append("firecrawl_map")
        
        # Only include sitemap if the site has one
        if site_config.is_sitemap:
            tasks.append(self._get_urls_from_sitemap(site_config))
            task_descriptions.append("sitemap")
            input_sources = 2
            print(f"🔍 Site {site_config.name} has sitemap - including sitemap processing")
        else:
            input_sources = 1
            print(f"🔍 Site {site_config.name} has no sitemap - skipping sitemap processing, using only Firecrawl map")
        
        # Step 1.2: Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Step 1.3: Handle exceptions and merge results
        url_lists = []
        successful_sources = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error getting URLs from {task_descriptions[i]}: {str(result)}")
                url_lists.append([])
            else:
                url_lists.append(result)
                successful_sources += 1
        
        # Step 1.4: Merge all URL lists using the proper merging function
        merged_urls = merge_url_lists(url_lists)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Step 1.5: Build and return UrlProcessingResult response object
        metadata = {
            "input_sources": input_sources,
            "successful_sources": successful_sources,
            "failed_sources": input_sources - successful_sources,
            "firecrawl_map_urls": len(url_lists[0]) if len(url_lists) > 0 else 0,
        }
        
        if site_config.is_sitemap:
            metadata["sitemap_urls"] = len(url_lists[1]) if len(url_lists) > 1 else 0
        
        return UrlProcessingResult(
            urls=merged_urls,
            total_count=len(merged_urls),
            processing_time_seconds=processing_time,
            operation_type="url_discovery",
            metadata=metadata
        )
    
    async def _get_urls_from_sitemap(self, site_config: SiteConfig) -> List[UrlInfo]:
        """Calls sitemap crawler client to get URLs."""
        async with SitemapCrawler() as crawler:
            if site_config.is_sitemap_index:
                return await crawler.parse_sitemap_index(site_config.sitemap_url)
            else:
                return await crawler.parse_sitemap(site_config.sitemap_url)
    
    async def _get_urls_from_firecrawl_map(self, site_config: SiteConfig) -> List[UrlInfo]:
        """Calls Firecrawl client to get URLs via SDK map endpoint."""
        async with FirecrawlClient() as client:
            urls = await client.map_site(site_config.url, include_subdomains=True)
            return [create_url_info(url, DetectionMethod.FIRECRAWL_MAP) for url in urls]
    
    async def _get_additional_urls_from_top_urls(self, top_urls: List[str]) -> List[UrlInfo]:
        """Gets additional URLs by crawling the top URLs with Firecrawl SDK."""
        if not top_urls:
            return []
        
        print(f"🔍 Starting to crawl {len(top_urls)} top URLs for additional URL discovery...")
        all_discovered_urls = []
        
        # Step 3.1: Import rate limiter
        from app.utils.rate_limiter import create_rate_limiter_from_config, process_with_rate_limiting
        
        # Step 3.2: Create adaptive rate limiter
        rate_limiter = create_rate_limiter_from_config(config_service)
        
        async with FirecrawlClient() as client:
            # Step 3.3: Define the processor function for each URL
            async def process_single_url(url: str):
                try:
                    print(f"🔍 Crawling URL: {url}")
                    
                    # Step 3.4.1a: Crawl single URL with Firecrawl
                    discovered_urls = await client.crawl_single_url(url, max_depth=3, limit=5)  # Increased from 2,2 for better discovery
                    
                    if discovered_urls:
                        # Step 3.4.1b: Filter out any None or invalid URLs before creating UrlInfo objects
                        valid_urls = [url for url in discovered_urls if url and isinstance(url, str) and url.strip()]
                        if valid_urls:
                            # Step 3.4.1c: Convert to UrlInfo objects
                            url_infos = [create_url_info(valid_url, DetectionMethod.FIRECRAWL_CRAWL) for valid_url in valid_urls]
                            print(f"🔍 Discovered {len(valid_urls)} valid URLs from {url}")
                            return url_infos
                        else:
                            print(f"🔍 No valid URLs discovered from {url}")
                            return []
                    else:
                        print(f"🔍 No new URLs discovered from {url}")
                        return []
                        
                except Exception as e:
                    print(f"Error crawling {url}: {str(e)}")
                    # Check if it's a rate limit error
                    is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()
                    rate_limiter.record_event(success=False, is_rate_limit=is_rate_limit)
                    raise e
            
            # Step 3.4: Process URLs with adaptive rate limiting
            batch_size = config_service.firecrawl_batch_size
            max_retries = config_service.firecrawl_max_retries
            print(f"🔍 Processing {len(top_urls)} URLs with batch size {batch_size} and retry logic (max {max_retries} retries)")
            
            results = await process_with_rate_limiting(
                top_urls, 
                process_single_url, 
                rate_limiter, 
                batch_size,
                max_retries
            )
            
            # Step 3.5: Collect all discovered URLs (results array is now guaranteed to match input length)
            print(f"🔍 Processing {len(results)} results from rate-limited processing")
            for i, result in enumerate(results):
                if result and isinstance(result, list):
                    print(f"🔍 Result {i}: Extending with list of {len(result)} items")
                    all_discovered_urls.extend(result)
                elif result is not None:
                    # Single result case
                    print(f"🔍 Result {i}: Single result of type {type(result)}")
                    if isinstance(result, UrlInfo):
                        all_discovered_urls.append(result)
                    elif isinstance(result, dict) and "error" in result:
                        print(f"⚠️  Result {i} had error: {result['error']}")
                        # For error results, try to create a minimal UrlInfo if possible
                        if "original_item" in result and hasattr(result["original_item"], "url"):
                            try:
                                fallback_url_info = create_url_info(result["original_item"], DetectionMethod.FIRECRAWL_CRAWL)
                                all_discovered_urls.append(fallback_url_info)
                                print(f"🔍 Created fallback UrlInfo for failed result {i}")
                            except Exception as fallback_error:
                                print(f"⚠️  Could not create fallback for result {i}: {fallback_error}")
                        # Skip error results but log them
                    else:
                        print(f"🔍 Result {i}: Unexpected result type: {type(result)}")
                        # Try to handle unexpected result types gracefully
                        if hasattr(result, 'url'):
                            try:
                                fallback_url_info = create_url_info(result.url, DetectionMethod.FIRECRAWL_CRAWL)
                                all_discovered_urls.append(fallback_url_info)
                                print(f"🔍 Created fallback UrlInfo for unexpected result {i}")
                            except Exception as fallback_error:
                                print(f"⚠️  Could not create fallback for unexpected result {i}: {fallback_error}")
                else:
                    print(f"⚠️  Result {i}: Still None after retries - this should not happen!")
                    # Emergency fallback for any remaining None results
                    try:
                        emergency_fallback = create_url_info(top_urls[i], DetectionMethod.FIRECRAWL_CRAWL)
                        all_discovered_urls.append(emergency_fallback)
                        print(f"🔍 Created emergency fallback for None result {i}")
                    except Exception as emergency_error:
                        print(f"⚠️  Emergency fallback failed for result {i}: {emergency_error}")
            
            # Step 3.6: Safety check - ensure all items are UrlInfo objects
            all_discovered_urls = [url for url in all_discovered_urls if isinstance(url, UrlInfo)]
            print(f"🔍 After safety check: {len(all_discovered_urls)} valid UrlInfo objects")
            
            # Step 3.8: Print rate limiter stats
            stats = rate_limiter.get_stats()
            print(f"🔍 Rate limiter stats: {stats}")
        
        # Step 3.9: Remove duplicates and return unique URLs
        if all_discovered_urls:
            print(f"🔍 Total discovered URLs before deduplication: {len(all_discovered_urls)}")
            
            # Deduplicate URLs using merge_url_lists
            # Since merge_url_lists expects a list of lists, we wrap our single list
            deduplicated_urls = merge_url_lists([all_discovered_urls])
            
            print(f"🔍 Total unique discovered URLs after deduplication: {len(deduplicated_urls)}")
            return deduplicated_urls
        
        print("🔍 No additional URLs discovered from top URLs")
        return []
    
    async def _get_additional_urls_from_top_urls_with_pagination(self, top_urls: List[str], site_config: SiteConfig) -> List[UrlInfo]:
        """
        Enhanced method to get additional URLs from top URLs with pagination support.
        
        This method extends the standard crawling with intelligent pagination
        detection for individual top URLs that might have paginated content.
        """
        if not top_urls:
            return []
        
        print(f"🔍 Crawling {len(top_urls)} top URLs for additional content (with pagination support)...")
        
        additional_urls = []
        
        for i, top_url in enumerate(top_urls, 1):
            try:
                print(f"🔍 Processing top URL {i}/{len(top_urls)}: {top_url}")
                
                # Check if this URL has pagination opportunities
                pagination_result = await self._check_and_process_pagination(site_config, [create_url_info(top_url, DetectionMethod.TOP_URL_CRAWLING)])
                
                if pagination_result and hasattr(pagination_result, 'article_urls') and pagination_result.article_urls:
                    # Convert article URLs to UrlInfo objects
                    for article_url in pagination_result.article_urls:
                        url_info = UrlInfo(
                            url=article_url,
                            detection_methods=[DetectionMethod.TOP_URL_CRAWLING],
                            detected_at=datetime.now(),
                            source_url=top_url
                        )
                        additional_urls.append(url_info)
                    
                    print(f"✅ Found {len(pagination_result.article_urls)} additional URLs from {top_url}")
                else:
                    # Fall back to standard crawling if no pagination
                    urls_from_page = await self._crawl_single_page(top_url)
                    for url in urls_from_page:
                        url_info = UrlInfo(
                            url=url,
                            detection_methods=[DetectionMethod.TOP_URL_CRAWLING],
                            detected_at=datetime.now(),
                            source_url=top_url
                        )
                        additional_urls.append(url_info)
                    
                    print(f"✅ Found {len(urls_from_page)} URLs from {top_url} (standard crawling)")
                
            except Exception as e:
                print(f"⚠️  Error processing {top_url}: {str(e)}")
                continue
        
        print(f"🔍 Total additional URLs found: {len(additional_urls)}")
        return additional_urls
    
    async def _check_and_process_pagination(self, site_config: SiteConfig, url_infos: List[UrlInfo]) -> Optional[CrawlResult]:
        """
        Check for pagination opportunities across all discovered URLs and process them.
        
        This method analyzes the discovered URLs to identify which ones might have
        pagination and then processes them to extract additional content.
        """
        try:
            # Check if pagination is enabled for this site
            if not getattr(site_config, 'pagination_enabled', False):
                print(f"📄 Pagination disabled for {site_config.name}, skipping pagination processing")
                return None
            
            print(f"🔍 Checking for pagination opportunities across {len(url_infos)} discovered URLs...")
            
            # Create pagination settings from site configuration
            pagination_settings = PaginationSettings(
                max_pages=getattr(site_config, 'pagination_max_pages', 1000),
                rate_limit_delay=getattr(site_config, 'pagination_rate_limit', 2.0),
                concurrent_batches=getattr(site_config, 'pagination_concurrent_batches', 10),
                timeout_seconds=30,
                max_retries=3
            )
            
            # Create pagination orchestrator
            orchestrator = PaginationOrchestrator(pagination_settings)
            
            # Create async crawler
            async with AsyncHTTPCrawler(
                timeout=30,
                max_retries=3,
                delay_between_requests=pagination_settings.rate_limit_delay
            ) as crawler:
                
                # Create crawl function
                async def crawl_function(url: str) -> str:
                    return await crawler.crawl_page(url)
                
                # Process each URL that might have pagination
                pagination_results = []
                total_pages_crawled = 0
                total_articles_found = 0
                
                for url_info in url_infos:
                    if not hasattr(url_info, 'url'):
                        continue
                        
                    url = url_info.url
                    print(f"🔍 Checking {url} for pagination...")
                    
                    try:
                        # Process the URL with pagination
                        result = await orchestrator.process_site_with_pagination(
                            url,
                            crawl_function,
                            max_pages=pagination_settings.max_pages
                        )
                        
                        if result and result.pagination_info and result.pagination_info.has_pagination:
                            print(f"✅ Pagination detected in {url}: {result.pagination_info.pagination_type}")
                            total_pages = result.pagination_info.total_pages
                            print(f"📄 Total pages: {total_pages if total_pages is not None else 'Unknown'}")
                            print(f"📄 Total articles: {len(result.article_urls) if hasattr(result, 'article_urls') else 'Unknown'}")
                            
                            pagination_results.append(result)
                            if total_pages is not None:
                                total_pages_crawled += total_pages
                            if hasattr(result, 'article_urls'):
                                total_articles_found += len(result.article_urls)
                        else:
                            print(f"📄 No pagination detected in {url}")
                            
                    except Exception as e:
                        print(f"⚠️  Error processing pagination for {url}: {str(e)}")
                        continue
                
                if pagination_results:
                    print(f"🎉 Pagination processing complete!")
                    print(f"📄 Sites with pagination: {len(pagination_results)}")
                    print(f"📄 Total pages crawled: {total_pages_crawled}")
                    print(f"📄 Total articles found: {total_articles_found}")
                    
                    # Return the first result as a representative (you could merge them if needed)
                    return pagination_results[0]
                else:
                    print(f"📄 No pagination opportunities found across {len(url_infos)} URLs")
                    return None
                    
        except Exception as e:
            print(f"⚠️  Pagination processing failed: {str(e)}")
            return None
    
    async def _crawl_single_page(self, url: str) -> List[str]:
        """
        Crawl a single page to extract URLs (fallback method when pagination is not detected).
        """
        try:
            async with AsyncHTTPCrawler(
                timeout=30,
                max_retries=3,
                delay_between_requests=1.0
            ) as crawler:
                
                content = await crawler.crawl_page(url)
                if not content:
                    print(f"⚠️  Failed to fetch content from {url}")
                    return []
                
                # Extract URLs from the page content
                from app.utils.content_extractor import ContentExtractor
                extractor = ContentExtractor()
                article_urls = extractor.extract_article_urls(content, url)
                
                print(f"✅ Extracted {len(article_urls)} URLs from {url}")
                return article_urls
                
        except Exception as e:
            print(f"⚠️  Error crawling {url}: {str(e)}")
            return []
    
    async def _save_url_set(self, url_set: UrlSet) -> Path:
        """Save URL set to timestamped directory."""
        # Save URL set using JsonWriter
        output_path = self.json_writer.write_url_set(url_set.site_id, url_set.urls)
        
        return output_path.parent

    async def _get_urls_from_multiple_sources_with_pagination(self, site_config: SiteConfig) -> UrlProcessingResult:
        """
        Enhanced URL discovery with pagination support.
        
        This method extends the standard discovery with intelligent pagination
        detection and crawling for sites that have paginated content.
        """
        start_time = datetime.now()
        
        # Step 1.1: Create tasks for concurrent execution based on site configuration
        tasks = []
        task_descriptions = []
        
        # Always include Firecrawl map
        tasks.append(self._get_urls_from_firecrawl_map(site_config))
        task_descriptions.append("firecrawl_map")
        
        # Only include sitemap if the site has one
        if site_config.is_sitemap:
            tasks.append(self._get_urls_from_sitemap(site_config))
            task_descriptions.append("sitemap")
            input_sources = 2
            print(f"🔍 Site {site_config.name} has sitemap - including sitemap processing")
        else:
            input_sources = 1
            print(f"🔍 Site {site_config.name} has no sitemap - skipping sitemap processing, using only Firecrawl map")
        
        # Step 1.2: Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Step 1.3: Handle exceptions and merge results
        url_lists = []
        successful_sources = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error getting URLs from {task_descriptions[i]}: {str(result)}")
                url_lists.append([])
            else:
                url_lists.append(result)
                successful_sources += 1
        
        # Step 1.4: Merge all URL lists using the proper merging function
        merged_urls = merge_url_lists(url_lists)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Step 1.5: Check for pagination opportunities
        pagination_result = await self._check_and_process_pagination(site_config, merged_urls)
        
        # Step 1.6: Build and return UrlProcessingResult response object
        metadata = {
            "input_sources": input_sources,
            "successful_sources": successful_sources,
            "pagination_processed": pagination_result is not None,
        }
        
        # Add pagination info to metadata in a safe way
        if pagination_result and hasattr(pagination_result, 'pagination_info') and pagination_result.pagination_info:
            pagination_info = pagination_result.pagination_info
            metadata.update({
                "pagination_type": str(getattr(pagination_info, 'pagination_type', 'unknown')),
                "total_pages": getattr(pagination_info, 'total_pages', 0) if getattr(pagination_info, 'total_pages') is not None else 0,
                "has_pagination": getattr(pagination_info, 'has_pagination', False),
                "confidence_score": getattr(pagination_info, 'confidence_score', 0.0),
                "base_url": str(getattr(pagination_info, 'base_url', '')) if getattr(pagination_info, 'base_url') else '',
                "next_url": str(getattr(pagination_info, 'next_url', '')) if getattr(pagination_info, 'next_url') else '',
                "previous_url": str(getattr(pagination_info, 'previous_url', '')) if getattr(pagination_info, 'previous_url') else ''
            })
        
        # Create a custom result object that includes pagination info
        result = UrlProcessingResult(
            urls=merged_urls,
            total_count=len(merged_urls),
            processing_time_seconds=processing_time,
            operation_type="discovery_with_pagination",
            metadata=metadata
        )
        
        # Add pagination info as an attribute
        result.pagination_info = pagination_result.pagination_info if pagination_result else None
        
        return result

class OnboardingUrlService:
    """Service for handling site onboarding process."""
    
    def __init__(self):
        # Access the global config_service instance
        from app.services.config_service import config_service
        self.config_service = config_service
    
    async def onboard_site(self, site_id: str, url_infos: List[UrlInfo], site_name: str) -> List[str]:
        """Complete onboarding process for a site."""
        print(f"🚀 Starting onboarding process for {site_id} ({site_name})...")
        
        # Extract URLs for AI analysis
        urls = [url_info.url for url_info in url_infos]
        print(f"🔍 Extracted {len(urls)} URLs for AI analysis")
        
        # Step 1: Run AI analysis with deduplication logic
        print(f"🤖 Running AI analysis on {len(urls)} URLs...")
        top_urls = await self._run_ai_analysis_with_deduplication(urls, site_name)
        print(f"🤖 AI analysis complete. Got {len(top_urls)} unique URLs: {top_urls}")
        
        # Step 2: Save onboarding results using existing config_service
        print(f"💾 Saving onboarding results...")
        await self._save_onboarding_results(site_id, top_urls, len(urls))
        
        print(f"✅ Onboarding process complete for {site_id}")
        return top_urls
    
    async def onboard_site_with_pagination(self, site_id: str, url_infos: List[UrlInfo], site_config: SiteConfig) -> List[str]:
        """
        Enhanced onboarding process for a site with pagination support.
        
        This method extends the standard onboarding process to handle pagination
        when onboarding URLs for a site that has paginated content.
        """
        print(f"🚀 Starting enhanced onboarding with pagination for {site_id} ({site_config.name})...")
        
        # Extract URLs for AI analysis
        urls = [url_info.url for url_info in url_infos]
        print(f"🔍 Extracted {len(urls)} URLs for AI analysis")
        
        # Step 1: Run AI analysis with deduplication logic (with pagination awareness)
        print(f"🤖 Running AI analysis on {len(urls)} URLs (with pagination awareness)...")
        top_urls = await self._run_ai_analysis_with_deduplication_with_pagination(urls, site_config)
        print(f"🤖 AI analysis complete. Got {len(top_urls)} unique URLs: {top_urls}")
        
        # Step 2: Save onboarding results using existing config_service
        print(f"💾 Saving onboarding results...")
        await self._save_onboarding_results(site_id, top_urls, len(urls))
        
        print(f"✅ Onboarding process complete for {site_id}")
        return top_urls
    
    async def _run_ai_analysis_with_deduplication(self, urls: List[str], site_name: str) -> List[str]:
        """Run AI analysis with automatic deduplication and retry logic."""
        max_attempts = 3
        attempt = 1
        
        while attempt <= max_attempts:
            print(f"🤖 AI Analysis Attempt {attempt}/{max_attempts}")
            
            # Step 1: Pre-filter obvious duplicates using aggressive normalization
            if attempt == 1:
                print(f"🔍 Pre-filtering URLs for obvious duplicates...")
                from app.utils.url_utils import pre_filter_duplicate_urls
                original_count = len(urls)
                urls = pre_filter_duplicate_urls(urls)
                filtered_count = len(urls)
                
                if filtered_count < original_count:
                    print(f"🔍 Pre-filtered from {original_count} to {filtered_count} URLs")
                else:
                    print(f"🔍 No obvious duplicates found in {len(urls)} URLs")
            
            # Step 2: Run AI analysis with batching and retry logic
            ai_suggestions = await self._run_ai_analysis(urls, site_name)
            print(f"🤖 AI analysis complete. Got {len(ai_suggestions)} suggestions")
            
            # Step 3: Run AI judge to select best 5
            print(f"👨‍⚖️ Running AI judge to select best 5 URLs...")
            top_urls = await self._run_ai_judge(ai_suggestions, site_name)
            print(f"👨‍⚖️ AI judge selected {len(top_urls)} URLs: {top_urls}")
            
            # Step 4: Check for resolved URL duplicates
            print(f"🔍 Checking for resolved URL duplicates...")
            dedup_result = await self._check_resolved_url_uniqueness(top_urls)
            
            if dedup_result.total_duplicates == 0:
                print(f"✅ No duplicates found. Final URLs: {top_urls}")
                return top_urls
            
            print(f"⚠️  Found {dedup_result.total_duplicates} duplicates:")
            for group in dedup_result.duplicate_groups:
                print(f"  - Group: {group}")
            
            # Step 5: If duplicates found, remove them and retry with remaining URLs
            if attempt < max_attempts:
                print(f"🔄 Retrying with duplicate URLs removed...")
                # Remove all URLs that have duplicates, keep only unique ones
                unique_urls = dedup_result.unique_urls
                print(f"🔄 Keeping {len(unique_urls)} unique URLs: {unique_urls}")
                
                # Update the URL list to exclude the ones that had duplicates
                # This ensures the AI doesn't suggest the same problematic URLs again
                urls = [url for url in urls if url not in top_urls or url in unique_urls]
                print(f"🔄 Updated URL pool for retry: {len(urls)} URLs")
                
                attempt += 1
            else:
                print(f"⚠️  Max attempts reached. Using unique URLs only: {dedup_result.unique_urls}")
                return dedup_result.unique_urls
        
        # This should never be reached, but just in case
        return []
    
    async def _run_ai_analysis(self, urls: List[str], site_name: str) -> List[OutputURLsWithInfo]:
        """Orchestrates 3 concurrent AI analyses with URL batching."""
        # Create request object
        request = UrlAnalysisRequest(urls=urls, site_name=site_name)
        
        # Determine batch size based on URL count to avoid token limits
        # OpenAI GPT-5 has ~450k TPM limit, so we need to be conservative
        # Each URL is roughly 50-100 characters, plus prompt overhead
        if len(urls) > 1000:  # Only batch if we have more than 1000 URLs
            batch_size = AIConfig.calculate_optimal_batch_size(len(urls))
            expected_batches = (len(urls) + batch_size - 1) // batch_size  # Ceiling division
            print(f"🤖 Large URL set detected ({len(urls)} URLs)")
            print(f"🤖 Using optimal batch size of {batch_size} URLs")
            print(f"🤖 Expected to create {expected_batches} batches")
            
            # Validate that the first batch won't exceed token limits
            first_batch = urls[:batch_size]
            if not AIConfig.validate_batch_size(first_batch, batch_size):
                print(f"⚠️  Warning: Calculated batch size may exceed token limits")
                print(f"⚠️  First batch would be ~{len(first_batch) * 75 // 4} estimated tokens")
        else:
            batch_size = len(urls)  # No batching needed for small sets
            print(f"🤖 Small URL set ({len(urls)} URLs), no batching needed")
        
        print(f"🤖 Processing {len(urls)} URLs in batches of {batch_size}")
        
        # Split URLs into batches
        url_batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]
        print(f"🤖 Created {len(url_batches)} batches for AI analysis")
        
        # Process each batch with AI analysis
        all_batch_results = []
        successful_batches = 0
        failed_batches = 0
        
        for batch_idx, url_batch in enumerate(url_batches):
            print(f"🤖 Processing batch {batch_idx + 1}/{len(url_batches)} with {len(url_batch)} URLs")
            
            # Create batch request
            batch_request = UrlAnalysisRequest(urls=url_batch, site_name=site_name)
            
            # Build prompt for this batch
            prompt = AIConfig.build_analysis_prompt(batch_request)
            
            # Run 3 concurrent AI analyses on this batch
            tasks = [
                self._run_single_ai_analysis(batch_request, prompt)
                for _ in range(3)
            ]
            
            # Execute concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Extract results from this batch
            batch_success = False
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"🤖 AI analysis failed for batch {batch_idx + 1}: {str(result)}")
                    failed_batches += 1
                else:
                    all_batch_results.append(result)
                    batch_success = True
            
            if batch_success:
                successful_batches += 1
                print(f"🤖 Batch {batch_idx + 1} completed successfully")
            else:
                print(f"🤖 Batch {batch_idx + 1} failed completely")
        
        print(f"🤖 Completed AI analysis on {len(url_batches)} batches")
        print(f"🤖 Successful batches: {successful_batches}, Failed batches: {failed_batches}")
        print(f"🤖 Total suggestions collected: {len(all_batch_results)}")
        
        # If we have no successful results, create a minimal fallback
        if not all_batch_results:
            print("🤖 No successful AI analysis results, creating fallback")
            all_batch_results.append(OutputURLsWithInfo(urls=[], total_count=0, timestamp=datetime.now()))
        
        return all_batch_results
    
    async def _run_single_ai_analysis(self, request: UrlAnalysisRequest, prompt: str) -> OutputURLsWithInfo:
        """Runs a single AI analysis."""
        async with OpenAIClient() as client:
            return await client.analyze_urls(request, prompt)
    
    async def _run_ai_judge(self, suggestions: List[OutputURLsWithInfo], site_name: str) -> List[str]:
        """Orchestrates AI judge process with enhanced handling for batched results."""
        # Extract URLs from suggestions, handling both successful and failed analyses
        url_suggestions = []
        for suggestion in suggestions:
            if suggestion.urls and len(suggestion.urls) > 0:
                # Extract URLs from successful suggestions
                urls = [url_info.url for url_info in suggestion.urls if hasattr(url_info, 'url')]
                if urls:
                    url_suggestions.append(urls)
            else:
                print(f"👨‍⚖️ Skipping empty suggestion with {len(suggestion.urls) if suggestion.urls else 0} URLs")
        
        if not url_suggestions:
            print("👨‍⚖️ No valid URL suggestions found for judging")
            return []
        
        print(f"👨‍⚖️ Processing {len(url_suggestions)} valid URL suggestions for judging")
        
        # If we have too many suggestions (from batching), we need to aggregate them first
        if len(url_suggestions) > 10:
            print(f"👨‍⚖️ Large number of suggestions ({len(url_suggestions)}), aggregating before judging...")
            url_suggestions = self._aggregate_url_suggestions(url_suggestions)
            print(f"👨‍⚖️ Aggregated to {len(url_suggestions)} suggestion groups")
        
        # Create request object
        request = UrlJudgeRequest(
            url_suggestions=url_suggestions,
            site_name=site_name,
            selection_count=5
        )
        
        # Build judge prompt
        prompt = AIConfig.build_judge_prompt(request)
        
        # Run AI judge
        try:
            async with OpenAIClient() as client:
                result = await client.judge_selection(request, prompt)
                return result.selected_urls
        except Exception as e:
            print(f"👨‍⚖️ AI judge failed: {str(e)}")
            # Fallback: return URLs from the first few successful suggestions
            fallback_urls = []
            for suggestion in suggestions[:3]:  # Take first 3 suggestions
                if suggestion.urls and len(suggestion.urls) > 0:
                    urls = [url_info.url for url_info in suggestion.urls if hasattr(url_info, 'url')]
                    fallback_urls.extend(urls[:2])  # Take first 2 URLs from each
                    if len(fallback_urls) >= 5:
                        break
            
            print(f"👨‍⚖️ Using fallback selection: {fallback_urls[:5]}")
            return fallback_urls[:5]
    
    def _aggregate_url_suggestions(self, url_suggestions: List[List[str]]) -> List[List[str]]:
        """Aggregate multiple URL suggestions into manageable groups for judging."""
        # Flatten all URLs and remove duplicates
        all_urls = []
        for suggestion in url_suggestions:
            all_urls.extend(suggestion)
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in all_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        # Group into chunks of 10-15 URLs for manageable judging
        chunk_size = 15
        aggregated_suggestions = []
        for i in range(0, len(unique_urls), chunk_size):
            chunk = unique_urls[i:i + chunk_size]
            aggregated_suggestions.append(chunk)
        
        return aggregated_suggestions
    
    async def _run_ai_analysis_with_deduplication_with_pagination(self, urls: List[str], site_config: SiteConfig) -> List[str]:
        """
        Enhanced AI analysis with automatic deduplication and retry logic,
        with pagination awareness.
        """
        max_attempts = 3
        attempt = 1
        
        while attempt <= max_attempts:
            print(f"🤖 AI Analysis Attempt {attempt}/{max_attempts}")
            
            # Step 1: Pre-filter obvious duplicates using aggressive normalization
            if attempt == 1:
                print(f"🔍 Pre-filtering URLs for obvious duplicates...")
                from app.utils.url_utils import pre_filter_duplicate_urls
                original_count = len(urls)
                urls = pre_filter_duplicate_urls(urls)
                filtered_count = len(urls)
                
                if filtered_count < original_count:
                    print(f"🔍 Pre-filtered from {original_count} to {filtered_count} URLs")
                else:
                    print(f"🔍 No obvious duplicates found in {len(urls)} URLs")
            
            # Step 2: Run AI analysis
            ai_suggestions = await self._run_ai_analysis(urls, site_config.name)
            print(f"🤖 AI analysis complete. Got {len(ai_suggestions)} suggestions")
            
            # Step 3: Run AI judge to select best 5
            print(f"👨‍⚖️ Running AI judge to select best 5 URLs...")
            top_urls = await self._run_ai_judge(ai_suggestions, site_config.name)
            print(f"👨‍⚖️ AI judge selected {len(top_urls)} URLs: {top_urls}")
            
            # Step 4: Check for resolved URL duplicates
            print(f"🔍 Checking for resolved URL duplicates...")
            dedup_result = await self._check_resolved_url_uniqueness(top_urls)
            
            if dedup_result.total_duplicates == 0:
                print(f"✅ No duplicates found. Final URLs: {top_urls}")
                return top_urls
            
            print(f"⚠️  Found {dedup_result.total_duplicates} duplicates:")
            for group in dedup_result.duplicate_groups:
                print(f"  - Group: {group}")
            
            # Step 5: If duplicates found, remove them and retry with remaining URLs
            if attempt < max_attempts:
                print(f"🔄 Retrying with duplicate URLs removed...")
                # Remove all URLs that have duplicates, keep only unique ones
                unique_urls = dedup_result.unique_urls
                print(f"🔄 Keeping {len(unique_urls)} unique URLs: {unique_urls}")
                
                # Update the URL list to exclude the ones that had duplicates
                # This ensures the AI doesn't suggest the same problematic URLs again
                urls = [url for url in urls if url not in top_urls or url in unique_urls]
                print(f"🔄 Updated URL pool for retry: {len(urls)} URLs")
                
                attempt += 1
            else:
                print(f"⚠️  Max attempts reached. Using unique URLs only: {dedup_result.unique_urls}")
                return dedup_result.unique_urls
        
        # This should never be reached, but just in case
        return []
    
    async def _check_resolved_url_uniqueness(self, urls: List[str]) -> 'UrlDeduplicationResult':
        """Check if URLs resolve to unique pages."""
        if not urls:
            from app.models.url_models import UrlDeduplicationResult
            return UrlDeduplicationResult(
                original_urls=[],
                unique_urls=[],
                duplicates_removed=[],
                duplicate_groups=[],
                total_original=0,
                total_unique=0,
                total_duplicates=0,
                processing_time_seconds=0
            )
        
        # Resolve the URLs
        resolution_mapping = await resolve_urls(urls)
        
        # Extract resolved URLs
        resolved_mapping = {
            original: result.resolved_url 
            for original, result in resolution_mapping.mappings.items()
            if result.resolution_success
        }
        
        # Find duplicates using the existing utility
        from app.utils.url_utils import find_duplicate_resolutions
        return find_duplicate_resolutions(resolved_mapping)
    
    async def _save_onboarding_results(self, site_id: str, top_urls: List[str], total_analyzed: int):
        """Save onboarding results using existing config_service."""
        print(f"💾 Saving onboarding results for {site_id}...")
        print(f"💾 Top URLs to save: {top_urls}")
        print(f"💾 Total URLs analyzed: {total_analyzed}")
        
        from app.models.url_models import OnboardingResult
        
        onboarding_result = OnboardingResult(
            site_id=site_id,
            top_urls=top_urls,
            onboarding_time=datetime.now(),
            total_urls_analyzed=total_analyzed
        )
        
        print(f"💾 Created OnboardingResult object: {onboarding_result}")
        
        try:
            self.config_service.mark_site_onboarded(site_id, onboarding_result)
            print(f"✅ Successfully saved onboarding results for {site_id}")
        except Exception as e:
            print(f"❌ Error saving onboarding results for {site_id}: {str(e)}")
            raise