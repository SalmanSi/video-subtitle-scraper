from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import asyncio
import logging

from db.models import Job, Setting, Log, Video, get_db
from utils.queue_manager import (
    get_queue_statistics,
    reset_processing_videos,
    reconcile_video_statuses,
    cleanup_old_logs
)
from utils.error_handler import get_recent_errors

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Pydantic models
class JobStatusResponse(BaseModel):
    status: str
    active_workers: int
    queue_stats: dict
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None

class JobControlResponse(BaseModel):
    message: str
    status: str
    queue_stats: dict

class ReconcileResponse(BaseModel):
    message: str
    completed_videos: int
    reset_videos: int

class SettingsResponse(BaseModel):
    max_workers: int
    max_retries: int
    backoff_factor: float
    output_dir: str

class SettingsUpdate(BaseModel):
    max_workers: Optional[int] = None
    max_retries: Optional[int] = None
    backoff_factor: Optional[float] = None
    output_dir: Optional[str] = None

class LogEntry(BaseModel):
    id: int
    video_id: Optional[int]
    level: str
    message: str
    timestamp: str

class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    level_filter: Optional[str]

class QueueStatsResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    total: int

class WorkerInfo(BaseModel):
    name: str
    video_id: Optional[int] = None
    since: Optional[datetime] = None
    status: str = "idle"

class RecentError(BaseModel):
    video_id: Optional[int] = None
    message: str
    timestamp: datetime

class RealTimeJobStatus(BaseModel):
    status: str
    active_workers: int
    pending: int
    processing: int
    completed: int
    failed: int
    throughput_per_min: float
    workers: List[WorkerInfo]
    recent_errors: List[RecentError]

async def get_real_time_job_data(db: Session) -> dict:
    """Get comprehensive real-time job monitoring data"""
    try:
        # Get current job status
        job = db.query(Job).first()
        if not job:
            job = Job(status='idle', active_workers=0)
            db.add(job)
            db.commit()
        
        # Get queue statistics
        queue_stats = get_queue_statistics(db)
        
        # Get recent errors (last 20)
        recent_errors = []
        error_logs = db.query(Log).filter(
            Log.level == 'ERROR'
        ).order_by(Log.timestamp.desc()).limit(20).all()
        
        for log in error_logs:
            recent_errors.append({
                "video_id": log.video_id,
                "message": log.message,
                "timestamp": log.timestamp.isoformat()
            })
        
        # Get processing videos (simulated workers)
        processing_videos = db.query(Video).filter(
            Video.status == 'processing'
        ).limit(10).all()
        
        workers = []
        for i, video in enumerate(processing_videos):
            workers.append({
                "name": f"worker-{i+1}",
                "video_id": video.id,
                "since": video.created_at.isoformat() if video.created_at else None,
                "status": "processing"
            })
        
        # Calculate throughput (completed videos in last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        completed_last_hour = db.query(Video).filter(
            Video.status == 'completed',
            Video.completed_at >= one_hour_ago
        ).count()
        throughput_per_min = completed_last_hour / 60.0
        
        return {
            "status": job.status,
            "active_workers": len(workers),
            "pending": queue_stats.get('pending', 0),
            "processing": queue_stats.get('processing', 0),
            "completed": queue_stats.get('completed', 0),
            "failed": queue_stats.get('failed', 0),
            "throughput_per_min": round(throughput_per_min, 2),
            "workers": workers,
            "recent_errors": recent_errors
        }
        
    except Exception as e:
        logging.error(f"Failed to get real-time job data: {str(e)}")
        return {
            "status": "error",
            "active_workers": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "throughput_per_min": 0.0,
            "workers": [],
            "recent_errors": [{"video_id": None, "message": f"Error fetching data: {str(e)}", "timestamp": datetime.now().isoformat()}]
        }

@router.websocket("/status")
async def websocket_job_status(websocket: WebSocket):
    """WebSocket endpoint for real-time job monitoring"""
    await websocket.accept()
    
    try:
        while True:
            # Get fresh database session for each update
            db = next(get_db())
            try:
                data = await get_real_time_job_data(db)
                await websocket.send_text(json.dumps(data))
            finally:
                db.close()
            
            # Send updates every second
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logging.info("WebSocket client disconnected from job status monitoring")
    except Exception as e:
        logging.error(f"WebSocket error in job status monitoring: {str(e)}")
        try:
            await websocket.close()
        except:
            pass

@router.get("/status", response_model=JobStatusResponse)
async def get_job_status(db: Session = Depends(get_db)):
    """Get current job processing status and queue statistics"""
    try:
        # Get current job status
        job = db.query(Job).first()
        if not job:
            # Create default job entry
            job = Job(status='idle', active_workers=0)
            db.add(job)
            db.commit()
        
        # Get queue statistics
        queue_stats = get_queue_statistics(db)
        
        return JobStatusResponse(
            status=job.status,
            active_workers=job.active_workers,
            queue_stats=queue_stats,
            started_at=job.started_at,
            stopped_at=job.stopped_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")

@router.post("/start", response_model=JobControlResponse)
async def start_jobs(db: Session = Depends(get_db)):
    """Start job processing"""
    try:
        # Get or create job entry
        job = db.query(Job).first()
        if not job:
            job = Job()
            db.add(job)
        
        if job.status == 'running':
            queue_stats = get_queue_statistics(db)
            return JobControlResponse(
                message="Job processing is already running",
                status=job.status,
                queue_stats=queue_stats
            )
        
        # Start the job
        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.stopped_at = None
        db.commit()
        
        # Get updated statistics
        queue_stats = get_queue_statistics(db)
        
        return JobControlResponse(
            message="Job processing started successfully",
            status=job.status,
            queue_stats=queue_stats
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start jobs: {str(e)}")

@router.post("/pause", response_model=JobControlResponse)
async def pause_jobs(db: Session = Depends(get_db)):
    """Pause job processing"""
    try:
        job = db.query(Job).first()
        if not job:
            raise HTTPException(status_code=404, detail="No job found")
        
        if job.status == 'paused':
            queue_stats = get_queue_statistics(db)
            return JobControlResponse(
                message="Job processing is already paused",
                status=job.status,
                queue_stats=queue_stats
            )
        
        # Pause the job
        job.status = 'paused'
        job.stopped_at = datetime.utcnow()
        db.commit()
        
        # Get updated statistics
        queue_stats = get_queue_statistics(db)
        
        return JobControlResponse(
            message="Job processing paused successfully",
            status=job.status,
            queue_stats=queue_stats
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to pause jobs: {str(e)}")

@router.post("/resume", response_model=JobControlResponse)
async def resume_jobs(db: Session = Depends(get_db)):
    """Resume job processing from paused state"""
    try:
        job = db.query(Job).first()
        if not job:
            raise HTTPException(status_code=404, detail="No job found")
        
        if job.status == 'running':
            queue_stats = get_queue_statistics(db)
            return JobControlResponse(
                message="Job processing is already running",
                status=job.status,
                queue_stats=queue_stats
            )
        
        # Resume the job
        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.stopped_at = None
        db.commit()
        
        # Get updated statistics
        queue_stats = get_queue_statistics(db)
        
        return JobControlResponse(
            message="Job processing resumed successfully",
            status=job.status,
            queue_stats=queue_stats
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resume jobs: {str(e)}")

@router.post("/stop", response_model=JobControlResponse)
async def stop_jobs(db: Session = Depends(get_db)):
    """Stop job processing and reset processing videos to pending"""
    try:
        job = db.query(Job).first()
        if not job:
            raise HTTPException(status_code=404, detail="No job found")
        
        # Stop the job
        job.status = 'idle'
        job.active_workers = 0
        job.stopped_at = datetime.utcnow()
        db.commit()
        
        # Reset any processing videos to pending
        reset_count = reset_processing_videos(db)
        
        # Get updated statistics
        queue_stats = get_queue_statistics(db)
        
        message = "Job processing stopped successfully"
        if reset_count > 0:
            message += f". Reset {reset_count} processing videos to pending"
        
        return JobControlResponse(
            message=message,
            status=job.status,
            queue_stats=queue_stats
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to stop jobs: {str(e)}")

@router.post("/reconcile", response_model=ReconcileResponse)
async def reconcile_queue(db: Session = Depends(get_db)):
    """Manually trigger queue reconciliation"""
    try:
        # Run reconciliation
        results = reconcile_video_statuses(db)
        
        # Also reset any stuck processing videos
        reset_count = reset_processing_videos(db)
        
        return ReconcileResponse(
            message="Queue reconciliation completed successfully",
            completed_videos=results['completed'],
            reset_videos=reset_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reconcile queue: {str(e)}")

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Get current job processing settings"""
    try:
        settings = db.query(Setting).filter(Setting.id == 1).first()
        if not settings:
            # Create default settings
            settings = Setting(id=1)
            db.add(settings)
            db.commit()
        
        return SettingsResponse(
            max_workers=settings.max_workers,
            max_retries=settings.max_retries,
            backoff_factor=settings.backoff_factor,
            output_dir=settings.output_dir
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")

@router.post("/settings", response_model=SettingsResponse)
async def update_settings(
    settings_update: SettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update job processing settings"""
    try:
        settings = db.query(Setting).filter(Setting.id == 1).first()
        if not settings:
            settings = Setting(id=1)
            db.add(settings)
        
        # Update provided fields
        if settings_update.max_workers is not None:
            if settings_update.max_workers < 1 or settings_update.max_workers > 20:
                raise HTTPException(status_code=400, detail="max_workers must be between 1 and 20")
            settings.max_workers = settings_update.max_workers
        
        if settings_update.max_retries is not None:
            if settings_update.max_retries < 0 or settings_update.max_retries > 10:
                raise HTTPException(status_code=400, detail="max_retries must be between 0 and 10")
            settings.max_retries = settings_update.max_retries
        
        if settings_update.backoff_factor is not None:
            if settings_update.backoff_factor < 1.0 or settings_update.backoff_factor > 10.0:
                raise HTTPException(status_code=400, detail="backoff_factor must be between 1.0 and 10.0")
            settings.backoff_factor = settings_update.backoff_factor
        
        if settings_update.output_dir is not None:
            settings.output_dir = settings_update.output_dir
        
        db.commit()
        
        return SettingsResponse(
            max_workers=settings.max_workers,
            max_retries=settings.max_retries,
            backoff_factor=settings.backoff_factor,
            output_dir=settings.output_dir
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.post("/cleanup")
async def cleanup_logs(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Clean up old log entries"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="days must be between 1 and 365")
        
        deleted_count = cleanup_old_logs(db, days)
        
        return {
            "message": f"Cleanup completed successfully",
            "deleted_logs": deleted_count,
            "days_kept": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup logs: {str(e)}")

@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of logs to return"),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARN, ERROR)"),
    video_id: Optional[int] = Query(None, description="Filter by video ID"),
    db: Session = Depends(get_db)
):
    """Get system logs with optional filtering for dashboard debugging"""
    try:
        # Validate level parameter
        if level and level.upper() not in ['INFO', 'WARN', 'ERROR']:
            raise HTTPException(status_code=400, detail="level must be one of: INFO, WARN, ERROR")
        
        # Build query with filters
        query = db.query(Log)
        
        if level:
            query = query.filter(Log.level == level.upper())
        
        if video_id:
            query = query.filter(Log.video_id == video_id)
        
        # Get total count
        total = query.count()
        
        # Apply ordering and limit
        logs = query.order_by(Log.timestamp.desc()).limit(limit).all()
        
        # Convert to response format
        log_entries = [
            LogEntry(
                id=log.id,
                video_id=log.video_id,
                level=log.level,
                message=log.message,
                timestamp=log.timestamp.isoformat()
            )
            for log in logs
        ]
        
        return LogsResponse(
            logs=log_entries,
            total=total,
            level_filter=level
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

# Worker Management Endpoints for Task 1-4 Parallel Scraping
@router.post("/workers/start")
async def start_workers(
    num_workers: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Start enhanced subtitle processing workers with parallel scraping capabilities"""
    try:
        # Import here to avoid circular imports
        from workers.worker import start_workers as start_subtitle_workers, get_worker_status
        
        # Validate worker count
        if num_workers is not None:
            if num_workers < 1 or num_workers > 20:
                raise HTTPException(status_code=400, detail="num_workers must be between 1 and 20")
        
        # Update job status
        job = db.query(Job).first()
        if not job:
            job = Job()
            db.add(job)
        
        # Start workers
        result = start_subtitle_workers(num_workers)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        # Update job status
        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.stopped_at = None
        job.active_workers = result['status']['num_workers']
        
        db.commit()
        
        return {
            "message": result['message'],
            "status": "running",
            "worker_status": result['status'],
            "parallel_features": {
                "atomic_claiming": True,
                "exponential_backoff": True,
                "graceful_shutdown": True,
                "performance_monitoring": True
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start workers: {str(e)}")

@router.post("/workers/stop")
async def stop_workers(db: Session = Depends(get_db)):
    """Stop subtitle processing workers gracefully"""
    try:
        # Import here to avoid circular imports
        from workers.worker import stop_workers as stop_subtitle_workers
        
        # Stop workers
        result = stop_subtitle_workers()
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        # Update job status
        job = db.query(Job).first()
        if job:
            job.status = 'idle'
            job.active_workers = 0
            job.stopped_at = datetime.utcnow()
            db.commit()
        
        # Reset any processing videos to pending
        reset_count = reset_processing_videos(db)
        
        message = result['message']
        if reset_count > 0:
            message += f". Reset {reset_count} processing videos to pending"
        
        return {
            "message": message,
            "status": "stopped",
            "reset_videos": reset_count,
            "worker_status": result['status']
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to stop workers: {str(e)}")

@router.post("/workers/restart")
async def restart_workers(
    num_workers: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Restart workers with new configuration"""
    try:
        # Import here to avoid circular imports
        from workers.worker import restart_workers as restart_subtitle_workers
        
        # Validate worker count
        if num_workers is not None:
            if num_workers < 1 or num_workers > 20:
                raise HTTPException(status_code=400, detail="num_workers must be between 1 and 20")
        
        # Restart workers
        result = restart_subtitle_workers(num_workers)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        # Update job status
        job = db.query(Job).first()
        if not job:
            job = Job()
            db.add(job)
        
        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.stopped_at = None
        job.active_workers = result['status']['num_workers']
        
        db.commit()
        
        return {
            "message": "Workers restarted successfully",
            "status": "running",
            "worker_status": result['status']
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to restart workers: {str(e)}")

@router.get("/workers/status")
async def get_workers_status():
    """Get comprehensive worker status with performance metrics"""
    try:
        # Import here to avoid circular imports
        from workers.worker import get_worker_status, get_performance_metrics
        
        worker_status = get_worker_status()
        performance_metrics = get_performance_metrics()
        
        return {
            "worker_status": worker_status,
            "performance_metrics": performance_metrics,
            "features": {
                "parallel_processing": True,
                "atomic_job_claiming": True,
                "exponential_backoff": True,
                "graceful_shutdown": True,
                "real_time_monitoring": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker status: {str(e)}")

@router.get("/workers/performance")
async def get_worker_performance():
    """Get detailed worker performance metrics"""
    try:
        # Import here to avoid circular imports
        from workers.worker import get_performance_metrics
        
        metrics = get_performance_metrics()
        
        return {
            "performance_metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats(db: Session = Depends(get_db)):
    """Get current queue statistics"""
    try:
        queue_stats = get_queue_statistics(db)
        return QueueStatsResponse(**queue_stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue statistics: {str(e)}")