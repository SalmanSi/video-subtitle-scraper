#!/usr/bin/env python3
"""
Comprehensive Test Suite for Task 1-4 Parallel Scraping Implementation

Tests:
1. Atomic job claiming
2. Exponential backoff
3. Graceful shutdown
4. Error handling
5. Performance metrics
6. Parallel processing
"""

import os
import sys
import time
import threading
import signal
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.orm import Session
from db.models import SessionLocal, Video, Channel, Setting, Log
from utils.queue_manager import claim_next_video, release_video, get_queue_statistics
from workers.worker import WorkerManager, start_workers, stop_workers, get_worker_status, get_performance_metrics

# Test configuration
API_BASE_URL = "http://localhost:8003/api"
TEST_CHANNELS = [
    "https://www.youtube.com/@TED",  # Large channel for testing
    "https://www.youtube.com/@kurzgesagt"  # Another test channel
]

class ParallelScrapingTester:
    """Comprehensive tester for parallel scraping functionality"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.test_results = {}
        self.start_time = datetime.utcnow()
    
    def __del__(self):
        if hasattr(self, 'db') and self.db:
            self.db.close()
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
    
    def setup_test_data(self):
        """Setup test data in database"""
        print("\n🔧 Setting up test data...")
        
        try:
            # Ensure settings exist
            settings = self.db.query(Setting).filter(Setting.id == 1).first()
            if not settings:
                settings = Setting(
                    id=1,
                    max_workers=3,
                    max_retries=2,
                    backoff_factor=2.0
                )
                self.db.add(settings)
                self.db.commit()
            
            # Create test channel if not exists
            test_channel = self.db.query(Channel).filter(Channel.url == TEST_CHANNELS[0]).first()
            if not test_channel:
                test_channel = Channel(
                    url=TEST_CHANNELS[0],
                    name="TED Test Channel",
                    total_videos=0
                )
                self.db.add(test_channel)
                self.db.commit()
            
            # Add some test videos for processing
            test_videos = [
                "https://www.youtube.com/watch?v=WUkmUqLwgLU",  # TED video with subtitles
                "https://www.youtube.com/watch?v=aD5RSQJP9F8",  # Another TED video
                "https://www.youtube.com/watch?v=invalid123",   # Invalid video for error testing
            ]
            
            for video_url in test_videos:
                existing = self.db.query(Video).filter(Video.url == video_url).first()
                if not existing:
                    video = Video(
                        channel_id=test_channel.id,
                        url=video_url,
                        title=f"Test Video - {video_url[-11:]}",
                        status='pending'
                    )
                    self.db.add(video)
            
            self.db.commit()
            self.log_test("setup_test_data", True, "Test data created successfully")
            
        except Exception as e:
            self.log_test("setup_test_data", False, f"Failed to setup test data: {e}")
    
    def test_atomic_claiming(self):
        """Test that video claiming is atomic and race-condition free"""
        print("\n🔒 Testing atomic job claiming...")
        
        try:
            # Get a pending video
            pending_videos = self.db.query(Video).filter(Video.status == 'pending').limit(5).all()
            if not pending_videos:
                self.log_test("atomic_claiming", False, "No pending videos found for testing")
                return
            
            claimed_videos = []
            
            def claim_worker(worker_id):
                """Worker function to test concurrent claiming"""
                db = SessionLocal()
                try:
                    for _ in range(3):  # Try to claim 3 videos
                        video_id = claim_next_video(db)
                        if video_id:
                            claimed_videos.append((worker_id, video_id))
                            time.sleep(0.1)  # Simulate processing
                            release_video(db, video_id, 'pending')  # Release back for next test
                finally:
                    db.close()
            
            # Start 3 concurrent workers
            threads = []
            for i in range(3):
                thread = threading.Thread(target=claim_worker, args=(i+1,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Check results
            unique_videos = set(video_id for _, video_id in claimed_videos)
            total_claims = len(claimed_videos)
            unique_claims = len(unique_videos)
            
            if total_claims == unique_claims:
                self.log_test("atomic_claiming", True, f"All {total_claims} claims were unique")
            else:
                self.log_test("atomic_claiming", False, f"Duplicate claims detected: {total_claims} total, {unique_claims} unique")
            
        except Exception as e:
            self.log_test("atomic_claiming", False, f"Error during atomic claiming test: {e}")
    
    def test_exponential_backoff(self):
        """Test exponential backoff implementation"""
        print("\n⏱️ Testing exponential backoff...")
        
        try:
            from workers.worker import SubtitleWorker
            
            worker = SubtitleWorker(999)  # Test worker
            
            # Test backoff calculation
            backoff_factor = 2.0
            expected_delays = [2.0, 4.0, 8.0, 16.0, 32.0]
            
            for attempts, expected in enumerate(expected_delays):
                calculated = worker.get_retry_delay(attempts, backoff_factor)
                if calculated != expected:
                    self.log_test("exponential_backoff", False, f"Incorrect delay: expected {expected}, got {calculated}")
                    return
            
            # Test max delay cap (should be 300s)
            max_delay = worker.get_retry_delay(10, backoff_factor)
            if max_delay != 300:
                self.log_test("exponential_backoff", False, f"Max delay not capped: got {max_delay}, expected 300")
                return
            
            self.log_test("exponential_backoff", True, "Exponential backoff working correctly")
            
        except Exception as e:
            self.log_test("exponential_backoff", False, f"Error during backoff test: {e}")
    
    def test_error_classification(self):
        """Test error classification for retry logic"""
        print("\n🔍 Testing error classification...")
        
        try:
            from workers.worker import SubtitleWorker
            
            worker = SubtitleWorker(999)
            
            # Test permanent errors (should not retry)
            permanent_errors = [
                Exception("No subtitles available"),
                Exception("Video unavailable"),
                Exception("Private video"),
                Exception("Video not found")
            ]
            
            for error in permanent_errors:
                if worker.classify_error(error):
                    self.log_test("error_classification", False, f"Permanent error classified as transient: {error}")
                    return
            
            # Test transient errors (should retry)
            transient_errors = [
                Exception("Connection timeout"),
                Exception("Network error"),
                Exception("Rate limit exceeded"),
                Exception("Service unavailable")
            ]
            
            for error in transient_errors:
                if not worker.classify_error(error):
                    self.log_test("error_classification", False, f"Transient error classified as permanent: {error}")
                    return
            
            self.log_test("error_classification", True, "Error classification working correctly")
            
        except Exception as e:
            self.log_test("error_classification", False, f"Error during classification test: {e}")
    
    def test_worker_management(self):
        """Test worker management functions"""
        print("\n👥 Testing worker management...")
        
        try:
            # Test starting workers
            result = start_workers(2)
            if not result['success']:
                self.log_test("worker_management", False, f"Failed to start workers: {result['message']}")
                return
            
            # Check status
            status = get_worker_status()
            if not status['running']:
                self.log_test("worker_management", False, "Workers not running after start")
                return
            
            if status['num_workers'] != 2:
                self.log_test("worker_management", False, f"Expected 2 workers, got {status['num_workers']}")
                return
            
            # Let workers run for a bit
            time.sleep(5)
            
            # Check performance metrics
            metrics = get_performance_metrics()
            if 'processing_rate_per_hour' not in metrics:
                self.log_test("worker_management", False, "Performance metrics not available")
                return
            
            # Test stopping workers
            stop_result = stop_workers()
            if not stop_result['success']:
                self.log_test("worker_management", False, f"Failed to stop workers: {stop_result['message']}")
                return
            
            # Verify workers stopped
            final_status = get_worker_status()
            if final_status['running']:
                self.log_test("worker_management", False, "Workers still running after stop")
                return
            
            self.log_test("worker_management", True, "Worker management functions working correctly")
            
        except Exception as e:
            self.log_test("worker_management", False, f"Error during worker management test: {e}")
    
    def test_api_endpoints(self):
        """Test API endpoints for worker management"""
        print("\n🌐 Testing API endpoints...")
        
        try:
            # Test start workers endpoint
            response = requests.post(f"{API_BASE_URL}/jobs/workers/start", json={"num_workers": 2})
            if response.status_code != 200:
                self.log_test("api_endpoints", False, f"Start workers API failed: {response.status_code}")
                return
            
            # Test status endpoint
            response = requests.get(f"{API_BASE_URL}/jobs/workers/status")
            if response.status_code != 200:
                self.log_test("api_endpoints", False, f"Status API failed: {response.status_code}")
                return
            
            data = response.json()
            if not data['worker_status']['running']:
                self.log_test("api_endpoints", False, "API reports workers not running")
                return
            
            # Test performance endpoint
            response = requests.get(f"{API_BASE_URL}/jobs/workers/performance")
            if response.status_code != 200:
                self.log_test("api_endpoints", False, f"Performance API failed: {response.status_code}")
                return
            
            # Test stop workers endpoint
            response = requests.post(f"{API_BASE_URL}/jobs/workers/stop")
            if response.status_code != 200:
                self.log_test("api_endpoints", False, f"Stop workers API failed: {response.status_code}")
                return
            
            self.log_test("api_endpoints", True, "All API endpoints working correctly")
            
        except requests.exceptions.ConnectionError:
            self.log_test("api_endpoints", False, "Could not connect to API server (is it running?)")
        except Exception as e:
            self.log_test("api_endpoints", False, f"Error during API test: {e}")
    
    def test_graceful_shutdown(self):
        """Test graceful shutdown behavior"""
        print("\n🛑 Testing graceful shutdown...")
        
        try:
            # Start workers
            result = start_workers(2)
            if not result['success']:
                self.log_test("graceful_shutdown", False, "Could not start workers for shutdown test")
                return
            
            # Let them run briefly
            time.sleep(2)
            
            # Test graceful stop
            start_time = time.time()
            stop_result = stop_workers()
            stop_time = time.time() - start_time
            
            if not stop_result['success']:
                self.log_test("graceful_shutdown", False, f"Graceful stop failed: {stop_result['message']}")
                return
            
            # Check that shutdown was reasonably fast (should be < 30s)
            if stop_time > 30:
                self.log_test("graceful_shutdown", False, f"Shutdown took too long: {stop_time:.1f}s")
                return
            
            # Verify no videos stuck in processing
            processing_count = self.db.query(Video).filter(Video.status == 'processing').count()
            if processing_count > 0:
                self.log_test("graceful_shutdown", False, f"{processing_count} videos stuck in processing state")
                return
            
            self.log_test("graceful_shutdown", True, f"Graceful shutdown completed in {stop_time:.1f}s")
            
        except Exception as e:
            self.log_test("graceful_shutdown", False, f"Error during shutdown test: {e}")
    
    def test_parallel_processing(self):
        """Test that parallel processing actually improves performance"""
        print("\n⚡ Testing parallel processing performance...")
        
        try:
            # Ensure we have some videos to process
            pending_count = self.db.query(Video).filter(Video.status == 'pending').count()
            if pending_count < 3:
                self.log_test("parallel_processing", False, f"Not enough pending videos for test: {pending_count}")
                return
            
            # Test with 1 worker
            print("Testing with 1 worker...")
            start_time = time.time()
            result = start_workers(1)
            if result['success']:
                time.sleep(10)  # Let it process for 10 seconds
                status_1 = get_worker_status()
                processed_1 = status_1['total_processed']
                stop_workers()
            else:
                self.log_test("parallel_processing", False, "Could not start single worker")
                return
            
            # Reset video statuses for fair comparison
            self.db.execute("UPDATE videos SET status = 'pending', attempts = 0, last_error = NULL WHERE status IN ('completed', 'failed')")
            self.db.commit()
            
            # Test with 3 workers
            print("Testing with 3 workers...")
            time.sleep(2)  # Brief pause
            result = start_workers(3)
            if result['success']:
                time.sleep(10)  # Let it process for 10 seconds
                status_3 = get_worker_status()
                processed_3 = status_3['total_processed']
                stop_workers()
            else:
                self.log_test("parallel_processing", False, "Could not start multiple workers")
                return
            
            # Compare performance
            if processed_3 > processed_1:
                improvement = ((processed_3 - processed_1) / max(processed_1, 1)) * 100
                self.log_test("parallel_processing", True, f"Parallel processing improved by {improvement:.1f}% ({processed_1} vs {processed_3} videos)")
            else:
                self.log_test("parallel_processing", False, f"No improvement seen: {processed_1} vs {processed_3} videos processed")
            
        except Exception as e:
            self.log_test("parallel_processing", False, f"Error during parallel processing test: {e}")
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        print("🚀 Starting Task 1-4 Parallel Scraping Test Suite")
        print("=" * 60)
        
        # Setup
        self.setup_test_data()
        
        # Core functionality tests
        self.test_atomic_claiming()
        self.test_exponential_backoff()
        self.test_error_classification()
        
        # Worker management tests
        self.test_worker_management()
        self.test_graceful_shutdown()
        
        # Performance tests
        self.test_parallel_processing()
        
        # API tests (if server is running)
        self.test_api_endpoints()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 TASK 1-4 PARALLEL SCRAPING TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        print("-" * 40)
        
        for test_name, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {test_name}")
            if result['details']:
                print(f"   {result['details']}")
        
        # Implementation status
        print("\n🔧 Implementation Features:")
        print("-" * 40)
        features = [
            ("Atomic Job Claiming", "atomic_claiming" in self.test_results and self.test_results["atomic_claiming"]["success"]),
            ("Exponential Backoff", "exponential_backoff" in self.test_results and self.test_results["exponential_backoff"]["success"]),
            ("Error Classification", "error_classification" in self.test_results and self.test_results["error_classification"]["success"]),
            ("Worker Management", "worker_management" in self.test_results and self.test_results["worker_management"]["success"]),
            ("Graceful Shutdown", "graceful_shutdown" in self.test_results and self.test_results["graceful_shutdown"]["success"]),
            ("Parallel Processing", "parallel_processing" in self.test_results and self.test_results["parallel_processing"]["success"]),
            ("API Integration", "api_endpoints" in self.test_results and self.test_results["api_endpoints"]["success"])
        ]
        
        for feature, implemented in features:
            status = "✅ IMPLEMENTED" if implemented else "❌ NOT WORKING"
            print(f"{status} {feature}")
        
        # Final verdict
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED - TASK 1-4 IMPLEMENTATION COMPLETE!")
        elif failed_tests <= 2:
            print(f"\n⚠️  MOSTLY WORKING - {failed_tests} minor issues to address")
        else:
            print(f"\n🔧 NEEDS WORK - {failed_tests} tests failed")
        
        print(f"\nTest Duration: {(datetime.utcnow() - self.start_time).total_seconds():.1f} seconds")

def main():
    """Main test function"""
    tester = ParallelScrapingTester()
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
    finally:
        # Cleanup - ensure no workers are left running
        try:
            stop_workers()
        except:
            pass

if __name__ == "__main__":
    main()
