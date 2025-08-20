#!/usr/bin/env python3
"""
Test the channel ingestion API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.status_code} - {response.json()}")
    return response.status_code == 200

def test_list_channels():
    """Test listing channels"""
    response = requests.get(f"{BASE_URL}/channels/")
    print(f"List channels: {response.status_code} - {response.json()}")
    return response.status_code == 200

def test_add_channel():
    """Test adding a channel"""
    test_channel = {
        "url": "https://www.youtube.com/@3Blue1Brown"
    }
    
    response = requests.post(
        f"{BASE_URL}/channels/",
        json=test_channel,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Add channel: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_add_invalid_channel():
    """Test adding an invalid channel URL"""
    test_channel = {
        "url": "https://example.com/not-youtube"
    }
    
    response = requests.post(
        f"{BASE_URL}/channels/",
        json=test_channel,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Add invalid channel: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 422  # Validation error expected

def main():
    """Run all tests"""
    print("Testing Video Subtitle Scraper API")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("List Channels", test_list_channels),
        ("Add Valid Channel", test_add_channel),
        ("Add Invalid Channel", test_add_invalid_channel),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        try:
            if test_func():
                print("✅ PASSED")
                passed += 1
            else:
                print("❌ FAILED")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
