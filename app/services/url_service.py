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
from typing import List, Dict, Any

# Astral AI ----
from app.models.url_models import (
    UrlInfo, 
    DetectionMethod, 
    UrlProcessingResult, 
    UrlSet,
    ProcessingSummary,
    UrlResolutionMapping,
    UrlDeduplicationResult,
    OutputURLsWithInfo,
    UrlAnalysisRequest,
    UrlJudgeRequest
)
from app.models.config_models import SiteConfig, SiteStatus
from app.clients.firecrawl_client import FirecrawlClient
from app.clients.openai_client import OpenAIClient
from app.crawler.sitemap_crawler import SitemapCrawler
from app.services.config_service import config_service
from app.utils.url_utils import (
    create_url_info, 
    merge_url_lists, 
    resolve_urls, 
    filter_resolved_duplicates
)
from app.utils.json_writer import JsonWriter
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
        
        # Step 4: Create URL set with proper structure
        print(f"🔍 Final URL set contains {len(all_url_infos)} total URLs")
        
        # Debug: Check the structure of all_url_infos
        print(f"🔍 Debug: Type of all_url_infos: {type(all_url_infos)}")
        if all_url_infos:
            print(f"🔍 Debug: First item type: {type(all_url_infos[0])}")
            print(f"🔍 Debug: First item: {all_url_infos[0]}")
        
        # Safety check: ensure all items are UrlInfo objects
        all_url_infos = [url for url in all_url_infos if isinstance(url, UrlInfo)]
        print(f"🔍 After safety check: {len(all_url_infos)} valid UrlInfo objects")
        
        # Show breakdown by detection method
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
        
        url_set = UrlSet(
            site_id=site_id,
            timestamp=datetime.now(),
            urls=all_url_infos,
            total_count=len(all_url_infos)
        )
        
        # Step 5: Save results using JsonWriter
        output_path = await self._save_url_set(url_set)
        
        # Step 6: Create processing summary
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Collect all detection methods safely
        detection_methods_used = []
        for url_info in all_url_infos:
            if hasattr(url_info, 'detection_methods'):
                for method in url_info.detection_methods:
                    detection_methods_used.append(method.value)
        
        summary = ProcessingSummary(
            status="completed",
            urls_found=len(all_url_infos),
            urls_processed=len(all_url_infos),
            processing_time_seconds=processing_time,
            detection_methods_used=list(set(detection_methods_used))
        )
        
        # Save the final processing summary with correct timing
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
    
    async def _get_urls_from_multiple_sources(self, site_config: SiteConfig) -> UrlProcessingResult:
        """Orchestrates concurrent URL discovery from sitemap and Firecrawl."""
        start_time = datetime.now()
        
        # Create tasks for concurrent execution
        tasks = [
            self._get_urls_from_sitemap(site_config),
            self._get_urls_from_firecrawl_map(site_config)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions and merge results
        url_lists = []
        successful_sources = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error getting URLs from source {i}: {str(result)}")
                url_lists.append([])
            else:
                url_lists.append(result)
                successful_sources += 1
        
        # Merge all URL lists using the proper merging function
        merged_urls = merge_url_lists(url_lists)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return UrlProcessingResult(
            urls=merged_urls,
            total_count=len(merged_urls),
            processing_time_seconds=processing_time,
            operation_type="url_discovery",
            metadata={
                "input_sources": 2,
                "successful_sources": successful_sources,
                "failed_sources": 2 - successful_sources,
                "sitemap_urls": len(url_lists[0]) if len(url_lists) > 0 else 0,
                "firecrawl_map_urls": len(url_lists[1]) if len(url_lists) > 1 else 0
            }
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
        
        # Import rate limiter
        from app.utils.rate_limiter import create_rate_limiter_from_config, process_with_rate_limiting
        
        # Create adaptive rate limiter
        rate_limiter = create_rate_limiter_from_config(config_service)
        
        async with FirecrawlClient() as client:
            # Define the processor function for each URL
            async def process_single_url(url: str):
                try:
                    print(f"🔍 Crawling URL: {url}")
                    
                    # Crawl single URL with Firecrawl
                    discovered_urls = await client.crawl_single_url(url, max_depth=2, limit=2)
                    
                    if discovered_urls:
                        # Filter out any None or invalid URLs before creating UrlInfo objects
                        valid_urls = [url for url in discovered_urls if url and isinstance(url, str) and url.strip()]
                        if valid_urls:
                            # Convert to UrlInfo objects
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
            
            # Process URLs with adaptive rate limiting
            batch_size = config_service.firecrawl_batch_size
            results = await process_with_rate_limiting(
                top_urls, 
                process_single_url, 
                rate_limiter, 
                batch_size
            )
            
            # Collect all discovered URLs
            for i, result in enumerate(results):
                print(f"🔍 Debug: Processing result {i}: {type(result)} - {result}")
                if result and isinstance(result, list):
                    print(f"🔍 Debug: Extending with list of {len(result)} items")
                    all_discovered_urls.extend(result)
                elif result is not None:
                    # Single result case
                    print(f"🔍 Debug: Appending single result: {type(result)}")
                    all_discovered_urls.append(result)
                else:
                    print(f"🔍 Debug: Skipping None result")
            
            # Safety check: filter out any None values that might have slipped through
            all_discovered_urls = [url for url in all_discovered_urls if url is not None]
            
            # Safety check: ensure all items are UrlInfo objects
            all_discovered_urls = [url for url in all_discovered_urls if isinstance(url, UrlInfo)]
            
            # Print rate limiter stats
            stats = rate_limiter.get_stats()
            print(f"🔍 Rate limiter stats: {stats}")
        
        # Remove duplicates and return unique URLs
        if all_discovered_urls:
            print(f"🔍 Total discovered URLs before deduplication: {len(all_discovered_urls)}")
            # Debug: Check the structure of all_discovered_urls
            print(f"🔍 Debug: Type of all_discovered_urls: {type(all_discovered_urls)}")
            if all_discovered_urls:
                print(f"🔍 Debug: First item type: {type(all_discovered_urls[0])}")
                print(f"🔍 Debug: First item: {all_discovered_urls[0]}")
            # Since all_discovered_urls is already a list of UrlInfo objects, just return it
            # The merge_url_lists function expects a list of lists, but we have a single list
            print(f"🔍 Total unique discovered URLs after deduplication: {len(all_discovered_urls)}")
            return all_discovered_urls
        
        print("🔍 No additional URLs discovered from top URLs")
        return []
    
    async def _save_url_set(self, url_set: UrlSet) -> Path:
        """Save URL set to timestamped directory."""
        # Save URL set using JsonWriter
        output_path = self.json_writer.write_url_set(url_set.site_id, url_set.urls)
        
        return output_path.parent

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
        
        # Step 1: Run 3 concurrent AI analyses
        print(f"🤖 Running AI analysis on {len(urls)} URLs...")
        ai_suggestions = await self._run_ai_analysis(urls, site_name)
        print(f"🤖 AI analysis complete. Got {len(ai_suggestions)} suggestions")
        
        # Step 2: Run AI judge to select best 5
        print(f"👨‍⚖️ Running AI judge to select best 5 URLs...")
        top_urls = await self._run_ai_judge(ai_suggestions, site_name)
        print(f"👨‍⚖️ AI judge selected {len(top_urls)} URLs: {top_urls}")
        
        # Step 3: Validate unique resolutions and filter content hubs
        print(f"🔍 Validating and filtering URLs...")
        validated_urls = await self._validate_and_filter_urls(top_urls, urls)
        print(f"🔍 Validation complete. Final URLs: {validated_urls}")
        
        # Step 4: Save onboarding results using existing config_service
        print(f"💾 Saving onboarding results...")
        await self._save_onboarding_results(site_id, validated_urls, len(urls))
        
        print(f"✅ Onboarding process complete for {site_id}")
        return validated_urls
    
    async def _run_ai_analysis(self, urls: List[str], site_name: str) -> List[OutputURLsWithInfo]:
        """Orchestrates 3 concurrent AI analyses."""
        # Create request object
        request = UrlAnalysisRequest(urls=urls, site_name=site_name)
        
        # Build prompt once
        prompt = AIConfig.build_analysis_prompt(request)
        
        # Create 3 concurrent tasks
        tasks = [
            self._run_single_ai_analysis(request, prompt)
            for _ in range(3)
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract results
        suggestions = []
        for result in results:
            if isinstance(result, Exception):
                print(f"AI analysis failed: {str(result)}")
                suggestions.append(OutputURLsWithInfo(urls=[], total_count=0, timestamp=datetime.now()))
            else:
                suggestions.append(result)
        
        return suggestions
    
    async def _run_single_ai_analysis(self, request: UrlAnalysisRequest, prompt: str) -> OutputURLsWithInfo:
        """Runs a single AI analysis."""
        async with OpenAIClient() as client:
            return await client.analyze_urls(request, prompt)
    
    async def _run_ai_judge(self, suggestions: List[OutputURLsWithInfo], site_name: str) -> List[str]:
        """Orchestrates AI judge process."""
        # Extract URLs from suggestions
        url_suggestions = [
            [url_info.url for url_info in suggestion.urls]
            for suggestion in suggestions
        ]
        
        # Create request object
        request = UrlJudgeRequest(
            url_suggestions=url_suggestions,
            site_name=site_name,
            selection_count=5
        )
        
        # Build judge prompt
        prompt = AIConfig.build_judge_prompt(request)
        
        # Run AI judge
        async with OpenAIClient() as client:
            result = await client.judge_selection(request, prompt)
            return result.selected_urls
    
    async def _validate_and_filter_urls(self, top_urls: List[str], all_urls: List[str]) -> List[str]:
        """Ensure URLs don't resolve to the same page and are content discovery hubs."""
        
        print(f"🔍 Validating and filtering {len(top_urls)} top URLs...")
        
        # Filter out URLs that look like individual articles
        filtered_urls = []
        for url in top_urls:
            if self._looks_like_content_hub(url):
                filtered_urls.append(url)
                print(f"✅ {url} - passed content hub validation")
            else:
                print(f"❌ {url} - failed content hub validation")
        
        print(f"🔍 After content hub filtering: {len(filtered_urls)} URLs")
        
        # If we don't have enough, try to find more from remaining URLs
        while len(filtered_urls) < 5 and all_urls:
            remaining = [url for url in all_urls if url not in filtered_urls]
            if not remaining:
                break
                
            for url in remaining:
                if self._looks_like_content_hub(url):
                    filtered_urls.append(url)
                    print(f"➕ Added replacement URL: {url}")
                    break
            else:
                break
        
        # Ensure we don't exceed 5 URLs
        filtered_urls = filtered_urls[:5]
        print(f"🔍 Final filtered URLs before resolution validation: {len(filtered_urls)}")
        
        # Validate unique resolutions
        if len(filtered_urls) > 1:
            print(f"🔍 Running resolution validation on {len(filtered_urls)} URLs...")
            validated_urls = await self._validate_unique_resolutions(filtered_urls, all_urls)
            print(f"🔍 After resolution validation: {len(validated_urls)} URLs")
            return validated_urls
        
        print(f"🔍 Skipping resolution validation (only {len(filtered_urls)} URLs)")
        return filtered_urls
    
    def _looks_like_content_hub(self, url: str) -> bool:
        """Check if URL looks like a content discovery hub rather than individual article."""

        
        # Look for patterns that suggest content hubs
        hub_patterns = [
            '/news/', '/blog/', '/press-releases/', '/judgments/',
            '/articles/', '/publications/', '/reports/', '/updates/',
            '/announcements/', '/media/', '/resources/', '/services/',
            '/council-', '/council_', '/government-', '/government_'
        ]
        
        # Look for patterns that suggest individual articles
        article_patterns = [
            '/news/20', '/blog/20', '/press-releases/20',  # Date patterns
            '.html', '.htm', '.php', '.aspx'  # File extensions
        ]
        
        # Check if it's likely a hub
        is_hub = any(pattern in url.lower() for pattern in hub_patterns)
        
        # Check if it's likely an individual article
        is_article = any(pattern in url.lower() for pattern in article_patterns)
        
        # Check URL depth - shallow URLs are more likely to be hubs
        url_depth = len([part for part in url.split('/') if part])
        
        # Additional checks for individual articles
        # URLs with dates in them are likely articles
        import re
        has_date = re.search(r'/\d{4}(?:/\d{2})?', url)
        
        # URLs with long path segments (likely titles) are probably articles
        path_parts = [part for part in url.split('/') if part]
        has_long_segments = any(len(part) > 30 for part in path_parts)  # Increased threshold
        
        # URLs ending with specific words that suggest articles
        article_endings = ['article', 'post', 'story', 'news', 'press-release']
        ends_with_article = any(url.lower().endswith(ending) for ending in article_endings)
        
        # URLs with file extensions are likely articles
        has_file_extension = re.search(r'\.(html?|php|aspx?|jsp|asp)$', url.lower())
        
        # Check for excessive hyphens/underscores that suggest article titles
        # But be more lenient - government URLs often use hyphens for readability
        path_parts = [part for part in url.split('/') if part]
        excessive_separators = any(
            len(part.split('-')) > 4 or len(part.split('_')) > 4 
            for part in path_parts
        )
        
        # If it has multiple article indicators, it's definitely an article
        article_indicators = sum([
            is_article,
            bool(has_date),
            has_long_segments,
            ends_with_article,
            bool(has_file_extension),
            excessive_separators
        ])
        # A good hub should have few article indicators and reasonable depth
        # Be more lenient with government URLs
        result = (is_hub or url_depth <= 3) and article_indicators <= 2 and 1 <= url_depth <= 5
        return result
    
    async def _validate_unique_resolutions(self, top_urls: List[str], all_urls: List[str]) -> List[str]:
        """Ensure URLs don't resolve to the same page."""
        # Resolve the top URLs
        resolution_mapping = await resolve_urls(top_urls)
        
        # Extract resolved URLs
        resolved_mapping = {
            original: result.resolved_url 
            for original, result in resolution_mapping.mappings.items()
            if result.resolution_success
        }
        
        # Find duplicates
        from app.utils.url_utils import find_duplicate_resolutions
        dedup_result = find_duplicate_resolutions(resolved_mapping)
        
        if dedup_result.total_duplicates == 0:
            return top_urls
        
        # Remove duplicates and find replacements
        unique_urls = dedup_result.unique_urls
        remaining_urls = [url for url in all_urls if url not in top_urls]
        
        # Try to find replacements for duplicates
        while len(unique_urls) < 5 and remaining_urls:
            # Take next URL from remaining
            replacement_url = remaining_urls.pop(0)
            
            # Check if it looks like a content hub
            if not self._looks_like_content_hub(replacement_url):
                continue
            
            # Resolve it
            replacement_resolution = await resolve_urls([replacement_url])
            replacement_resolved = replacement_resolution.mappings[replacement_url].resolved_url
            
            # Check if it's unique
            if replacement_resolved not in [resolved_mapping[url] for url in unique_urls]:
                unique_urls.append(replacement_url)
        
        return unique_urls[:5]  # Ensure we don't exceed 5
    
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