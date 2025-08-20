#!/usr/bin/env python3
"""
Test script for channel ingestion functionality.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.models import init_db, SessionLocal, Channel, Video
from utils.yt_dlp_helper import validate_youtube_url, normalize_channel_url
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_database_init():
    """Test database initialization"""
    print("Testing database initialization...")
    try:
        init_db()
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def test_url_validation():
    """Test URL validation"""
    print("\nTesting URL validation...")
    
    test_urls = [
        ("https://www.youtube.com/@PythonExplained", True),
        ("https://youtube.com/c/PythonExplained", True),
        ("https://www.youtube.com/channel/UCkw4JCwteGrDHIsyIIKo4tQ", True),
        ("https://www.youtube.com/user/PythonExplained", True),
        ("https://example.com", False),
        ("not_a_url", False),
    ]
    
    all_passed = True
    for url, expected in test_urls:
        result = validate_youtube_url(url)
        if result == expected:
            print(f"✓ {url} -> {result}")
        else:
            print(f"✗ {url} -> {result} (expected {expected})")
            all_passed = False
    
    return all_passed

def test_url_normalization():
    """Test URL normalization"""
    print("\nTesting URL normalization...")
    
    test_cases = [
        ("https://www.youtube.com/@PythonExplained", "https://www.youtube.com/@PythonExplained"),
        ("https://youtube.com/c/PythonExplained", "https://www.youtube.com/c/PythonExplained"),
        ("https://m.youtube.com/channel/UCkw4JCwteGrDHIsyIIKo4tQ", "https://www.youtube.com/channel/UCkw4JCwteGrDHIsyIIKo4tQ"),
    ]
    
    all_passed = True
    for input_url, expected in test_cases:
        try:
            result = normalize_channel_url(input_url)
            if result == expected:
                print(f"✓ {input_url} -> {result}")
            else:
                print(f"✗ {input_url} -> {result} (expected {expected})")
                all_passed = False
        except Exception as e:
            print(f"✗ {input_url} -> Error: {e}")
            all_passed = False
    
    return all_passed

def test_database_operations():
    """Test basic database operations"""
    print("\nTesting database operations...")
    
    try:
        db = SessionLocal()
        
        # Test channel creation
        test_channel = Channel(
            url="https://www.youtube.com/@test-channel",
            name="Test Channel",
            total_videos=0
        )
        db.add(test_channel)
        db.commit()
        
        # Test channel retrieval
        retrieved = db.query(Channel).filter(Channel.url == "https://www.youtube.com/@test-channel").first()
        if retrieved and retrieved.name == "Test Channel":
            print("✓ Channel creation and retrieval works")
        else:
            print("✗ Channel creation or retrieval failed")
            return False
        
        # Test video creation
        test_video = Video(
            channel_id=retrieved.id,
            url="https://www.youtube.com/watch?v=test123",
            title="Test Video",
            status="pending"
        )
        db.add(test_video)
        db.commit()
        
        # Test video retrieval
        video_count = db.query(Video).filter(Video.channel_id == retrieved.id).count()
        if video_count == 1:
            print("✓ Video creation and retrieval works")
        else:
            print("✗ Video creation or retrieval failed")
            return False
        
        # Cleanup
        db.delete(test_video)
        db.delete(test_channel)
        db.commit()
        db.close()
        
        print("✓ Database operations test passed")
        return True
        
    except Exception as e:
        print(f"✗ Database operations test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Channel Ingestion Tests")
    print("=" * 50)
    
    tests = [
        test_database_init,
        test_url_validation,
        test_url_normalization,
        test_database_operations,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
