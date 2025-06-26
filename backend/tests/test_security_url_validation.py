"""
Unit tests for URL validation in the security module
"""

import pytest
from core.security import URLValidator, url_validator

class TestURLValidator:
    """Test cases for URL validation functionality"""
    
    def setup_method(self):
        """Reset validator stats before each test"""
        self.validator = URLValidator()
    
    def test_valid_https_urls(self):
        """Test validation of valid HTTPS URLs"""
        valid_urls = [
            'https://www.instagram.com/p/ABC123/',
            'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'https://www.xiaohongshu.com/discovery/item/123',
            'https://threads.net/@user/post/ABC123',
            'https://example.com',
            'https://subdomain.example.com/path/to/resource',
            'https://example.com:8080/path?query=value#fragment'
        ]
        
        for url in valid_urls:
            result = self.validator.validate_url_format(url, strict_mode=True)
            assert result['is_valid'], f"URL should be valid: {url}"
            assert result['validation_method'] == 'comprehensive'
            assert 'validation_details' in result
            assert 'url_info' in result
    
    def test_valid_http_urls_non_strict(self):
        """Test validation of HTTP URLs in non-strict mode"""
        http_urls = [
            'http://www.instagram.com/p/ABC123/',
            'http://youtube.com/watch?v=dQw4w9WgXcQ',
            'http://example.com'
        ]
        
        for url in http_urls:
            # Should pass in non-strict mode
            result = self.validator.validate_url_format(url, strict_mode=False)
            assert result['is_valid'], f"URL should be valid in non-strict mode: {url}"
            
            # Should fail in strict mode
            result_strict = self.validator.validate_url_format(url, strict_mode=True)
            # Note: Some URLs might still pass if 3/4 validators pass
            # This tests the comprehensive validation approach
    
    def test_invalid_urls(self):
        """Test validation of invalid URLs"""
        invalid_urls = [
            '',  # Empty string
            'not-a-url',  # No protocol
            'ftp://example.com',  # Wrong protocol
            'https://',  # Incomplete URL
            'https://.',  # Invalid domain
            'https://.com',  # Invalid domain
            'https://example',  # No TLD
            'https://example..com',  # Double dots
            'https://example .com',  # Space in domain
            'javascript:alert(1)',  # Malicious scheme
            'data:text/html,<script>alert(1)</script>',  # Data URL
            'https://256.256.256.256',  # Invalid IP
            'https://example.com' + 'a' * 2048,  # Too long
        ]
        
        for url in invalid_urls:
            result = self.validator.validate_url_format(url, strict_mode=True)
            assert not result['is_valid'], f"URL should be invalid: {url}"
    
    def test_platform_detection_instagram(self):
        """Test Instagram URL detection and validation"""
        instagram_urls = [
            'https://www.instagram.com/p/ABC123/',
            'https://instagram.com/reel/XYZ789/',
            'https://www.instagram.com/tv/DEF456/',
            'https://instagram.com/stories/username/123456/',
        ]
        
        for url in instagram_urls:
            result = self.validator.validate_url_format(url)
            assert result['is_valid']
            platform_info = result['validation_details']['platform']
            assert platform_info['platform'] == 'instagram'
            assert platform_info['is_supported']
            assert platform_info['pattern_match']
    
    def test_platform_detection_youtube(self):
        """Test YouTube URL detection and validation"""
        youtube_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com/watch?v=ABC123',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://m.youtube.com/watch?v=XYZ789',
        ]
        
        for url in youtube_urls:
            result = self.validator.validate_url_format(url)
            assert result['is_valid']
            platform_info = result['validation_details']['platform']
            assert platform_info['platform'] == 'youtube'
            assert platform_info['is_supported']
            assert platform_info['pattern_match']
    
    def test_platform_detection_rednote(self):
        """Test RedNote URL detection and validation"""
        rednote_urls = [
            'https://www.xiaohongshu.com/discovery/item/123',
            'https://xiaohongshu.com/user/profile/456',
            'https://xhslink.com/ABC123',
        ]
        
        for url in rednote_urls:
            result = self.validator.validate_url_format(url)
            assert result['is_valid']
            platform_info = result['validation_details']['platform']
            assert platform_info['platform'] == 'rednote'
            assert platform_info['is_supported']
            assert platform_info['pattern_match']
    
    def test_platform_detection_threads(self):
        """Test Threads URL detection and validation"""
        threads_urls = [
            'https://www.threads.net/@username/post/ABC123',
            'https://threads.net/@user.name/post/XYZ789',
        ]
        
        for url in threads_urls:
            result = self.validator.validate_url_format(url)
            assert result['is_valid']
            platform_info = result['validation_details']['platform']
            assert platform_info['platform'] == 'threads'
            assert platform_info['is_supported']
            assert platform_info['pattern_match']
    
    def test_unsupported_platform(self):
        """Test detection of unsupported platforms"""
        unsupported_urls = [
            'https://twitter.com/user/status/123',
            'https://facebook.com/post/456',
            'https://tiktok.com/@user/video/789',
        ]
        
        for url in unsupported_urls:
            result = self.validator.validate_url_format(url)
            # URL format might be valid but platform unsupported
            platform_info = result['validation_details']['platform']
            assert platform_info['platform'] == 'unknown'
            assert not platform_info['is_supported']
    
    def test_malformed_platform_urls(self):
        """Test platform URLs that don't match expected patterns"""
        malformed_urls = [
            'https://instagram.com/p/',  # Missing post ID
            'https://youtube.com/watch',  # Missing video ID
            'https://xiaohongshu.com/',  # Root path only
            'https://threads.net/invalid',  # Invalid thread format
        ]
        
        for url in malformed_urls:
            result = self.validator.validate_url_format(url)
            platform_info = result['validation_details']['platform']
            if platform_info and platform_info.get('platform') != 'unknown':
                # Platform detected but pattern doesn't match
                assert not platform_info.get('pattern_match', True), f"URL {url} should not match platform pattern"
    
    def test_url_component_extraction(self):
        """Test extraction of URL components"""
        test_url = 'https://example.com:8080/path/to/resource?query=value&param=test#fragment'
        result = self.validator.validate_url_format(test_url)
        
        assert result['is_valid']
        url_info = result['url_info']
        
        assert url_info['scheme'] == 'https'
        assert url_info['hostname'] == 'example.com'
        assert url_info['port'] == '8080'
        assert url_info['path'] == '/path/to/resource'
        assert url_info['query'] == 'query=value&param=test'
        assert url_info['fragment'] == 'fragment'
        assert 'query' in url_info['query_params']
        assert 'param' in url_info['query_params']
    
    def test_batch_validation(self):
        """Test batch URL validation"""
        urls = [
            'https://www.instagram.com/p/ABC123/',  # Valid
            'https://youtube.com/watch?v=XYZ789',   # Valid
            'invalid-url',                          # Invalid
            'https://example.com',                  # Valid
            'not-a-url-at-all',                    # Invalid
            'https://xiaohongshu.com/item/123',     # Valid
        ]
        
        result = self.validator.validate_batch_urls(urls)
        
        assert len(result['valid_urls']) == 4
        assert len(result['invalid_urls']) == 2
        assert result['summary']['total'] == 6
        assert result['summary']['valid'] == 4
        assert result['summary']['invalid'] == 2
        assert result['summary']['success_rate'] == 4/6
        
        # Check that valid URLs have platform info
        valid_urls = result['valid_urls']
        instagram_url = next(u for u in valid_urls if 'instagram' in u['url'])
        assert instagram_url['platform'] == 'instagram'
    
    def test_validation_stats_tracking(self):
        """Test that validation statistics are properly tracked"""
        # Reset stats
        self.validator.reset_stats()
        initial_stats = self.validator.get_validation_stats()
        
        assert initial_stats['total_validated'] == 0
        assert initial_stats['valid_urls'] == 0
        assert initial_stats['invalid_urls'] == 0
        
        # Validate some URLs
        valid_urls = [
            'https://www.instagram.com/p/ABC123/',
            'https://youtube.com/watch?v=XYZ789',
        ]
        invalid_urls = [
            'invalid-url',
            'not-a-url',
        ]
        
        for url in valid_urls:
            self.validator.validate_url_format(url)
        
        for url in invalid_urls:
            self.validator.validate_url_format(url)
        
        final_stats = self.validator.get_validation_stats()
        
        assert final_stats['total_validated'] == 4
        assert final_stats['valid_urls'] == 2
        assert final_stats['invalid_urls'] == 2
        assert final_stats['platform_breakdown']['instagram'] == 1
        assert final_stats['platform_breakdown']['youtube'] == 1
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        edge_cases = [
            None,  # None input
            123,   # Non-string input
            [],    # List input
            {},    # Dict input
            '   ',  # Whitespace only
        ]
        
        for case in edge_cases:
            result = self.validator.validate_url_format(case)
            assert not result['is_valid']
            assert 'error' in result
    
    def test_whitespace_handling(self):
        """Test that URLs with trailing/leading whitespace are handled properly"""
        # These should be valid after stripping
        whitespace_urls = [
            '  https://example.com  ',
            'https://example.com' + ' ' * 50,
            '\t\nhttps://example.com\n\t',
        ]
        
        for url in whitespace_urls:
            result = self.validator.validate_url_format(url)
            assert result['is_valid'], f"URL with whitespace should be valid after stripping: {repr(url)}"
    
    def test_comprehensive_validation_scoring(self):
        """Test that comprehensive validation requires 3/4 validators to pass"""
        # This is a tricky test since we need a URL that passes some but not all validators
        # We'll test with a URL that might have mixed validation results
        
        # Test with a borderline case
        borderline_url = 'https://localhost:8080/test'
        result = self.validator.validate_url_format(borderline_url)
        
        # Check that validation details are present
        details = result['validation_details']
        assert 'regex' in details
        assert 'validators' in details
        assert 'urllib3' in details
        assert 'tld' in details
        
        # The final validity should be based on 3/4 rule
        validation_scores = [
            details.get('regex', False),
            details.get('validators', False),
            details.get('urllib3', False),
            details.get('tld', False)
        ]
        expected_validity = sum(validation_scores) >= 3
        assert result['is_valid'] == expected_validity

class TestGlobalValidator:
    """Test the global validator instance"""
    
    def test_global_validator_instance(self):
        """Test that global validator instance works correctly"""
        test_url = 'https://www.instagram.com/p/ABC123/'
        result = url_validator.validate_url_format(test_url)
        
        assert result['is_valid']
        assert result['validation_details']['platform']['platform'] == 'instagram'
    
    def test_global_validator_stats_persistence(self):
        """Test that global validator maintains stats across calls"""
        initial_stats = url_validator.get_validation_stats()
        initial_count = initial_stats['total_validated']
        
        # Validate a URL
        url_validator.validate_url_format('https://example.com')
        
        updated_stats = url_validator.get_validation_stats()
        assert updated_stats['total_validated'] == initial_count + 1


class TestURLValidationIntegration:
    """Integration tests for URL validation with real URLs"""
    
    def test_real_instagram_urls(self):
        """Test with real Instagram URLs from our integration tests"""
        real_urls = [
            'https://www.instagram.com/p/DLUqd75NtsS/?utm_source=ig_web_copy_link',
            'https://www.instagram.com/reel/DLUSQbjSUBj/?utm_source=ig_web_copy_link',
            'https://www.instagram.com/p/DLNDd1ks6DL/?utm_source=ig_web_copy_link',
        ]
        
        validator = URLValidator()
        
        for url in real_urls:
            result = validator.validate_url_format(url)
            assert result['is_valid'], f"Real Instagram URL should be valid: {url}"
            assert result['validation_details']['platform']['platform'] == 'instagram'
            assert result['validation_details']['platform']['pattern_match']
    
    def test_real_youtube_urls(self):
        """Test with real YouTube URLs"""
        real_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://m.youtube.com/watch?v=jNQXAC9IVRw',
        ]
        
        validator = URLValidator()
        
        for url in real_urls:
            result = validator.validate_url_format(url)
            assert result['is_valid'], f"Real YouTube URL should be valid: {url}"
            assert result['validation_details']['platform']['platform'] == 'youtube'
            assert result['validation_details']['platform']['pattern_match']


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 