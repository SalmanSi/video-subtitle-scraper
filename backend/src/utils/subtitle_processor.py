"""
Subtitle Processing Module for Task 1-3
Handles video subtitle extraction, processing, and database operations
"""

import logging
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import Video, Subtitle, Log, Setting
from utils.yt_dlp_helper import fetch_subtitle_text, is_transient_error
from utils.queue_manager import release_video

# Configure logging
logger = logging.getLogger(__name__)

class SubtitleProcessor:
    """Handles subtitle extraction and processing for videos"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.settings = self._get_settings()
    
    def _get_settings(self) -> dict:
        """Get application settings from database"""
        settings = self.db.query(Setting).filter(Setting.id == 1).first()
        if not settings:
            # Return defaults if no settings found
            return {
                'preferred_languages': ['en'],
                'max_retries': 3,
                'backoff_factor': 2.0
            }
        
        return {
            'preferred_languages': ['en'],  # TODO: Make configurable
            'max_retries': settings.max_retries,
            'backoff_factor': settings.backoff_factor
        }
    
    def process_video_subtitles(self, video: Video) -> bool:
        """
        Process subtitles for a single video.
        
        Args:
            video: Video object to process
            
        Returns:
            True if successful, False if failed
        """
        try:
            logger.info(f"Processing subtitles for video {video.id}: {video.title}")
            
            # Extract subtitle text
            preferred_langs = self.settings['preferred_languages']
            lang, content = fetch_subtitle_text(video.url, preferred_langs)
            
            if not lang or not content:
                # No subtitles available - mark as failed
                error_msg = 'No native subtitles available'
                self._mark_video_failed(video, error_msg)
                self._log_error(video.id, 'WARN', error_msg)
                return False
            
            # Save subtitle to database
            success = self._save_subtitle(video.id, lang, content)
            if not success:
                error_msg = 'Failed to save subtitle to database'
                self._mark_video_failed(video, error_msg)
                self._log_error(video.id, 'ERROR', error_msg)
                return False
            
            # Mark video as completed
            self._mark_video_completed(video)
            self._log_info(video.id, f'Successfully extracted {lang} subtitles ({len(content)} characters)')
            
            logger.info(f"Successfully processed video {video.id}")
            return True
            
        except Exception as e:
            error_msg = f"Error processing video {video.id}: {str(e)}"
            logger.error(error_msg)
            
            # Determine if error is transient or permanent
            if is_transient_error(e):
                # Let the queue manager handle retry logic
                success = release_video(self.db, video.id, 'failed', str(e))
                if success:
                    self._log_error(video.id, 'WARN', f'Transient error, will retry: {str(e)}')
                else:
                    self._log_error(video.id, 'ERROR', f'Failed to requeue video: {str(e)}')
            else:
                # Permanent error - mark as failed
                self._mark_video_failed(video, str(e))
                self._log_error(video.id, 'ERROR', f'Permanent error: {str(e)}')
            
            return False
    
    def _save_subtitle(self, video_id: int, language: str, content: str) -> bool:
        """
        Save subtitle content to database.
        
        Args:
            video_id: Video ID
            language: Language code
            content: Subtitle text content
            
        Returns:
            True if saved successfully
        """
        try:
            # Check if subtitle already exists for this video and language
            existing = self.db.query(Subtitle).filter(
                Subtitle.video_id == video_id,
                Subtitle.language == language
            ).first()
            
            if existing:
                # Update existing subtitle
                existing.content = content
                existing.downloaded_at = datetime.utcnow()
                logger.info(f"Updated existing {language} subtitle for video {video_id}")
            else:
                # Create new subtitle
                subtitle = Subtitle(
                    video_id=video_id,
                    language=language,
                    content=content,
                    downloaded_at=datetime.utcnow()
                )
                self.db.add(subtitle)
                logger.info(f"Created new {language} subtitle for video {video_id}")
            
            self.db.commit()
            return True
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error saving subtitle for video {video_id}: {str(e)}")
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving subtitle for video {video_id}: {str(e)}")
            return False
    
    def _mark_video_completed(self, video: Video):
        """Mark video as completed"""
        try:
            video.status = 'completed'
            video.completed_at = datetime.utcnow()
            self.db.commit()
            logger.debug(f"Marked video {video.id} as completed")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking video {video.id} as completed: {str(e)}")
            raise
    
    def _mark_video_failed(self, video: Video, error_message: str):
        """Mark video as failed"""
        try:
            video.status = 'failed'
            video.last_error = error_message
            video.attempts += 1
            self.db.commit()
            logger.debug(f"Marked video {video.id} as failed: {error_message}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking video {video.id} as failed: {str(e)}")
            raise
    
    def _log_info(self, video_id: int, message: str):
        """Log info message"""
        self._log_message(video_id, 'INFO', message)
    
    def _log_error(self, video_id: int, level: str, message: str):
        """Log error message"""
        self._log_message(video_id, level, message)
    
    def _log_message(self, video_id: int, level: str, message: str):
        """Log message to database"""
        try:
            log_entry = Log(
                video_id=video_id,
                level=level,
                message=message,
                timestamp=datetime.utcnow()
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error logging message: {str(e)}")

def process_video_subtitles(video: Video, db: Session) -> bool:
    """
    Standalone function to process video subtitles.
    
    Args:
        video: Video object to process
        db: Database session
        
    Returns:
        True if successful, False if failed
    """
    processor = SubtitleProcessor(db)
    return processor.process_video_subtitles(video)
