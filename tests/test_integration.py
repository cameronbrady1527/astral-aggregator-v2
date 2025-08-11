# ==============================================================================
# test_integration.py — Integration tests
# ==============================================================================
# Purpose: Test URL processing integration
# Sections: Imports, Test functions
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Astral AI ----
from app.services.url_service import UrlService
from app.services.config_service import config_service
from app.models.url_models import UrlAnalysisRequest, UrlJudgeRequest
from app.clients.firecrawl_client import FirecrawlClient
from app.clients.openai_client import OpenAIClient
from app.crawler.sitemap_crawler import SitemapCrawler

# ==============================================================================
# Test functions
# ==============================================================================

async def test_single_site_processing():
    """Test processing a single site."""
    print("Testing single site processing...")
    url_service = UrlService()
    
    # Test with judiciary_uk
    try:
        result = await url_service.process_site("judiciary_uk")
        print(f"✅ Processing result: {result}")
        return True
    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")
        return False

async def test_firecrawl_sdk():
    """Test Firecrawl SDK integration."""
    print("Testing Firecrawl SDK integration...")
    
    try:
        async with FirecrawlClient() as client:
            urls = await client.map_site("https://judiciary.uk/", include_subdomains=True)
            print(f"✅ Firecrawl SDK found {len(urls)} URLs")
            return True
    except Exception as e:
        print(f"❌ Firecrawl SDK test failed: {str(e)}")
        return False

async def test_sitemap_crawler():
    """Test sitemap crawler integration."""
    print("Testing sitemap crawler...")
    
    try:
        async with SitemapCrawler() as crawler:
            urls = await crawler.parse_sitemap("https://www.judiciary.uk/sitemap_index.xml")
            print(f"✅ Sitemap crawler found {len(urls)} URLs")
            return True
    except Exception as e:
        print(f"❌ Sitemap crawler test failed: {str(e)}")
        return False

async def test_openai_client():
    """Test OpenAI client integration."""
    print("Testing OpenAI client...")
    
    try:
        async with OpenAIClient() as client:
            # Test with a simple request
            request = UrlAnalysisRequest(
                urls=["https://example.com/news", "https://example.com/blog"],
                site_name="Example Site"
            )
            
            # Note: This will make an actual API call, so it might cost money
            # Uncomment the following lines to test (be careful with API costs)
            # result = await client.analyze_urls(request, "Test prompt")
            # print(f"✅ OpenAI client test successful: {result}")
            
            print("✅ OpenAI client initialized successfully (API call skipped)")
            return True
    except Exception as e:
        print(f"❌ OpenAI client test failed: {str(e)}")
        return False

async def test_ai_models():
    """Test AI model structures."""
    print("Testing AI model structures...")
    
    try:
        # Test UrlAnalysisRequest
        analysis_request = UrlAnalysisRequest(
            urls=["https://example.com/news", "https://example.com/blog"],
            site_name="Example Site"
        )
        print(f"✅ Analysis request: {analysis_request.model_dump()}")
        
        # Test UrlJudgeRequest
        judge_request = UrlJudgeRequest(
            url_suggestions=[
                ["https://example.com/news", "https://example.com/blog"],
                ["https://example.com/news", "https://example.com/updates"]
            ],
            site_name="Example Site",
            selection_count=5
        )
        print(f"✅ Judge request: {judge_request.model_dump()}")
        
        return True
    except Exception as e:
        print(f"❌ AI models test failed: {str(e)}")
        return False

async def test_config_service():
    """Test configuration service."""
    print("Testing configuration service...")
    
    try:
        # Test getting all sites
        sites = config_service.all_sites
        print(f"✅ Found {len(sites)} sites in configuration")
        
        # Test getting a specific site
        site = config_service.site("judiciary_uk")
        if site:
            print(f"✅ Found site: {site.name}")
        else:
            print("❌ Site not found")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Configuration service test failed: {str(e)}")
        return False

async def test_all_components():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Configuration Service", test_config_service),
        ("AI Models", test_ai_models),
        ("Firecrawl SDK", test_firecrawl_sdk),
        ("Sitemap Crawler", test_sitemap_crawler),
        ("OpenAI Client", test_openai_client),
        ("Single Site Processing", test_single_site_processing),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    # Check if environment variables are set
    required_env_vars = ["FIRECRAWL_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        sys.exit(1)
    
    # Run tests
    success = asyncio.run(test_all_components())
    sys.exit(0 if success else 1)
