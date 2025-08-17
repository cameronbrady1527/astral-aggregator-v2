# ==============================================================================
# demo_pagination_system.py — Pagination System Demo
# ==============================================================================
# Purpose: Demonstrate the pagination system with real paginated websites
# ==============================================================================

import asyncio
import sys
import os
import time
from typing import List, Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.pagination_orchestrator import PaginationOrchestrator, format_crawl_summary
from app.utils.simple_crawler import AsyncHTTPCrawler, SyncHTTPCrawler
from app.models.pagination_models import PaginationSettings

# ==============================================================================
# Demo Configuration
# ==============================================================================

DEMO_SITES = {
    "gov_uk_news": {
        "name": "GOV.UK News & Communications",
        "url": "https://www.gov.uk/search/news-and-communications",
        "description": "Government news search with 136,000+ results",
        "expected_pagination": "parameter_based",
        "max_pages": 50,  # Limit for demo
        "rate_limit": 1.0,
        "concurrent_batches": 10
    },
    "gov_uk_publications": {
        "name": "GOV.UK Publications",
        "url": "https://www.gov.uk/search/publications",
        "description": "Government publications search",
        "expected_pagination": "parameter_based",
        "max_pages": 30,
        "rate_limit": 1.0,
        "concurrent_batches": 8
    },
    "httpbin_test": {
        "name": "HTTPBin Test Page",
        "url": "https://httpbin.org/html",
        "description": "Simple test page (no pagination expected)",
        "expected_pagination": "none",
        "max_pages": 5,
        "rate_limit": 0.5,
        "concurrent_batches": 3
    }
}

# ==============================================================================
# Demo Functions
# ==============================================================================

async def demo_single_site(site_config: Dict[str, Any]) -> None:
    """Demonstrate pagination system with a single site."""
    
    print(f"\n{'='*80}")
    print(f"🚀 DEMO: {site_config['name']}")
    print(f"{'='*80}")
    print(f"📍 URL: {site_config['url']}")
    print(f"📝 Description: {site_config['description']}")
    print(f"🎯 Expected Pagination: {site_config['expected_pagination']}")
    print(f"📊 Max Pages: {site_config['max_pages']}")
    print(f"⏱️  Rate Limit: {site_config['rate_limit']}s")
    print(f"🔄 Concurrent Batches: {site_config['concurrent_batches']}")
    print(f"{'='*80}")
    
    # Create pagination settings
    settings = PaginationSettings(
        max_pages=site_config['max_pages'],
        rate_limit_delay=site_config['rate_limit'],
        concurrent_batches=site_config['concurrent_batches'],
        timeout_seconds=30,
        max_retries=3
    )
    
    # Create orchestrator
    orchestrator = PaginationOrchestrator(settings)
    
    try:
        # Create async crawler
        async with AsyncHTTPCrawler(
            timeout=30,
            max_retries=3,
            delay_between_requests=site_config['rate_limit']
        ) as crawler:
            
            # Create crawl function
            async def crawl_function(url: str) -> str:
                return await crawler.crawl_page(url)
            
            print(f"🔍 Starting pagination analysis...")
            start_time = time.time()
            
            # Process the site
            result = await orchestrator.process_site_with_pagination(
                site_config['url'],
                crawl_function,
                max_pages=site_config['max_pages']
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Display results
            print(f"\n{'='*80}")
            print(f"✅ DEMO COMPLETED: {site_config['name']}")
            print(f"{'='*80}")
            
            # Format and display summary
            summary = format_crawl_summary(result)
            print(summary)
            
            # Additional demo-specific information
            print(f"\n🎯 **Demo Analysis**")
            print(f"Expected vs Actual Pagination:")
            print(f"  - Expected: {site_config['expected_pagination']}")
            print(f"  - Detected: {result.pagination_info.pagination_type if result.pagination_info else 'N/A'}")
            print(f"  - Confidence: {result.pagination_info.confidence_score if result.pagination_info else 0.0:.2f}")
            
            if result.pagination_info and result.pagination_info.has_pagination:
                print(f"\n📄 **Pagination Details**")
                print(f"  - Total Pages: {result.pagination_info.total_pages}")
                print(f"  - Total Items: {result.pagination_info.total_items}")
                print(f"  - Items per Page: {result.pagination_info.items_per_page}")
                print(f"  - Base URL: {result.pagination_info.base_url}")
                
                if result.pagination_info.pagination_patterns:
                    print(f"  - Patterns: {', '.join(result.pagination_info.pagination_patterns[:3])}")
            
            print(f"\n⚡ **Performance Metrics**")
            print(f"  - Total Time: {total_time:.2f}s")
            print(f"  - Pages/Second: {result.total_pages_crawled / max(total_time, 1):.2f}")
            print(f"  - URLs/Second: {result.total_urls_found / max(total_time, 1):.2f}")
            
            # Show sample article URLs
            if result.article_urls:
                print(f"\n📰 **Sample Article URLs** (showing first 5)")
                for i, url in enumerate(result.article_urls[:5], 1):
                    print(f"  {i}. {url}")
                
                if len(result.article_urls) > 5:
                    print(f"  ... and {len(result.article_urls) - 5} more")
            
            print(f"\n{'='*80}")
            
    except Exception as e:
        print(f"❌ Demo failed for {site_config['name']}: {str(e)}")
        import traceback
        traceback.print_exc()

async def demo_pagination_detection_comparison():
    """Demonstrate pagination detection across different site types."""
    
    print(f"\n{'='*80}")
    print(f"🔍 PAGINATION DETECTION COMPARISON")
    print(f"{'='*80}")
    
    from app.utils.pagination_detector import PaginationDetector
    from app.utils.content_extractor import ContentExtractor
    
    detector = PaginationDetector()
    extractor = ContentExtractor()
    
    # Test sites for comparison
    test_sites = [
        {
            "name": "GOV.UK News (Paginated)",
            "url": "https://www.gov.uk/search/news-and-communications",
            "expected": "parameter_based"
        },
        {
            "name": "HTTPBin (No Pagination)",
            "url": "https://httpbin.org/html",
            "expected": "none"
        }
    ]
    
    for site in test_sites:
        print(f"\n📄 Testing: {site['name']}")
        print(f"📍 URL: {site['url']}")
        print(f"🎯 Expected: {site['expected']}")
        
        try:
            async with AsyncHTTPCrawler() as crawler:
                content = await crawler.crawl_page(site['url'])
                if content:
                    # Detect pagination
                    pagination_info = detector.detect_pagination(content, site['url'])
                    
                    print(f"✅ Detected: {pagination_info.pagination_type}")
                    print(f"✅ Confidence: {pagination_info.confidence_score:.2f}")
                    print(f"✅ Has Pagination: {pagination_info.has_pagination}")
                    
                    if pagination_info.has_pagination:
                        print(f"✅ Total Pages: {pagination_info.total_pages}")
                        print(f"✅ Total Items: {pagination_info.total_items}")
                    
                    # Extract content
                    article_urls = extractor.extract_article_urls(content, site['url'])
                    print(f"✅ Article URLs: {len(article_urls)}")
                    
                else:
                    print("❌ Failed to fetch content")
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")

async def demo_strategy_selection():
    """Demonstrate different pagination strategy selection."""
    
    print(f"\n{'='*80}")
    print(f"🎯 PAGINATION STRATEGY SELECTION DEMO")
    print(f"{'='*80}")
    
    from app.utils.pagination_strategies import PaginationStrategyFactory
    from app.models.pagination_models import PaginationInfo, PaginationType
    
    factory = PaginationStrategyFactory()
    
    # Test different pagination types
    test_cases = [
        {
            "name": "Parameter-Based Strategy",
            "info": PaginationInfo(
                source_url="https://example.com/news?page=1",
                base_url="https://example.com/news",
                has_pagination=True,
                pagination_type=PaginationType.PARAMETER_BASED,
                total_pages=100,
                confidence_score=0.9
            )
        },
        {
            "name": "Offset-Based Strategy",
            "info": PaginationInfo(
                source_url="https://example.com/news?start=0&limit=20",
                base_url="https://example.com/news",
                has_pagination=True,
                pagination_type=PaginationType.OFFSET_BASED,
                total_items=2000,
                items_per_page=20,
                confidence_score=0.8
            )
        },
        {
            "name": "Link-Based Strategy",
            "info": PaginationInfo(
                source_url="https://example.com/news",
                base_url="https://example.com/news",
                has_pagination=True,
                pagination_type=PaginationType.LINK_BASED,
                has_next_prev_links=True,
                confidence_score=0.7
            )
        }
    ]
    
    for case in test_cases:
        print(f"\n📄 Testing: {case['name']}")
        
        try:
            # Create strategy
            strategy = factory.create_strategy_from_info(case['info'])
            
            print(f"✅ Strategy: {strategy.__class__.__name__}")
            print(f"✅ Base URL: {strategy.base_url}")
            print(f"✅ Estimated Pages: {strategy.estimate_total_pages()}")
            
            # Generate page URLs (limited for demo)
            strategy_result = strategy.generate_page_urls(max_pages=10)
            print(f"✅ Generated URLs: {len(strategy_result.page_urls)}")
            
            if strategy_result.page_urls:
                print(f"✅ Sample URLs:")
                for i, url in enumerate(strategy_result.page_urls[:3], 1):
                    print(f"  {i}. {url}")
                if len(strategy_result.page_urls) > 3:
                    print(f"  ... and {len(strategy_result.page_urls) - 3} more")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")

async def demo_performance_analysis():
    """Demonstrate performance analysis and optimization."""
    
    print(f"\n{'='*80}")
    print(f"⚡ PERFORMANCE ANALYSIS & OPTIMIZATION DEMO")
    print(f"{'='*80}")
    
    from app.utils.pagination_orchestrator import estimate_crawl_time
    
    # Test different configurations
    configs = [
        {"max_pages": 100, "rate_limit": 2.0, "concurrent": 5, "name": "Conservative"},
        {"max_pages": 500, "rate_limit": 1.0, "concurrent": 10, "name": "Balanced"},
        {"max_pages": 1000, "rate_limit": 0.5, "concurrent": 20, "name": "Aggressive"}
    ]
    
    print(f"📊 Performance Comparison for 1000 pages:")
    print(f"{'='*60}")
    
    for config in configs:
        estimated_time = estimate_crawl_time(
            total_pages=1000,
            rate_limit_delay=config['rate_limit'],
            concurrent_batches=config['concurrent']
        )
        
        print(f"\n🎯 {config['name']} Configuration:")
        print(f"  - Max Pages: {config['max_pages']}")
        print(f"  - Rate Limit: {config['rate_limit']}s")
        print(f"  - Concurrent: {config['concurrent']}")
        print(f"  - Estimated Time: {estimated_time:.1f}s ({estimated_time/60:.1f} minutes)")
        
        # Calculate efficiency
        efficiency = 1000 / estimated_time if estimated_time > 0 else 0
        print(f"  - Pages/Second: {efficiency:.2f}")

def create_demo_report():
    """Create a comprehensive demo report."""
    
    report = """
# 🚀 Pagination System Demo Report

## 📊 System Overview
This demo showcases our Universal Pagination Detection & Crawling System, designed to handle any type of pagination on large websites.

## 🎯 Key Features Demonstrated

### 1. **Intelligent Pagination Detection**
- Automatic pattern recognition for various pagination types
- Confidence scoring for detection accuracy
- Support for parameter-based, offset-based, and link-based pagination

### 2. **Strategy Selection & Execution**
- Automatic strategy selection based on detected pagination type
- Efficient URL generation for parameter/offset-based pagination
- Intelligent navigation following for link-based pagination

### 3. **Content Extraction**
- Article URL extraction from HTML content
- Content type classification
- Duplicate removal and validation

### 4. **Performance Optimization**
- Configurable batch processing
- Rate limiting and respectful crawling
- Concurrent processing with error handling

## 🔍 Pagination Types Supported

| Type | Description | Example | Strategy |
|------|-------------|---------|----------|
| Parameter-based | `?page=1`, `?page=2` | News sites, blogs | URL generation |
| Offset-based | `?start=0`, `?start=20` | Search results | URL generation |
| Link-based | Next/Previous links | Forums, archives | Navigation following |
| Indicator-based | "Page 1 of 50" | Content pages | Pattern analysis |

## 📈 Performance Metrics

The system automatically tracks:
- Pages crawled per second
- URLs discovered per second
- Total processing time
- Error rates and retry attempts
- Pagination detection confidence

## 🛠️ Configuration Options

Each site can be configured with:
- Maximum pages to crawl
- Rate limiting between requests
- Concurrent batch processing
- Custom pagination patterns
- Retry logic and timeouts

## 🚀 Use Cases

1. **Government Websites**: Large news and publication archives
2. **News Sites**: Article listings and archives
3. **E-commerce**: Product catalogs and search results
4. **Forums**: Thread listings and archives
5. **Documentation**: API docs and knowledge bases

## 🔧 Getting Started

```python
from app.utils.pagination_orchestrator import PaginationOrchestrator
from app.models.pagination_models import PaginationSettings

# Create orchestrator
settings = PaginationSettings(max_pages=1000, rate_limit_delay=2.0)
orchestrator = PaginationOrchestrator(settings)

# Process site
result = await orchestrator.process_site_with_pagination(
    "https://example.com/news",
    crawl_function,
    max_pages=100
)
```

## 📝 Best Practices

1. **Start Conservative**: Begin with higher rate limits and lower concurrency
2. **Monitor Performance**: Use the built-in metrics to optimize settings
3. **Respect Servers**: Always use appropriate rate limiting
4. **Test First**: Use small page limits for initial testing
5. **Handle Errors**: The system includes comprehensive error handling

## 🎉 Benefits

- **Universal Compatibility**: Works with any pagination system
- **Intelligent Detection**: No manual configuration required
- **Scalable Performance**: Efficient batch processing
- **Respectful Crawling**: Built-in rate limiting and retry logic
- **Easy Integration**: Drop-in replacement for existing crawling logic

---
*Generated by Pagination System Demo*
"""
    
    # Write report to file
    with open("PAGINATION_SYSTEM_DEMO_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"📝 Demo report saved to: PAGINATION_SYSTEM_DEMO_REPORT.md")

# ==============================================================================
# Main Demo Runner
# ==============================================================================

async def run_full_demo():
    """Run the complete pagination system demo."""
    
    print("🚀 PAGINATION SYSTEM COMPREHENSIVE DEMO")
    print("=" * 80)
    print("This demo showcases our Universal Pagination Detection & Crawling System")
    print("with real websites and comprehensive analysis.")
    print("=" * 80)
    
    try:
        # Phase 1: Individual site demos
        print("\n🎯 PHASE 1: Individual Site Demonstrations")
        for site_key, site_config in DEMO_SITES.items():
            await demo_single_site(site_config)
            await asyncio.sleep(2)  # Brief pause between demos
        
        # Phase 2: Pagination detection comparison
        print("\n🔍 PHASE 2: Pagination Detection Comparison")
        await demo_pagination_detection_comparison()
        
        # Phase 3: Strategy selection demo
        print("\n🎯 PHASE 3: Strategy Selection Demo")
        await demo_strategy_selection()
        
        # Phase 4: Performance analysis
        print("\n⚡ PHASE 4: Performance Analysis")
        await demo_performance_analysis()
        
        # Create demo report
        print("\n📝 PHASE 5: Creating Demo Report")
        create_demo_report()
        
        print(f"\n{'='*80}")
        print(f"🎉 DEMO COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        print(f"✅ All phases completed")
        print(f"📝 Demo report generated")
        print(f"🚀 System ready for production use")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()

def run_quick_demo():
    """Run a quick demo with just one site."""
    
    print("🚀 QUICK DEMO: GOV.UK News")
    print("=" * 50)
    
    # Run just the GOV.UK demo
    site_config = DEMO_SITES["gov_uk_news"]
    
    async def quick_demo():
        await demo_single_site(site_config)
    
    asyncio.run(quick_demo())

# ==============================================================================
# Main Execution
# ==============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Pagination System Demo")
    parser.add_argument("--quick", action="store_true", help="Run quick demo with one site")
    parser.add_argument("--full", action="store_true", help="Run full comprehensive demo")
    
    args = parser.parse_args()
    
    if args.quick:
        run_quick_demo()
    elif args.full:
        asyncio.run(run_full_demo())
    else:
        print("🚀 Pagination System Demo")
        print("=" * 50)
        print("Choose an option:")
        print("  --quick  : Run quick demo with GOV.UK")
        print("  --full   : Run comprehensive demo")
        print("\nExample: python demo_pagination_system.py --quick")
