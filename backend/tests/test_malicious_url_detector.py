"""
Unit tests for malicious URL detection in the security module
"""

import os
import json
import tempfile
import pytest
from core.malicious_url_detector import MaliciousURLDetector

class TestMaliciousURLDetector:
    """Test cases for malicious URL detection functionality"""
    
    def setup_method(self):
        """Set up a fresh detector instance for each test"""
        # Create a temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        self.detector = MaliciousURLDetector(cache_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up after tests"""
        # Clean up temp files
        for filename in os.listdir(self.temp_dir):
            os.unlink(os.path.join(self.temp_dir, filename))
        os.rmdir(self.temp_dir)
    
    def test_valid_safe_urls(self):
        """Test detection of valid, safe URLs"""
        safe_urls = [
            'https://www.google.com',
            'https://github.com/user/repo',
            'https://stackoverflow.com/questions/12345',
            'https://www.microsoft.com/en-us/windows',
        ]
        
        for url in safe_urls:
            result = self.detector.check_url(url)
            assert not result['is_malicious'], f"URL should be safe: {url}"
            assert result['is_valid'], f"URL should be valid: {url}"
    
    def test_blacklisted_domains(self):
        """Test detection of blacklisted domains"""
        # These domains are in the default blacklist
        blacklisted_urls = [
            'https://malware.com/download',
            'https://phishing.com/login',
            'https://evil.com/script.js',
        ]
        
        for url in blacklisted_urls:
            result = self.detector.check_url(url)
            assert result['is_malicious'], f"URL should be detected as malicious: {url}"
            assert result['detection_method'] == 'blacklist'
    
    def test_whitelisted_domains(self):
        """Test detection of whitelisted domains"""
        # These domains are in the default whitelist
        whitelisted_urls = [
            'https://google.com/search?q=test',
            'https://microsoft.com/products',
            'https://github.com/user/repo',
        ]
        
        for url in whitelisted_urls:
            result = self.detector.check_url(url)
            assert not result['is_malicious'], f"URL should be safe: {url}"
            assert result['detection_method'] == 'whitelist'
    
    def test_phishing_patterns(self):
        """Test detection of phishing patterns in URLs"""
        phishing_urls = [
            'https://paypal-secure-login.com/verify',
            'https://amazon-account-verify.net/login',
            'https://secure-banking-login.com/confirm',
            'https://account-verify-apple.com/signin',
            'https://microsoft-update-billing.info/confirm',
        ]
        
        for url in phishing_urls:
            result = self.detector.check_url(url)
            assert result['is_malicious'], f"URL should be detected as phishing: {url}"
            assert result['detection_method'] == 'phishing_patterns'
            assert result['threat_type'] == 'phishing'
            assert result['checks']['phishing_patterns']['detected']
    
    def test_invalid_urls(self):
        """Test handling of invalid URLs"""
        invalid_urls = [
            '',  # Empty string
            'not-a-url',  # No protocol
            'ftp://example.com',  # Wrong protocol
            'https://',  # Incomplete URL
        ]
        
        for url in invalid_urls:
            result = self.detector.check_url(url)
            assert not result['is_valid'], f"URL should be invalid: {url}"
            assert not result['is_malicious'], f"Invalid URL should not be marked malicious: {url}"
            assert result['detection_method'] == 'url_validation'
    
    def test_ip_based_urls(self):
        """Test detection of IP-based URLs"""
        ip_urls = [
            'https://192.168.1.1/admin',
            'https://127.0.0.1:8080/login',
            'https://8.8.8.8/dns',
        ]
        
        for url in ip_urls:
            result = self.detector.check_url(url)
            assert result['is_valid'], f"URL should be valid: {url}"
            assert result['checks']['is_ip_url'], f"URL should be detected as IP-based: {url}"
    
    def test_extremely_long_urls(self):
        """Test detection of suspiciously long URLs"""
        # Create a very long URL
        long_url = 'https://example.com/' + 'a' * 1500
        
        result = self.detector.check_url(long_url)
        assert result['is_valid'], f"Long URL should still be valid"
        assert result['checks']['url_length'] > 1000
        assert result['checks']['suspicious_length']
    
    def test_caching(self):
        """Test that URL scan results are properly cached"""
        test_url = 'https://example.com/test'
        
        # First scan should not be cached
        first_result = self.detector.check_url(test_url)
        assert self.detector.stats['cache_hits'] == 0
        
        # Second scan should hit the cache
        second_result = self.detector.check_url(test_url)
        assert self.detector.stats['cache_hits'] == 1
        
        # Results should be the same
        assert first_result['is_malicious'] == second_result['is_malicious']
        assert first_result['is_valid'] == second_result['is_valid']
    
    def test_batch_checking(self):
        """Test batch URL checking functionality"""
        urls = [
            'https://google.com/search',  # Safe, whitelisted
            'https://malware.com/download',  # Malicious, blacklisted
            'https://example.com/normal',  # Safe, not listed
            'https://paypal-secure-login.net/verify',  # Malicious, phishing pattern
            'not-a-url'  # Invalid
        ]
        
        results = self.detector.check_batch_urls(urls)
        
        # We should have 3 safe URLs (including the invalid one) and 2 malicious
        assert results['summary']['total'] == 5
        assert results['summary']['malicious'] == 2
        assert results['summary']['safe'] == 3
    
    def test_add_to_blacklist(self):
        """Test adding domains to the blacklist"""
        # Domain not initially blacklisted
        test_url = 'https://example-test.com/path'
        initial_result = self.detector.check_url(test_url)
        assert not initial_result['is_malicious']
        
        # Add to blacklist
        success = self.detector.add_to_blacklist('example-test.com')
        assert success
        
        # Should now be detected as malicious
        updated_result = self.detector.check_url(test_url)
        assert updated_result['is_malicious']
        assert updated_result['detection_method'] == 'blacklist'
    
    def test_add_to_whitelist(self):
        """Test adding domains to the whitelist"""
        # Create a URL that would be detected as phishing
        test_url = 'https://paypal-secure-verify.com/login'
        initial_result = self.detector.check_url(test_url)
        assert initial_result['is_malicious']
        
        # Add to whitelist
        success = self.detector.add_to_whitelist('paypal-secure-verify.com')
        assert success
        
        # Should now be considered safe
        updated_result = self.detector.check_url(test_url)
        assert not updated_result['is_malicious']
        assert updated_result['detection_method'] == 'whitelist'
    
    def test_stats_tracking(self):
        """Test that detection statistics are properly tracked"""
        # Reset stats
        self.detector.reset_stats()
        initial_stats = self.detector.get_stats()
        
        assert initial_stats['urls_checked'] == 0
        assert initial_stats['malicious_detected'] == 0
        
        # Check some URLs
        self.detector.check_url('https://google.com')  # Safe, whitelisted
        self.detector.check_url('https://malware.com')  # Malicious, blacklisted
        self.detector.check_url('https://example.com')  # Safe, not listed
        self.detector.check_url('https://paypal-secure-login.net/verify')  # Malicious, phishing
        
        final_stats = self.detector.get_stats()
        
        assert final_stats['urls_checked'] == 4
        assert final_stats['malicious_detected'] == 2
        assert final_stats['blacklisted'] == 1
        assert final_stats['whitelisted'] == 1
        assert final_stats['phishing_detected'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 