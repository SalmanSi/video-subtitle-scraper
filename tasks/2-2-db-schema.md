## 2-2 Database Schema

### Objective
Define and initialize SQLite schema aligning with TRD Section 2.2 supporting ingestion, queue, subtitles, logging, settings, and job control.

### Tables Summary
1. `channels` – channel metadata & aggregate counts (optional derived counts computed on demand rather than stored except `total_videos`).
2. `videos` – per-video queue state & status tracking.
3. `subtitles` – persisted transcript text.
4. `jobs` – lifecycle of scraping session.
5. `logs` – application event/error records.
6. `settings` – singleton configuration.

### Schema SQL (Reference)
```sql
CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE NOT NULL,
  name TEXT,
  total_videos INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
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

CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);

CREATE TABLE IF NOT EXISTS subtitles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  language TEXT DEFAULT 'en',
  content TEXT NOT NULL,
  downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT CHECK(status IN ('idle','running','paused','completed','failed')) DEFAULT 'idle',
  active_workers INTEGER DEFAULT 0,
  started_at DATETIME,
  stopped_at DATETIME
);

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER,
  level TEXT CHECK(level IN ('INFO','WARN','ERROR')),
  message TEXT NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  max_workers INTEGER DEFAULT 5,
  max_retries INTEGER DEFAULT 3,
  backoff_factor REAL DEFAULT 2.0,
  output_dir TEXT DEFAULT './subtitles'
);
INSERT OR IGNORE INTO settings(id) VALUES (1);
```

### Migration Strategy
- Initial schema via `migrations/init.sql` executed at startup if DB file missing.
- For future changes adopt simple migration table `schema_migrations(version)` storing applied versions.

### Data Integrity Rules
- UNIQUE `videos.url` ensures dedup across channels (if URL moves channels, may violate; acceptable assumption: stable mapping).
- `attempts` reset logic on restart per error handling policy.
- `total_videos` updated after ingestion; not decremented unless deletion cascade triggers recount (future: trigger-based update).

### Acceptance Criteria
- Schema matches TRD exactly.
- Indexes exist for status and channel lookups.
- settings row auto-created.

### Definition of Done
- Verified schema creation script runs cleanly; tables present; initial settings row exists.
