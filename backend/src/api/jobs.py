from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from db.models import Job, Setting, get_db
from utils.queue_manager import (
    get_queue_statistics,
    reset_processing_videos,
    reconcile_video_statuses,
    cleanup_old_logs
)

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

class QueueStatsResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    total: int

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