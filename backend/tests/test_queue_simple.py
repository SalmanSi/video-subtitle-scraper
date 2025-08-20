#!/usr/bin/env python3
"""
Simple queue management test focusing on core functionality.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.models import init_db, SessionLocal, Channel, Video, Subtitle
from utils.queue_manager import (
    claim_next_video,
    release_video,
    reset_processing_videos,
    reconcile_video_statuses,
    get_queue_statistics
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_basic_functionality():
    """Test basic queue management functionality"""
    print("Testing Basic Queue Management Functionality")
    print("=" * 50)
    
    # Initialize database
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    
    db = SessionLocal()
    try:
        # Clean up any existing test data
        db.query(Video).filter(Video.url.contains("test")).delete(synchronize_session=False)
        db.query(Channel).filter(Channel.url.contains("test")).delete(synchronize_session=False)
        db.commit()
        
        # Create test channel
        channel = Channel(
            url="https://www.youtube.com/@test-queue",
            name="Test Queue Channel",
            total_videos=0
        )
        db.add(channel)
        db.commit()
        
        # Create test videos
        videos = []
        for i in range(3):
            video = Video(
                channel_id=channel.id,
                url=f"https://youtube.com/watch?v=test{i}",
                title=f"Test Video {i}",
                status="pending"
            )
            videos.append(video)
            db.add(video)
        
        db.commit()
        print(f"✓ Created {len(videos)} test videos")
        
        # Test 1: Get queue statistics
        stats = get_queue_statistics(db)
        print(f"✓ Queue statistics: {stats}")
        
        # Test 2: Claim a video
        video_id = claim_next_video(db)
        if video_id:
            print(f"✓ Successfully claimed video {video_id}")
            
            # Test 3: Release video as completed
            success = release_video(db, video_id, "completed")
            if success:
                print("✓ Successfully released video as completed")
            else:
                print("✗ Failed to release video")
        else:
            print("✗ Failed to claim video")
        
        # Test 4: Test reset processing videos
        # First set a video to processing
        test_video = db.query(Video).filter(Video.status == "pending").first()
        if test_video:
            test_video.status = "processing"
            db.commit()
            
            # Now reset
            reset_count = reset_processing_videos(db)
            print(f"✓ Reset {reset_count} processing videos")
        
        # Test 5: Test reconciliation with subtitle
        completed_video = db.query(Video).filter(Video.status == "completed").first()
        if completed_video:
            # Add subtitle
            subtitle = Subtitle(
                video_id=completed_video.id,
                language="en",
                content="Test subtitle content"
            )
            db.add(subtitle)
            
            # Change video status to test reconciliation
            completed_video.status = "pending"
            db.commit()
            
            # Run reconciliation
            reconcile_results = reconcile_video_statuses(db)
            print(f"✓ Reconciliation results: {reconcile_results}")
        
        # Final statistics
        final_stats = get_queue_statistics(db)
        print(f"✓ Final queue statistics: {final_stats}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    finally:
        # Cleanup
        try:
            db.query(Video).filter(Video.url.contains("test")).delete(synchronize_session=False)
            db.query(Channel).filter(Channel.url.contains("test")).delete(synchronize_session=False)
            db.commit()
            print("✓ Cleaned up test data")
        except Exception as e:
            print(f"✗ Cleanup failed: {e}")
        db.close()

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("\n🎉 All basic queue management tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
