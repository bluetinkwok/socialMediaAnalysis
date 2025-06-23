"""
Rate Limiter - Controls request frequency to avoid being blocked
"""

import asyncio
import time
from typing import Dict, Optional
from datetime import datetime, timedelta


class RateLimiter:
    """
    Rate limiter to control request frequency and avoid being blocked by platforms
    """
    
    def __init__(self, delay: float = 2.0, burst_limit: int = 5, window_size: int = 60):
        """
        Initialize rate limiter
        
        Args:
            delay: Minimum delay between requests in seconds
            burst_limit: Maximum requests allowed in a time window
            window_size: Time window in seconds for burst limiting
        """
        self.delay = delay
        self.burst_limit = burst_limit
        self.window_size = window_size
        
        self.last_request_time = 0.0
        self.request_times: list = []
        self._lock = asyncio.Lock()
        
    async def wait(self):
        """Wait for the appropriate amount of time before making a request"""
        async with self._lock:
            current_time = time.time()
            
            # Clean old request times outside the window
            cutoff_time = current_time - self.window_size
            self.request_times = [t for t in self.request_times if t > cutoff_time]
            
            # Check burst limit
            if len(self.request_times) >= self.burst_limit:
                # Wait until the oldest request falls out of the window
                wait_time = self.request_times[0] + self.window_size - current_time + 0.1
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    current_time = time.time()
                    
            # Check minimum delay
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.delay:
                wait_time = self.delay - time_since_last
                await asyncio.sleep(wait_time)
                current_time = time.time()
                
            # Record this request
            self.last_request_time = current_time
            self.request_times.append(current_time)
            
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        current_time = time.time()
        cutoff_time = current_time - self.window_size
        recent_requests = [t for t in self.request_times if t > cutoff_time]
        
        return {
            'delay': self.delay,
            'burst_limit': self.burst_limit,
            'window_size': self.window_size,
            'requests_in_window': len(recent_requests),
            'time_since_last_request': current_time - self.last_request_time,
            'can_make_request_now': (
                len(recent_requests) < self.burst_limit and 
                (current_time - self.last_request_time) >= self.delay
            )
        }
        
    def reset(self):
        """Reset the rate limiter state"""
        self.last_request_time = 0.0
        self.request_times.clear()


class PlatformRateLimiter:
    """
    Manages rate limiters for different platforms
    """
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        
        # Default configurations for different platforms
        self.default_configs = {
            'youtube': {'delay': 1.0, 'burst_limit': 10, 'window_size': 60},
            'instagram': {'delay': 3.0, 'burst_limit': 5, 'window_size': 120},
            'threads': {'delay': 2.0, 'burst_limit': 8, 'window_size': 90},
            'rednote': {'delay': 4.0, 'burst_limit': 3, 'window_size': 180},
            'default': {'delay': 2.0, 'burst_limit': 5, 'window_size': 60}
        }
        
    def get_limiter(self, platform: str) -> RateLimiter:
        """Get or create a rate limiter for a platform"""
        platform = platform.lower()
        
        if platform not in self.limiters:
            config = self.default_configs.get(platform, self.default_configs['default'])
            self.limiters[platform] = RateLimiter(**config)
            
        return self.limiters[platform]
        
    async def wait_for_platform(self, platform: str):
        """Wait for the appropriate rate limit for a platform"""
        limiter = self.get_limiter(platform)
        await limiter.wait()
        
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all platform rate limiters"""
        return {
            platform: limiter.get_stats() 
            for platform, limiter in self.limiters.items()
        }
        
    def reset_platform(self, platform: str):
        """Reset rate limiter for a specific platform"""
        platform = platform.lower()
        if platform in self.limiters:
            self.limiters[platform].reset()
            
    def reset_all(self):
        """Reset all rate limiters"""
        for limiter in self.limiters.values():
            limiter.reset()


# Global platform rate limiter instance
platform_rate_limiter = PlatformRateLimiter() 