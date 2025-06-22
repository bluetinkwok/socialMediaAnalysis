#!/usr/bin/env python3
"""
Simple test script to verify FastAPI endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoints():
    """Test all available endpoints"""
    
    print("🧪 Testing FastAPI Backend Endpoints")
    print("=" * 50)
    
    # Test root endpoint
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Root endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
    
    print()
    
    # Test ping endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ping")
        print(f"✅ Ping endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Ping endpoint failed: {e}")
    
    print()
    
    # Test health endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health")
        print(f"✅ Health endpoint: {response.status_code}")
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Service: {data.get('service')}")
        print(f"   Environment: {data.get('environment')}")
        print(f"   Features: {len(data.get('features', {}))}")
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
    
    print()
    
    # Test docs endpoint
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✅ API Docs: {response.status_code}")
    except Exception as e:
        print(f"❌ API Docs failed: {e}")

if __name__ == "__main__":
    print("Waiting 2 seconds for server to be ready...")
    time.sleep(2)
    test_endpoints() 