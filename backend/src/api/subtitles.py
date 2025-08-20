from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import PlainTextResponse, FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
import io
import zipfile
import tempfile
import os
from datetime import datetime

from db.models import Subtitle, Video, Channel, get_db
from utils.yt_dlp_helper import extract_single_video_subtitles, get_video_info_only

router = APIRouter(prefix="/subtitles", tags=["subtitles"])

# Pydantic models for request/response
class VideoUrlRequest(BaseModel):
    video_url: str
    preferred_languages: Optional[List[str]] = ["en"]
    include_auto_generated: Optional[bool] = False

class VideoInfoRequest(BaseModel):
    video_url: str

@router.get("/")
async def list_subtitles(
    video_id: Optional[int] = None,
    language: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List subtitles with optional filtering"""
    query = db.query(Subtitle).options(joinedload(Subtitle.video))
    
    if video_id:
        query = query.filter(Subtitle.video_id == video_id)
    
    if language:
        query = query.filter(Subtitle.language == language)
    
    query = query.offset(offset).limit(limit)
    subtitles = query.all()
    
    return {
        "subtitles": [
            {
                "id": sub.id,
                "video_id": sub.video_id,
                "video_title": sub.video.title if sub.video else None,
                "language": sub.language,
                "content_length": len(sub.content) if sub.content else 0,
                "downloaded_at": sub.downloaded_at
            }
            for sub in subtitles
        ],
        "total": query.count(),
        "limit": limit,
        "offset": offset
    }

@router.get("/{subtitle_id}")
async def get_subtitle(subtitle_id: int, db: Session = Depends(get_db)):
    """Get a specific subtitle"""
    subtitle = db.query(Subtitle).options(joinedload(Subtitle.video)).filter(
        Subtitle.id == subtitle_id
    ).first()
    
    if not subtitle:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    
    return {
        "id": subtitle.id,
        "video_id": subtitle.video_id,
        "video_title": subtitle.video.title if subtitle.video else None,
        "video_url": subtitle.video.url if subtitle.video else None,
        "language": subtitle.language,
        "content": subtitle.content,
        "content_length": len(subtitle.content) if subtitle.content else 0,
        "downloaded_at": subtitle.downloaded_at
    }

@router.get("/{subtitle_id}/download")
async def download_subtitle(subtitle_id: int, db: Session = Depends(get_db)):
    """Download subtitle as plain text file"""
    subtitle = db.query(Subtitle).options(joinedload(Subtitle.video)).filter(
        Subtitle.id == subtitle_id
    ).first()
    
    if not subtitle:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    
    if not subtitle.content:
        raise HTTPException(status_code=404, detail="Subtitle content not available")
    
    # Generate filename
    video_title = subtitle.video.title if subtitle.video else f"video_{subtitle.video_id}"
    # Clean filename
    safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_title}_{subtitle.language}.txt"
    
    return PlainTextResponse(
        content=subtitle.content,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

# Video-specific subtitle endpoints (as per TRD)
@router.get("/videos/{video_id}")
async def get_video_subtitles(video_id: int, db: Session = Depends(get_db)):
    """Get all subtitles for a specific video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    subtitles = db.query(Subtitle).filter(Subtitle.video_id == video_id).all()
    
    return {
        "video_id": video_id,
        "video_title": video.title,
        "video_url": video.url,
        "status": video.status,
        "subtitles": [
            {
                "id": sub.id,
                "language": sub.language,
                "content": sub.content,
                "content_length": len(sub.content) if sub.content else 0,
                "downloaded_at": sub.downloaded_at
            }
            for sub in subtitles
        ]
    }

@router.get("/videos/{video_id}/download")
async def download_video_subtitles(video_id: int, db: Session = Depends(get_db)):
    """Download all subtitles for a video as a ZIP file or single TXT if only one"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    subtitles = db.query(Subtitle).filter(Subtitle.video_id == video_id).all()
    
    if not subtitles:
        raise HTTPException(status_code=404, detail="No subtitles found for this video")
    
    # Clean video title for filename
    safe_title = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_')).strip()
    
    if len(subtitles) == 1:
        # Single subtitle - return as plain text
        subtitle = subtitles[0]
        filename = f"{safe_title}_{subtitle.language}.txt"
        return PlainTextResponse(
            content=subtitle.content,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    else:
        # Multiple subtitles - return as ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for subtitle in subtitles:
                filename = f"{safe_title}_{subtitle.language}.txt"
                zip_file.writestr(filename, subtitle.content.encode('utf-8'))
        
        zip_buffer.seek(0)
        zip_filename = f"{safe_title}_subtitles.zip"
        
        return Response(
            content=zip_buffer.getvalue(),
            headers={
                "Content-Disposition": f"attachment; filename=\"{zip_filename}\"",
                "Content-Type": "application/zip"
            }
        )

@router.get("/channels/{channel_id}/download")
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
                
                for subtitle in subtitles:
                    # Create hierarchical structure in ZIP
                    filename = f"{safe_title}_{subtitle.language}.txt"
                    zip_file.writestr(filename, subtitle.content.encode('utf-8'))
        
        tmp_file_path = tmp_file.name
    
    # Clean channel name for ZIP filename
    safe_channel_name = "".join(c for c in channel.name if c.isalnum() or c in (' ', '-', '_')).strip()
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

# New endpoints for individual video subtitle extraction

@router.post("/extract")
async def extract_video_subtitles(request: VideoUrlRequest):
    """
    Extract subtitles from a single video URL without saving to database.
    
    This endpoint extracts subtitles directly from a YouTube video URL and returns
    the subtitle content along with metadata. Useful for testing or one-off extractions.
    """
    try:
        result = extract_single_video_subtitles(
            video_url=request.video_url,
            preferred_langs=request.preferred_languages,
            include_auto_generated=request.include_auto_generated
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=400 if not result['is_transient_error'] else 503,
                detail=f"Failed to extract subtitles: {result['error']}"
            )
        
        return {
            "success": True,
            "video_info": {
                "title": result['video_title'],
                "video_id": result['video_id'],
                "duration": result['duration']
            },
            "subtitle_info": {
                "language": result['language'],
                "content": result['content'],
                "content_length": result['content_length'],
                "format": result['subtitle_format'],
                "is_auto_generated": result.get('is_auto_generated', False)
            },
            "available_languages": {
                "native": result['available_languages'],
                "auto_generated": result['auto_generated_available']
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/extract/download")
async def extract_and_download_subtitles(request: VideoUrlRequest):
    """
    Extract subtitles from a video URL and return as downloadable .txt file.
    """
    try:
        result = extract_single_video_subtitles(
            video_url=request.video_url,
            preferred_langs=request.preferred_languages,
            include_auto_generated=request.include_auto_generated
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=400 if not result['is_transient_error'] else 503,
                detail=f"Failed to extract subtitles: {result['error']}"
            )
        
        # Generate filename
        video_title = result['video_title'] or f"video_{result['video_id']}"
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_title}_{result['language']}.txt"
        
        return PlainTextResponse(
            content=result['content'],
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/info")
async def get_video_info(request: VideoInfoRequest):
    """
    Get video information and available subtitle languages without downloading content.
    
    Useful for checking what subtitle languages are available before extraction.
    """
    try:
        result = get_video_info_only(request.video_url)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=f"Failed to get video info: {result['error']}")
        
        return {
            "success": True,
            "video_info": {
                "video_id": result['video_id'],
                "title": result['title'],
                "duration": result['duration'],
                "upload_date": result['upload_date'],
                "uploader": result['uploader'],
                "view_count": result['view_count'],
                "like_count": result['like_count'],
                "tags": result['tags'][:10] if result['tags'] else []  # Limit tags for response size
            },
            "subtitle_availability": {
                "native_languages": result['available_subtitle_languages'],
                "auto_generated_languages": result['auto_caption_languages']
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/batch-extract")
async def batch_extract_subtitles(
    video_urls: List[str],
    preferred_languages: Optional[List[str]] = ["en"],
    include_auto_generated: Optional[bool] = False,
    max_videos: int = 10
):
    """
    Extract subtitles from multiple video URLs (batch operation).
    
    Limited to 10 videos per request to prevent abuse and timeout issues.
    """
    if len(video_urls) > max_videos:
        raise HTTPException(
            status_code=400, 
            detail=f"Too many videos requested. Maximum allowed: {max_videos}"
        )
    
    results = []
    
    for i, video_url in enumerate(video_urls):
        try:
            result = extract_single_video_subtitles(
                video_url=video_url,
                preferred_langs=preferred_languages,
                include_auto_generated=include_auto_generated
            )
            
            results.append({
                "video_url": video_url,
                "index": i,
                "success": result['success'],
                "video_title": result['video_title'],
                "video_id": result['video_id'],
                "language": result['language'] if result['success'] else None,
                "content_length": result['content_length'] if result['success'] else 0,
                "error": result['error'] if not result['success'] else None
            })
            
            # Add small delay between requests to avoid rate limiting
            if i < len(video_urls) - 1:  # Don't sleep after the last video
                import time
                time.sleep(1)
                
        except Exception as e:
            results.append({
                "video_url": video_url,
                "index": i,
                "success": False,
                "error": str(e)
            })
    
    successful_extractions = sum(1 for r in results if r['success'])
    
    return {
        "total_requested": len(video_urls),
        "successful_extractions": successful_extractions,
        "failed_extractions": len(video_urls) - successful_extractions,
        "results": results
    }