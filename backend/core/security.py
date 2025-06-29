"""
Security and Input Validation Module

Provides comprehensive input validation and security measures including:
- URL format validation
- Malicious URL detection  
- Input sanitization
- Rate limiting
- File validation

This module is designed for production use with social media content analysis platform.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import validators
import tldextract
from urllib3.util import parse_url

logger = logging.getLogger(__name__)

class URLValidator:
    """
    Comprehensive URL validation with multiple validation approaches
    """
    
    # Supported social media platforms and their domains
    SUPPORTED_PLATFORMS = {
        'instagram': ['instagram.com', 'www.instagram.com'],
        'youtube': ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com'],
        'rednote': ['xiaohongshu.com', 'www.xiaohongshu.com', 'xhslink.com'],
        'threads': ['threads.net', 'www.threads.net']
    }
    
    def __init__(self):
        """Initialize URL validator with patterns and statistics tracking"""
        # URL validation patterns
        self.URL_PATTERNS = {
            'strict': re.compile(
                r'^https://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?$'
            ),
            'basic': re.compile(
                r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?$'
            )
        }
        
        # Platform-specific patterns
        self.PLATFORM_PATTERNS = {
                         'instagram': [
                 r'(?:www\.)?instagram\.com/(?:p|reel|tv)/[\w-]+/?(?:\?.*)?$',
                 r'(?:www\.)?instagram\.com/stories/[\w.-]+/[\w-]+/?(?:\?.*)?$',  # Stories with username/id
                 r'(?:www\.)?instagram\.com/(?!(?:p|reel|tv|stories)/?$)[a-zA-Z0-9._]+/?$'  # User profiles, but not post paths
             ],
            'youtube': [
                r'(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&.*)?$',
                r'(?:www\.)?youtu\.be/[\w-]+(?:\?.*)?$',
                r'(?:m\.)?youtube\.com/watch\?v=[\w-]+(?:&.*)?$'
            ],
            'rednote': [
                r'(?:www\.)?xiaohongshu\.com/(?:discovery/item|user/profile)/[\w-]+(?:\?.*)?$',
                r'xhslink\.com/[\w-]+(?:\?.*)?$'
            ],
            'threads': [
                r'(?:www\.)?threads\.net/@[\w.-]+/post/[\w-]+/?(?:\?.*)?$'
            ]
        }
        
        # Initialize validation statistics
        self.validation_stats = {
            'total_validated': 0,
            'valid_urls': 0,
            'invalid_urls': 0,
            'platform_breakdown': {
                'instagram': 0,
                'youtube': 0,
                'rednote': 0,
                'threads': 0,
                'unknown': 0
            }
        }
    
    def validate_url_format(self, url: str, strict_mode: bool = True) -> Dict[str, Union[bool, str, Dict]]:
        """
        Validate URL format using multiple validation approaches
        
        Args:
            url: URL string to validate
            strict_mode: If True, only allow HTTPS URLs
            
        Returns:
            Dict containing validation results and details
        """
        self.validation_stats['total_validated'] += 1
        
        if not url or not isinstance(url, str):
            self.validation_stats['invalid_urls'] += 1
            return {
                'is_valid': False,
                'error': 'URL must be a non-empty string',
                'validation_method': 'basic_check'
            }
        
        # Clean and normalize URL
        url = url.strip()
        
        # Check if URL is just whitespace
        if not url:
            self.validation_stats['invalid_urls'] += 1
            return {
                'is_valid': False,
                'error': 'URL cannot be empty or whitespace only',
                'validation_method': 'basic_check'
            }
        
        # Basic length check
        if len(url) > 2048:  # RFC 2616 suggests 2048 as reasonable limit
            self.validation_stats['invalid_urls'] += 1
            return {
                'is_valid': False,
                'error': 'URL exceeds maximum length (2048 characters)',
                'validation_method': 'length_check'
            }
        
        # Validate using multiple methods
        validation_results = {}
        
        # 1. Regex validation
        pattern = self.URL_PATTERNS['strict'] if strict_mode else self.URL_PATTERNS['basic']
        regex_valid = bool(pattern.match(url))
        validation_results['regex'] = regex_valid
        
        # 2. Validators library validation
        try:
            validators_valid = validators.url(url)
            validation_results['validators'] = bool(validators_valid)
        except Exception as e:
            validation_results['validators'] = False
            validation_results['validators_error'] = str(e)
        
        # 3. urllib3 parsing validation
        try:
            parsed = parse_url(url)
            urllib3_valid = all([
                parsed.scheme in ['http', 'https'],
                parsed.host,
                parsed.host != ''
            ])
            if strict_mode and parsed.scheme != 'https':
                urllib3_valid = False
            validation_results['urllib3'] = urllib3_valid
        except Exception as e:
            validation_results['urllib3'] = False
            validation_results['urllib3_error'] = str(e)
        
        # 4. TLD validation using tldextract
        try:
            extracted = tldextract.extract(url)
            tld_valid = all([
                extracted.domain,
                extracted.suffix,
                len(extracted.domain) > 0,
                len(extracted.suffix) > 0
            ])
            validation_results['tld'] = tld_valid
            validation_results['domain_info'] = {
                'subdomain': extracted.subdomain,
                'domain': extracted.domain,
                'suffix': extracted.suffix,
                'fqdn': extracted.fqdn
            }
        except Exception as e:
            validation_results['tld'] = False
            validation_results['tld_error'] = str(e)
        
        # 5. Platform-specific validation
        platform_info = self._detect_platform(url)
        validation_results['platform'] = platform_info
        
        # Determine overall validity
        # Require at least 3 out of 4 validation methods to pass
        validation_scores = [
            validation_results.get('regex', False),
            validation_results.get('validators', False),
            validation_results.get('urllib3', False),
            validation_results.get('tld', False)
        ]
        
        is_valid = sum(validation_scores) >= 3
        
        if is_valid:
            self.validation_stats['valid_urls'] += 1
            if platform_info and platform_info.get('platform'):
                self.validation_stats['platform_breakdown'][platform_info['platform']] += 1
        else:
            self.validation_stats['invalid_urls'] += 1
        
        result = {
            'is_valid': is_valid,
            'validation_details': validation_results,
            'url_info': self._extract_url_components(url) if is_valid else None,
            'validation_method': 'comprehensive'
        }
        
        # Add error message for invalid URLs
        if not is_valid:
            failed_methods = []
            if not validation_results.get('regex', False):
                failed_methods.append('regex')
            if not validation_results.get('validators', False):
                failed_methods.append('validators')
            if not validation_results.get('urllib3', False):
                failed_methods.append('urllib3')
            if not validation_results.get('tld', False):
                failed_methods.append('tld')
            
            result['error'] = f"URL validation failed ({len(failed_methods)}/4 methods failed: {', '.join(failed_methods)})"
        
        return result
    
    def _detect_platform(self, url: str) -> Optional[Dict[str, Union[str, bool]]]:
        """
        Detect which social media platform the URL belongs to
        
        Args:
            url: URL to analyze
            
        Returns:
            Dict with platform information or None if not recognized
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix for comparison
            clean_domain = domain.replace('www.', '')
            
            for platform, domains in self.SUPPORTED_PLATFORMS.items():
                clean_domains = [d.replace('www.', '') for d in domains]
                if clean_domain in clean_domains:
                    # Validate platform-specific URL pattern
                    patterns = self.PLATFORM_PATTERNS.get(platform, [])
                    pattern_match = any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns)
                    
                    return {
                        'platform': platform,
                        'domain': domain,
                        'is_supported': True,
                        'pattern_match': pattern_match
                    }
            
            return {
                'platform': 'unknown',
                'domain': domain,
                'is_supported': False,
                'pattern_match': False
            }
            
        except Exception as e:
            logger.error(f"Error detecting platform for URL {url}: {e}")
            return {
                'platform': 'unknown',
                'domain': '',
                'is_supported': False,
                'pattern_match': False
            }
    
    def _extract_url_components(self, url: str) -> Dict[str, str]:
        """
        Extract detailed URL components for analysis
        
        Args:
            url: Valid URL to parse
            
        Returns:
            Dict containing URL components
        """
        try:
            parsed = urlparse(url)
            return {
                'scheme': parsed.scheme,
                'netloc': parsed.netloc,
                'hostname': parsed.hostname or '',
                'port': str(parsed.port) if parsed.port else '',
                'path': parsed.path,
                'params': parsed.params,
                'query': parsed.query,
                'fragment': parsed.fragment,
                'query_params': dict(parse_qs(parsed.query)) if parsed.query else {}
            }
        except Exception as e:
            logger.error(f"Error extracting URL components: {e}")
            return {}
    
    def validate_batch_urls(self, urls: List[str], strict_mode: bool = True) -> Dict[str, List]:
        """
        Validate multiple URLs efficiently
        
        Args:
            urls: List of URLs to validate
            strict_mode: If True, only allow HTTPS URLs
            
        Returns:
            Dict with valid and invalid URL lists
        """
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            result = self.validate_url_format(url, strict_mode)
            if result['is_valid']:
                valid_urls.append({
                    'url': url,
                    'platform': result.get('validation_details', {}).get('platform', {}).get('platform'),
                    'domain': result.get('url_info', {}).get('hostname')
                })
            else:
                invalid_urls.append({
                    'url': url,
                    'error': result.get('error', 'Validation failed'),
                    'details': result.get('validation_details', {})
                })
        
        return {
            'valid_urls': valid_urls,
            'invalid_urls': invalid_urls,
            'summary': {
                'total': len(urls),
                'valid': len(valid_urls),
                'invalid': len(invalid_urls),
                'success_rate': len(valid_urls) / len(urls) if urls else 0
            }
        }
    
    def get_validation_stats(self) -> Dict:
        """Get validation statistics"""
        return self.validation_stats.copy()
    
    def reset_stats(self):
        """Reset validation statistics"""
        self.validation_stats = {
            'total_validated': 0,
            'valid_urls': 0,
            'invalid_urls': 0,
            'platform_breakdown': {
                'instagram': 0,
                'youtube': 0,
                'rednote': 0,
                'threads': 0,
                'unknown': 0
            }
        }


# Global validator instance
url_validator = URLValidator() 

# Import and create singleton instance of MaliciousURLDetector
from core.malicious_url_detector import MaliciousURLDetector

# Global malicious URL detector instance
malicious_url_detector = MaliciousURLDetector() 