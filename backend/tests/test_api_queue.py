#!/usr/bin/env python3
"""
Test queue management API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_queue_api_endpoints():
    """Test the queue management API endpoints"""
    print("Testing Queue Management API Endpoints")
    print("=" * 50)
    
    # First, add a test channel to get some videos
    print("\n1. Adding test channel...")
    channel_data = {
        "url": "https://www.youtube.com/@PythonExplained"
    }
    
    response = requests.post(f"{BASE_URL}/channels/", json=channel_data)
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Added channel: {result.get('channels_created', 0)} channels, {result.get('videos_enqueued', 0)} videos")
    else:
        print(f"✗ Failed to add channel: {response.status_code} - {response.text}")
        return False
    
    # Test video statistics
    print("\n2. Testing video statistics...")
    response = requests.get(f"{BASE_URL}/videos/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"✓ Video statistics: {stats}")
    else:
        print(f"✗ Failed to get video stats: {response.status_code}")
        return False
    
    # Test video listing
    print("\n3. Testing video listing...")
    response = requests.get(f"{BASE_URL}/videos/?status=pending&limit=5")
    if response.status_code == 200:
        videos = response.json()
        print(f"✓ Listed {len(videos)} pending videos")
        
        if videos:
            # Test getting a specific video
            video_id = videos[0]['id']
            response = requests.get(f"{BASE_URL}/videos/{video_id}")
            if response.status_code == 200:
                video = response.json()
                print(f"✓ Retrieved video {video_id}: {video['title']}")
            else:
                print(f"✗ Failed to get video {video_id}")
                return False
    else:
        print(f"✗ Failed to list videos: {response.status_code}")
        return False
    
    # Test channel videos
    print("\n4. Testing channel-specific videos...")
    response = requests.get(f"{BASE_URL}/channels/")
    if response.status_code == 200:
        channels = response.json()
        if channels:
            channel_id = channels[0]['id']
            
            # Get channel videos
            response = requests.get(f"{BASE_URL}/videos/channels/{channel_id}/videos")
            if response.status_code == 200:
                channel_videos = response.json()
                print(f"✓ Channel {channel_id} has {len(channel_videos)} videos")
                
                # Get channel stats
                response = requests.get(f"{BASE_URL}/videos/channels/{channel_id}/stats")
                if response.status_code == 200:
                    channel_stats = response.json()
                    print(f"✓ Channel stats: {channel_stats}")
                else:
                    print(f"✗ Failed to get channel stats")
                    return False
            else:
                print(f"✗ Failed to get channel videos")
                return False
    else:
        print(f"✗ Failed to get channels")
        return False
    
    # Test failed videos list
    print("\n5. Testing failed videos list...")
    response = requests.get(f"{BASE_URL}/videos/failed/list")
    if response.status_code == 200:
        failed_result = response.json()
        print(f"✓ Found {failed_result.get('count', 0)} failed videos")
    else:
        print(f"✗ Failed to get failed videos: {response.status_code}")
        return False
    
    # Test job status endpoints
    print("\n6. Testing job status...")
    response = requests.get(f"{BASE_URL}/jobs/status")
    if response.status_code == 200:
        job_status = response.json()
        print(f"✓ Job status: {job_status['status']}")
    else:
        print(f"✗ Failed to get job status: {response.status_code}")
        return False
    
    print("\n🎉 All API endpoint tests passed!")
    return True

if __name__ == "__main__":
    import sys
    
    try:
        success = test_queue_api_endpoints()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)
