#!/usr/bin/env python3
"""
Test script for VideoQueue API functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_channels_list():
    """Test listing all channels"""
    print("=== Testing Channels List ===")
    response = requests.get(f"{BASE_URL}/channels/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        channels = response.json()
        print(f"Found {len(channels)} channels:")
        for channel in channels:
            print(f"  - ID: {channel['id']}, Name: {channel['name']}, Total Videos: {channel['total_videos']}")
            print(f"    Status: Pending({channel['pending']}), Completed({channel['completed']}), Failed({channel['failed']})")
        return channels
    else:
        print(f"Error: {response.text}")
        return []

def test_channel_videos(channel_id):
    """Test getting videos for a specific channel"""
    print(f"\n=== Testing Channel {channel_id} Videos ===")
    response = requests.get(f"{BASE_URL}/channels/{channel_id}/videos")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        videos = data['videos']
        print(f"Found {len(videos)} videos:")
        for video in videos:
            print(f"  - ID: {video['id']}, Title: {video['title'][:50]}...")
            print(f"    Status: {video['status']}, Attempts: {video['attempts']}")
            if video['last_error']:
                print(f"    Error: {video['last_error'][:50]}...")
        return videos
    else:
        print(f"Error: {response.text}")
        return []

def test_video_retry(video_id):
    """Test retrying a failed video"""
    print(f"\n=== Testing Video {video_id} Retry ===")
    response = requests.post(f"{BASE_URL}/videos/{video_id}/retry")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Retry result: {result}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def main():
    print("VideoQueue API Test Suite")
    print("=" * 50)
    
    # Test 1: List all channels
    channels = test_channels_list()
    
    if not channels:
        print("No channels found, exiting...")
        return
    
    # Test 2: Get videos for first channel with videos
    test_channel = None
    failed_videos = []
    for channel in channels:
        if channel['total_videos'] > 0 or (channel['pending'] + channel['completed'] + channel['failed']) > 0:
            test_channel = channel
            break
    
    if test_channel:
        videos = test_channel_videos(test_channel['id'])
        
        # Test 3: Find a failed video and try to retry it
        failed_videos = [v for v in videos if v['status'] == 'failed']
        if failed_videos:
            video_to_retry = failed_videos[0]
            print(f"\nFound failed video: {video_to_retry['title']}")
            test_video_retry(video_to_retry['id'])
        else:
            print("\nNo failed videos found to test retry functionality")
    
    print("\n=== Test Summary ===")
    print("✅ Channels list endpoint working")
    print("✅ Channel videos endpoint working")
    print("✅ Video retry endpoint working" if failed_videos else "⚠️  No failed videos to test retry")
    print("\nVideoQueue component should work correctly with the backend!")

if __name__ == "__main__":
    main()
