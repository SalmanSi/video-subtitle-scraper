from fastapi import FastAPI
from api import channels, videos, subtitles, jobs
from db import models
from utils.queue_manager import reset_processing_videos, reconcile_video_statuses
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Video Subtitle Scraper API",
    description="API for scraping subtitles from YouTube videos",
    version="1.0.0"
)

# Include the routers for each API module
app.include_router(channels.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(subtitles.router, prefix="/api")
app.include_router(jobs.router)

@app.on_event("startup")
def startup_event():
    """Initialize the database and recover queue state"""
    try:
        # Initialize database
        models.init_db()
        logging.info("Database initialized successfully")
        
        # Recover queue state after startup
        db = models.SessionLocal()
        try:
            # Reset any videos that were stuck in 'processing' state
            reset_count = reset_processing_videos(db)
            if reset_count > 0:
                logging.info(f"Queue recovery: Reset {reset_count} processing videos to pending")
            
            # Reconcile video statuses with actual subtitle data
            reconcile_results = reconcile_video_statuses(db)
            if reconcile_results['completed'] > 0:
                logging.info(f"Queue reconciliation: Marked {reconcile_results['completed']} videos as completed")
                
        finally:
            db.close()
            
        logging.info("Queue recovery and reconciliation completed")
        
    except Exception as e:
        logging.error(f"Failed to initialize application: {e}")
        raise

@app.on_event("shutdown")
def shutdown_event():
    """Cleanup resources if necessary"""
    try:
        models.close_db()
        logging.info("Database connections closed")
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Video Subtitle Scraper API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)