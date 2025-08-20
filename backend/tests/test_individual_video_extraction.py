#!/usr/bin/env python3
"""
Test script for individual video subtitle extraction functionality.
"""

import sys
import os
import requests
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_api_endpoints():
    """Test the new API endpoints for individual video extraction."""
    
    base_url = "http://localhost:8003/api/subtitles"
    test_video_url = "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo"  # TED talk with subtitles
    
    print("🧪 Testing Individual Video Subtitle Extraction API")
    print("=" * 60)
    print()
    
    # Test 1: Get video info
    print("1. Testing video info endpoint...")
    try:
        response = requests.post(f"{base_url}/info", 
                               json={"video_url": test_video_url},
                               timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Video info retrieved successfully")
            print(f"   Title: {data['video_info']['title']}")
            print(f"   Duration: {data['video_info']['duration']} seconds")
            print(f"   Native languages: {data['subtitle_availability']['native_languages'][:5]}...")
            print(f"   Auto-generated languages: {len(data['subtitle_availability']['auto_generated_languages'])} available")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # Test 2: Extract subtitles
    print("2. Testing subtitle extraction endpoint...")
    try:
        response = requests.post(f"{base_url}/extract",
                               json={
                                   "video_url": test_video_url,
                                   "preferred_languages": ["en"],
                                   "include_auto_generated": False
                               },
                               timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Subtitles extracted successfully")
            print(f"   Language: {data['subtitle_info']['language']}")
            print(f"   Content length: {data['subtitle_info']['content_length']} characters")
            print(f"   Format: {data['subtitle_info']['format']}")
            print(f"   Auto-generated: {data['subtitle_info']['is_auto_generated']}")
            print(f"   Preview: {data['subtitle_info']['content'][:100]}...")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # Test 3: Batch extraction (small batch)
    print("3. Testing batch extraction endpoint...")
    test_urls = [
        "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo",  # TED talk
        "https://www.youtube.com/watch?v=8jPQjjsBbIc"   # Another TED talk
    ]
    
    try:
        response = requests.post(f"{base_url}/batch-extract",
                               json={
                                   "video_urls": test_urls,
                                   "preferred_languages": ["en"]
                               },
                               timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Batch extraction completed")
            print(f"   Total requested: {data['total_requested']}")
            print(f"   Successful: {data['successful_extractions']}")
            print(f"   Failed: {data['failed_extractions']}")
            
            for result in data['results']:
                status = "✅" if result['success'] else "❌"
                print(f"   {status} {result['video_title'][:50]}...")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_direct_functions():
    """Test the functions directly without API."""
    
    from utils.yt_dlp_helper import extract_single_video_subtitles, get_video_info_only
    
    print()
    print("🔬 Testing Direct Function Calls")
    print("=" * 40)
    print()
    
    test_video_url = "https://www.youtube.com/watch?v=ZQUxL4Jm1Lo"
    
    # Test 1: Video info
    print("1. Testing get_video_info_only()...")
    try:
        result = get_video_info_only(test_video_url)
        if result['success']:
            print("✅ Video info extracted successfully")
            print(f"   Title: {result['title']}")
            print(f"   Duration: {result['duration']} seconds")
            print(f"   Uploader: {result['uploader']}")
            print(f"   Native subtitles: {result['available_subtitle_languages']}")
        else:
            print(f"❌ Failed: {result['error']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # Test 2: Subtitle extraction
    print("2. Testing extract_single_video_subtitles()...")
    try:
        result = extract_single_video_subtitles(
            video_url=test_video_url,
            preferred_langs=["en"],
            include_auto_generated=False
        )
        
        if result['success']:
            print("✅ Subtitles extracted successfully")
            print(f"   Title: {result['video_title']}")
            print(f"   Language: {result['language']}")
            print(f"   Content length: {result['content_length']} characters")
            print(f"   Format: {result['subtitle_format']}")
            print(f"   Preview: {result['content'][:150]}...")
        else:
            print(f"❌ Failed: {result['error']}")
            print(f"   Is transient error: {result['is_transient_error']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 Individual Video Subtitle Extraction Test Suite")
    print("=" * 60)
    print()
    
    # Check if API server is running
    try:
        response = requests.get("http://localhost:8003/api/subtitles/", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
            test_api_endpoints()
        else:
            print("⚠️  API server not responding correctly")
    except:
        print("⚠️  API server not running, testing direct functions only")
    
    test_direct_functions()
    
    print()
    print("🎉 Test suite completed!")
    print()
    print("📖 New API Endpoints Available:")
    print("   POST /api/subtitles/extract - Extract subtitles from single video")
    print("   POST /api/subtitles/extract/download - Extract and download as .txt")
    print("   POST /api/subtitles/info - Get video info and available languages")
    print("   POST /api/subtitles/batch-extract - Extract from multiple videos")
