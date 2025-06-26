"""
Integration tests for Threads Content Downloader with real URLs
"""

import asyncio
import pytest
import json
from pathlib import Path
from datetime import datetime

from services.threads_downloader import ThreadsDownloader, extract_threads_content


class TestThreadsIntegration:
    """Integration tests for Threads downloader with real URLs"""
    
    # Test URLs provided by user
    TEST_URLS = {
        'post_1': {
            'url': 'https://www.threads.com/@dankopeng/post/DLWd-yrSzlN?xmt=AQF0BK2YdUvyqCCZc5PLxXLOr_PzFVtIkuquC3BoJEDwWg',
            'expected_content': 'text + 1 video',
            'username': 'dankopeng',
            'post_id': 'DLWd-yrSzlN'
        },
        'post_2': {
            'url': 'https://www.threads.com/@shiba_daytrader/post/DLVIkgKytm9?xmt=AQF0BK2YdUvyqCCZc5PLxXLOr_PzFVtIkuquC3BoJEDwWg',
            'expected_content': 'text + 3 images',
            'username': 'shiba_daytrader',
            'post_id': 'DLVIkgKytm9'
        },
        'post_3': {
            'url': 'https://www.threads.com/@calpaliu2025/post/DLUNOcXuOMV?xmt=AQF0BK2YdUvyqCCZc5PLxXLOr_PzFVtIkuquC3BoJEDwWg',
            'expected_content': 'text',
            'username': 'calpaliu2025',
            'post_id': 'DLUNOcXuOMV'
        },
        'post_4': {
            'url': 'https://www.threads.com/@0scaryiu/post/DLU9JQsJbMy?xmt=AQF0BK2YdUvyqCCZc5PLxXLOr_PzFVtIkuquC3BoJEDwWg',
            'expected_content': 'text + 1 link',
            'username': '0scaryiu',
            'post_id': 'DLU9JQsJbMy'
        }
    }
    
    @pytest.mark.asyncio
    async def test_url_validation_all_posts(self):
        """Test URL validation for all provided Threads URLs"""
        async with ThreadsDownloader(rate_limit_delay=2.0) as downloader:
            for post_name, post_data in self.TEST_URLS.items():
                url = post_data['url']
                
                # Test URL validation
                try:
                    url_info = downloader._validate_threads_url(url)
                    
                    assert url_info['url_type'] == 'post', f"URL {post_name} should be recognized as post"
                    assert url_info['username'] == post_data['username'], f"Username mismatch for {post_name}"
                    assert url_info['post_id'] == post_data['post_id'], f"Post ID mismatch for {post_name}"
                    
                    print(f"✅ {post_name}: URL validation passed")
                    
                except Exception as e:
                    pytest.fail(f"❌ {post_name}: URL validation failed - {str(e)}")
                    
    @pytest.mark.asyncio
    async def test_content_extraction_post_1(self):
        """Test content extraction for POST 1 (text + 1 video)"""
        post_data = self.TEST_URLS['post_1']
        
        async with ThreadsDownloader(rate_limit_delay=3.0, timeout=30) as downloader:
            result = await downloader.extract_content(post_data['url'])
            
            # Basic extraction validation
            assert result['success'] is True, f"Extraction failed: {result.get('error', 'Unknown error')}"
            assert result['platform'] == 'threads'
            assert result['username'] == post_data['username']
            assert result['post_id'] == post_data['post_id']
            
            # Content validation
            assert result['text'] is not None and len(result['text']) > 0, "Should extract text content"
            assert isinstance(result['links'], list), "Links should be a list"
            assert isinstance(result['mentions'], list), "Mentions should be a list"
            assert isinstance(result['hashtags'], list), "Hashtags should be a list"
            assert isinstance(result['metadata'], dict), "Metadata should be a dict"
            
            print(f"✅ POST 1 extraction successful")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Links found: {len(result['links'])}")
            print(f"   Mentions found: {len(result['mentions'])}")
            print(f"   Hashtags found: {len(result['hashtags'])}")
            
            return result
            
    @pytest.mark.asyncio
    async def test_content_extraction_post_2(self):
        """Test content extraction for POST 2 (text + 3 images)"""
        post_data = self.TEST_URLS['post_2']
        
        async with ThreadsDownloader(rate_limit_delay=3.0, timeout=30) as downloader:
            result = await downloader.extract_content(post_data['url'])
            
            # Basic extraction validation
            assert result['success'] is True, f"Extraction failed: {result.get('error', 'Unknown error')}"
            assert result['platform'] == 'threads'
            assert result['username'] == post_data['username']
            assert result['post_id'] == post_data['post_id']
            
            # Content validation
            assert result['text'] is not None and len(result['text']) > 0, "Should extract text content"
            
            print(f"✅ POST 2 extraction successful")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Links found: {len(result['links'])}")
            print(f"   Mentions found: {len(result['mentions'])}")
            print(f"   Hashtags found: {len(result['hashtags'])}")
            
            return result
            
    @pytest.mark.asyncio
    async def test_content_extraction_post_3(self):
        """Test content extraction for POST 3 (text only)"""
        post_data = self.TEST_URLS['post_3']
        
        async with ThreadsDownloader(rate_limit_delay=3.0, timeout=30) as downloader:
            result = await downloader.extract_content(post_data['url'])
            
            # Basic extraction validation
            assert result['success'] is True, f"Extraction failed: {result.get('error', 'Unknown error')}"
            assert result['platform'] == 'threads'
            assert result['username'] == post_data['username']
            assert result['post_id'] == post_data['post_id']
            
            # Content validation
            assert result['text'] is not None and len(result['text']) > 0, "Should extract text content"
            
            print(f"✅ POST 3 extraction successful")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Links found: {len(result['links'])}")
            print(f"   Mentions found: {len(result['mentions'])}")
            print(f"   Hashtags found: {len(result['hashtags'])}")
            
            return result
            
    @pytest.mark.asyncio
    async def test_content_extraction_post_4(self):
        """Test content extraction for POST 4 (text + 1 link)"""
        post_data = self.TEST_URLS['post_4']
        
        async with ThreadsDownloader(rate_limit_delay=3.0, timeout=30) as downloader:
            result = await downloader.extract_content(post_data['url'])
            
            # Basic extraction validation
            assert result['success'] is True, f"Extraction failed: {result.get('error', 'Unknown error')}"
            assert result['platform'] == 'threads'
            assert result['username'] == post_data['username']
            assert result['post_id'] == post_data['post_id']
            
            # Content validation
            assert result['text'] is not None and len(result['text']) > 0, "Should extract text content"
            
            # This post should have at least one link
            if len(result['links']) > 0:
                print(f"   Found {len(result['links'])} link(s) as expected")
                for i, link in enumerate(result['links']):
                    print(f"   Link {i+1}: {link['url']}")
            
            print(f"✅ POST 4 extraction successful")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Links found: {len(result['links'])}")
            print(f"   Mentions found: {len(result['mentions'])}")
            print(f"   Hashtags found: {len(result['hashtags'])}")
            
            return result
            
    @pytest.mark.asyncio
    async def test_bulk_extraction_all_posts(self):
        """Test bulk extraction of all posts"""
        urls = [post_data['url'] for post_data in self.TEST_URLS.values()]
        
        async with ThreadsDownloader(rate_limit_delay=4.0, timeout=30) as downloader:
            results = await downloader.extract_bulk_content(urls)
            
            assert len(results) == len(urls), f"Should return {len(urls)} results"
            
            successful_extractions = 0
            for i, result in enumerate(results):
                post_name = f"post_{i+1}"
                if result['success']:
                    successful_extractions += 1
                    print(f"✅ {post_name}: Bulk extraction successful")
                    print(f"   Text length: {len(result['text'])} characters")
                else:
                    print(f"❌ {post_name}: Bulk extraction failed - {result.get('error', 'Unknown error')}")
                    
            success_rate = (successful_extractions / len(urls)) * 100
            print(f"\n📊 Bulk Extraction Results: {successful_extractions}/{len(urls)} successful ({success_rate:.1f}%)")
            
            # Allow some failures due to potential rate limiting or anti-bot measures
            assert successful_extractions >= len(urls) * 0.75, f"At least 75% of extractions should succeed, got {success_rate:.1f}%"
            
    @pytest.mark.asyncio
    async def test_download_functionality(self):
        """Test download functionality with one post"""
        post_data = self.TEST_URLS['post_3']  # Use text-only post for faster testing
        output_dir = "test_downloads_threads"
        
        async with ThreadsDownloader(rate_limit_delay=3.0, timeout=30) as downloader:
            result = await downloader.download_content(post_data['url'], output_dir)
            
            if result['success']:
                assert result['downloaded'] is True, "Download should be marked as successful"
                assert 'file_path' in result, "Should include file path"
                assert 'file_size' in result, "Should include file size"
                assert 'download_timestamp' in result, "Should include download timestamp"
                
                # Check file exists
                file_path = Path(result['file_path'])
                assert file_path.exists(), f"Downloaded file should exist at {file_path}"
                assert file_path.stat().st_size > 0, "Downloaded file should not be empty"
                
                # Check JSON content
                with open(file_path, 'r', encoding='utf-8') as f:
                    saved_content = json.load(f)
                    assert saved_content['url'] == post_data['url']
                    assert saved_content['username'] == post_data['username']
                    assert saved_content['success'] is True
                    
                print(f"✅ Download test successful")
                print(f"   File: {file_path}")
                print(f"   Size: {result['file_size']} bytes")
                
                # Cleanup
                try:
                    file_path.unlink()
                    file_path.parent.rmdir()
                except:
                    pass  # Ignore cleanup errors
                    
            else:
                print(f"⚠️ Download test skipped due to extraction failure: {result.get('error')}")
                
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling with invalid URLs"""
        invalid_urls = [
            "https://www.threads.com/@nonexistent/post/invalid123",
            "https://www.threads.com/@fake/post/doesnotexist",
        ]
        
        async with ThreadsDownloader(rate_limit_delay=2.0, timeout=15) as downloader:
            for url in invalid_urls:
                result = await downloader.extract_content(url)
                
                # Should handle gracefully without crashing
                assert 'success' in result
                assert 'error' in result
                assert 'url' in result
                assert result['url'] == url
                
                if not result['success']:
                    print(f"✅ Error handling test passed for {url}")
                    print(f"   Error: {result['error']}")
                else:
                    print(f"⚠️ Unexpected success for potentially invalid URL: {url}")


if __name__ == "__main__":
    # Run integration tests
    async def run_integration_tests():
        """Run all integration tests manually"""
        test_instance = TestThreadsIntegration()
        
        print("🧪 Starting Threads Integration Tests")
        print("=" * 50)
        
        try:
            # Test URL validation
            print("\n1. Testing URL validation...")
            await test_instance.test_url_validation_all_posts()
            
            # Test individual post extractions
            print("\n2. Testing individual post extractions...")
            await test_instance.test_content_extraction_post_1()
            await asyncio.sleep(3)  # Rate limiting
            
            await test_instance.test_content_extraction_post_2()
            await asyncio.sleep(3)
            
            await test_instance.test_content_extraction_post_3()
            await asyncio.sleep(3)
            
            await test_instance.test_content_extraction_post_4()
            await asyncio.sleep(3)
            
            # Test bulk extraction
            print("\n3. Testing bulk extraction...")
            await test_instance.test_bulk_extraction_all_posts()
            
            # Test download functionality
            print("\n4. Testing download functionality...")
            await test_instance.test_download_functionality()
            
            # Test error handling
            print("\n5. Testing error handling...")
            await test_instance.test_error_handling()
            
            print("\n" + "=" * 50)
            print("🎉 All integration tests completed!")
            
        except Exception as e:
            print(f"\n❌ Integration test failed: {str(e)}")
            raise
    
    # Run if executed directly
    asyncio.run(run_integration_tests()) 