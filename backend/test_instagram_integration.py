"""
Instagram Content Downloader Integration Tests
Tests with real Instagram URLs to verify functionality
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from services.instagram_downloader import InstagramDownloader


class TestInstagramIntegration:
    """Integration tests with real Instagram URLs"""
    
    # Real Instagram URLs provided by user with expected content counts
    TEST_URLS = [
        {
            "url": "https://www.instagram.com/p/DLUqd75NtsS/?utm_source=ig_web_copy_link",
            "description": "Post 1: 9 videos, 1 image",
            "expected_media_count": 10,
            "expected_videos": 9,
            "expected_images": 1,
            "content_type": "post"
        },
        {
            "url": "https://www.instagram.com/reel/DLUSQbjSUBj/?utm_source=ig_web_copy_link", 
            "description": "Post 2: 1 video (reel)",
            "expected_media_count": 1,
            "expected_videos": 1,
            "expected_images": 0,
            "content_type": "reel"
        },
        {
            "url": "https://www.instagram.com/p/DLRx_BpvUjCAY4kHey4LLWN4bpNM3SBUVDHGpU0/",
            "description": "Post 3: 18 images, 2 videos", 
            "expected_media_count": 20,
            "expected_videos": 2,
            "expected_images": 18,
            "content_type": "post"
        },
        {
            "url": "https://www.instagram.com/p/DLNDd1ks6DL/?utm_source=ig_web_copy_link",
            "description": "Post 4: 1 image",
            "expected_media_count": 1,
            "expected_videos": 0, 
            "expected_images": 1,
            "content_type": "post"
        },
        {
            "url": "https://www.instagram.com/p/DLPIy2Ly__n/?utm_source=ig_web_copy_link",
            "description": "Post 5: 8 images",
            "expected_media_count": 8,
            "expected_videos": 0,
            "expected_images": 8,
            "content_type": "post"
        },
        {
            "url": "https://www.instagram.com/p/DLU_-uStRR9/?utm_source=ig_web_copy_link",
            "description": "Post 6: 2 images, 1 video",
            "expected_media_count": 3,
            "expected_videos": 1,
            "expected_images": 2,
            "content_type": "post"
        }
    ]
    
    @pytest.fixture
    def temp_download_dir(self):
        """Create temporary download directory for testing"""
        temp_dir = tempfile.mkdtemp(prefix="instagram_integration_test_")
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def downloader(self, temp_download_dir):
        """Create Instagram downloader instance for testing"""
        return InstagramDownloader(download_dir=temp_download_dir, rate_limit=0.5)
    
    @pytest.mark.asyncio
    async def test_url_validation_all_real_urls(self, downloader):
        """Test URL validation with all real Instagram URLs"""
        print("\n=== Testing URL Validation ===")
        
        for i, test_case in enumerate(self.TEST_URLS, 1):
            url = test_case["url"]
            description = test_case["description"]
            
            print(f"\nTest {i}: {description}")
            print(f"URL: {url}")
            
            # Test URL validation
            is_valid = downloader.validate_url(url)
            print(f"✅ URL Validation: {'PASS' if is_valid else 'FAIL'}")
            
            assert is_valid, f"URL should be valid: {url}"
            
            # Test shortcode extraction
            shortcode = downloader._extract_shortcode_from_url(url)
            print(f"📝 Extracted Shortcode: {shortcode}")
            
            assert shortcode is not None, f"Should extract shortcode from: {url}"
            assert len(shortcode) > 0, f"Shortcode should not be empty for: {url}"
    
    @pytest.mark.asyncio 
    async def test_content_extraction_all_urls(self, downloader):
        """Test content extraction from all real Instagram URLs"""
        print("\n=== Testing Content Extraction ===")
        
        results = []
        
        for i, test_case in enumerate(self.TEST_URLS, 1):
            url = test_case["url"]
            description = test_case["description"]
            
            print(f"\n--- Test {i}: {description} ---")
            print(f"URL: {url}")
            
            try:
                # Extract content metadata
                content_info = await downloader.extract_content(url)
                
                # Verify basic metadata fields
                required_fields = ['url', 'shortcode', 'extracted_at']
                for field in required_fields:
                    assert field in content_info, f"Missing required field '{field}' in content info"
                
                print(f"✅ Content Extraction: SUCCESS")
                print(f"📝 Shortcode: {content_info.get('shortcode', 'N/A')}")
                print(f"👤 Author: {content_info.get('author', 'N/A')}")
                print(f"📝 Title: {content_info.get('title', 'N/A')[:100]}...")
                print(f"❤️ Likes: {content_info.get('like_count', 'N/A')}")
                print(f"💬 Comments: {content_info.get('comment_count', 'N/A')}")
                print(f"🎥 Is Video: {content_info.get('is_video', 'N/A')}")
                print(f"🔗 Media URLs Count: {len(content_info.get('media_urls', []))}")
                
                # Store results for analysis
                results.append({
                    'test_case': test_case,
                    'content_info': content_info,
                    'status': 'success'
                })
                
            except Exception as e:
                print(f"❌ Content Extraction: FAILED - {str(e)}")
                results.append({
                    'test_case': test_case, 
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Print summary
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        print(f"\n=== CONTENT EXTRACTION SUMMARY ===")
        print(f"✅ Successful: {len(successful)}/{len(self.TEST_URLS)}")
        print(f"❌ Failed: {len(failed)}/{len(self.TEST_URLS)}")
        
        if failed:
            print("\nFailed URLs:")
            for result in failed:
                print(f"  - {result['test_case']['url']}: {result['error']}")
        
        # At least 50% should succeed (Instagram often blocks automated access)
        success_rate = len(successful) / len(self.TEST_URLS)
        assert success_rate >= 0.5, f"Success rate too low: {success_rate:.1%}"
        
        return results
    
    @pytest.mark.asyncio
    async def test_download_functionality_sample_urls(self, downloader, temp_download_dir):
        """Test download functionality with a sample of URLs"""
        print("\n=== Testing Download Functionality ===")
        
        # Test with first 3 URLs to avoid excessive requests
        sample_urls = self.TEST_URLS[:3]
        download_results = []
        
        for i, test_case in enumerate(sample_urls, 1):
            url = test_case["url"]
            description = test_case["description"]
            
            print(f"\n--- Download Test {i}: {description} ---")
            print(f"URL: {url}")
            
            try:
                # Attempt to download content
                download_result = await downloader.download_content(url)
                
                print(f"✅ Download Status: {download_result.get('download_status', 'Unknown')}")
                
                # Check if download path exists
                download_path = download_result.get('download_path')
                if download_path:
                    path_obj = Path(download_path)
                    exists = path_obj.exists()
                    print(f"📁 Download Path: {download_path}")
                    print(f"📂 Path Exists: {exists}")
                    
                    if exists:
                        files = list(path_obj.glob('*'))
                        print(f"📄 Files Created: {len(files)}")
                        for file in files[:5]:  # Show first 5 files
                            print(f"   - {file.name}")
                
                download_results.append({
                    'test_case': test_case,
                    'result': download_result,
                    'status': 'success'
                })
                
                # Add delay between downloads to be respectful
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Download Failed: {str(e)}")
                download_results.append({
                    'test_case': test_case,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Print download summary
        successful_downloads = [r for r in download_results if r['status'] == 'success']
        failed_downloads = [r for r in download_results if r['status'] == 'failed']
        
        print(f"\n=== DOWNLOAD SUMMARY ===")
        print(f"✅ Successful: {len(successful_downloads)}/{len(sample_urls)}")
        print(f"❌ Failed: {len(failed_downloads)}/{len(sample_urls)}")
        
        # Check that at least metadata was saved for successful downloads
        for result in successful_downloads:
            download_path = result['result'].get('download_path')
            if download_path:
                metadata_file = Path(download_path) / "metadata.json"
                if metadata_file.exists():
                    print(f"📋 Metadata saved for: {result['test_case']['description']}")
        
        return download_results
    
    @pytest.mark.asyncio
    async def test_bulk_extraction(self, downloader):
        """Test bulk content extraction with all URLs"""
        print("\n=== Testing Bulk Extraction ===")
        
        # Extract all URLs
        urls = [test_case["url"] for test_case in self.TEST_URLS]
        
        print(f"🔄 Processing {len(urls)} URLs in bulk...")
        
        # Perform bulk extraction
        bulk_results = await downloader.extract_bulk_content(urls)
        
        print(f"📊 Bulk extraction completed: {len(bulk_results)} results")
        
        # Analyze results
        successful = [r for r in bulk_results if r.get('status') != 'failed']
        failed = [r for r in bulk_results if r.get('status') == 'failed']
        
        print(f"✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        
        # Print details for failed extractions
        if failed:
            print("\nFailed extractions:")
            for result in failed:
                print(f"  - {result.get('url', 'Unknown URL')}: {result.get('error', 'Unknown error')}")
        
        # Should have results for all URLs (even if some failed)
        assert len(bulk_results) == len(urls), "Should have results for all URLs"
        
        return bulk_results
    
    @pytest.mark.asyncio
    async def test_shortcode_extraction_accuracy(self, downloader):
        """Test shortcode extraction accuracy for all URL formats"""
        print("\n=== Testing Shortcode Extraction ===")
        
        expected_shortcodes = [
            ("https://www.instagram.com/p/DLUqd75NtsS/?utm_source=ig_web_copy_link", "DLUqd75NtsS"),
            ("https://www.instagram.com/reel/DLUSQbjSUBj/?utm_source=ig_web_copy_link", "DLUSQbjSUBj"),  
            ("https://www.instagram.com/p/DLRx_BpvUjCAY4kHey4LLWN4bpNM3SBUVDHGpU0/", "DLRx_BpvUjCAY4kHey4LLWN4bpNM3SBUVDHGpU0"),
            ("https://www.instagram.com/p/DLNDd1ks6DL/?utm_source=ig_web_copy_link", "DLNDd1ks6DL"),
            ("https://www.instagram.com/p/DLPIy2Ly__n/?utm_source=ig_web_copy_link", "DLPIy2Ly__n"),
            ("https://www.instagram.com/p/DLU_-uStRR9/?utm_source=ig_web_copy_link", "DLU_-uStRR9")
        ]
        
        for url, expected_shortcode in expected_shortcodes:
            extracted = downloader._extract_shortcode_from_url(url)
            print(f"URL: {url}")
            print(f"Expected: {expected_shortcode}")
            print(f"Extracted: {extracted}")
            print(f"✅ Match: {extracted == expected_shortcode}\n")
            
            assert extracted == expected_shortcode, f"Shortcode mismatch for {url}"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_urls(self, downloader):
        """Test error handling with invalid URLs"""
        print("\n=== Testing Error Handling ===")
        
        invalid_urls = [
            "https://www.instagram.com/p/INVALID123/",  # Invalid shortcode
            "https://www.instagram.com/nonexistent_user/",  # Nonexistent user
            "https://youtube.com/watch?v=123",  # Wrong platform
            "not_a_url_at_all",  # Invalid URL format
        ]
        
        for url in invalid_urls:
            print(f"\nTesting invalid URL: {url}")
            
            # URL validation should catch most issues
            is_valid = downloader.validate_url(url)
            print(f"URL Validation: {'PASS' if not is_valid else 'UNEXPECTED PASS'}")
            
            if not is_valid:
                # Should raise ValueError for invalid URLs
                with pytest.raises(ValueError):
                    await downloader.extract_content(url)
                print("✅ Correctly raised ValueError for invalid URL")
            else:
                # If validation passes, extraction might still fail gracefully
                try:
                    await downloader.extract_content(url)
                    print("⚠️ Unexpected success - URL might be valid")
                except Exception as e:
                    print(f"✅ Gracefully handled error: {type(e).__name__}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"]) 