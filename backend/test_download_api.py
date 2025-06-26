#!/usr/bin/env python3
"""
Manual test script for download API endpoints
"""

import asyncio
import requests
import json
from api.v1.downloads import detect_platform_from_url, PLATFORM_DOWNLOADERS, PlatformType

async def test_platform_detection():
    """Test platform detection"""
    test_urls = [
        "https://www.threads.net/@test/post/123",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.instagram.com/p/ABC123/",
        "https://www.xiaohongshu.com/explore/123"
    ]
    
    for url in test_urls:
        platform = detect_platform_from_url(url)
        print(f"URL: {url}")
        print(f"Detected platform: {platform}")
        print()

def test_downloader_mapping():
    """Test downloader mapping"""
    print("Testing downloader mapping:")
    for platform, downloader_class in PLATFORM_DOWNLOADERS.items():
        print(f"Platform: {platform}")
        print(f"Downloader class: {downloader_class}")
        
        try:
            downloader = downloader_class()
            domains = downloader.get_platform_domains()
            print(f"Domains: {domains}")
            has_download = hasattr(downloader, 'download_content')
            print(f"Has download_content: {has_download}")
        except Exception as e:
            print(f"Error creating downloader: {e}")
        print()

def test_platforms_endpoint():
    """Test the platforms endpoint logic"""
    print("Testing platforms endpoint logic:")
    
    platforms_info = []
    
    for platform in PlatformType:
        print(f"Processing platform: {platform}")
        downloader_class = PLATFORM_DOWNLOADERS.get(platform)
        is_available = downloader_class is not None
        print(f"Is available: {is_available}")
        
        if is_available:
            # Get platform domains from downloader
            try:
                downloader = downloader_class()
                domains = downloader.get_platform_domains()
                supports_download = hasattr(downloader, 'download_content')
                print(f"Domains: {domains}")
                print(f"Supports download: {supports_download}")
                
                platforms_info.append({
                    "platform": platform.value,
                    "display_name": platform.value.title(),
                    "is_available": True,
                    "supported_domains": domains,
                    "supports_download": supports_download
                })
            except Exception as e:
                print(f"Error getting platform info: {e}")
                platforms_info.append({
                    "platform": platform.value,
                    "display_name": platform.value.title(),
                    "is_available": False,
                    "supported_domains": [],
                    "supports_download": False,
                    "error": str(e)
                })
        else:
            platforms_info.append({
                "platform": platform.value,
                "display_name": platform.value.title(),
                "is_available": False,
                "supported_domains": [],
                "supports_download": False
            })
        print()
    
    print("Final platforms info:")
    print(json.dumps(platforms_info, indent=2))

if __name__ == "__main__":
    print("=== Testing Platform Detection ===")
    asyncio.run(test_platform_detection())
    
    print("\n=== Testing Downloader Mapping ===")
    test_downloader_mapping()
    
    print("\n=== Testing Platforms Endpoint Logic ===")
    test_platforms_endpoint() 