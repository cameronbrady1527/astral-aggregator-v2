#!/usr/bin/env python3
# ==============================================================================
# detect_pagination.py — Pagination Detection Script
# ==============================================================================
# Purpose: Detect pagination patterns on websites to determine if pagination is needed
# ==============================================================================

"""
🔍 Pagination Detection Script

This script analyzes websites to detect pagination patterns and determine
whether pagination configuration is needed. It's useful for:

- Analyzing new sites before adding them to configuration
- Troubleshooting existing sites that might need pagination
- Understanding the structure of websites for optimization

Usage:
    python scripts/detect_pagination.py <url>                    # Analyze specific URL
    python scripts/detect_pagination.py --site <site_id>         # Analyze configured site
    python scripts/detect_pagination.py --list-patterns          # Show detection patterns
    python scripts/detect_pagination.py --help                   # Show help
"""

import asyncio
import sys
import os
import argparse
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.services.pagination_detector import PaginationDetector, ContentTypeDetector
from app.services.pagination_strategies import PaginationStrategyFactory
from app.utils.simple_crawler import create_crawler
from app.services.config_service import config_service

# ==============================================================================
# Pagination Detection Functions
# ==============================================================================

async def detect_pagination_for_url(url: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Detect pagination patterns for a specific URL.
    
    Args:
        url: The URL to analyze
        max_depth: Maximum depth to crawl for pagination detection
    
    Returns:
        Detection results dictionary
    """
    print(f"🔍 Analyzing URL: {url}")
    print("=" * 60)
    
    try:
        # Create crawler
        crawler = create_crawler()
        
        # Create detectors
        pagination_detector = PaginationDetector()
        content_detector = ContentTypeDetector()
        
        # Crawl the page
        print("📡 Crawling page...")
        response = await crawler.crawl_async(url)
        
        if not response or not response.get('content'):
            return {"error": "Failed to crawl page or no content received"}
        
        html_content = response['content']
        final_url = response.get('final_url', url)
        
        print(f"✅ Page crawled successfully")
        print(f"📄 Final URL: {final_url}")
        print(f"📊 Content length: {len(html_content)} characters")
        
        # Detect pagination patterns
        print("\n🔍 Detecting pagination patterns...")
        pagination_info = pagination_detector.detect_pagination(url, html_content)
        
        # Detect content type
        print("📄 Analyzing content type...")
        content_type = content_detector.classify_content(html_content)
        
        # Analyze pagination strategy
        strategy = None
        if pagination_info.pagination_type:
            strategy_factory = PaginationStrategyFactory()
            strategy = strategy_factory.create_strategy(pagination_info.pagination_type)
        
        # Compile results
        results = {
            "url": url,
            "final_url": final_url,
            "content_length": len(html_content),
            "pagination_detected": pagination_info.pagination_type is not None,
            "pagination_info": pagination_info.dict() if pagination_info else None,
            "content_type": content_type.value if content_type else "unknown",
            "strategy": strategy.__class__.__name__ if strategy else None,
            "recommendations": generate_recommendations(pagination_info, content_type, len(html_content))
        }
        
        # Display results
        display_detection_results(results)
        
        return results
        
    except Exception as e:
        error_msg = f"Error analyzing URL {url}: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def detect_pagination_for_site(site_id: str) -> Dict[str, Any]:
    """
    Detect pagination for a configured site.
    
    Args:
        site_id: The site ID from configuration
    
    Returns:
        Detection results dictionary
    """
    print(f"🔍 Analyzing configured site: {site_id}")
    print("=" * 60)
    
    try:
        # Get site configuration
        site_config = config_service.site(site_id)
        if not site_config:
            return {"error": f"Site {site_id} not found in configuration"}
        
        print(f"📄 Site: {site_config.name}")
        print(f"🌐 URL: {site_config.url}")
        print(f"📊 Sitemap: {'Yes' if site_config.is_sitemap else 'No'}")
        
        # Check current pagination configuration
        current_pagination = {
            "enabled": getattr(site_config, 'pagination_enabled', False),
            "max_pages": getattr(site_config, 'pagination_max_pages', None),
            "rate_limit": getattr(site_config, 'pagination_rate_limit', None),
            "concurrent_batches": getattr(site_config, 'pagination_concurrent_batches', None)
        }
        
        print(f"🚀 Current Pagination: {'Enabled' if current_pagination['enabled'] else 'Disabled'}")
        if current_pagination['enabled']:
            print(f"  📄 Max Pages: {current_pagination['max_pages']}")
            print(f"  📄 Rate Limit: {current_pagination['rate_limit']}s")
            print(f"  📄 Concurrent: {current_pagination['concurrent_batches']}")
        
        print("\n" + "=" * 60)
        
        # Analyze the site URL
        results = await detect_pagination_for_url(site_config.url)
        
        # Add site configuration analysis
        if 'error' not in results:
            results['site_config'] = site_config.dict()
            results['current_pagination'] = current_pagination
            results['configuration_recommendations'] = generate_config_recommendations(
                results, current_pagination
            )
        
        return results
        
    except Exception as e:
        error_msg = f"Error analyzing site {site_id}: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

def generate_recommendations(pagination_info, content_type, content_length: int) -> List[str]:
    """Generate recommendations based on detection results."""
    recommendations = []
    
    # Content type recommendations
    if content_type.value == "search_results":
        recommendations.append("🔍 This appears to be a search results page - pagination likely needed")
    elif content_type.value == "listing":
        recommendations.append("📋 This appears to be a content listing page - pagination may be needed")
    elif content_type.value == "article":
        recommendations.append("📄 This appears to be an article page - pagination not needed")
    
    # Content length recommendations
    if content_length > 50000:
        recommendations.append("📊 Large page content detected - may indicate complex structure")
    elif content_length < 5000:
        recommendations.append("📊 Small page content - may be simple or incomplete")
    
    # Pagination-specific recommendations
    if pagination_info and pagination_info.pagination_type:
        if pagination_info.confidence_score > 0.8:
            recommendations.append("✅ Strong pagination detection - configuration recommended")
        elif pagination_info.confidence_score > 0.5:
            recommendations.append("⚠️  Moderate pagination detection - configuration may be beneficial")
        else:
            recommendations.append("❓ Weak pagination detection - manual review recommended")
        
        if pagination_info.total_pages and pagination_info.total_pages > 100:
            recommendations.append(f"📄 Large number of pages detected ({pagination_info.total_pages}) - high concurrency recommended")
    
    # Default recommendations
    if not recommendations:
        recommendations.append("💡 No specific recommendations - manual review suggested")
    
    return recommendations

def generate_config_recommendations(detection_results: Dict[str, Any], current_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate configuration recommendations based on detection results."""
    recommendations = {}
    
    # Should pagination be enabled?
    should_enable = detection_results.get('pagination_detected', False)
    recommendations['enable_pagination'] = should_enable
    
    if should_enable:
        # Recommended max pages
        if detection_results.get('pagination_info', {}).get('total_pages'):
            total_pages = detection_results['pagination_info']['total_pages']
            recommended_max = min(total_pages * 2, 1000)  # 2x detected + cap at 1000
        else:
            recommended_max = 200  # Conservative default
        
        recommendations['max_pages'] = recommended_max
        
        # Recommended rate limit
        if detection_results.get('content_type') == 'search_results':
            recommendations['rate_limit'] = 1.5  # More aggressive for search
        else:
            recommendations['rate_limit'] = 2.0  # Conservative for content
        
        # Recommended concurrency
        if detection_results.get('pagination_info', {}).get('total_pages', 0) > 500:
            recommendations['concurrent_batches'] = 10  # High for large sites
        else:
            recommendations['concurrent_batches'] = 5   # Moderate for smaller sites
        
        # Custom patterns if needed
        if detection_results.get('pagination_info', {}).get('custom_patterns'):
            recommendations['custom_patterns'] = detection_results['pagination_info']['custom_patterns']
        else:
            recommendations['custom_patterns'] = []
    
    return recommendations

def display_detection_results(results: Dict[str, Any]) -> None:
    """Display the detection results in a formatted way."""
    print("\n📊 Detection Results")
    print("=" * 60)
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return
    
    print(f"🌐 URL: {results['url']}")
    print(f"📄 Final URL: {results['final_url']}")
    print(f"📊 Content Length: {results['content_length']:,} characters")
    print(f"📄 Content Type: {results['content_type']}")
    
    # Pagination information
    if results['pagination_detected']:
        pagination_info = results['pagination_info']
        print(f"\n🚀 Pagination Detected: YES")
        print(f"📄 Type: {pagination_info.get('pagination_type', 'N/A')}")
        print(f"📄 Confidence: {pagination_info.get('confidence_score', 'N/A'):.2f}")
        print(f"📄 Total Pages: {pagination_info.get('total_pages', 'N/A')}")
        print(f"📄 Total Items: {pagination_info.get('total_items', 'N/A')}")
        print(f"📄 Base URL: {pagination_info.get('base_url', 'N/A')}")
        
        if pagination_info.get('custom_patterns'):
            print(f"📄 Custom Patterns: {', '.join(pagination_info['custom_patterns'])}")
    else:
        print(f"\n❌ Pagination Detected: NO")
    
    # Strategy information
    if results['strategy']:
        print(f"📄 Strategy: {results['strategy']}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    for rec in results['recommendations']:
        print(f"   {rec}")
    
    # Configuration recommendations (if available)
    if 'configuration_recommendations' in results:
        config_recs = results['configuration_recommendations']
        print(f"\n⚙️  Configuration Recommendations:")
        
        if config_recs.get('enable_pagination'):
            print(f"   ✅ Enable pagination: true")
            print(f"   📄 Max pages: {config_recs.get('max_pages')}")
            print(f"   📄 Rate limit: {config_recs.get('rate_limit')}s")
            print(f"   📄 Concurrent batches: {config_recs.get('concurrent_batches')}")
            
            if config_recs.get('custom_patterns'):
                print(f"   📄 Custom patterns: {config_recs['custom_patterns']}")
        else:
            print(f"   ❌ Enable pagination: false (not needed)")

def list_detection_patterns() -> None:
    """List all available pagination detection patterns."""
    print("🔍 Available Pagination Detection Patterns")
    print("=" * 60)
    
    print("\n📄 URL Parameter Patterns:")
    print("   - ?page=X (e.g., ?page=2, ?page=3)")
    print("   - ?start=X (e.g., ?start=20, ?start=40)")
    print("   - ?offset=X (e.g., ?offset=0, ?offset=25)")
    print("   - ?p=X (e.g., ?p=2, ?p=3)")
    
    print("\n📄 Path-based Patterns:")
    print("   - /page/X (e.g., /page/2, /page/3)")
    print("   - /p/X (e.g., /p/2, /p/3)")
    print("   - /X (e.g., /2, /3) - when context suggests pagination")
    
    print("\n📄 HTML Content Patterns:")
    print("   - 'Page X of Y' text")
    print("   - 'Showing X-Y of Z results' text")
    print("   - Navigation links (Next, Previous, First, Last)")
    print("   - Page number links")
    
    print("\n📄 Content Indicators:")
    print("   - Search results pages")
    print("   - Article listings")
    print("   - Product catalogs")
    print("   - News archives")
    print("   - Document repositories")

# ==============================================================================
# Main Execution
# ==============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pagination Detection Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/detect_pagination.py https://example.com/news
  python scripts/detect_pagination.py --site judiciary_uk
  python scripts/detect_pagination.py --list-patterns
        """
    )
    
    parser.add_argument(
        "url", 
        nargs="?", 
        type=str, 
        help="URL to analyze for pagination"
    )
    
    parser.add_argument(
        "--site", 
        type=str, 
        help="Site ID from configuration to analyze"
    )
    
    parser.add_argument(
        "--list-patterns", 
        action="store_true",
        help="List all available pagination detection patterns"
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("🔍 Pagination Detection Script")
    print("=" * 60)
    print("Analyze websites to detect pagination patterns and configuration needs")
    print("=" * 60)
    
    try:
        if args.list_patterns:
            list_detection_patterns()
        elif args.site:
            await detect_pagination_for_site(args.site)
        elif args.url:
            await detect_pagination_for_url(args.url)
        else:
            print("❌ No URL or site specified. Use --help for usage information.")
            print("\n💡 Examples:")
            print("   python scripts/detect_pagination.py https://example.com/news")
            print("   python scripts/detect_pagination.py --site judiciary_uk")
            print("   python scripts/detect_pagination.py --list-patterns")
            
    except KeyboardInterrupt:
        print("\n\n👋 Operation interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
