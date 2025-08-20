"""
Queue management utilities for video processing.

Implements atomic video claiming, status management, reconciliation,
and recovery according to TRD Section 1.2.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import text, func
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging
import time

from db.models import Video, Subtitle, Log, Setting


def claim_next_video(db: Session) -> Optional[int]:
    """
    Atomically claim the next pending video for processing.
    
    Uses SQLite atomic UPDATE to ensure only one worker can claim a video.
    
    Returns:
        video_id (int) if a video was claimed, None if queue is empty
    """
    try:
        # For SQLite compatibility, use a simpler approach
        # First, get the next pending video
        video = db.query(Video).filter(Video.status == 'pending').order_by(Video.id).first()
        
        if not video:
            logging.debug("No pending videos available")
            return None
        
        # Try to update the specific video to processing
        result = db.execute(text("""
            UPDATE videos 
            SET status = 'processing'
            WHERE id = :video_id AND status = 'pending'
        """), {'video_id': video.id})
        
        if result.rowcount == 1:
            db.commit()
            logging.info(f"Claimed video {video.id} for processing")
            return video.id
        else:
            # Another worker claimed it first
            db.rollback()
            logging.debug(f"Video {video.id} was claimed by another worker")
            return None
            
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to claim video: {e}")
        return None


def release_video(db: Session, video_id: int, status: str, error_message: str = None) -> bool:
    """
    Release a video back to the queue or mark as completed/failed.
    
    Args:
        db: Database session
        video_id: ID of the video to release
        status: New status ('pending', 'completed', 'failed')
        error_message: Error message if status is 'failed'
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logging.error(f"Video {video_id} not found")
            return False
        
        # Get retry settings
        settings = db.query(Setting).filter(Setting.id == 1).first()
        max_retries = settings.max_retries if settings else 3
        
        if status == 'failed':
            video.attempts += 1
            video.last_error = error_message
            
            # Check if we should retry or mark as permanently failed
            if video.attempts < max_retries:
                video.status = 'pending'  # Requeue for retry
                logging.info(f"Video {video_id} failed, requeuing (attempt {video.attempts}/{max_retries})")
            else:
                video.status = 'failed'
                logging.warning(f"Video {video_id} permanently failed after {video.attempts} attempts")
                
                # Log the failure
                log_entry = Log(
                    video_id=video_id,
                    level='ERROR',
                    message=f"Video permanently failed: {error_message}",
                    timestamp=datetime.utcnow()
                )
                db.add(log_entry)
        
        elif status == 'completed':
            video.status = 'completed'
            video.completed_at = datetime.utcnow()
            video.last_error = None
            logging.info(f"Video {video_id} completed successfully")
            
        elif status == 'pending':
            video.status = 'pending'
            logging.info(f"Video {video_id} reset to pending")
            
        else:
            logging.error(f"Invalid status '{status}' for video {video_id}")
            return False
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to release video {video_id}: {e}")
        return False


def reset_processing_videos(db: Session) -> int:
    """
    Reset all 'processing' videos back to 'pending' status.
    This is called on startup to recover from crashes.
    
    Returns:
        int: Number of videos reset
    """
    try:
        result = db.execute(text("""
            UPDATE videos 
            SET status = 'pending' 
            WHERE status = 'processing'
        """))
        
        reset_count = result.rowcount
        db.commit()
        
        if reset_count > 0:
            logging.info(f"Reset {reset_count} processing videos to pending on startup")
            
            # Log the recovery
            log_entry = Log(
                video_id=None,
                level='INFO',
                message=f"Startup recovery: Reset {reset_count} processing videos to pending",
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
        
        return reset_count
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to reset processing videos: {e}")
        return 0


def reconcile_video_statuses(db: Session) -> Dict[str, int]:
    """
    Reconcile video statuses with actual subtitle data.
    Videos with subtitles should be marked as 'completed'.
    
    Returns:
        dict: Counts of reconciliation actions
    """
    try:
        # Find videos that have subtitles but aren't marked as completed
        result = db.execute(text("""
            UPDATE videos 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT DISTINCT v.id 
                FROM videos v 
                INNER JOIN subtitles s ON v.id = s.video_id 
                WHERE v.status != 'completed'
            )
        """))
        
        completed_count = result.rowcount
        db.commit()
        
        if completed_count > 0:
            logging.info(f"Reconciliation: Marked {completed_count} videos as completed")
            
            # Log the reconciliation
            log_entry = Log(
                video_id=None,
                level='INFO',
                message=f"Reconciliation: Marked {completed_count} videos as completed",
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
        
        return {
            'completed': completed_count,
            'reset': 0  # Could add more reconciliation logic here
        }
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to reconcile video statuses: {e}")
        return {'completed': 0, 'reset': 0}


def get_queue_statistics(db: Session) -> Dict[str, int]:
    """
    Get current queue statistics across all videos.
    
    Returns:
        dict: Counts by status
    """
    try:
        result = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM videos
            GROUP BY status
        """)).fetchall()
        
        stats = {
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'total': 0
        }
        
        for row in result:
            status, count = row
            stats[status] = count
            stats['total'] += count
        
        return stats
        
    except Exception as e:
        logging.error(f"Failed to get queue statistics: {e}")
        return {'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0, 'total': 0}


def get_channel_statistics(db: Session, channel_id: int) -> Dict[str, int]:
    """
    Get queue statistics for a specific channel.
    
    Args:
        channel_id: ID of the channel
        
    Returns:
        dict: Counts by status for the channel
    """
    try:
        result = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM videos
            WHERE channel_id = :channel_id
            GROUP BY status
        """), {'channel_id': channel_id}).fetchall()
        
        stats = {
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'total': 0
        }
        
        for row in result:
            status, count = row
            stats[status] = count
            stats['total'] += count
        
        return stats
        
    except Exception as e:
        logging.error(f"Failed to get channel {channel_id} statistics: {e}")
        return {'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0, 'total': 0}


def retry_failed_video(db: Session, video_id: int) -> bool:
    """
    Manually retry a failed video by resetting its status and attempts.
    
    Args:
        video_id: ID of the video to retry
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logging.error(f"Video {video_id} not found")
            return False
        
        if video.status != 'failed':
            logging.warning(f"Video {video_id} is not in failed state (current: {video.status})")
            return False
        
        # Reset for retry
        video.status = 'pending'
        video.attempts = 0
        video.last_error = None
        
        db.commit()
        
        logging.info(f"Manually reset video {video_id} for retry")
        
        # Log the manual retry
        log_entry = Log(
            video_id=video_id,
            level='INFO',
            message="Manual retry initiated",
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        
        return True
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to retry video {video_id}: {e}")
        return False


def get_failed_videos(db: Session, limit: int = 100) -> List[Dict]:
    """
    Get list of failed videos with their error information.
    
    Args:
        limit: Maximum number of videos to return
        
    Returns:
        list: Failed videos with details
    """
    try:
        result = db.execute(text("""
            SELECT v.id, v.url, v.title, v.attempts, v.last_error, 
                   v.created_at, c.name as channel_name
            FROM videos v
            LEFT JOIN channels c ON v.channel_id = c.id
            WHERE v.status = 'failed'
            ORDER BY v.id DESC
            LIMIT :limit
        """), {'limit': limit}).fetchall()
        
        failed_videos = []
        for row in result:
            failed_videos.append({
                'id': row[0],
                'url': row[1],
                'title': row[2],
                'attempts': row[3],
                'last_error': row[4],
                'created_at': row[5],
                'channel_name': row[6]
            })
        
        return failed_videos
        
    except Exception as e:
        logging.error(f"Failed to get failed videos: {e}")
        return []


def cleanup_old_logs(db: Session, days: int = 30) -> int:
    """
    Clean up log entries older than specified days.
    
    Args:
        days: Number of days to keep logs
        
    Returns:
        int: Number of logs deleted
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = db.execute(text("""
            DELETE FROM logs 
            WHERE timestamp < :cutoff_date
        """), {'cutoff_date': cutoff_date})
        
        deleted_count = result.rowcount
        db.commit()
        
        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} old log entries")
        
        return deleted_count
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to cleanup old logs: {e}")
        return 0
