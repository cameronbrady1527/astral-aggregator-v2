# ==============================================================================
# rate_limiter.py — Adaptive Rate Limiting Utility
# ==============================================================================
# Purpose: Intelligent rate limiting that adapts to API responses
# Sections: Imports, Rate Limiter Class, Helper Functions
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
import asyncio
import time
import random
from typing import List, Optional, Callable, Any
from collections import deque
from dataclasses import dataclass

# ==============================================================================
# Data Structures
# ==============================================================================

@dataclass
class RateLimitEvent:
    """Represents a rate limit event (success or failure)"""
    timestamp: float
    success: bool
    is_rate_limit: bool
    response_time: Optional[float] = None

# ==============================================================================
# Main Classes
# ==============================================================================

class AdaptiveRateLimiter:
    """
    Intelligent rate limiter that adapts to API responses.
    
    Features:
    - Tracks success/failure rates over time
    - Automatically adjusts delays based on rate limit responses
    - Implements exponential backoff with jitter
    - Maintains optimal throughput while respecting limits
    """
    
    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 10.0,
        window_size: int = 60,
        success_threshold: float = 0.8,
        rate_limit_threshold: float = 0.1
    ):
        """
        Initialize the adaptive rate limiter.
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            window_size: Time window in seconds to track events
            success_threshold: Success rate threshold to decrease delay
            rate_limit_threshold: Rate limit rate threshold to increase delay
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.window_size = window_size
        self.success_threshold = success_threshold
        self.rate_limit_threshold = rate_limit_threshold
        
        # Current delay state
        self.current_delay = min_delay
        self.base_delay = min_delay
        
        # Event tracking
        self.events: deque = deque()
        self.last_request_time = 0.0
        
        # Rate limit tracking
        self.rate_limit_count = 0
        self.total_requests = 0
        
    def record_event(self, success: bool, is_rate_limit: bool = False, response_time: Optional[float] = None):
        """
        Record a request event for rate limiting analysis.
        
        Args:
            success: Whether the request was successful
            is_rate_limit: Whether this was a rate limit error
            response_time: Response time in seconds (optional)
        """
        now = time.time()
        event = RateLimitEvent(
            timestamp=now,
            success=success,
            is_rate_limit=is_rate_limit,
            response_time=response_time
        )
        
        self.events.append(event)
        self.total_requests += 1
        
        if is_rate_limit:
            self.rate_limit_count += 1
        
        # Clean up old events outside the window
        self._cleanup_old_events(now)
        
        # Adjust delay based on recent events
        self._adjust_delay()
        
    def get_delay(self) -> float:
        """
        Get the current delay to use before the next request.
        
        Returns:
            Delay in seconds
        """
        now = time.time()
        time_since_last = now - self.last_request_time
        
        # If we haven't waited long enough, return remaining time
        if time_since_last < self.current_delay:
            return self.current_delay - time_since_last
        
        # Update last request time and return current delay
        self.last_request_time = now
        return 0.0
    
    async def wait_if_needed(self):
        """Wait for the appropriate delay if needed."""
        delay = self.get_delay()
        if delay > 0:
            await asyncio.sleep(delay)
    
    def _cleanup_old_events(self, current_time: float):
        """Remove events outside the tracking window."""
        cutoff_time = current_time - self.window_size
        while self.events and self.events[0].timestamp < cutoff_time:
            self.events.popleft()
    
    def _adjust_delay(self):
        """Adjust the current delay based on recent event patterns."""
        if not self.events:
            return
        
        # Calculate success and rate limit rates in the window
        window_events = list(self.events)
        success_count = sum(1 for e in window_events if e.success)
        rate_limit_count = sum(1 for e in window_events if e.is_rate_limit)
        total_in_window = len(window_events)
        
        if total_in_window == 0:
            return
        
        success_rate = success_count / total_in_window
        rate_limit_rate = rate_limit_count / total_in_window
        
        # Adjust delay based on patterns
        if rate_limit_rate > self.rate_limit_threshold:
            # Too many rate limits - increase delay
            self._increase_delay()
        elif success_rate > self.success_threshold and rate_limit_rate < 0.05:
            # High success rate, low rate limits - decrease delay
            self._decrease_delay()
    
    def _increase_delay(self):
        """Increase the current delay using exponential backoff with jitter."""
        # Exponential backoff
        self.current_delay = min(
            self.current_delay * 1.5,
            self.max_delay
        )
        
        # Add jitter (±20% of current delay)
        jitter = random.uniform(0.8, 1.2)
        self.current_delay *= jitter
        
        # Ensure we stay within bounds
        self.current_delay = max(self.min_delay, min(self.current_delay, self.max_delay))
        
        print(f"🔍 Rate limiter: Increased delay to {self.current_delay:.2f}s (rate limit detected)")
    
    def _decrease_delay(self):
        """Decrease the current delay gradually."""
        # Gradual decrease
        self.current_delay = max(
            self.current_delay * 0.9,
            self.min_delay
        )
        
        print(f"🔍 Rate limiter: Decreased delay to {self.current_delay:.2f}s (good performance)")
    
    def get_stats(self) -> dict:
        """Get current rate limiting statistics."""
        return {
            "current_delay": self.current_delay,
            "total_requests": self.total_requests,
            "rate_limit_count": self.rate_limit_count,
            "success_rate": self._calculate_success_rate(),
            "rate_limit_rate": self._calculate_rate_limit_rate(),
            "events_in_window": len(self.events)
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_requests - self.rate_limit_count) / self.total_requests
    
    def _calculate_rate_limit_rate(self) -> float:
        """Calculate overall rate limit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.rate_limit_count / self.total_requests

# ==============================================================================
# Helper Functions
# ==============================================================================

def create_rate_limiter_from_config(config_service) -> AdaptiveRateLimiter:
    """
    Create a rate limiter instance from configuration.
    
    Args:
        config_service: Configuration service instance
        
    Returns:
        Configured AdaptiveRateLimiter instance
    """
    return AdaptiveRateLimiter(
        min_delay=config_service.firecrawl_min_delay,
        max_delay=config_service.firecrawl_max_delay,
        window_size=config_service.firecrawl_rate_limit_window
    )

async def process_with_rate_limiting(
    items: List[Any],
    processor: Callable[[Any], Any],
    rate_limiter: AdaptiveRateLimiter,
    batch_size: int = 3
) -> List[Any]:
    """
    Process items with intelligent rate limiting and batching.
    
    Args:
        items: List of items to process
        processor: Async function to process each item
        rate_limiter: Rate limiter instance
        batch_size: Number of items to process in each batch
        
    Returns:
        List of processed results
    """
    results = []
    
    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        print(f"🔍 Processing batch {i//batch_size + 1}/{(len(items) + batch_size - 1)//batch_size} ({len(batch)} items)")
        
        # Step 1: Process batch concurrently
        batch_tasks = []
        for item in batch:
            # Wait for rate limiter before starting each task
            await rate_limiter.wait_if_needed()
            task = asyncio.create_task(processor(item))
            batch_tasks.append(task)
        
        # Step 2: Wait for batch to complete
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Step 3: Process results and record events
        for result in batch_results:
            if isinstance(result, Exception):
                # Check if it's a rate limit error
                is_rate_limit = "429" in str(result) or "rate limit" in str(result).lower()
                rate_limiter.record_event(success=False, is_rate_limit=is_rate_limit)
                results.append(None)  # or handle error as needed
            else:
                rate_limiter.record_event(success=True)
                results.append(result)
        
        # Small delay between batches
        if i + batch_size < len(items):
            await asyncio.sleep(0.5)
    
    return results
