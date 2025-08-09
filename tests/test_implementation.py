# ==============================================================================
# test_implementation.py — Quick implementation test
# ==============================================================================
# Purpose: Test the implementation without running full integration tests
# ==============================================================================

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("Testing imports...")
    
    try:
        from app.services.config_service import config_service
        print("✅ Config service imported")
        
        from app.models.url_models import UrlInfo, DetectionMethod
        print("✅ URL models imported")
        
        from app.models.config_models import SiteConfig
        print("✅ Config models imported")
        
        from app.clients.firecrawl_client import FirecrawlClient
        print("✅ Firecrawl client imported")
        
        from app.clients.openai_client import OpenAIClient
        print("✅ OpenAI client imported")
        
        from app.crawler.sitemap_crawler import SitemapCrawler
        print("✅ Sitemap crawler imported")
        
        from app.ai.config import AIConfig
        print("✅ AI config imported")
        
        from app.services.url_service import UrlService, OnboardingUrlService
        print("✅ URL service imported")
        
        from app.routers.url_router import router
        print("✅ URL router imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        return False

def test_config_service():
    """Test configuration service functionality."""
    print("\nTesting configuration service...")
    
    try:
        from app.services.config_service import config_service
        
        # Test getting all sites
        sites = config_service.all_sites
        print(f"✅ Found {len(sites)} sites in configuration")
        
        # Test getting a specific site
        site = config_service.site("judiciary_uk")
        if site:
            print(f"✅ Found site: {site.name}")
            print(f"   URL: {site.url}")
            print(f"   Sitemap: {site.sitemap_url}")
            print(f"   Is index: {site.is_sitemap_index}")
            print(f"   Onboarded: {site.onboarded}")
        else:
            print("❌ Site not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration service test failed: {str(e)}")
        return False

def test_models():
    """Test model creation and validation."""
    print("\nTesting models...")
    
    try:
        from app.models.url_models import UrlInfo, DetectionMethod, UrlAnalysisRequest, UrlJudgeRequest
        from app.models.config_models import SiteConfig
        from datetime import datetime
        
        # Test UrlInfo creation
        url_info = UrlInfo(
            url="https://example.com",
            detection_methods=[DetectionMethod.SITEMAP],
            detected_at=datetime.now()
        )
        print("✅ UrlInfo created successfully")
        
        # Test UrlAnalysisRequest
        analysis_request = UrlAnalysisRequest(
            urls=["https://example.com/news", "https://example.com/blog"],
            site_name="Example Site"
        )
        print("✅ UrlAnalysisRequest created successfully")
        
        # Test UrlJudgeRequest
        judge_request = UrlJudgeRequest(
            url_suggestions=[
                ["https://example.com/news", "https://example.com/blog"],
                ["https://example.com/news", "https://example.com/updates"]
            ],
            site_name="Example Site",
            selection_count=5
        )
        print("✅ UrlJudgeRequest created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Models test failed: {str(e)}")
        return False

def test_ai_config():
    """Test AI configuration."""
    print("\nTesting AI configuration...")
    
    try:
        from app.ai.config import AIConfig
        from app.models.url_models import UrlAnalysisRequest, UrlJudgeRequest
        
        # Test analysis prompt
        analysis_request = UrlAnalysisRequest(
            urls=["https://example.com/news", "https://example.com/blog"],
            site_name="Example Site"
        )
        prompt = AIConfig.build_analysis_prompt(analysis_request)
        print("✅ Analysis prompt built successfully")
        
        # Test judge prompt
        judge_request = UrlJudgeRequest(
            url_suggestions=[
                ["https://example.com/news", "https://example.com/blog"],
                ["https://example.com/news", "https://example.com/updates"]
            ],
            site_name="Example Site",
            selection_count=5
        )
        prompt = AIConfig.build_judge_prompt(judge_request)
        print("✅ Judge prompt built successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ AI config test failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Implementation Verification Tests")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration Service", test_config_service),
        ("Models", test_models),
        ("AI Configuration", test_ai_config),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
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
        print("🎉 All tests passed! Implementation is ready.")
        print("\nTo run the full integration tests (with API calls), use:")
        print("python tests/test_integration.py")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    # Check if environment variables are set
    required_env_vars = ["FIRECRAWL_API_KEY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️  Missing environment variables (but continuing with basic tests):")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nSome tests may fail without these variables set.")
        print("Set them in your .env file or environment for full functionality.")
    
    # Run tests
    success = main()
    sys.exit(0 if success else 1)
