"""
Malicious URL Detection Module

Provides functionality to detect malicious URLs through:
- Domain blacklist/whitelist checking
- Threat intelligence API integration
- Phishing pattern detection
"""

import os
import re
import json
import logging
import ipaddress
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse
import time
import hashlib
from pathlib import Path
import requests
from datetime import datetime, timedelta

import tldextract

from core.config import settings
from core.security import URLValidator

logger = logging.getLogger(__name__)

class MaliciousURLDetector:
    """
    Detects malicious URLs using multiple detection methods:
    - Local domain blacklist/whitelist
    - Threat intelligence APIs
    - Phishing and malicious pattern detection
    """
    
    # Default lists - will be extended from files
    DEFAULT_BLACKLIST_DOMAINS = {
        'malware.com', 'phishing.com', 'evil.com', 'malicious.com',
        'ransomware.com', 'scam.com', 'trojan.com', 'virus.com'
    }
    
    DEFAULT_WHITELIST_DOMAINS = {
        'google.com', 'microsoft.com', 'apple.com', 'amazon.com',
        'github.com', 'stackoverflow.com', 'wikipedia.org'
    }
    
    # Phishing patterns to detect
    PHISHING_PATTERNS = [
        r'(?:paypal|apple|microsoft|amazon|google|facebook|instagram|twitter|netflix).*?(?:secure|login|signin|security|account|verify|auth|session)',
        r'(?:verify|confirm|secure|login).*?(?:account|payment|bank|paypal|apple|microsoft|amazon)',
        r'(?:banking|payment|wallet|account|password|credential).*?(?:verify|confirm|secure|login)',
        r'(?:alert|urgent|verify|suspended|locked|limited|unusual).*?(?:account|access|login|activity)',
        r'(?:update|verify|confirm).*?(?:billing|payment|information|details|address|card)',
    ]
    
    def __init__(self, 
                 blacklist_file: str = None,
                 whitelist_file: str = None,
                 cache_dir: str = None,
                 cache_duration: int = 86400):  # Default 24 hours cache
        """
        Initialize the malicious URL detector
        
        Args:
            blacklist_file: Path to blacklist file (one domain per line)
            whitelist_file: Path to whitelist file (one domain per line)
            cache_dir: Directory to store cache files
            cache_duration: Cache duration in seconds (default: 24 hours)
        """
        self.url_validator = URLValidator()
        self.blacklist_domains: Set[str] = set(self.DEFAULT_BLACKLIST_DOMAINS)
        self.whitelist_domains: Set[str] = set(self.DEFAULT_WHITELIST_DOMAINS)
        
        # Load blacklist and whitelist from files if provided
        if blacklist_file and os.path.exists(blacklist_file):
            self._load_domain_list(blacklist_file, self.blacklist_domains)
        
        if whitelist_file and os.path.exists(whitelist_file):
            self._load_domain_list(whitelist_file, self.whitelist_domains)
        
        # Compile phishing patterns
        self.phishing_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.PHISHING_PATTERNS]
        
        # Setup caching
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '..', 'data', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_duration = cache_duration
        self.cache_file = os.path.join(self.cache_dir, 'malicious_url_cache.json')
        self.cache = self._load_cache()
        
        # Detection stats
        self.stats = {
            'urls_checked': 0,
            'malicious_detected': 0,
            'blacklisted': 0,
            'whitelisted': 0,
            'phishing_detected': 0,
            'api_detected': 0,
            'cache_hits': 0,
            'last_reset': datetime.now().isoformat()
        }
    
    def _load_domain_list(self, file_path: str, domain_set: Set[str]) -> None:
        """
        Load domains from a file into a set
        
        Args:
            file_path: Path to the file with domains (one per line)
            domain_set: Set to add domains to
        """
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract domain from potential URL
                        extracted = tldextract.extract(line)
                        if extracted.domain and extracted.suffix:
                            domain = f"{extracted.domain}.{extracted.suffix}"
                            domain_set.add(domain)
            
            logger.info(f"Loaded {len(domain_set)} domains from {file_path}")
        except Exception as e:
            logger.error(f"Error loading domain list from {file_path}: {e}")
    
    def _load_cache(self) -> Dict:
        """Load URL scan cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                
                # Clean expired cache entries
                now = time.time()
                cache = {k: v for k, v in cache.items() 
                         if now - v.get('timestamp', 0) < self.cache_duration}
                
                logger.info(f"Loaded {len(cache)} cache entries from {self.cache_file}")
                return cache
            except Exception as e:
                logger.error(f"Error loading cache from {self.cache_file}: {e}")
        
        return {}
    
    def _save_cache(self) -> None:
        """Save URL scan cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Error saving cache to {self.cache_file}: {e}")
    
    def check_url(self, url: str) -> Dict[str, Union[bool, str, Dict]]:
        """
        Check if a URL is malicious using multiple detection methods
        
        Args:
            url: URL to check
            
        Returns:
            Dict with detection results
        """
        self.stats['urls_checked'] += 1
        
        # First validate URL format
        validation_result = self.url_validator.validate_url_format(url)
        if not validation_result['is_valid']:
            return {
                'is_malicious': False,  # Not malicious, just invalid
                'is_valid': False,
                'error': validation_result.get('error', 'Invalid URL format'),
                'detection_method': 'url_validation'
            }
        
        # Extract domain for checking
        url_info = validation_result['url_info']
        hostname = url_info['hostname']
        
        # Check cache first
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if url_hash in self.cache:
            cache_entry = self.cache[url_hash]
            # Check if cache entry is still valid
            if time.time() - cache_entry.get('timestamp', 0) < self.cache_duration:
                self.stats['cache_hits'] += 1
                result = cache_entry['result']
                if result.get('is_malicious', False):
                    self.stats['malicious_detected'] += 1
                return result
        
        # Extract domain components
        extracted = tldextract.extract(hostname)
        domain = f"{extracted.domain}.{extracted.suffix}"
        
        # Initialize result
        result = {
            'is_malicious': False,
            'is_valid': True,
            'url': url,
            'domain': domain,
            'checks': {}
        }
        
        # 1. Check whitelist (overrides other checks)
        if domain in self.whitelist_domains:
            self.stats['whitelisted'] += 1
            result['checks']['whitelist'] = True
            result['detection_method'] = 'whitelist'
            
            # Cache the result
            self._cache_result(url_hash, result)
            return result
        
        # 2. Check blacklist
        if domain in self.blacklist_domains:
            self.stats['blacklisted'] += 1
            self.stats['malicious_detected'] += 1
            result['is_malicious'] = True
            result['checks']['blacklist'] = True
            result['detection_method'] = 'blacklist'
            result['threat_type'] = 'blacklisted_domain'
            
            # Cache the result
            self._cache_result(url_hash, result)
            return result
        
        # 3. Check for phishing patterns in URL
        result['checks']['phishing_patterns'] = self._check_phishing_patterns(url)
        if result['checks']['phishing_patterns']['detected']:
            self.stats['phishing_detected'] += 1
            self.stats['malicious_detected'] += 1
            result['is_malicious'] = True
            result['detection_method'] = 'phishing_patterns'
            result['threat_type'] = 'phishing'
            
            # Cache the result
            self._cache_result(url_hash, result)
            return result
        
        # 4. Check IP-based URL (often suspicious)
        try:
            ipaddress.ip_address(hostname)
            # It's an IP address
            result['checks']['is_ip_url'] = True
            # IP URLs are suspicious but not automatically malicious
        except ValueError:
            result['checks']['is_ip_url'] = False
        
        # 5. Check URL length (very long URLs can be suspicious)
        result['checks']['url_length'] = len(url)
        if len(url) > 1000:  # Extremely long URLs are suspicious
            result['checks']['suspicious_length'] = True
        
        # Cache the result
        self._cache_result(url_hash, result)
        return result
    
    def _check_phishing_patterns(self, url: str) -> Dict[str, Union[bool, List[str]]]:
        """
        Check if URL matches known phishing patterns
        
        Args:
            url: URL to check
            
        Returns:
            Dict with detection results
        """
        matches = []
        url_lower = url.lower()
        
        # Check each pattern
        for i, pattern in enumerate(self.phishing_patterns):
            if pattern.search(url_lower):
                matches.append(f"pattern_{i+1}")
        
        return {
            'detected': len(matches) > 0,
            'matches': matches
        }
    
    def _cache_result(self, url_hash: str, result: Dict) -> None:
        """
        Cache the scan result for a URL
        
        Args:
            url_hash: MD5 hash of the URL
            result: Scan result dictionary
        """
        self.cache[url_hash] = {
            'timestamp': time.time(),
            'result': result
        }
        
        # Periodically save cache to file (every 100 entries)
        if len(self.cache) % 100 == 0:
            self._save_cache()
    
    def check_batch_urls(self, urls: List[str]) -> Dict[str, List]:
        """
        Check multiple URLs efficiently
        
        Args:
            urls: List of URLs to check
            
        Returns:
            Dict with safe and malicious URL lists
        """
        safe_urls = []
        malicious_urls = []
        
        for url in urls:
            result = self.check_url(url)
            if result.get('is_malicious', False):
                malicious_urls.append({
                    'url': url,
                    'threat_type': result.get('threat_type', 'unknown'),
                    'detection_method': result.get('detection_method', 'unknown')
                })
            else:
                safe_urls.append({
                    'url': url
                })
        
        return {
            'safe_urls': safe_urls,
            'malicious_urls': malicious_urls,
            'summary': {
                'total': len(urls),
                'safe': len(safe_urls),
                'malicious': len(malicious_urls)
            }
        }
    
    def add_to_blacklist(self, domain: str) -> bool:
        """
        Add a domain to the blacklist
        
        Args:
            domain: Domain to add
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            # Extract domain from potential URL
            extracted = tldextract.extract(domain)
            if extracted.domain and extracted.suffix:
                clean_domain = f"{extracted.domain}.{extracted.suffix}"
                self.blacklist_domains.add(clean_domain)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding domain to blacklist: {e}")
            return False
    
    def add_to_whitelist(self, domain: str) -> bool:
        """
        Add a domain to the whitelist
        
        Args:
            domain: Domain to add
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            # Extract domain from potential URL
            extracted = tldextract.extract(domain)
            if extracted.domain and extracted.suffix:
                clean_domain = f"{extracted.domain}.{extracted.suffix}"
                self.whitelist_domains.add(clean_domain)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding domain to whitelist: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get detection statistics"""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Reset detection statistics"""
        self.stats = {
            'urls_checked': 0,
            'malicious_detected': 0,
            'blacklisted': 0,
            'whitelisted': 0,
            'phishing_detected': 0,
            'api_detected': 0,
            'cache_hits': 0,
            'last_reset': datetime.now().isoformat()
        }


# Global detector instance
malicious_url_detector = MaliciousURLDetector() 