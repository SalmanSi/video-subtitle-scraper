"""
Worker Module for Task 1-4 Parallel Scraping
Handles N concurrent workers with atomic job claiming, retry logic with exponential backoff, 
and graceful shutdown according to TRD Section 1.4.

Enhanced with centralized error handling from Task 1-7.
"""

import os
import sys
import time
import threading
import signal
import logging
import math
from datetime import datetime
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from db.models import SessionLocal, Video, Setting, Log, get_db
from utils.queue_manager import claim_next_video, release_video, reset_processing_videos
from utils.subtitle_processor import process_video_subtitles
from utils.error_handler import (
    log, log_exception, handle_worker_exception, 
    TransientError, PermanentError, startup_recovery,
    classify_yt_dlp_error
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global stop event for graceful shutdown
STOP_EVENT = threading.Event()

class SubtitleWorker:
    """Individual worker for processing video subtitles with enhanced error handling and backoff"""
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.running = True
        self.processed_count = 0
        self.failed_count = 0
        self.current_video_id = None
        self.started_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
    def stop(self):
        """Stop the worker gracefully"""
        self.running = False
        log('INFO', f"Worker {self.worker_id} stopping...")
    
    def get_retry_delay(self, attempts: int, backoff_factor: float) -> float:
        """Calculate exponential backoff delay"""
        return min(backoff_factor ** attempts, 300)  # Cap at 5 minutes
    
    def run(self):
        """Enhanced worker loop with centralized error handling"""
        log('INFO', f"Worker {self.worker_id} started")
        
        while self.running and not STOP_EVENT.is_set():
            db = SessionLocal()
            try:
                # Claim next video from queue
                video_id = claim_next_video(db)
                
                if not video_id:
                    # No videos available, wait and continue
                    db.close()
                    time.sleep(1)  # Idle backoff
                    continue
                
                self.current_video_id = video_id
                self.last_activity = datetime.utcnow()
                
                # Get video details
                video = db.query(Video).filter(Video.id == video_id).first()
                if not video:
                    log('ERROR', f"Worker {self.worker_id}: Video {video_id} not found")
                    db.close()
                    continue
                
                log('INFO', f"Worker {self.worker_id} processing video {video_id}: {video.title}")
                
                try:
                    # Process subtitles (close DB connection during network operations)
                    db.close()
                    
                    # This may take a while, so we release the DB connection
                    success = self.process_video_safely(video_id)
                    
                    if success:
                        self.processed_count += 1
                        log('INFO', f"Worker {self.worker_id} completed video {video_id}")
                    else:
                        self.failed_count += 1
                        
                except Exception as e:
                    # Use centralized exception handling
                    action = handle_worker_exception(video_id, e)
                    self.failed_count += 1
                    log('ERROR', f"Worker {self.worker_id} error (action: {action}): {str(e)}", video_id)
                
            except Exception as e:
                log('ERROR', f"Worker {self.worker_id} critical error: {str(e)}")
                if 'video_id' in locals() and video_id:
                    try:
                        # Reconnect if needed for cleanup
                        if not db.is_active:
                            db = SessionLocal()
                        release_video(db, video_id, 'failed', f"Critical worker error: {str(e)}")
                    except Exception as cleanup_error:
                        log_exception(video_id, cleanup_error)
            finally:
                self.current_video_id = None
                if db.is_active:
                    db.close()
        
        log('INFO', f"Worker {self.worker_id} stopped. Processed: {self.processed_count}, Failed: {self.failed_count}")
    
    def process_video_safely(self, video_id: int) -> bool:
        """Process video with proper exception classification and handling"""
        try:
            # Process the video subtitles
            success = process_video_subtitles_standalone(video_id)
            return success
            
        except Exception as e:
            # Classify the error and raise appropriate exception type
            error_class = classify_yt_dlp_error(str(e))
            
            if error_class == PermanentError:
                raise PermanentError(str(e)) from e
            else:
                raise TransientError(str(e)) from e
    
    def process_video_with_retry(self, video_id: int, max_retries: int, backoff_factor: float) -> bool:
        """Process video with built-in retry logic and exponential backoff"""
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                return False
            
            # Check if we've exceeded retry attempts
            if video.attempts >= max_retries:
                release_video(db, video_id, 'failed', f"Exceeded maximum retries ({max_retries})")
                return False
            
            try:
                # Close DB during network operation
                db.close()
                
                # Process the video (this is the network-bound operation)
                success = process_video_subtitles_standalone(video_id)
                
                # Reconnect to update status
                db = SessionLocal()
                
                if success:
                    release_video(db, video_id, 'completed')
                    return True
                else:
                    # Determine if this should be retried
                    video = db.query(Video).filter(Video.id == video_id).first()
                    if video and video.attempts < max_retries:
                        # Calculate backoff delay
                        delay = self.get_retry_delay(video.attempts, backoff_factor)
                        logger.info(f"Worker {self.worker_id}: Video {video_id} failed, retrying in {delay:.1f}s (attempt {video.attempts + 1}/{max_retries})")
                        
                        # Apply exponential backoff
                        time.sleep(delay)
                        
                        # Mark for retry
                        release_video(db, video_id, 'failed', "Subtitle extraction failed, retrying")
                    else:
                        release_video(db, video_id, 'failed', "Subtitle extraction failed permanently")
                    return False
                    
            except Exception as e:
                # Reconnect if needed
                if not db.is_active:
                    db = SessionLocal()
                    
                is_transient = self.classify_error(e)
                
                if is_transient and video.attempts < max_retries:
                    # Transient error - apply backoff and retry
                    delay = self.get_retry_delay(video.attempts, backoff_factor)
                    logger.warning(f"Worker {self.worker_id}: Transient error for video {video_id}, retrying in {delay:.1f}s: {str(e)}")
                    
                    time.sleep(delay)
                    release_video(db, video_id, 'failed', f"Transient error: {str(e)}")
                    return False
                else:
                    # Permanent error or max retries exceeded
                    error_msg = f"Permanent error: {str(e)}" if not is_transient else f"Max retries exceeded: {str(e)}"
                    logger.error(f"Worker {self.worker_id}: {error_msg}")
                    release_video(db, video_id, 'failed', error_msg)
                    return False
                    
        finally:
            if db.is_active:
                db.close()

def process_video_subtitles_standalone(video_id: int) -> bool:
    """Standalone function to process video subtitles without holding DB connection"""
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return False
        
        # Use the existing subtitle processor
        return process_video_subtitles(video, db)
    finally:
        db.close()

class WorkerManager:
    """Enhanced worker manager with graceful shutdown and monitoring"""
    
    def __init__(self, num_workers: int = None):
        self.workers: List[SubtitleWorker] = []
        self.threads: List[threading.Thread] = []
        self.running = False
        self.startup_recovery_done = False
        
        # Get number of workers from settings or use default
        if num_workers is None:
            db = SessionLocal()
            try:
                settings = db.query(Setting).filter(Setting.id == 1).first()
                self.num_workers = settings.max_workers if settings else 5
            finally:
                db.close()
        else:
            self.num_workers = num_workers
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            STOP_EVENT.set()
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _startup_recovery(self):
        """Perform startup recovery to reset stuck videos"""
        if self.startup_recovery_done:
            return
            
        log('INFO', "Performing startup recovery...")
        try:
            # Use centralized startup recovery
            startup_recovery()
        except Exception as e:
            log_exception(None, e)
        finally:
            self.startup_recovery_done = True
    
    def start(self):
        """Start all workers with enhanced monitoring"""
        if self.running:
            logger.warning("Workers already running")
            return
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Perform startup recovery
        self._startup_recovery()
        
        # Clear stop event
        STOP_EVENT.clear()
        
        self.running = True
        logger.info(f"Starting {self.num_workers} subtitle workers...")
        
        # Create and start worker threads
        for i in range(self.num_workers):
            worker = SubtitleWorker(i + 1)
            thread = threading.Thread(
                target=worker.run, 
                name=f"SubtitleWorker-{i+1}",
                daemon=False  # Ensure proper shutdown
            )
            
            self.workers.append(worker)
            self.threads.append(thread)
            thread.start()
            
            # Small delay between worker starts to avoid DB contention
            time.sleep(0.1)
        
        logger.info(f"Started {len(self.workers)} subtitle workers")
    
    def stop(self):
        """Stop all workers gracefully with timeout"""
        if not self.running:
            logger.warning("Workers not running")
            return
        
        logger.info("Initiating graceful shutdown of subtitle workers...")
        
        # Set global stop event
        STOP_EVENT.set()
        self.running = False
        
        # Signal all workers to stop
        for worker in self.workers:
            worker.stop()
        
        # Wait for all threads to complete with timeout
        shutdown_timeout = 30  # 30 seconds
        start_time = time.time()
        
        for i, thread in enumerate(self.threads):
            remaining_time = shutdown_timeout - (time.time() - start_time)
            if remaining_time <= 0:
                logger.warning(f"Shutdown timeout reached, some workers may not have stopped gracefully")
                break
                
            logger.info(f"Waiting for worker {i+1} to stop (timeout: {remaining_time:.1f}s)...")
            thread.join(timeout=remaining_time)
            
            if thread.is_alive():
                logger.warning(f"Worker {i+1} did not stop within timeout")
        
        # Perform final cleanup - reset any videos that were still processing
        db = SessionLocal()
        try:
            reset_count = reset_processing_videos(db)
            if reset_count > 0:
                logger.info(f"Shutdown cleanup: Reset {reset_count} processing videos to pending")
        except Exception as e:
            logger.error(f"Shutdown cleanup failed: {e}")
        finally:
            db.close()
        
        logger.info("All subtitle workers stopped")
        self.workers.clear()
        self.threads.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive worker status"""
        total_processed = sum(w.processed_count for w in self.workers)
        total_failed = sum(w.failed_count for w in self.workers)
        active_count = sum(1 for t in self.threads if t.is_alive())
        
        # Get queue statistics
        db = SessionLocal()
        try:
            from utils.queue_manager import get_queue_statistics
            queue_stats = get_queue_statistics(db)
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            queue_stats = {}
        finally:
            db.close()
        
        return {
            'running': self.running,
            'num_workers': len(self.workers),
            'active_workers': active_count,
            'total_processed': total_processed,
            'total_failed': total_failed,
            'startup_recovery_done': self.startup_recovery_done,
            'queue_stats': queue_stats,
            'workers': [
                {
                    'id': w.worker_id,
                    'processed': w.processed_count,
                    'failed': w.failed_count,
                    'running': w.running,
                    'current_video': w.current_video_id,
                    'started_at': w.started_at.isoformat(),
                    'last_activity': w.last_activity.isoformat(),
                    'thread_alive': self.threads[i].is_alive() if i < len(self.threads) else False
                }
                for i, w in enumerate(self.workers)
            ]
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        if not self.workers:
            return {'error': 'No workers running'}
        
        total_runtime = sum(
            (datetime.utcnow() - w.started_at).total_seconds() 
            for w in self.workers
        )
        total_processed = sum(w.processed_count for w in self.workers)
        total_failed = sum(w.failed_count for w in self.workers)
        
        avg_runtime = total_runtime / len(self.workers) if self.workers else 0
        processing_rate = total_processed / (total_runtime / 3600) if total_runtime > 0 else 0  # per hour
        success_rate = total_processed / (total_processed + total_failed) if (total_processed + total_failed) > 0 else 0
        
        return {
            'average_runtime_seconds': avg_runtime,
            'processing_rate_per_hour': processing_rate,
            'success_rate': success_rate,
            'total_processed': total_processed,
            'total_failed': total_failed,
            'estimated_completion_time': self._estimate_completion_time()
        }
    
    def _estimate_completion_time(self) -> Optional[str]:
        """Estimate time to complete remaining queue"""
        try:
            db = SessionLocal()
            try:
                from utils.queue_manager import get_queue_statistics
                stats = get_queue_statistics(db)
                pending_count = stats.get('pending', 0)
                
                if pending_count == 0:
                    return "Queue complete"
                
                # Calculate processing rate
                total_processed = sum(w.processed_count for w in self.workers)
                total_runtime = sum(
                    (datetime.utcnow() - w.started_at).total_seconds() 
                    for w in self.workers
                )
                
                if total_processed > 0 and total_runtime > 0:
                    rate_per_second = total_processed / total_runtime
                    estimated_seconds = pending_count / (rate_per_second * len(self.workers))
                    
                    hours = int(estimated_seconds // 3600)
                    minutes = int((estimated_seconds % 3600) // 60)
                    
                    if hours > 0:
                        return f"~{hours}h {minutes}m"
                    else:
                        return f"~{minutes}m"
                
                return "Calculating..."
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to estimate completion time: {e}")
            return "Unknown"

# Global worker manager instance
worker_manager = WorkerManager()

def start_workers(num_workers: int = None) -> Dict[str, Any]:
    """Start subtitle workers with enhanced monitoring"""
    global worker_manager
    try:
        if num_workers:
            worker_manager = WorkerManager(num_workers)
        worker_manager.start()
        return {
            'success': True,
            'message': f'Started {worker_manager.num_workers} workers',
            'status': worker_manager.get_status()
        }
    except Exception as e:
        logger.error(f"Failed to start workers: {e}")
        return {
            'success': False,
            'message': f'Failed to start workers: {str(e)}',
            'status': {}
        }

def stop_workers() -> Dict[str, Any]:
    """Stop subtitle workers gracefully"""
    global worker_manager
    try:
        worker_manager.stop()
        return {
            'success': True,
            'message': 'Workers stopped successfully',
            'status': worker_manager.get_status()
        }
    except Exception as e:
        logger.error(f"Failed to stop workers: {e}")
        return {
            'success': False,
            'message': f'Failed to stop workers: {str(e)}',
            'status': {}
        }

def get_worker_status() -> Dict[str, Any]:
    """Get comprehensive worker status"""
    global worker_manager
    return worker_manager.get_status()

def get_performance_metrics() -> Dict[str, Any]:
    """Get worker performance metrics"""
    global worker_manager
    return worker_manager.get_performance_metrics()

def restart_workers(num_workers: int = None) -> Dict[str, Any]:
    """Restart workers with new configuration"""
    logger.info("Restarting workers...")
    stop_result = stop_workers()
    if not stop_result['success']:
        return stop_result
    
    # Brief pause to ensure clean shutdown
    time.sleep(2)
    
    return start_workers(num_workers)

if __name__ == "__main__":
    # Enhanced command line interface for testing
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Subtitle Worker Manager for Task 1-4')
    parser.add_argument('--workers', type=int, default=5, help='Number of workers (1-20)')
    parser.add_argument('--test', action='store_true', help='Run in test mode (30s duration)')
    parser.add_argument('--performance', action='store_true', help='Show performance metrics')
    parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds')
    
    args = parser.parse_args()
    
    # Validate worker count
    if args.workers < 1 or args.workers > 20:
        logger.error("Worker count must be between 1 and 20")
        sys.exit(1)
    
    if args.performance:
        # Show performance metrics of running workers
        status = get_worker_status()
        metrics = get_performance_metrics()
        
        print("\n" + "="*60)
        print("WORKER PERFORMANCE METRICS")
        print("="*60)
        print(f"Running: {status['running']}")
        print(f"Active Workers: {status['active_workers']}/{status['num_workers']}")
        print(f"Total Processed: {status['total_processed']}")
        print(f"Total Failed: {status['total_failed']}")
        
        if 'processing_rate_per_hour' in metrics:
            print(f"Processing Rate: {metrics['processing_rate_per_hour']:.1f} videos/hour")
            print(f"Success Rate: {metrics['success_rate']:.1%}")
            print(f"Est. Completion: {metrics['estimated_completion_time']}")
        
        print("\nQueue Statistics:")
        queue_stats = status.get('queue_stats', {})
        for status_type, count in queue_stats.items():
            print(f"  {status_type}: {count}")
        
        sys.exit(0)
    
    if args.test:
        # Test mode - process videos for specified duration and show results
        logger.info(f"Running in test mode for {args.duration} seconds with {args.workers} workers...")
        worker_manager = WorkerManager(args.workers)
        
        try:
            # Start workers
            start_time = time.time()
            worker_manager.start()
            
            # Monitor progress
            while time.time() - start_time < args.duration:
                if not worker_manager.running:
                    break
                    
                # Show status every 10 seconds
                if int(time.time() - start_time) % 10 == 0:
                    status = worker_manager.get_status()
                    logger.info(f"Progress: {status['total_processed']} processed, {status['total_failed']} failed, {status['active_workers']} active")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        finally:
            # Show final results
            final_status = worker_manager.get_status()
            metrics = worker_manager.get_performance_metrics()
            
            print("\n" + "="*60)
            print("TEST RESULTS")
            print("="*60)
            print(f"Duration: {args.duration}s")
            print(f"Workers: {args.workers}")
            print(f"Videos Processed: {final_status['total_processed']}")
            print(f"Videos Failed: {final_status['total_failed']}")
            
            if 'processing_rate_per_hour' in metrics:
                print(f"Processing Rate: {metrics['processing_rate_per_hour']:.1f} videos/hour")
                print(f"Success Rate: {metrics['success_rate']:.1%}")
            
            worker_manager.stop()
    else:
        # Normal mode - run until interrupted
        logger.info(f"Starting {args.workers} workers in production mode...")
        worker_manager = WorkerManager(args.workers)
        
        try:
            worker_manager.start()
            
            # Keep running until interrupted
            while worker_manager.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            worker_manager.stop()
            
            # Show final statistics
            final_status = worker_manager.get_status()
            logger.info(f"Final statistics: {final_status['total_processed']} processed, {final_status['total_failed']} failed")