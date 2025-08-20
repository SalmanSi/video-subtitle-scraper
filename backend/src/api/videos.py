from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from db.models import Video, Channel, get_db
from utils.queue_manager import (
    retry_failed_video, 
    get_queue_statistics, 
    get_channel_statistics,
    get_failed_videos
)

router = APIRouter(prefix="/videos", tags=["videos"])

# Pydantic models
class VideoOutput(BaseModel):
    id: int
    channel_id: int
    url: str
    title: Optional[str]
    status: str
    attempts: int
    last_error: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime
    
    model_config = {"from_attributes": True}

class VideoListResponse(BaseModel):
    videos: List[VideoOutput]
    total: int
    status_counts: dict

class QueueStatsResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    total: int

class RetryResponse(BaseModel):
    message: str
    video_id: int
    status: str

@router.get("/", response_model=VideoListResponse)
async def list_videos(
    status: Optional[str] = Query(None, description="Filter by status"),
    channel_id: Optional[int] = Query(None, description="Filter by channel"),
    limit: int = Query(100, description="Maximum number of videos to return"),
    offset: int = Query(0, description="Number of videos to skip"),
    db: Session = Depends(get_db)
):
    """List videos with optional filtering"""
    try:
        # Build query with filters
        query = db.query(Video)
        
        if channel_id:
            query = query.filter(Video.channel_id == channel_id)
        
        if status:
            if status not in ['pending', 'processing', 'completed', 'failed']:
                raise HTTPException(status_code=400, detail="Invalid status filter")
            query = query.filter(Video.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        videos = query.order_by(Video.id.desc()).offset(offset).limit(limit).all()
        
        # Get status counts
        if channel_id:
            status_counts = get_channel_statistics(db, channel_id)
        else:
            status_counts = get_queue_statistics(db)
        
        return VideoListResponse(
            videos=videos,
            total=total,
            status_counts=status_counts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")

@router.get("/{video_id}", response_model=VideoOutput)
async def get_video(video_id: int, db: Session = Depends(get_db)):
    """Get a specific video by ID"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return video

@router.post("/{video_id}/retry", response_model=RetryResponse)
async def retry_video(video_id: int, db: Session = Depends(get_db)):
    """Retry a failed video by resetting its status and attempts"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != 'failed':
        raise HTTPException(
            status_code=400, 
            detail=f"Video is not in failed state (current status: {video.status})"
        )
    
    success = retry_failed_video(db, video_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to retry video")
    
    return RetryResponse(
        message="Video retry initiated successfully",
        video_id=video_id,
        status="pending"
    )

@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(db: Session = Depends(get_db)):
    """Get overall queue statistics"""
    stats = get_queue_statistics(db)
    return QueueStatsResponse(**stats)

@router.get("/queue/failed")
async def get_failed_video_list(
    limit: int = Query(50, description="Maximum number of failed videos to return"),
    db: Session = Depends(get_db)
):
    """Get list of failed videos with error details"""
    failed_videos = get_failed_videos(db, limit)
    return {
        "failed_videos": failed_videos,
        "total": len(failed_videos)
    }

@router.get("/channels/{channel_id}/videos", response_model=VideoListResponse)
async def get_channel_videos(
    channel_id: int,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, description="Maximum number of videos to return"),
    offset: int = Query(0, description="Number of videos to skip"),
    db: Session = Depends(get_db)
):
    """Get all videos for a specific channel"""
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    try:
        # Build query
        query = db.query(Video).filter(Video.channel_id == channel_id)
        
        if status:
            if status not in ['pending', 'processing', 'completed', 'failed']:
                raise HTTPException(status_code=400, detail="Invalid status filter")
            query = query.filter(Video.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        videos = query.order_by(Video.id.desc()).offset(offset).limit(limit).all()
        
        # Get status counts for this channel
        status_counts = get_channel_statistics(db, channel_id)
        
        return VideoListResponse(
            videos=videos,
            total=total,
            status_counts=status_counts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channel videos: {str(e)}")

@router.delete("/{video_id}")
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    """Delete a video (admin operation)"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    try:
        db.delete(video)
        db.commit()
        return {"message": f"Video {video_id} deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")