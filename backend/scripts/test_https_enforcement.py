#!/usr/bin/env python3
"""
Script to test HTTPS enforcement and trusted host middleware.

This script sends requests to the API with different protocols and host headers
to verify that HTTPS enforcement and trusted host validation are working correctly.
"""

import argparse
import requests
from urllib.parse import urlparse


def test_https_enforcement(base_url):
    """Test HTTPS enforcement by sending HTTP requests."""
    parsed_url = urlparse(base_url)
    http_url = f"http://{parsed_url.netloc}{parsed_url.path}/health"
    
    try:
        response = requests.get(http_url, allow_redirects=False)
        if response.status_code == 307 and "https" in response.headers.get("Location", ""):
            print("✅ HTTPS Enforcement: Working correctly")
            print(f"   Received {response.status_code} redirect to {response.headers.get('Location')}")
        else:
            print("❌ HTTPS Enforcement: Not working as expected")
            print(f"   Received status code {response.status_code}")
            if "Location" in response.headers:
                print(f"   Redirect location: {response.headers['Location']}")
    except requests.RequestException as e:
        print(f"❌ Error testing HTTPS enforcement: {e}")


def test_trusted_host(base_url, fake_host="malicious-host.com"):
    """Test trusted host validation by sending requests with fake host headers."""
    parsed_url = urlparse(base_url)
    url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}/health"
    
    try:
        response = requests.get(url, headers={"Host": fake_host})
        if response.status_code == 400:
            print("✅ Trusted Host Validation: Working correctly")
            print(f"   Received {response.status_code} Bad Request for fake host '{fake_host}'")
        else:
            print("❌ Trusted Host Validation: Not working as expected")
            print(f"   Received status code {response.status_code} for fake host '{fake_host}'")
            print(f"   Response: {response.text[:100]}...")
    except requests.RequestException as e:
        print(f"❌ Error testing trusted host validation: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test HTTPS enforcement and trusted host middleware")
    parser.add_argument("--url", default="https://localhost:8000/api/v1", help="Base URL of the API")
    parser.add_argument("--fake-host", default="malicious-host.com", help="Fake host header to use for testing")
    args = parser.parse_args()
    
    print(f"Testing API at {args.url}")
    print("-" * 50)
    
    test_https_enforcement(args.url)
    print("-" * 50)
    
    test_trusted_host(args.url, args.fake_host)


if __name__ == "__main__":
    main()
