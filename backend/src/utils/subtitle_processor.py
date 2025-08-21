"""
Subtitle Processing Module for Task 1-3
Handles video subtitle extraction, processing, and database operations

Enhanced with centralized error handling from Task 1-7.
"""

import logging
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import Video, Subtitle, Log, Setting
from utils.yt_dlp_helper import fetch_subtitle_text, is_transient_error
from utils.queue_manager import release_video
from utils.error_handler import (
    log, log_exception, TransientError, PermanentError, 
    classify_yt_dlp_error
)

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
        Process subtitles for a single video with centralized error handling.
        
        Args:
            video: Video object to process
            
        Returns:
            True if successful, False if failed
        """
        try:
            log('INFO', f"Processing subtitles for video {video.id}: {video.title}", video.id)
            
            # Extract subtitle text using improved function with auto-generated support
            from utils.yt_dlp_helper import extract_single_video_subtitles
            
            preferred_langs = self.settings['preferred_languages']
            
            # Use the improved function that supports auto-generated subtitles
            result = extract_single_video_subtitles(
                video_url=video.url,
                preferred_langs=preferred_langs,
                include_auto_generated=True,  # Always include auto-generated subtitles
                max_retries=self.settings['max_retries'],
                base_delay=1.0
            )
            
            if not result['success']:
                if result['is_transient_error']:
                    error_msg = f"Transient error: {result['error']}"
                    raise TransientError(error_msg)
                else:
                    error_msg = f"Permanent error: {result['error']}"
                    raise PermanentError(error_msg)
            
            # Extract the results
            lang = result['language']
            content = result['content']
            
            if not lang or not content:
                # No subtitles available - this is a permanent error
                error_msg = 'No subtitles (native or auto-generated) available'
                raise PermanentError(error_msg)
            
            # Save subtitle to database
            success = self._save_subtitle(video.id, lang, content)
            if not success:
                error_msg = 'Failed to save subtitle to database'
                raise Exception(error_msg)  # This will be classified as transient
            
            # Mark video as completed
            self._mark_video_completed(video)
            
            is_auto = result.get('is_auto_generated', False)
            subtitle_type = 'auto-generated' if is_auto else 'native'
            log('INFO', f'Successfully extracted {lang} {subtitle_type} subtitles ({len(content)} characters)', video.id)
            
            return True
            
        except (TransientError, PermanentError):
            # Re-raise classified errors for proper handling by worker
            raise
            
        except Exception as e:
            # Classify unknown errors using centralized logic
            error_class = classify_yt_dlp_error(str(e))
            
            if error_class == PermanentError:
                raise PermanentError(str(e)) from e
            else:
                raise TransientError(str(e)) from e
    
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
                log('INFO', f"Updated existing {language} subtitle for video {video_id}", video_id)
            else:
                # Create new subtitle
                subtitle = Subtitle(
                    video_id=video_id,
                    language=language,
                    content=content,
                    downloaded_at=datetime.utcnow()
                )
                self.db.add(subtitle)
                log('INFO', f"Created new {language} subtitle for video {video_id}", video_id)
            
            self.db.commit()
            return True
            
        except IntegrityError as e:
            self.db.rollback()
            log('ERROR', f"Database integrity error saving subtitle: {str(e)}", video_id)
            return False
        except Exception as e:
            self.db.rollback()
            log('ERROR', f"Error saving subtitle: {str(e)}", video_id)
            return False
    
    def _mark_video_completed(self, video: Video):
        """Mark video as completed"""
        try:
            video.status = 'completed'
            video.completed_at = datetime.utcnow()
            self.db.commit()
            log('INFO', f"Marked video as completed", video.id)
        except Exception as e:
            self.db.rollback()
            log_exception(video.id, e)
            raise

def process_video_subtitles(video: Video, db: Session) -> bool:
    """
    Standalone function to process video subtitles with centralized error handling.
    
    Args:
        video: Video object to process
        db: Database session
        
    Returns:
        True if successful, False if failed
    """
    processor = SubtitleProcessor(db)
    return processor.process_video_subtitles(video)
