"""
Centralized Error Handling for Task 1-7

Implements centralized logging, recovery strategy, and automatic requeue logic
according to TRD Section 1.7 Error Handling.
"""

import logging
import traceback
from datetime import datetime
from typing import Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.models import Log, Video, Setting, SessionLocal


class TransientError(Exception):
    """Errors that should be retried with exponential backoff"""
    pass


class PermanentError(Exception):
    """Errors that should not be retried"""
    pass


def get_db_session() -> Session:
    """Get a database session for logging operations"""
    return SessionLocal()


def log_to_db(db: Session, video_id: Optional[int], level: str, message: str) -> bool:
    """
    Log entry to database logs table.
    
    Args:
        db: Database session
        video_id: Video ID if applicable (nullable)
        level: Log level (INFO, WARN, ERROR)
        message: Log message (will be truncated if too long)
        
    Returns:
        bool: True if logged successfully, False if failed
    """
    try:
        # Truncate message to prevent DB bloat (4000 chars max)
        truncated_message = message[-4000:] if len(message) > 4000 else message
        
        log_entry = Log(
            video_id=video_id,
            level=level.upper(),
            message=truncated_message,
            timestamp=datetime.utcnow()
        )
        
        db.add(log_entry)
        db.commit()
        return True
        
    except Exception as e:
        # Fallback to console logging if DB logging fails
        logging.error(f"Failed to log to database: {e}")
        db.rollback()
        return False


def log(level: str, message: str, video_id: Optional[int] = None):
    """
    Centralized logging function that logs to both console and database.
    
    Args:
        level: Log level (INFO, WARN, ERROR)
        message: Log message
        video_id: Optional video ID
    """
    # Log to console first
    log_level = getattr(logging, level.upper(), logging.INFO)
    if video_id:
        logging.log(log_level, f"Video {video_id}: {message}")
    else:
        logging.log(log_level, message)
    
    # Try to log to database
    try:
        db = get_db_session()
        try:
            log_to_db(db, video_id, level, message)
        finally:
            db.close()
    except Exception as e:
        # If DB logging fails, only log to console (avoid infinite recursion)
        logging.error(f"Database logging failed, using console only: {e}")


def log_exception(video_id: Optional[int], exc: Exception):
    """
    Log exception with full stack trace.
    
    Args:
        video_id: Video ID if applicable
        exc: Exception object
    """
    # Get full traceback
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    
    # Truncate to prevent unbounded size (keep last 4000 chars)
    trimmed_tb = tb[-4000:] if len(tb) > 4000 else tb
    
    # Log the exception
    log('ERROR', f"Exception: {str(exc)}\nTraceback: {trimmed_tb}", video_id)


def schedule_retry(db: Session, video_id: int, error: Exception):
    """
    Schedule a video for retry by updating its status and attempt count.
    
    Args:
        db: Database session
        video_id: Video ID to retry
        error: Exception that caused the failure
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            log('ERROR', f"Video {video_id} not found for retry", video_id)
            return
        
        # Get retry settings
        settings = db.query(Setting).filter(Setting.id == 1).first()
        max_retries = settings.max_retries if settings else 3
        
        video.attempts += 1
        video.last_error = str(error)
        
        if video.attempts < max_retries:
            video.status = 'pending'
            log('WARN', f"Scheduling retry (attempt {video.attempts}/{max_retries}): {str(error)}", video_id)
        else:
            video.status = 'failed'
            log('ERROR', f"Permanently failed after {video.attempts} attempts: {str(error)}", video_id)
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        log_exception(video_id, e)


def mark_failed(db: Session, video_id: int, error_message: str):
    """
    Mark a video as permanently failed.
    
    Args:
        db: Database session
        video_id: Video ID to mark as failed
        error_message: Error description
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            log('ERROR', f"Video {video_id} not found for failure marking", video_id)
            return
        
        video.status = 'failed'
        video.last_error = error_message
        video.attempts += 1
        
        db.commit()
        log('ERROR', f"Marked as permanently failed: {error_message}", video_id)
        
    except Exception as e:
        db.rollback()
        log_exception(video_id, e)


def reset_retry_attempts(db: Session) -> int:
    """
    Reset retry attempts for all pending and processing videos on startup.
    
    This implements the TRD requirement: "Retry attempts must reset after system restart"
    
    Args:
        db: Database session
        
    Returns:
        int: Number of videos that had their attempts reset
    """
    try:
        # Reset attempts for pending and processing videos
        result = db.execute(text("""
            UPDATE videos 
            SET attempts = 0 
            WHERE status IN ('pending', 'processing')
        """))
        
        reset_count = result.rowcount
        db.commit()
        
        log('INFO', f"Reset retry attempts for {reset_count} videos on startup")
        return reset_count
        
    except Exception as e:
        db.rollback()
        log_exception(None, e)
        return 0


def reset_processing_videos(db: Session) -> int:
    """
    Reset processing videos to pending on startup.
    
    Args:
        db: Database session
        
    Returns:
        int: Number of videos reset from processing to pending
    """
    try:
        result = db.execute(text("""
            UPDATE videos 
            SET status = 'pending'
            WHERE status = 'processing'
        """))
        
        reset_count = result.rowcount
        db.commit()
        
        log('INFO', f"Reset {reset_count} processing videos to pending on startup")
        return reset_count
        
    except Exception as e:
        db.rollback()
        log_exception(None, e)
        return 0


def handle_worker_exception(video_id: int, exc: Exception) -> str:
    """
    Handle exceptions in worker processing with proper classification.
    
    Args:
        video_id: Video ID being processed
        exc: Exception that occurred
        
    Returns:
        str: Action taken ('retry', 'failed', 'unknown')
    """
    db = get_db_session()
    try:
        # Classify exception type
        if isinstance(exc, TransientError):
            log('WARN', f"Transient error: {str(exc)}", video_id)
            schedule_retry(db, video_id, exc)
            return 'retry'
        
        elif isinstance(exc, PermanentError):
            log('ERROR', f"Permanent error: {str(exc)}", video_id)
            mark_failed(db, video_id, str(exc))
            return 'failed'
        
        else:
            # Unknown exception - log with full traceback and retry
            log_exception(video_id, exc)
            schedule_retry(db, video_id, exc)
            return 'retry'
    
    finally:
        db.close()


def get_recent_errors(db: Session, limit: int = 50) -> list:
    """
    Get recent error logs for dashboard display.
    
    Args:
        db: Database session
        limit: Maximum number of errors to return
        
    Returns:
        list: Recent error log entries
    """
    try:
        errors = db.query(Log).filter(
            Log.level == 'ERROR'
        ).order_by(
            Log.timestamp.desc()
        ).limit(limit).all()
        
        return [
            {
                'id': error.id,
                'video_id': error.video_id,
                'message': error.message,
                'timestamp': error.timestamp.isoformat()
            }
            for error in errors
        ]
        
    except Exception as e:
        log_exception(None, e)
        return []


def startup_recovery():
    """
    Perform startup recovery operations.
    
    This function should be called on application startup to:
    1. Reset processing videos to pending
    2. Reset retry attempts
    """
    db = get_db_session()
    try:
        log('INFO', "Starting recovery operations...")
        
        # Reset processing videos to pending
        reset_count = reset_processing_videos(db)
        
        # Reset retry attempts
        attempt_reset_count = reset_retry_attempts(db)
        
        log('INFO', f"Recovery complete: {reset_count} videos reset to pending, {attempt_reset_count} attempts reset")
        
    except Exception as e:
        log_exception(None, e)
    finally:
        db.close()


# Exception classification helpers
def classify_yt_dlp_error(error_message: str) -> type:
    """
    Classify yt-dlp errors as transient or permanent.
    
    Args:
        error_message: Error message from yt-dlp
        
    Returns:
        Exception class (TransientError or PermanentError)
    """
    error_lower = error_message.lower()
    
    # Permanent errors (don't retry)
    permanent_indicators = [
        'private video',
        'unavailable',
        'deleted',
        'no such file',
        'age restricted',
        'no subtitles available',
        'no native subtitles',
        'subtitles not available',
        'invalid url',
        'unknown video id'
    ]
    
    # Transient errors (should retry)
    transient_indicators = [
        'timeout',
        'connection',
        'network',
        'temporary',
        '503',
        '502', 
        '500',
        'rate limit',
        'quota exceeded'
    ]
    
    for indicator in permanent_indicators:
        if indicator in error_lower:
            return PermanentError
    
    for indicator in transient_indicators:
        if indicator in error_lower:
            return TransientError
    
    # Default to transient (retry) for unknown errors
    return TransientError
