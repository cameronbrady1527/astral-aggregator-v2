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
            all_url_infos = discovery_result.urls + additional_urls
        else:
            # Step 3: Get additional URLs from existing top URLs
            top_urls = site_config.top_urls or []
            additional_urls = await self._get_additional_urls_from_top_urls(top_urls)
            all_url_infos = discovery_result.urls + additional_urls
        
        # Step 4: Create URL set with proper structure
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
        summary = ProcessingSummary(
            status="completed",
            urls_found=len(all_url_infos),
            urls_processed=len(all_url_infos),
            processing_time_seconds=processing_time,
            detection_methods_used=list(set(
                method.value for url_info in all_url_infos 
                for method in url_info.detection_methods
            ))
        )
        
        # Save the final processing summary with correct timing
        self.json_writer.write_processing_summary(site_id, summary)
        
        return {
            "site_id": site_id,
            "site_name": site_config.name,
            "url_set": url_set.dict(),
            "processing_summary": summary.dict(),
            "discovery_result": discovery_result.dict(),
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
        
        async with FirecrawlClient() as client:
            urls = await client.crawl_urls(top_urls, max_depth=2, limit=1)
            return [create_url_info(url, DetectionMethod.FIRECRAWL_CRAWL) for url in urls]
    
    async def _save_url_set(self, url_set: UrlSet) -> Path:
        """Save URL set to timestamped directory."""
        # Save URL set using JsonWriter
        output_path = self.json_writer.write_url_set(url_set.site_id, url_set.urls)
        
        return output_path.parent

class OnboardingUrlService:
    """Service for handling site onboarding process."""
    
    def __init__(self):
        pass
    
    async def onboard_site(self, site_id: str, url_infos: List[UrlInfo], site_name: str) -> List[str]:
        """Complete onboarding process for a site."""
        # Extract URLs for AI analysis
        urls = [url_info.url for url_info in url_infos]
        
        # Step 1: Run 3 concurrent AI analyses
        ai_suggestions = await self._run_ai_analysis(urls, site_name)
        
        # Step 2: Run AI judge to select best 5
        top_urls = await self._run_ai_judge(ai_suggestions, site_name)
        
        # Step 3: Validate unique resolutions
        validated_urls = await self._validate_unique_resolutions(top_urls, urls)
        
        # Step 4: Save onboarding results using existing config_service
        await self._save_onboarding_results(site_id, validated_urls, len(urls))
        
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
        from app.models.url_models import OnboardingResult
        
        onboarding_result = OnboardingResult(
            site_id=site_id,
            top_urls=top_urls,
            onboarding_time=datetime.now(),
            total_urls_analyzed=total_analyzed
        )
        
        config_service.mark_site_onboarded(site_id, onboarding_result)