#!/usr/bin/env python3
"""
Test script for queue management functionality.
Tests atomic video claiming, status management, reconciliation, and recovery.
"""

import sys
import os
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.models import init_db, SessionLocal, Channel, Video, Subtitle, Log
from utils.queue_manager import (
    claim_next_video,
    release_video,
    reset_processing_videos,
    reconcile_video_statuses,
    get_queue_statistics,
    get_channel_statistics,
    retry_failed_video,
    get_failed_videos
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_test_data():
    """Create test channel and videos"""
    db = SessionLocal()
    try:
        # Clean up existing test data
        db.query(Video).filter(Video.url.like('%test%')).delete(synchronize_session=False)
        db.query(Channel).filter(Channel.url.like('%test%')).delete(synchronize_session=False)
        db.commit()
        
        # Create test channel
        test_channel = Channel(
            url="https://www.youtube.com/@test-queue-management",
            name="Test Queue Management",
            total_videos=0
        )
        db.add(test_channel)
        db.flush()
        
        # Create test videos
        test_videos = []
        for i in range(10):
            video = Video(
                channel_id=test_channel.id,
                url=f"https://www.youtube.com/watch?v=test{i:03d}",
                title=f"Test Video {i:03d}",
                status='pending',
                attempts=0
            )
            test_videos.append(video)
            db.add(video)
        
        db.commit()
        
        print(f"✓ Created test channel with {len(test_videos)} videos")
        return test_channel.id, [v.id for v in test_videos]
        
    except Exception as e:
        db.rollback()
        print(f"✗ Failed to setup test data: {e}")
        return None, []
    finally:
        db.close()

def test_atomic_claiming():
    """Test that only one worker can claim a video at a time"""
    print("\n🧪 Testing atomic video claiming...")
    
    def worker_claim_videos(worker_id, results):
        """Worker function to claim videos"""
        claimed_videos = []
        db = SessionLocal()
        try:
            for _ in range(5):  # Try to claim up to 5 videos
                video_id = claim_next_video(db)
                if video_id:
                    claimed_videos.append(video_id)
                    time.sleep(0.01)  # Small delay to increase chance of race conditions
                else:
                    break
        finally:
            db.close()
        
        results[worker_id] = claimed_videos
    
    # Run multiple workers concurrently
    results = {}
    threads = []
    
    for i in range(5):  # 5 workers
        thread = threading.Thread(target=worker_claim_videos, args=(i, results))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify results
    all_claimed = []
    for worker_id, claimed in results.items():
        print(f"  Worker {worker_id} claimed: {claimed}")
        all_claimed.extend(claimed)
    
    # Check for duplicates
    if len(all_claimed) == len(set(all_claimed)):
        print("✓ No duplicate claims - atomic claiming works correctly")
        return True
    else:
        print("✗ Duplicate claims detected - atomic claiming failed")
        return False

def test_status_transitions():
    """Test video status transitions and retry logic"""
    print("\n🧪 Testing status transitions...")
    
    db = SessionLocal()
    try:
        # Claim a video
        video_id = claim_next_video(db)
        if not video_id:
            print("✗ No video available to claim")
            return False
        
        # Test successful completion
        success = release_video(db, video_id, 'completed')
        if not success:
            print("✗ Failed to mark video as completed")
            return False
        
        # Verify status
        video = db.query(Video).filter(Video.id == video_id).first()
        if video.status != 'completed':
            print(f"✗ Video status not updated correctly: {video.status}")
            return False
        
        print("✓ Successful completion transition works")
        
        # Test failure with retry
        video_id = claim_next_video(db)
        if video_id:
            success = release_video(db, video_id, 'failed', 'Test error message')
            if not success:
                print("✗ Failed to mark video as failed")
                return False
            
            # Check that it was requeued (attempts < max_retries)
            video = db.query(Video).filter(Video.id == video_id).first()
            if video.status == 'pending' and video.attempts == 1:
                print("✓ Failed video requeued for retry")
            elif video.status == 'failed':
                print("✓ Video marked as permanently failed")
            else:
                print(f"✗ Unexpected video state: status={video.status}, attempts={video.attempts}")
                return False
        else:
            print("✓ No more videos available (all claimed)")
        
        return True
        
    except Exception as e:
        print(f"✗ Status transition test failed: {e}")
        return False
    finally:
        db.close()

def test_reconciliation():
    """Test queue reconciliation functionality"""
    print("\n🧪 Testing queue reconciliation...")
    
    db = SessionLocal()
    try:
        # Create a video and manually add a subtitle to test reconciliation
        # First, get any processing video or create one
        processing_video = db.query(Video).filter(Video.status == 'processing').first()
        if not processing_video:
            # Get a pending video and set it to processing
            pending_video = db.query(Video).filter(Video.status == 'pending').first()
            if pending_video:
                pending_video.status = 'processing'
                db.commit()
                processing_video = pending_video
        
        if not processing_video:
            print("✗ No video available for reconciliation test")
            return False
        
        video_id = processing_video.id
        
        # Manually create a subtitle for this video
        subtitle = Subtitle(
            video_id=video_id,
            language='en',
            content='Test subtitle content for reconciliation'
        )
        db.add(subtitle)
        db.commit()
        
        print(f"  Created subtitle for video {video_id}")
        
        # Run reconciliation
        results = reconcile_video_statuses(db)
        print(f"  Reconciliation results: {results}")
        
        # Check if video was marked as completed
        video = db.query(Video).filter(Video.id == video_id).first()
        if video.status == 'completed':
            print("✓ Reconciliation correctly marked video as completed")
            return True
        else:
            print(f"✗ Reconciliation failed: video status is {video.status}")
            return False
        
    except Exception as e:
        print(f"✗ Reconciliation test failed: {e}")
        return False
    finally:
        db.close()

def test_crash_recovery():
    """Test crash recovery functionality"""
    print("\n🧪 Testing crash recovery...")
    
    db = SessionLocal()
    try:
        # Manually set some videos to 'processing' to simulate crash
        # SQLite doesn't support LIMIT in UPDATE, so use a subquery
        pending_videos = db.query(Video).filter(Video.status == 'pending').limit(3).all()
        processing_count = len(pending_videos)
        
        for video in pending_videos:
            video.status = 'processing'
        db.commit()
        
        if processing_count == 0:
            print("✗ No videos to test crash recovery with")
            return False
        
        print(f"  Simulated crash with {processing_count} processing videos")
        
        # Run crash recovery
        reset_count = reset_processing_videos(db)
        print(f"  Reset {reset_count} videos to pending")
        
        # The function resets ALL processing videos, not just the ones we set
        # So we check that it reset at least the ones we set
        if reset_count >= processing_count:
            print("✓ Crash recovery correctly reset processing videos")
            return True
        else:
            print(f"✗ Crash recovery failed: expected at least {processing_count}, got {reset_count}")
            return False
        
    except Exception as e:
        print(f"✗ Crash recovery test failed: {e}")
        return False
    finally:
        db.close()

def test_statistics():
    """Test queue statistics functionality"""
    print("\n🧪 Testing queue statistics...")
    
    db = SessionLocal()
    try:
        # Get overall statistics
        overall_stats = get_queue_statistics(db)
        print(f"  Overall queue stats: {overall_stats}")
        
        # Get channel-specific statistics
        channel_id = db.query(Channel).filter(Channel.url.like('%test%')).first().id
        channel_stats = get_channel_statistics(db, channel_id)
        print(f"  Channel {channel_id} stats: {channel_stats}")
        
        # Verify statistics make sense
        if overall_stats['total'] > 0 and channel_stats['total'] > 0:
            print("✓ Statistics functions return valid data")
            return True
        else:
            print("✗ Statistics functions returned invalid data")
            return False
        
    except Exception as e:
        print(f"✗ Statistics test failed: {e}")
        return False
    finally:
        db.close()

def test_failed_video_retry():
    """Test manual retry of failed videos"""
    print("\n🧪 Testing failed video retry...")
    
    db = SessionLocal()
    try:
        # Claim and fail a video multiple times to make it permanently failed
        # First, let's get any pending video
        pending_video = db.query(Video).filter(Video.status == 'pending').first()
        if not pending_video:
            print("✗ No pending video available for retry test")
            return False
        
        video_id = pending_video.id
        
        # Manually set it to failed with high attempts
        pending_video.status = 'failed'
        pending_video.attempts = 5  # More than max_retries (3)
        pending_video.last_error = 'Test permanent failure'
        db.commit()
        
        print(f"  Video {video_id} is set to permanently failed with {pending_video.attempts} attempts")
        
        # Test manual retry
        success = retry_failed_video(db, video_id)
        if not success:
            print("✗ Manual retry failed")
            return False
        
        # Check if it was reset
        video = db.query(Video).filter(Video.id == video_id).first()
        if video.status == 'pending' and video.attempts == 0:
            print("✓ Manual retry successfully reset failed video")
            return True
        else:
            print(f"✗ Manual retry failed: status={video.status}, attempts={video.attempts}")
            return False
        
    except Exception as e:
        print(f"✗ Failed video retry test failed: {e}")
        return False
    finally:
        db.close()

def cleanup_test_data():
    """Clean up test data"""
    db = SessionLocal()
    try:
        # Remove test data
        db.query(Subtitle).filter(Subtitle.content.like('%Test%')).delete(synchronize_session=False)
        db.query(Video).filter(Video.url.like('%test%')).delete(synchronize_session=False)
        db.query(Channel).filter(Channel.url.like('%test%')).delete(synchronize_session=False)
        db.commit()
        print("✓ Cleaned up test data")
    except Exception as e:
        print(f"✗ Failed to cleanup test data: {e}")
    finally:
        db.close()

def main():
    """Run all queue management tests"""
    print("Testing Queue Management Functionality")
    print("=" * 50)
    
    try:
        # Initialize database
        init_db()
        print("✓ Database initialized")
        
        # Setup test data
        channel_id, video_ids = setup_test_data()
        if not channel_id:
            print("❌ Failed to setup test data")
            return 1
        
        # Run tests
        tests = [
            ("Atomic Video Claiming", test_atomic_claiming),
            ("Status Transitions", test_status_transitions),
            ("Queue Reconciliation", test_reconciliation),
            ("Crash Recovery", test_crash_recovery),
            ("Queue Statistics", test_statistics),
            ("Failed Video Retry", test_failed_video_retry),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 {test_name}")
            try:
                if test_func():
                    print(f"✅ {test_name} PASSED")
                    passed += 1
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
        
        # Cleanup
        cleanup_test_data()
        
        print(f"\n📊 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All queue management tests passed!")
            return 0
        else:
            print("❌ Some queue management tests failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
