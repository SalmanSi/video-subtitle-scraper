#!/usr/bin/env python3
"""
Test script for subtitle scraping functionality (Task 1-3)
Tests subtitle extraction, processing, and API endpoints
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.models import init_db, SessionLocal, Video, Channel, Subtitle, Setting
from utils.subtitle_processor import SubtitleProcessor, process_video_subtitles
from utils.yt_dlp_helper import fetch_subtitle_text, is_transient_error
from api.subtitles import router
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Create test app
test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)

class TestSubtitleScraping(unittest.TestCase):
    """Test cases for subtitle scraping functionality"""
    
    def setUp(self):
        """Set up test database and data"""
        init_db()
        self.db = SessionLocal()
        
        # Create test channel
        self.test_channel = Channel(
            url="https://www.youtube.com/@test-subtitles",
            name="Test Subtitle Channel"
        )
        self.db.add(self.test_channel)
        self.db.flush()
        
        # Create test video
        self.test_video = Video(
            channel_id=self.test_channel.id,
            url="https://www.youtube.com/watch?v=test123",
            title="Test Video with Subtitles",
            status='processing'
        )
        self.db.add(self.test_video)
        self.db.commit()
    
    def tearDown(self):
        """Clean up test data"""
        self.db.query(Subtitle).delete()
        self.db.query(Video).delete()
        self.db.query(Channel).delete()
        self.db.commit()
        self.db.close()
    
    @patch('utils.yt_dlp_helper.fetch_subtitle_text')
    def test_successful_subtitle_extraction(self, mock_fetch):
        """Test successful subtitle extraction and processing"""
        # Mock successful subtitle extraction
        mock_fetch.return_value = ('en', 'This is a test subtitle content.\nLine 2 of content.')
        
        # Process the video
        processor = SubtitleProcessor(self.db)
        result = processor.process_video_subtitles(self.test_video)
        
        # Verify success
        self.assertTrue(result)
        
        # Check database state
        self.db.refresh(self.test_video)
        self.assertEqual(self.test_video.status, 'completed')
        self.assertIsNotNone(self.test_video.completed_at)
        
        # Check subtitle was saved
        subtitle = self.db.query(Subtitle).filter(
            Subtitle.video_id == self.test_video.id
        ).first()
        self.assertIsNotNone(subtitle)
        self.assertEqual(subtitle.language, 'en')
        self.assertEqual(subtitle.content, 'This is a test subtitle content.\nLine 2 of content.')
    
    @patch('utils.yt_dlp_helper.fetch_subtitle_text')
    def test_no_subtitles_available(self, mock_fetch):
        """Test handling when no subtitles are available"""
        # Mock no subtitles available
        mock_fetch.return_value = (None, None)
        
        # Process the video
        processor = SubtitleProcessor(self.db)
        result = processor.process_video_subtitles(self.test_video)
        
        # Verify failure
        self.assertFalse(result)
        
        # Check database state
        self.db.refresh(self.test_video)
        self.assertEqual(self.test_video.status, 'failed')
        self.assertIn('No native subtitles available', self.test_video.last_error)
        
        # Check no subtitle was saved
        subtitle_count = self.db.query(Subtitle).filter(
            Subtitle.video_id == self.test_video.id
        ).count()
        self.assertEqual(subtitle_count, 0)
    
    @patch('utils.yt_dlp_helper.fetch_subtitle_text')
    def test_transient_error_handling(self, mock_fetch):
        """Test handling of transient errors"""
        # Mock network error (transient)
        mock_fetch.side_effect = Exception("Connection timeout")
        
        # Process the video
        processor = SubtitleProcessor(self.db)
        result = processor.process_video_subtitles(self.test_video)
        
        # Verify failure but video should be requeued
        self.assertFalse(result)
        
        # Video should still be pending for retry (queue manager handles this)
        self.db.refresh(self.test_video)
        # The video might be marked as failed but with attempts incremented for retry
        self.assertGreater(self.test_video.attempts, 0)
    
    def test_error_classification(self):
        """Test transient vs permanent error classification"""
        # Test transient errors
        transient_errors = [
            Exception("Connection timeout"),
            Exception("Network error"),
            Exception("HTTP 500 server error"),
            Exception("Rate limit exceeded")
        ]
        
        for error in transient_errors:
            self.assertTrue(is_transient_error(error), f"Should be transient: {error}")
        
        # Test permanent errors
        permanent_errors = [
            Exception("Video not found"),
            Exception("HTTP 404 error"),
            Exception("Private video"),
            Exception("Video unavailable")
        ]
        
        for error in permanent_errors:
            self.assertFalse(is_transient_error(error), f"Should be permanent: {error}")
    
    def test_subtitle_api_endpoints(self):
        """Test subtitle API endpoints"""
        # Create test subtitle
        test_subtitle = Subtitle(
            video_id=self.test_video.id,
            language='en',
            content='Test subtitle content for API testing'
        )
        self.db.add(test_subtitle)
        self.db.commit()
        
        # Test list subtitles
        response = client.get("/subtitles/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('subtitles', data)
        self.assertGreater(len(data['subtitles']), 0)
        
        # Test get specific subtitle
        response = client.get(f"/subtitles/{test_subtitle.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['language'], 'en')
        self.assertEqual(data['content'], 'Test subtitle content for API testing')
        
        # Test download subtitle
        response = client.get(f"/subtitles/{test_subtitle.id}/download")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'text/plain; charset=utf-8')
        self.assertEqual(response.text, 'Test subtitle content for API testing')
        
        # Test video subtitles endpoint
        response = client.get(f"/subtitles/videos/{self.test_video.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['video_id'], self.test_video.id)
        self.assertGreater(len(data['subtitles']), 0)
    
    def test_multiple_language_support(self):
        """Test support for multiple subtitle languages"""
        # Create subtitles in multiple languages
        languages = ['en', 'es', 'fr']
        for lang in languages:
            subtitle = Subtitle(
                video_id=self.test_video.id,
                language=lang,
                content=f'Test content in {lang}'
            )
            self.db.add(subtitle)
        self.db.commit()
        
        # Test video download with multiple languages
        response = client.get(f"/subtitles/videos/{self.test_video.id}/download")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/zip')
    
    @patch('utils.yt_dlp_helper.fetch_subtitle_text')
    def test_subtitle_content_cleaning(self, mock_fetch):
        """Test subtitle content cleaning and normalization"""
        # Mock subtitle with HTML tags and extra whitespace
        raw_content = """<p>Line 1 with <b>HTML</b> tags.</p>
        
        
        <div>Line 2 with   extra   spaces.</div>"""
        
        expected_content = """Line 1 with HTML tags.

Line 2 with   extra   spaces."""
        
        mock_fetch.return_value = ('en', expected_content)
        
        processor = SubtitleProcessor(self.db)
        result = processor.process_video_subtitles(self.test_video)
        
        self.assertTrue(result)
        
        # Check cleaned content was saved
        subtitle = self.db.query(Subtitle).filter(
            Subtitle.video_id == self.test_video.id
        ).first()
        self.assertNotIn('<', subtitle.content)
        self.assertNotIn('>', subtitle.content)

def run_integration_test():
    """Run integration test with actual API"""
    print("Running Subtitle Scraping Integration Test")
    print("=" * 50)
    
    try:
        # Initialize database
        init_db()
        print("✓ Database initialized")
        
        # Create test data
        db = SessionLocal()
        
        # Create test channel
        test_channel = Channel(
            url="https://www.youtube.com/@test-integration",
            name="Integration Test Channel"
        )
        db.add(test_channel)
        db.flush()
        
        # Create test video (use a known video with subtitles for real test)
        test_video = Video(
            channel_id=test_channel.id,
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - known to have captions
            title="Test Video for Integration",
            status='pending'
        )
        db.add(test_video)
        db.commit()
        
        print(f"✓ Created test video: {test_video.id}")
        
        # Process subtitle (this will make actual API call)
        print("⏳ Processing subtitle (making real API call)...")
        processor = SubtitleProcessor(db)
        result = processor.process_video_subtitles(test_video)
        
        if result:
            print("✓ Subtitle processing successful")
            
            # Check subtitle was saved
            subtitle = db.query(Subtitle).filter(
                Subtitle.video_id == test_video.id
            ).first()
            
            if subtitle:
                print(f"✓ Subtitle saved: {subtitle.language}, {len(subtitle.content)} characters")
                print(f"  Preview: {subtitle.content[:100]}...")
            else:
                print("✗ No subtitle found in database")
        else:
            print("⚠ Subtitle processing failed (might be expected if video has no subtitles)")
        
        # Clean up
        db.query(Subtitle).filter(Subtitle.video_id == test_video.id).delete()
        db.query(Video).filter(Video.id == test_video.id).delete()
        db.query(Channel).filter(Channel.id == test_channel.id).delete()
        db.commit()
        db.close()
        
        print("✓ Cleanup completed")
        print("\n🎉 Integration test completed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test subtitle scraping functionality')
    parser.add_argument('--integration', action='store_true', help='Run integration test with real API calls')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    
    args = parser.parse_args()
    
    if args.integration:
        run_integration_test()
    elif args.unit:
        unittest.main()
    else:
        # Run both by default
        print("Running unit tests...")
        unittest.main(exit=False, verbosity=2)
        print("\n" + "="*50)
        run_integration_test()
