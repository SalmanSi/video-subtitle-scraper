-- This SQL script initializes the database schema for the Video Subtitle Scraper application.

-- Create the channels table
CREATE TABLE channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    name TEXT,
    total_videos INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create the videos table
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    status TEXT CHECK(status IN ('pending','processing','completed','failed')) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_error TEXT,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
);

-- Create the subtitles table
CREATE TABLE subtitles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    language TEXT DEFAULT 'en',
    content TEXT NOT NULL,         -- subtitle text
    downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);

-- Create the jobs table
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT CHECK(status IN ('idle','running','paused','completed','failed')) DEFAULT 'idle',
    active_workers INTEGER DEFAULT 0,
    started_at DATETIME,
    stopped_at DATETIME
);

-- Create the logs table
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER,
    level TEXT CHECK(level IN ('INFO','WARN','ERROR')),
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE SET NULL
);

-- Create the settings table
CREATE TABLE settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton row
    max_workers INTEGER DEFAULT 5,
    max_retries INTEGER DEFAULT 3,
    backoff_factor REAL DEFAULT 2.0,
    output_dir TEXT DEFAULT './subtitles'
);