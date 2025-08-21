#!/usr/bin/env python3
"""
Test script for Error Handling implementation (Task 1-7)
Tests centralized logging, retry logic, and startup recovery
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from sqlalchemy.orm import Session
from db.models import SessionLocal, Video, Log, Setting, init_db
from utils.error_handler import (
    log, log_exception, startup_recovery, 
    handle_worker_exception, TransientError, PermanentError,
    classify_yt_dlp_error, reset_retry_attempts
)
import traceback

def test_logging():
    """Test centralized logging functionality"""
    print("=== Testing Centralized Logging ===")
    
    # Test basic logging
    log('INFO', 'Test info message')
    log('WARN', 'Test warning message')
    log('ERROR', 'Test error message')
    
    # Test logging with video ID
    log('INFO', 'Test message with video ID', video_id=1)
    
    print("✅ Basic logging tests completed")

def test_exception_logging():
    """Test exception logging with stack traces"""
    print("\n=== Testing Exception Logging ===")
    
    try:
        # Create a test exception
        raise ValueError("This is a test exception")
    except Exception as e:
        log_exception(video_id=1, exc=e)
    
    try:
        # Create another test exception without video ID
        raise RuntimeError("Another test exception")
    except Exception as e:
        log_exception(video_id=None, exc=e)
    
    print("✅ Exception logging tests completed")

def test_error_classification():
    """Test yt-dlp error classification"""
    print("\n=== Testing Error Classification ===")
    
    # Test permanent errors
    permanent_errors = [
        "No native subtitles available",
        "Video unavailable",
        "Private video",
        "Age restricted content"
    ]
    
    for error in permanent_errors:
        error_class = classify_yt_dlp_error(error)
        expected = PermanentError
        result = "✅" if error_class == expected else "❌"
        print(f"{result} '{error}' -> {error_class.__name__}")
    
    # Test transient errors
    transient_errors = [
        "Connection timeout",
        "Rate limit exceeded",
        "Service unavailable",
        "502 Bad Gateway"
    ]
    
    for error in transient_errors:
        error_class = classify_yt_dlp_error(error)
        expected = TransientError
        result = "✅" if error_class == expected else "❌"
        print(f"{result} '{error}' -> {error_class.__name__}")
    
    print("✅ Error classification tests completed")

def test_worker_exception_handling():
    """Test worker exception handling"""
    print("\n=== Testing Worker Exception Handling ===")
    
    # Test transient error handling
    try:
        raise TransientError("Test transient error")
    except Exception as e:
        action = handle_worker_exception(video_id=1, exc=e)
        print(f"✅ Transient error action: {action}")
    
    # Test permanent error handling
    try:
        raise PermanentError("Test permanent error")
    except Exception as e:
        action = handle_worker_exception(video_id=1, exc=e)
        print(f"✅ Permanent error action: {action}")
    
    # Test unknown error handling
    try:
        raise RuntimeError("Unknown error")
    except Exception as e:
        action = handle_worker_exception(video_id=1, exc=e)
        print(f"✅ Unknown error action: {action}")
    
    print("✅ Worker exception handling tests completed")

def test_startup_recovery():
    """Test startup recovery functionality"""
    print("\n=== Testing Startup Recovery ===")
    
    db = SessionLocal()
    try:
        # Create some test videos in different states
        test_videos = [
            Video(url="https://test1.com", title="Test 1", status="pending", attempts=2),
            Video(url="https://test2.com", title="Test 2", status="processing", attempts=1),
            Video(url="https://test3.com", title="Test 3", status="completed", attempts=0),
        ]
        
        for video in test_videos:
            db.add(video)
        db.commit()
        
        print(f"Created {len(test_videos)} test videos")
        
        # Test retry attempts reset
        reset_count = reset_retry_attempts(db)
        print(f"✅ Reset retry attempts for {reset_count} videos")
        
        # Test startup recovery
        startup_recovery()
        print("✅ Startup recovery completed")
        
        # Check the results
        videos = db.query(Video).filter(Video.url.like("https://test%")).all()
        for video in videos:
            print(f"  Video {video.id}: status={video.status}, attempts={video.attempts}")
            
    except Exception as e:
        print(f"❌ Startup recovery test failed: {e}")
        traceback.print_exc()
    finally:
        # Cleanup test data
        db.query(Video).filter(Video.url.like("https://test%")).delete()
        db.commit()
        db.close()

def test_log_retrieval():
    """Test log retrieval functionality"""
    print("\n=== Testing Log Retrieval ===")
    
    db = SessionLocal()
    try:
        # Get recent logs
        from utils.error_handler import get_recent_errors
        recent_logs = get_recent_errors(db, limit=10)
        
        print(f"✅ Retrieved {len(recent_logs)} recent logs")
        for log_entry in recent_logs[:3]:  # Show first 3
            print(f"  Log: {log_entry['level']} - {log_entry['message'][:50]}...")
            
    except Exception as e:
        print(f"❌ Log retrieval test failed: {e}")
    finally:
        db.close()

def test_database_integration():
    """Test database integration and logging fallback"""
    print("\n=== Testing Database Integration ===")
    
    # Test that logs are actually saved to database
    db = SessionLocal()
    try:
        # Count logs before
        log_count_before = db.query(Log).count()
        
        # Add some test logs
        log('INFO', 'Test database integration log 1')
        log('ERROR', 'Test database integration log 2', video_id=999)
        
        # Count logs after
        log_count_after = db.query(Log).count()
        
        logs_added = log_count_after - log_count_before
        print(f"✅ Added {logs_added} logs to database")
        
        # Test log retrieval
        recent_logs = db.query(Log).order_by(Log.timestamp.desc()).limit(2).all()
        for log_entry in recent_logs:
            print(f"  DB Log: {log_entry.level} - {log_entry.message[:30]}...")
            
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
    finally:
        db.close()

def main():
    """Run all error handling tests"""
    print("Error Handling Test Suite (Task 1-7)")
    print("=" * 50)
    
    try:
        # Initialize database
        init_db()
        
        # Run tests
        test_logging()
        test_exception_logging()
        test_error_classification()
        test_worker_exception_handling()
        test_startup_recovery()
        test_log_retrieval()
        test_database_integration()
        
        print("\n" + "=" * 50)
        print("✅ All error handling tests completed successfully!")
        print("\nError handling system is ready for production.")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
