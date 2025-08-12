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
    OutputURLsWithInfo,
    UrlAnalysisRequest,
    UrlJudgeRequest
)
from app.models.config_models import SiteConfig
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
    
    async def _get_urls_from_multiple_sources(self, site_config: SiteConfig) -> UrlProcessingResult:
        """Orchestrates concurrent URL discovery from sitemap and Firecrawl."""
        start_time = datetime.now()
        
        # Step 1.1: Create tasks for concurrent execution
        tasks = [
            self._get_urls_from_sitemap(site_config),
            self._get_urls_from_firecrawl_map(site_config)
        ]
        
        # Step 1.2: Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Step 1.3: Handle exceptions and merge results
        url_lists = []
        successful_sources = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error getting URLs from source {i}: {str(result)}")
                url_lists.append([])
            else:
                url_lists.append(result)
                successful_sources += 1
        
        # Step 1.4: Merge all URL lists using the proper merging function
        merged_urls = merge_url_lists(url_lists)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Step 1.5: Build and return UrlProcessingResult response object
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
        
        # Step 3: Validate unique resolutions
        print(f"🔍 Validating URLs...")
        validated_urls = await self._validate_unique_resolutions(top_urls, urls)
        print(f"🔍 Validation complete. Final URLs: {validated_urls}")
        
        # Step 4: Save onboarding results using existing config_service
        print(f"💾 Saving onboarding results...")
        await self._save_onboarding_results(site_id, validated_urls, len(urls))
        
        print(f"✅ Onboarding process complete for {site_id}")
        return validated_urls
    
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