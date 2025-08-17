# ==============================================================================
# simple_crawler.py — Simple HTTP Crawler for Testing
# ==============================================================================
# Purpose: Simple HTTP crawler for testing pagination system
# ==============================================================================

import asyncio
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import aiohttp
import requests

# ==============================================================================
# Async HTTP Crawler
# ==============================================================================

class AsyncHTTPCrawler:
    """Asynchronous HTTP crawler using aiohttp."""
    
    def __init__(self, 
                 timeout: int = 30,
                 max_retries: int = 3,
                 delay_between_requests: float = 1.0,
                 user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"):
        
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        self.user_agent = user_agent
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Headers to mimic a real browser
        self.default_headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout_config = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            timeout=timeout_config,
            headers=self.default_headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def crawl_page(self, url: str) -> Optional[str]:
        """Crawl a single page and return HTML content."""
        
        if not self.session:
            raise RuntimeError("Crawler not initialized. Use async context manager.")
        
        for attempt in range(self.max_retries):
            try:
                print(f"🌐 Crawling {url} (attempt {attempt + 1})")
                
                async with self.session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        content = await response.text()
                        print(f"✅ Successfully crawled {url} ({len(content)} characters)")
                        
                        # Delay between requests to be respectful
                        if self.delay_between_requests > 0:
                            await asyncio.sleep(self.delay_between_requests)
                        
                        return content
                    else:
                        print(f"⚠️  HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                print(f"⏰ Timeout for {url} (attempt {attempt + 1})")
            except Exception as e:
                print(f"❌ Error crawling {url} (attempt {attempt + 1}): {str(e)}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
        print(f"❌ Failed to crawl {url} after {self.max_retries} attempts")
        return None
    
    async def crawl_multiple_pages(self, urls: list) -> Dict[str, Optional[str]]:
        """Crawl multiple pages concurrently."""
        
        if not self.session:
            raise RuntimeError("Crawler not initialized. Use async context manager.")
        
        print(f"🚀 Starting concurrent crawl of {len(urls)} pages...")
        
        # Create tasks for all URLs
        tasks = [self.crawl_page(url) for url in urls]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        page_contents = {}
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                print(f"❌ Exception for {url}: {str(result)}")
                page_contents[url] = None
            else:
                page_contents[url] = result
        
        return page_contents

# ==============================================================================
# Sync HTTP Crawler (Fallback)
# ==============================================================================

class SyncHTTPCrawler:
    """Synchronous HTTP crawler using requests (fallback)."""
    
    def __init__(self, 
                 timeout: int = 30,
                 max_retries: int = 3,
                 delay_between_requests: float = 1.0,
                 user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"):
        
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        self.user_agent = user_agent
        
        # Headers to mimic a real browser
        self.default_headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def crawl_page(self, url: str) -> Optional[str]:
        """Crawl a single page and return HTML content."""
        
        for attempt in range(self.max_retries):
            try:
                print(f"🌐 Crawling {url} (attempt {attempt + 1})")
                
                response = requests.get(
                    url, 
                    headers=self.default_headers, 
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    content = response.text
                    print(f"✅ Successfully crawled {url} ({len(content)} characters)")
                    
                    # Delay between requests to be respectful
                    if self.delay_between_requests > 0:
                        time.sleep(self.delay_between_requests)
                    
                    return content
                else:
                    print(f"⚠️  HTTP {response.status_code} for {url}")
                    
            except requests.Timeout:
                print(f"⏰ Timeout for {url} (attempt {attempt + 1})")
            except Exception as e:
                print(f"❌ Error crawling {url} (attempt {attempt + 1}): {str(e)}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        print(f"❌ Failed to crawl {url} after {self.max_retries} attempts")
        return None
    
    def crawl_multiple_pages(self, urls: list) -> Dict[str, Optional[str]]:
        """Crawl multiple pages sequentially."""
        
        print(f"🚀 Starting sequential crawl of {len(urls)} pages...")
        
        page_contents = {}
        for url in urls:
            content = self.crawl_page(url)
            page_contents[url] = content
        
        return page_contents

# ==============================================================================
# Crawler Factory
# ==============================================================================

def create_crawler(async_mode: bool = True, **kwargs) -> Any:
    """Create a crawler instance based on preference."""
    
    if async_mode:
        try:
            import aiohttp
            return AsyncHTTPCrawler(**kwargs)
        except ImportError:
            print("⚠️  aiohttp not available, falling back to sync crawler")
            return SyncHTTPCrawler(**kwargs)
    else:
        return SyncHTTPCrawler(**kwargs)

# ==============================================================================
# Utility Functions
# ==============================================================================

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def normalize_url(url: str) -> str:
    """Normalize URL for consistency."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.rstrip('/')

# ==============================================================================
# Example Usage
# ==============================================================================

async def example_async_crawl():
    """Example of async crawling."""
    
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/xml"
    ]
    
    async with AsyncHTTPCrawler(delay_between_requests=0.5) as crawler:
        results = await crawler.crawl_multiple_pages(urls)
        
        for url, content in results.items():
            if content:
                print(f"📄 {url}: {len(content)} characters")
            else:
                print(f"❌ {url}: Failed to crawl")

def example_sync_crawl():
    """Example of sync crawling."""
    
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/xml"
    ]
    
    crawler = SyncHTTPCrawler(delay_between_requests=0.5)
    results = crawler.crawl_multiple_pages(urls)
    
    for url, content in results.items():
        if content:
            print(f"📄 {url}: {len(content)} characters")
        else:
            print(f"❌ {url}: Failed to crawl")

if __name__ == "__main__":
    # Run examples
    print("🚀 Running async example...")
    asyncio.run(example_async_crawl())
    
    print("\n🚀 Running sync example...")
    example_sync_crawl()
