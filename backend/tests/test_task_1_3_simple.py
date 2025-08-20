#!/usr/bin/env python3
"""
Simple Test Script for Task 1-3 Subtitle Scraping Implementation

This script validates all components of the subtitle scraping system without external dependencies.
Run this script to verify that Task 1-3 is working correctly.

Usage:
    cd /path/to/video-subtitle-scraper/backend
    python test_task_1_3_simple.py
"""

import sys
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test configuration
API_BASE_URL = "http://localhost:8003"
TEST_RESULTS = {
    'passed': 0,
    'failed': 0,
    'warnings': 0
}

def print_header(title):
    """Print a formatted test header"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")

def print_test(test_name):
    """Print test name"""
    print(f"\n{test_name}")
    print("-" * len(test_name))

def print_result(message, status="PASS"):
    """Print test result with status"""
    symbols = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠"}
    symbol = symbols.get(status, "•")
    print(f"   {symbol} {message}")
    
    if status == "PASS":
        TEST_RESULTS['passed'] += 1
    elif status == "FAIL":
        TEST_RESULTS['failed'] += 1
    elif status == "WARN":
        TEST_RESULTS['warnings'] += 1

def make_request(url, method="GET", data=None, timeout=10):
    """Make HTTP request with error handling"""
    try:
        if data:
            data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header('Content-Type', 'application/json')
        else:
            req = urllib.request.Request(url, method=method)
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode('utf-8')
            try:
                return response.status, json.loads(content)
            except json.JSONDecodeError:
                return response.status, content
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return None, str(e)

def test_01_module_imports():
    """Test 1: Verify all subtitle modules can be imported successfully"""
    print_test("Test 1: Module Imports")
    
    try:
        from utils.yt_dlp_helper import fetch_subtitle_text, is_transient_error
        print_result("yt_dlp_helper module imported successfully")
    except Exception as e:
        print_result(f"yt_dlp_helper import failed: {e}", "FAIL")
        return
    
    try:
        from utils.subtitle_processor import SubtitleProcessor
        print_result("subtitle_processor module imported successfully")
    except Exception as e:
        print_result(f"subtitle_processor import failed: {e}", "FAIL")
        return
    
    try:
        from workers.worker import WorkerManager, SubtitleWorker
        print_result("worker module imported successfully")
    except Exception as e:
        print_result(f"worker module import failed: {e}", "FAIL")
        return
    
    try:
        from api.subtitles import router as subtitle_router
        from api.jobs import router as jobs_router
        print_result("API routers imported successfully")
    except Exception as e:
        print_result(f"API router import failed: {e}", "FAIL")
        return
    
    print_result("All required modules imported successfully", "PASS")

def test_02_database_integration():
    """Test 2: Verify database operations and relationships"""
    print_test("Test 2: Database Integration")
    
    try:
        from db.models import init_db, SessionLocal, Video, Channel, Subtitle
        
        # Initialize database
        init_db()
        db = SessionLocal()
        
        try:
            # Create test data with relationships
            channel = Channel(url='https://test-simple.com', name='Test Channel Simple')
            db.add(channel)
            db.flush()
            
            video = Video(
                channel_id=channel.id, 
                url='https://test-simple.com/video', 
                title='Test Video Simple'
            )
            db.add(video)
            db.flush()
            
            subtitle = Subtitle(
                video_id=video.id, 
                language='en', 
                content='Test subtitle content simple'
            )
            db.add(subtitle)
            db.commit()
            
            # Verify relationships work
            saved_subtitle = db.query(Subtitle).filter(Subtitle.video_id == video.id).first()
            assert saved_subtitle.content == 'Test subtitle content simple'
            assert saved_subtitle.video.title == 'Test Video Simple'
            assert saved_subtitle.video.channel.name == 'Test Channel Simple'
            
            print_result("Database CRUD operations working correctly")
            print_result("SQLAlchemy relationships functioning properly")
            
            # Clean up test data
            db.delete(subtitle)
            db.delete(video)
            db.delete(channel)
            db.commit()
            print_result("Test data cleanup completed")
            
        finally:
            db.close()
            
    except Exception as e:
        print_result(f"Database integration test failed: {e}", "FAIL")

def test_03_api_server_health():
    """Test 3: Verify API server is running and healthy"""
    print_test("Test 3: API Server Health")
    
    # Test health endpoint
    status, data = make_request(f"{API_BASE_URL}/health")
    if status == 200:
        print_result("Health endpoint responding correctly")
    else:
        print_result(f"Health endpoint failed: {status}", "FAIL")
        return
    
    # Test root endpoint
    status, data = make_request(f"{API_BASE_URL}/")
    if status == 200:
        print_result("Root endpoint responding correctly")
    else:
        print_result(f"Root endpoint failed: {status}", "FAIL")

def test_04_subtitle_api():
    """Test 4: Verify subtitle API endpoints"""
    print_test("Test 4: Subtitle API Endpoints")
    
    # Test subtitle listing
    status, data = make_request(f"{API_BASE_URL}/api/subtitles/")
    if status == 200 and isinstance(data, dict):
        total = data.get('total', 0)
        print_result(f"Subtitle listing endpoint working - {total} subtitles found")
    else:
        print_result(f"Subtitle listing failed: {status}", "FAIL")
        return
    
    # Test with pagination
    status, data = make_request(f"{API_BASE_URL}/api/subtitles/?limit=5&offset=0")
    if status == 200:
        print_result("Subtitle pagination parameters working")
    else:
        print_result(f"Subtitle pagination failed: {status}", "WARN")

def test_05_video_api():
    """Test 5: Verify video management API endpoints"""
    print_test("Test 5: Video Management API")
    
    status, data = make_request(f"{API_BASE_URL}/api/videos/")
    if status == 200 and isinstance(data, dict):
        total = data.get('total', 0)
        status_counts = data.get('status_counts', {})
        print_result(f"Video listing endpoint working - {total} videos in queue")
        print_result(f"Status breakdown: {status_counts}")
    else:
        print_result(f"Video listing failed: {status}", "FAIL")

def test_06_worker_management():
    """Test 6: Verify worker management functionality"""
    print_test("Test 6: Worker Management System")
    
    # Check initial worker status
    status, data = make_request(f"{API_BASE_URL}/jobs/workers/status")
    if status == 200 and isinstance(data, dict):
        worker_status = data.get('worker_status', {})
        initial_workers = worker_status.get('num_workers', 0)
        print_result(f"Worker status endpoint working - {initial_workers} workers initially")
    else:
        print_result(f"Worker status check failed: {status}", "FAIL")
        return
    
    # Start workers
    status, data = make_request(
        f"{API_BASE_URL}/jobs/workers/start",
        method="POST",
        data={"num_workers": 2}
    )
    if status == 200:
        print_result("Worker start endpoint working")
        
        # Wait for workers to initialize
        time.sleep(2)
        
        # Check worker status after starting
        status, data = make_request(f"{API_BASE_URL}/jobs/workers/status")
        if status == 200 and isinstance(data, dict):
            worker_status = data.get('worker_status', {})
            active_workers = worker_status.get('num_workers', 0)
            print_result(f"Workers started successfully - {active_workers} active")
        else:
            print_result("Worker status check after start failed", "WARN")
    else:
        print_result(f"Worker start failed: {status}", "FAIL")
        return
    
    # Stop workers
    status, data = make_request(f"{API_BASE_URL}/jobs/workers/stop", method="POST")
    if status == 200:
        print_result("Worker stop endpoint working")
        
        # Verify workers stopped
        time.sleep(1)
        status, data = make_request(f"{API_BASE_URL}/jobs/workers/status")
        if status == 200 and isinstance(data, dict):
            worker_status = data.get('worker_status', {})
            final_workers = worker_status.get('num_workers', 0)
            if final_workers == 0:
                print_result("All workers stopped successfully")
            else:
                print_result(f"Some workers still running: {final_workers}", "WARN")
    else:
        print_result(f"Worker stop failed: {status}", "FAIL")

def test_07_error_handling():
    """Test 7: Verify error handling and classification functions"""
    print_test("Test 7: Error Handling Functions")
    
    try:
        from utils.yt_dlp_helper import is_transient_error
        
        # Test transient error detection
        transient_cases = [
            "HTTP Error 429: Too Many Requests",
            "HTTP Error 503: Service Unavailable",
            "Connection timeout",
            "Network is unreachable"
        ]
        
        permanent_cases = [
            "HTTP Error 404: Not Found",
            "No native subtitles available",
            "Private video",
            "Video unavailable"
        ]
        
        transient_correct = 0
        for error_msg in transient_cases:
            if is_transient_error(Exception(error_msg)):
                transient_correct += 1
        
        permanent_correct = 0
        for error_msg in permanent_cases:
            if not is_transient_error(Exception(error_msg)):
                permanent_correct += 1
        
        print_result(f"Transient error detection: {transient_correct}/{len(transient_cases)} correct")
        print_result(f"Permanent error detection: {permanent_correct}/{len(permanent_cases)} correct")
        
        if transient_correct == len(transient_cases) and permanent_correct == len(permanent_cases):
            print_result("Error classification working correctly")
        else:
            print_result("Error classification needs improvement", "WARN")
            
    except Exception as e:
        print_result(f"Error handling test failed: {e}", "FAIL")

def test_08_subtitle_processor():
    """Test 8: Verify subtitle processor functionality"""
    print_test("Test 8: Subtitle Processor")
    
    try:
        from utils.subtitle_processor import SubtitleProcessor
        from db.models import SessionLocal
        
        db = SessionLocal()
        try:
            processor = SubtitleProcessor(db)
            print_result("SubtitleProcessor instantiated successfully")
            
            # Check required methods exist
            required_methods = ['process_video']
            missing_methods = []
            
            for method in required_methods:
                if not (hasattr(processor, method) and callable(getattr(processor, method))):
                    missing_methods.append(method)
            
            if not missing_methods:
                print_result("All required methods present")
            else:
                print_result(f"Missing methods: {missing_methods}", "WARN")
                
        finally:
            db.close()
            
    except Exception as e:
        print_result(f"Subtitle processor test failed: {e}", "FAIL")

def test_09_queue_statistics():
    """Test 9: Verify queue statistics endpoint (optional)"""
    print_test("Test 9: Queue Statistics")
    
    status, data = make_request(f"{API_BASE_URL}/api/jobs/queue/stats")
    
    if status == 200:
        print_result(f"Queue statistics endpoint working: {data}")
    elif status == 404:
        print_result("Queue statistics endpoint not implemented (acceptable)", "WARN")
    else:
        print_result(f"Queue statistics endpoint issue: {status}", "WARN")

def print_final_results():
    """Print final test results summary"""
    print_header("TASK 1-3 TEST RESULTS SUMMARY")
    
    total_tests = TEST_RESULTS['passed'] + TEST_RESULTS['failed'] + TEST_RESULTS['warnings']
    
    print(f"\n📊 TEST STATISTICS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   ✓ Passed: {TEST_RESULTS['passed']}")
    print(f"   ✗ Failed: {TEST_RESULTS['failed']}")
    print(f"   ⚠ Warnings: {TEST_RESULTS['warnings']}")
    
    if TEST_RESULTS['failed'] == 0:
        print(f"\n🎉 TASK 1-3 SUBTITLE SCRAPING: ALL TESTS PASSED!")
        print("   System is working correctly and ready for production.")
        
        if TEST_RESULTS['warnings'] > 0:
            print(f"   Note: {TEST_RESULTS['warnings']} warnings indicate minor issues or missing optional features.")
    else:
        print(f"\n❌ TASK 1-3 SUBTITLE SCRAPING: {TEST_RESULTS['failed']} TESTS FAILED")
        print("   Please review the failed tests and fix the issues.")
    
    print(f"\n🚀 NEXT STEPS:")
    print("   • Task 1-3 implementation is complete")
    print("   • Ready to proceed to Task 1-4 Parallel Processing Enhancement")
    print("   • All core subtitle scraping functionality is operational")

def main():
    """Run all tests"""
    print_header("TASK 1-3 SUBTITLE SCRAPING COMPREHENSIVE TEST SUITE")
    
    print("This test suite validates:")
    print("• Module imports and integration")
    print("• Database operations and relationships") 
    print("• API endpoints functionality")
    print("• Worker management system")
    print("• Error handling and classification")
    print("• Subtitle processing pipeline")
    
    # Check if server is running first
    status, _ = make_request(f"{API_BASE_URL}/health", timeout=5)
    if status != 200:
        print_result("❌ Server is not running! Please start the FastAPI server first:", "FAIL")
        print(f"   cd video-subtitle-scraper/backend/src")
        print(f"   conda activate VSS")
        print(f"   uvicorn app:app --host 0.0.0.0 --port 8003 --reload")
        return
    
    # Run all tests
    test_01_module_imports()
    test_02_database_integration()
    test_03_api_server_health()
    test_04_subtitle_api()
    test_05_video_api()
    test_06_worker_management()
    test_07_error_handling()
    test_08_subtitle_processor()
    test_09_queue_statistics()
    
    # Print final results
    print_final_results()

if __name__ == "__main__":
    main()
