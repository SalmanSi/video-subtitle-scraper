#!/usr/bin/env python3
"""
Comprehensive Test Suite for Task 1-3 Subtitle Scraping Implementation

This test suite validates all components of the subtitle scraping system:
- Module imports and integration
- Database operations and relationships
- API endpoints functionality
- Worker management system
- Error handling and classification
- Subtitle processing pipeline
"""

import sys
import os
import pytest
import requests
import time
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test configuration
API_BASE_URL = "http://localhost:8003"
TEST_TIMEOUT = 30  # seconds

class TestTask1_3SubtitleScraping:
    """Comprehensive test suite for Task 1-3 Subtitle Scraping"""
    
    @classmethod
    def setup_class(cls):
        """Setup test class - ensure server is running"""
        print("\n🎯 STARTING TASK 1-3 COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        # Check if server is running
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✓ Server is running and accessible")
            else:
                pytest.fail("Server is not responding correctly")
        except requests.exceptions.RequestException:
            pytest.fail("Server is not running. Please start the FastAPI server first.")
    
    def test_01_module_imports(self):
        """Test 1: Verify all subtitle modules can be imported successfully"""
        print("\n1. Testing Module Imports...")
        
        try:
            from utils.yt_dlp_helper import fetch_subtitle_text, is_transient_error
            from utils.subtitle_processor import SubtitleProcessor
            from workers.worker import WorkerManager, SubtitleWorker
            from api.subtitles import router as subtitle_router
            from api.jobs import router as jobs_router
            print("   ✓ All subtitle modules imported successfully")
            assert True
        except ImportError as e:
            pytest.fail(f"Module import failed: {e}")
    
    def test_02_database_integration(self):
        """Test 2: Verify database operations and relationships"""
        print("\n2. Testing Database Integration...")
        
        try:
            from db.models import init_db, SessionLocal, Video, Channel, Subtitle
            
            # Initialize database
            init_db()
            db = SessionLocal()
            
            try:
                # Create test data with relationships
                channel = Channel(url='https://test-task-1-3.com', name='Test Channel Task 1-3')
                db.add(channel)
                db.flush()
                
                video = Video(
                    channel_id=channel.id, 
                    url='https://test-task-1-3.com/video', 
                    title='Test Video Task 1-3'
                )
                db.add(video)
                db.flush()
                
                subtitle = Subtitle(
                    video_id=video.id, 
                    language='en', 
                    content='Test subtitle content for Task 1-3'
                )
                db.add(subtitle)
                db.commit()
                
                # Verify relationships work
                saved_subtitle = db.query(Subtitle).filter(Subtitle.video_id == video.id).first()
                assert saved_subtitle.content == 'Test subtitle content for Task 1-3'
                assert saved_subtitle.video.title == 'Test Video Task 1-3'
                assert saved_subtitle.video.channel.name == 'Test Channel Task 1-3'
                
                print("   ✓ Database operations and relationships working correctly")
                
                # Clean up test data
                db.delete(subtitle)
                db.delete(video)
                db.delete(channel)
                db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            pytest.fail(f"Database integration test failed: {e}")
    
    def test_03_api_health_check(self):
        """Test 3: Verify API server health"""
        print("\n3. Testing API Health...")
        
        response = requests.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        print("   ✓ API health check passed")
    
    def test_04_subtitle_api_endpoints(self):
        """Test 4: Verify subtitle API endpoints"""
        print("\n4. Testing Subtitle API Endpoints...")
        
        # Test subtitle listing
        response = requests.get(f"{API_BASE_URL}/api/subtitles/")
        assert response.status_code == 200
        data = response.json()
        assert 'subtitles' in data
        assert 'total' in data
        print(f"   ✓ Subtitle listing: {data['total']} subtitles found")
        
        # Test with pagination parameters
        response = requests.get(f"{API_BASE_URL}/api/subtitles/?limit=5&offset=0")
        assert response.status_code == 200
        print("   ✓ Subtitle pagination working")
    
    def test_05_video_api_endpoints(self):
        """Test 5: Verify video management API endpoints"""
        print("\n5. Testing Video API Endpoints...")
        
        # Test video listing
        response = requests.get(f"{API_BASE_URL}/api/videos/")
        assert response.status_code == 200
        data = response.json()
        assert 'videos' in data
        assert 'total' in data
        assert 'status_counts' in data
        print(f"   ✓ Video listing: {data['total']} videos in queue")
        print(f"   ✓ Status breakdown: {data['status_counts']}")
    
    def test_06_worker_management_api(self):
        """Test 6: Verify worker management functionality"""
        print("\n6. Testing Worker Management API...")
        
        # Check initial worker status
        response = requests.get(f"{API_BASE_URL}/jobs/workers/status")
        assert response.status_code == 200
        initial_status = response.json()
        print(f"   ✓ Initial worker status: {initial_status['worker_status']['num_workers']} workers")
        
        # Start workers
        start_response = requests.post(
            f"{API_BASE_URL}/jobs/workers/start",
            json={"num_workers": 2}
        )
        assert start_response.status_code == 200
        start_data = start_response.json()
        print(f"   ✓ Started workers: {start_data['worker_status']['num_workers']}")
        
        # Wait a moment for workers to initialize
        time.sleep(2)
        
        # Check worker status after starting
        response = requests.get(f"{API_BASE_URL}/jobs/workers/status")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data['worker_status']['num_workers'] >= 2
        print(f"   ✓ Workers active: {status_data['worker_status']['num_workers']}")
        
        # Stop workers
        stop_response = requests.post(f"{API_BASE_URL}/jobs/workers/stop")
        assert stop_response.status_code == 200
        stop_data = stop_response.json()
        print(f"   ✓ Stopped workers: {stop_data['status']}")
        
        # Verify workers stopped
        time.sleep(1)
        response = requests.get(f"{API_BASE_URL}/jobs/workers/status")
        final_status = response.json()
        assert final_status['worker_status']['num_workers'] == 0
        print("   ✓ All workers stopped successfully")
    
    def test_07_error_handling_functions(self):
        """Test 7: Verify error handling and classification functions"""
        print("\n7. Testing Error Handling Functions...")
        
        try:
            from utils.yt_dlp_helper import is_transient_error
            
            # Test transient error detection
            transient_errors = [
                "HTTP Error 429: Too Many Requests",
                "HTTP Error 503: Service Unavailable",
                "Connection timeout",
                "Network is unreachable"
            ]
            
            permanent_errors = [
                "HTTP Error 404: Not Found",
                "No native subtitles available",
                "Private video",
                "Video unavailable"
            ]
            
            for error in transient_errors:
                assert is_transient_error(Exception(error)), f"Should be transient: {error}"
            
            for error in permanent_errors:
                assert not is_transient_error(Exception(error)), f"Should be permanent: {error}"
            
            print("   ✓ Error classification working correctly")
            
        except Exception as e:
            pytest.fail(f"Error handling test failed: {e}")
    
    def test_08_subtitle_processor_functionality(self):
        """Test 8: Verify subtitle processor core functionality"""
        print("\n8. Testing Subtitle Processor...")
        
        try:
            from utils.subtitle_processor import SubtitleProcessor
            from db.models import SessionLocal
            
            db = SessionLocal()
            try:
                processor = SubtitleProcessor(db)
                assert processor is not None
                print("   ✓ SubtitleProcessor instantiated successfully")
                
                # Test that processor has required methods
                assert hasattr(processor, 'process_video')
                assert callable(getattr(processor, 'process_video'))
                print("   ✓ SubtitleProcessor has required methods")
                
            finally:
                db.close()
                
        except Exception as e:
            pytest.fail(f"Subtitle processor test failed: {e}")
    
    def test_09_api_endpoint_coverage(self):
        """Test 9: Verify all required API endpoints exist"""
        print("\n9. Testing API Endpoint Coverage...")
        
        required_endpoints = [
            ("GET", "/api/subtitles/"),
            ("GET", "/api/videos/"),
            ("GET", "/jobs/workers/status"),
            ("POST", "/jobs/workers/start"),
            ("POST", "/jobs/workers/stop"),
            ("GET", "/health")
        ]
        
        for method, endpoint in required_endpoints:
            if method == "GET":
                response = requests.get(f"{API_BASE_URL}{endpoint}")
            elif method == "POST":
                # Use appropriate data for POST endpoints
                if "start" in endpoint:
                    response = requests.post(f"{API_BASE_URL}{endpoint}", json={"num_workers": 1})
                else:
                    response = requests.post(f"{API_BASE_URL}{endpoint}")
            
            # We expect 200 or other valid status codes, not 404
            assert response.status_code != 404, f"Endpoint not found: {method} {endpoint}"
            print(f"   ✓ {method} {endpoint} - Status: {response.status_code}")
            
            # Clean up any workers started during testing
            if "start" in endpoint:
                requests.post(f"{API_BASE_URL}/jobs/workers/stop")
    
    def test_10_queue_statistics(self):
        """Test 10: Verify queue statistics (if endpoint exists)"""
        print("\n10. Testing Queue Statistics...")
        
        # Try the queue stats endpoint
        response = requests.get(f"{API_BASE_URL}/api/jobs/queue/stats")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Queue statistics available: {data}")
        elif response.status_code == 404:
            print("   ⚠ Queue statistics endpoint not found (acceptable for current implementation)")
        else:
            print(f"   ⚠ Queue statistics endpoint returned: {response.status_code}")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests"""
        print("\n" + "=" * 60)
        print("🎉 TASK 1-3 COMPREHENSIVE TEST SUITE COMPLETED")
        print("=" * 60)
        
        # Ensure no workers are left running
        try:
            requests.post(f"{API_BASE_URL}/jobs/workers/stop", timeout=5)
            print("✓ Cleanup: Ensured all workers are stopped")
        except:
            pass


def run_comprehensive_tests():
    """Run the comprehensive test suite with detailed output"""
    print("🎯 TASK 1-3 SUBTITLE SCRAPING COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print("This test suite validates:")
    print("• Module imports and integration")
    print("• Database operations and relationships")
    print("• API endpoints functionality")
    print("• Worker management system")
    print("• Error handling and classification")
    print("• Subtitle processing pipeline")
    print("=" * 60)
    
    # Run tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])


if __name__ == "__main__":
    run_comprehensive_tests()
