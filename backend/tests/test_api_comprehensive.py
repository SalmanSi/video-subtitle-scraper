#!/usr/bin/env python3
"""
Comprehensive API test for Queue Management endpoints
Tests all API endpoints without requiring external server
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from src.app import app
from src.db.models import get_db, Channel, Video

def setup_test_data():
    """Setup test data in the database"""
    print("Setting up test data...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Clear existing data
        db.query(Video).delete()
        db.query(Channel).delete()
        db.commit()
        
        # Insert test channel using ORM
        test_channel = Channel(
            url="https://youtube.com/@test",
            name="Test Channel",
            total_videos=4
        )
        db.add(test_channel)
        db.flush()  # Get the ID
        
        # Insert test videos using ORM
        test_videos = [
            Video(channel_id=test_channel.id, url="https://youtube.com/watch?v=video1", 
                  title="Test Video 1", status="pending"),
            Video(channel_id=test_channel.id, url="https://youtube.com/watch?v=video2", 
                  title="Test Video 2", status="processing"),
            Video(channel_id=test_channel.id, url="https://youtube.com/watch?v=video3", 
                  title="Test Video 3", status="completed"),
            Video(channel_id=test_channel.id, url="https://youtube.com/watch?v=video4", 
                  title="Test Video 4", status="failed"),
        ]
        
        for video in test_videos:
            db.add(video)
        
        db.commit()
        print("✓ Test data setup complete")
        
    finally:
        db.close()

def test_queue_statistics():
    """Test /api/videos/stats endpoint"""
    print("\n1. Testing Queue Statistics Endpoint")
    
    client = TestClient(app)
    response = client.get("/api/videos/stats")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    expected_keys = ["pending", "processing", "completed", "failed", "total"]
    
    for key in expected_keys:
        assert key in data, f"Missing key: {key}"
    
    # Verify counts match our test data
    assert data["pending"] == 1, f"Expected 1 pending, got {data['pending']}"
    assert data["processing"] == 1, f"Expected 1 processing, got {data['processing']}"
    assert data["completed"] == 1, f"Expected 1 completed, got {data['completed']}"
    assert data["failed"] == 1, f"Expected 1 failed, got {data['failed']}"
    assert data["total"] == 4, f"Expected 4 total, got {data['total']}"
    
    print("✓ Queue statistics endpoint working correctly")
    print(f"  Stats: {data}")

def test_video_list():
    """Test /api/videos endpoint"""
    print("\n2. Testing Video List Endpoint")
    
    client = TestClient(app)
    
    # Test without filters
    response = client.get("/api/videos")
    assert response.status_code == 200
    
    data = response.json()
    assert "videos" in data
    assert len(data["videos"]) == 4, f"Expected 4 videos, got {len(data['videos'])}"
    
    print("✓ Video list endpoint working")
    
    # Test with status filter
    response = client.get("/api/videos?status=pending")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["videos"]) == 1, f"Expected 1 pending video, got {len(data['videos'])}"
    assert data["videos"][0]["status"] == "pending"
    
    print("✓ Video list with status filter working")

def test_video_detail():
    """Test /api/videos/{video_id} endpoint"""
    print("\n3. Testing Video Detail Endpoint")
    
    client = TestClient(app)
    
    # First get a video ID from the list
    response = client.get("/api/videos?status=pending")
    assert response.status_code == 200
    
    data = response.json()
    video_id = data["videos"][0]["id"]
    
    # Test existing video
    response = client.get(f"/api/videos/{video_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == video_id
    assert data["title"] == "Test Video 1"
    assert data["status"] == "pending"
    
    print("✓ Video detail endpoint working")
    
    # Test non-existing video
    response = client.get("/api/videos/99999")
    assert response.status_code == 404
    
    print("✓ Video detail 404 handling working")

def test_video_retry():
    """Test /api/videos/{video_id}/retry endpoint"""
    print("\n4. Testing Video Retry Endpoint")
    
    client = TestClient(app)
    
    # Get a failed video ID
    response = client.get("/api/videos?status=failed")
    assert response.status_code == 200
    
    data = response.json()
    failed_video_id = data["videos"][0]["id"]
    
    # Test retrying a failed video
    response = client.post(f"/api/videos/{failed_video_id}/retry")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "message" in data
    
    # Verify video status was reset to pending
    response = client.get(f"/api/videos/{failed_video_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    
    print("✓ Video retry endpoint working")

def test_channel_videos():
    """Test /api/channels/{channel_id}/videos endpoint"""
    print("\n5. Testing Channel Videos Endpoint")
    
    client = TestClient(app)
    
    # First get the channel ID
    db = next(get_db())
    try:
        channel = db.query(Channel).first()
        channel_id = channel.id
    finally:
        db.close()
    
    response = client.get(f"/api/channels/{channel_id}/videos")
    assert response.status_code == 200
    
    data = response.json()
    assert "videos" in data
    assert len(data["videos"]) == 4, f"Expected 4 videos for channel, got {len(data['videos'])}"
    
    print("✓ Channel videos endpoint working")

def test_jobs_status():
    """Test /api/jobs/status endpoint"""
    print("\n6. Testing Jobs Status Endpoint")
    
    client = TestClient(app)
    
    response = client.get("/api/jobs/status")
    assert response.status_code == 200
    
    data = response.json()
    expected_keys = ["queue_stats", "worker_count", "active_jobs"]
    
    for key in expected_keys:
        assert key in data, f"Missing key: {key}"
    
    print("✓ Jobs status endpoint working")
    print(f"  Worker count: {data['worker_count']}")
    print(f"  Active jobs: {data['active_jobs']}")

def cleanup_test_data():
    """Clean up test data"""
    print("\n7. Cleaning up test data...")
    
    db = next(get_db())
    try:
        db.query(Video).delete()
        db.query(Channel).delete()
        db.commit()
        print("✓ Test data cleaned up")
    finally:
        db.close()

def main():
    """Run all API tests"""
    print("Testing Queue Management API Endpoints")
    print("=" * 50)
    
    try:
        # Setup
        setup_test_data()
        
        # Run tests
        test_queue_statistics()
        test_video_list()
        test_video_detail()
        test_video_retry()
        test_channel_videos()
        test_jobs_status()
        
        # Cleanup
        cleanup_test_data()
        
        print("\n🎉 All API endpoint tests passed!")
        print("Queue Management system is fully functional!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
