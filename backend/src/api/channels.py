from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging
import tempfile
import zipfile
import os

from db.models import Channel, Video, Log, Subtitle, get_db
from utils.yt_dlp_helper import (
    validate_youtube_url, 
    normalize_channel_url, 
    extract_video_entries,
    get_channel_info,
    log_error
)
from utils.queue_manager import get_channel_statistics

router = APIRouter(prefix="/channels", tags=["channels"])

# Pydantic models
class ChannelInput(BaseModel):
    url: str
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not validate_youtube_url(v):
            raise ValueError('Invalid YouTube channel URL')
        return normalize_channel_url(v)

class ChannelBulkInput(BaseModel):
    urls: List[str]
    
    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v):
        validated = []
        for url in v:
            if not validate_youtube_url(url):
                raise ValueError(f'Invalid YouTube channel URL: {url}')
            validated.append(normalize_channel_url(url))
        return validated

class ChannelOutput(BaseModel):
    id: int
    url: str
    name: Optional[str]
    total_videos: int
    pending: int
    processing: int
    completed: int
    failed: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

class ChannelIngestionResponse(BaseModel):
    channels_created: int
    videos_enqueued: int
    channels_skipped: Optional[List[str]] = None
    videos_existing: Optional[int] = None

def get_or_create_channel(db: Session, url: str) -> tuple[Channel, bool]:
    """
    Get existing channel or create new one.
    
    Returns:
        tuple: (channel, is_new)
    """
    # Check if channel already exists
    channel = db.query(Channel).filter(Channel.url == url).first()
    if channel:
        return channel, False
    
    # Get channel info from yt-dlp
    try:
        channel_info = get_channel_info(url)
        channel_name = channel_info.get('title', 'Unknown Channel')
    except Exception as e:
        logging.warning(f"Could not get channel name for {url}: {e}")
        channel_name = 'Unknown Channel'
    
    # Create new channel
    channel = Channel(
        url=url,
        name=channel_name,
        total_videos=0,
        created_at=datetime.utcnow()
    )
    
    db.add(channel)
    db.flush()  # Get the ID without committing
    
    return channel, True

def ingest_channel_videos(db: Session, channel: Channel) -> int:
    """
    Ingest videos for a channel.
    
    Returns:
        int: Number of new videos added
    """
    try:
        # Extract video entries
        entries = extract_video_entries(channel.url)
        new_videos = 0
        
        for entry in entries:
            # Get video URL
            video_url = entry.get('webpage_url') or entry.get('url')
            if not video_url and entry.get('id'):
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            
            if not video_url:
                continue
                
            # Get video title
            title = entry.get('title', 'Unknown Title')
            
            # Check if video already exists
            existing_video = db.query(Video).filter(Video.url == video_url).first()
            if not existing_video:
                video = Video(
                    channel_id=channel.id,
                    url=video_url,
                    title=title,
                    status='pending',
                    attempts=0,
                    created_at=datetime.utcnow()
                )
                db.add(video)
                new_videos += 1
        
        # Update channel total_videos count
        total_videos = db.query(Video).filter(Video.channel_id == channel.id).count()
        channel.total_videos = total_videos
        
        logging.info(f"Ingested {new_videos} new videos for channel {channel.url}")
        return new_videos
        
    except Exception as e:
        error_msg = f"Failed to ingest videos for channel {channel.url}: {str(e)}"
        logging.error(error_msg)
        
        # Log to database
        log_entry = Log(
            video_id=None,
            level='ERROR',
            message=error_msg,
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        
        raise HTTPException(status_code=400, detail=error_msg)

@router.post("/", response_model=ChannelIngestionResponse)
async def add_channel(
    channel_input: Union[ChannelInput, ChannelBulkInput],
    db: Session = Depends(get_db)
):
    """
    Add one or more channels and ingest their videos.
    """
    # Handle both single and bulk input
    if isinstance(channel_input, ChannelInput):
        urls = [channel_input.url]
    else:
        urls = channel_input.urls
    
    channels_created = 0
    videos_enqueued = 0
    channels_skipped = []
    videos_existing = 0
    
    try:
        for url in urls:
            try:
                # Get or create channel
                channel, is_new = get_or_create_channel(db, url)
                
                if not is_new:
                    channels_skipped.append(url)
                    # Count existing videos for this channel
                    existing_count = db.query(Video).filter(Video.channel_id == channel.id).count()
                    videos_existing += existing_count
                else:
                    channels_created += 1
                
                # Ingest videos (both new and existing channels to catch new videos)
                new_videos = ingest_channel_videos(db, channel)
                videos_enqueued += new_videos
                
            except Exception as e:
                # Log error but continue with other channels
                error_msg = f"Failed to process channel {url}: {str(e)}"
                logging.error(error_msg)
                
                log_entry = Log(
                    video_id=None,
                    level='ERROR',
                    message=error_msg,
                    timestamp=datetime.utcnow()
                )
                db.add(log_entry)
        
        # Commit all changes
        db.commit()
        
        # Determine response
        if channels_created > 0:
            return ChannelIngestionResponse(
                channels_created=channels_created,
                videos_enqueued=videos_enqueued,
                channels_skipped=channels_skipped if channels_skipped else None,
                videos_existing=videos_existing if videos_existing > 0 else None
            )
        else:
            # All channels already existed
            return ChannelIngestionResponse(
                channels_created=0,
                videos_enqueued=videos_enqueued,
                channels_skipped=channels_skipped,
                videos_existing=videos_existing
            )
            
    except Exception as e:
        db.rollback()
        error_msg = f"Failed to process channels: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/", response_model=List[ChannelOutput])
async def list_channels(db: Session = Depends(get_db)):
    """
    List all channels with their progress statistics.
    """
    try:
        channels = db.query(Channel).all()
        result = []
        
        for channel in channels:
            # Get status counts for this channel using queue manager
            stats = get_channel_statistics(db, channel.id)
            
            channel_data = ChannelOutput(
                id=channel.id,
                url=channel.url,
                name=channel.name,
                total_videos=channel.total_videos,
                pending=stats['pending'],
                processing=stats['processing'],
                completed=stats['completed'],
                failed=stats['failed'],
                created_at=channel.created_at
            )
            result.append(channel_data)
        
        return result
        
    except Exception as e:
        logging.error(f"Failed to list channels: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve channels")

@router.delete("/{channel_id}")
async def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """
    Delete a channel and all its videos.
    """
    try:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Delete channel (CASCADE will delete videos)
        db.delete(channel)
        db.commit()
        
        logging.info(f"Deleted channel {channel.url} (ID: {channel_id})")
        return {"message": "Channel deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to delete channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete channel")

@router.get("/{channel_id}/subtitles/download")
async def download_channel_subtitles(channel_id: int, db: Session = Depends(get_db)):
    """
    Download all completed subtitles for a channel as ZIP file.
    
    This endpoint creates a ZIP file containing all completed subtitle files
    for the specified channel. Files are named with video ID and sanitized title.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get all completed videos with subtitles for this channel
    videos_with_subtitles = db.query(Video).filter(
        Video.channel_id == channel_id,
        Video.status == 'completed'
    ).join(Subtitle).all()
    
    if not videos_with_subtitles:
        raise HTTPException(status_code=404, detail="No completed videos with subtitles found for this channel")
    
    # Create temporary file for the ZIP
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for video in videos_with_subtitles:
                subtitles = db.query(Subtitle).filter(Subtitle.video_id == video.id).all()
                
                # Clean video title for filename (keep first 50 chars)
                safe_title = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title[:50] if len(safe_title) > 50 else safe_title
                
                for subtitle in subtitles:
                    # Create filename with video ID and title for uniqueness
                    filename = f"{video.id}_{safe_title}_{subtitle.language}.txt"
                    zip_file.writestr(filename, subtitle.content.encode('utf-8'))
        
        tmp_file_path = tmp_file.name
    
    # Clean channel name for ZIP filename
    safe_channel_name = "".join(c for c in (channel.name or f"channel-{channel_id}") if c.isalnum() or c in (' ', '-', '_')).strip()
    zip_filename = f"{safe_channel_name}_subtitles.zip"
    
    def cleanup():
        """Clean up temporary file after response"""
        try:
            os.unlink(tmp_file_path)
        except:
            pass
    
    return FileResponse(
        path=tmp_file_path,
        filename=zip_filename,
        media_type="application/zip",
        background=cleanup  # Clean up temp file after download
    )

@router.get("/{channel_id}/subtitles/download")
async def download_channel_subtitles(channel_id: int, db: Session = Depends(get_db)):
    """Download all completed subtitles for a channel as ZIP file"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get all completed videos with subtitles for this channel
    videos_with_subtitles = db.query(Video).filter(
        Video.channel_id == channel_id,
        Video.status == 'completed'
    ).join(Subtitle).all()
    
    if not videos_with_subtitles:
        raise HTTPException(status_code=404, detail="No completed videos with subtitles found for this channel")
    
    # Create temporary file for the ZIP
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for video in videos_with_subtitles:
                subtitles = db.query(Subtitle).filter(Subtitle.video_id == video.id).all()
                
                # Clean video title for folder/filename
                safe_title = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title[:80]  # Truncate to avoid long filenames
                
                for subtitle in subtitles:
                    # Create filename with video ID to ensure uniqueness
                    filename = f"{video.id}_{safe_title}_{subtitle.language}.txt"
                    zip_file.writestr(filename, subtitle.content.encode('utf-8'))
        
        tmp_file_path = tmp_file.name
    
    # Clean channel name for ZIP filename
    safe_channel_name = "".join(c for c in (channel.name or f"channel-{channel_id}") if c.isalnum() or c in (' ', '-', '_')).strip()
    zip_filename = f"{safe_channel_name}-subtitles.zip"
    
    def cleanup():
        """Clean up temporary file after response"""
        try:
            os.unlink(tmp_file_path)
        except:
            pass
    
    return FileResponse(
        path=tmp_file_path,
        filename=zip_filename,
        media_type="application/zip",
        background=cleanup  # Clean up temp file after download
    )