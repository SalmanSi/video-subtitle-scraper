from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Text, CheckConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import sqlite3
import os

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    name = Column(String)
    total_videos = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")

class Video(Base):
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    status = Column(String, CheckConstraint("status IN ('pending','processing','completed','failed')"), default='pending')
    attempts = Column(Integer, default=0)
    last_error = Column(Text)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_videos_status', 'status'),
        Index('idx_videos_channel', 'channel_id'),
        Index('idx_videos_pending_order', 'status', 'id'),  # Optimized for queue claiming
    )
    
    # Relationships
    channel = relationship("Channel", back_populates="videos")
    subtitles = relationship("Subtitle", back_populates="video", cascade="all, delete-orphan")

class Subtitle(Base):
    __tablename__ = 'subtitles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    language = Column(String, default='en')
    content = Column(Text, nullable=False)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="subtitles")

class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String, CheckConstraint("status IN ('idle','running','paused','completed','failed')"), default='idle')
    active_workers = Column(Integer, default=0)
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)

class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='SET NULL'))
    level = Column(String, CheckConstraint("level IN ('INFO','WARN','ERROR')"))
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    max_workers = Column(Integer, default=5)
    max_retries = Column(Integer, default=3)
    backoff_factor = Column(Integer, default=2)
    output_dir = Column(String, default='./subtitles')

    __table_args__ = (
        CheckConstraint("id = 1"),
    )

# Database setup
# Use absolute path to ensure consistent database location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Go up from src/db to backend/
DATABASE_PATH = os.path.join(BASE_DIR, "data", "app.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Configure engine for better SQLite concurrency
engine = create_engine(
    DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 20,  # 20 second timeout for database locks
    },
    pool_pre_ping=True,
    pool_recycle=300
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database and create all tables"""
    # Check if database file exists to determine if this is first run
    db_exists = os.path.exists(DATABASE_PATH)
    
    if not db_exists:
        # For new database, execute the migration SQL file
        _execute_migration_file()
    else:
        # For existing database, just create any new tables via SQLAlchemy
        Base.metadata.create_all(bind=engine)
        
        # Insert default settings if not exists
        db = SessionLocal()
        try:
            if not db.query(Setting).filter(Setting.id == 1).first():
                default_settings = Setting(id=1)
                db.add(default_settings)
                db.commit()
        finally:
            db.close()

def _execute_migration_file():
    """Execute the initial migration SQL file"""
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))), 
        "migrations", 
        "init.sql"
    )
    
    if os.path.exists(migration_file):
        # Use raw SQLite connection to execute the migration
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            # Execute the migration in chunks (split by semicolon)
            for statement in migration_sql.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(statement)
            
            conn.commit()
        finally:
            conn.close()
    else:
        # Fallback to SQLAlchemy if migration file not found
        Base.metadata.create_all(bind=engine)
        
        # Insert default settings
        db = SessionLocal()
        try:
            if not db.query(Setting).filter(Setting.id == 1).first():
                default_settings = Setting(id=1)
                db.add(default_settings)
                db.commit()
        finally:
            db.close()

def check_migration_status():
    """Check which migrations have been applied"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if migration table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='schema_migrations'
        """)
        
        if cursor.fetchone():
            # Get applied migrations
            cursor.execute("SELECT version FROM schema_migrations ORDER BY applied_at")
            applied_migrations = [row[0] for row in cursor.fetchall()]
            return applied_migrations
        else:
            return []
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except:
            pass

def apply_migration(version, sql_statements):
    """Apply a specific migration"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Ensure schema_migrations table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if migration already applied
        cursor.execute("SELECT version FROM schema_migrations WHERE version = ?", (version,))
        if cursor.fetchone():
            return False  # Already applied
        
        # Apply migration statements
        for statement in sql_statements:
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        # Record migration as applied
        cursor.execute(
            "INSERT INTO schema_migrations(version) VALUES (?)", 
            (version,)
        )
        
        conn.commit()
        return True  # Successfully applied
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def close_db():
    """Close database connections"""
    pass