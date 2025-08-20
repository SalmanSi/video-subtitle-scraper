## 2-3 Backend API

### Objective
Expose REST + WebSocket endpoints specified in TRD 2.3 for channels, videos, subtitles, jobs, and settings.

### Technology
FastAPI (preferred) with routers per resource. Use pydantic models for request/response validation.

### Routers & Endpoints
Channels:
- POST /channels
- GET /channels
- DELETE /channels/{id}

Videos:
- GET /channels/{id}/videos
- POST /videos/{id}/retry

Subtitles:
- GET /videos/{id}/subtitles
- GET /videos/{id}/subtitles/download
- GET /channels/{id}/subtitles/download (batch)

Jobs:
- POST /jobs/start
- POST /jobs/pause
- POST /jobs/resume
- GET /jobs/status (WebSocket)

Settings:
- GET /settings
- POST /settings

### Response Models (Sketch)
```python
class ChannelOut(BaseModel):
    id:int; url:str; name:str|None; total_videos:int
    pending:int; processing:int; completed:int; failed:int; created_at:datetime

class VideoOut(BaseModel):
    id:int; title:str|None; status:str; attempts:int; last_error:str|None

class SubtitleOut(BaseModel):
    video_id:int; language:str; content:str

class SettingsOut(BaseModel):
    max_workers:int; max_retries:int; backoff_factor:float; output_dir:str
```

### Error Codes
400 Validation / invalid input.
404 Not found (channel/video not existing or subtitle missing).
409 Conflict (retry non-failed video).
500 Internal unexpected error (logged).

### Pagination (Future)
Add `?limit=&offset=` for large listing endpoints.

### WebSocket Job Status Push
Server side periodic broadcaster (1s) sending JSON with counts (see Job Monitor task) + active workers.

### Security
Local-only usage (TRD). No auth required initially. Future: token-based protection.

### Acceptance Criteria
- All endpoints implemented returning JSON per spec.
- OpenAPI docs auto-generated at `/docs` show models.
- Error paths produce structured JSON: `{ "detail": "message" }`.

### Definition of Done
- Unit tests for core endpoints (channels add/list, video retry, subtitle retrieval, settings update).
- WebSocket tested manually (receives data frames).