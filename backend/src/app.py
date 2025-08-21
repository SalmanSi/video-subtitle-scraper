from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import channels, videos, subtitles, jobs
from db import models
from utils.queue_manager import reconcile_video_statuses
from utils.error_handler import startup_recovery, log, log_exception
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Video Subtitle Scraper API",
    description="API for scraping subtitles from YouTube videos",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        log('INFO', "Database initialized successfully")
        
        # Perform centralized startup recovery (resets processing videos and attempts)
        startup_recovery()
        
        # Reconcile video statuses with actual subtitle data
        db = models.SessionLocal()
        try:
            reconcile_results = reconcile_video_statuses(db)
            if reconcile_results['completed'] > 0:
                log('INFO', f"Queue reconciliation: Marked {reconcile_results['completed']} videos as completed")
        finally:
            db.close()
            
        log('INFO', "Application startup and recovery completed")
        
    except Exception as e:
        log_exception(None, e)
        raise

@app.on_event("shutdown")
def shutdown_event():
    """Cleanup resources if necessary"""
    try:
        models.close_db()
        log('INFO', "Database connections closed")
    except Exception as e:
        log_exception(None, e)

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