## 1-7 Error Handling

### Objective
Centralized logging & recovery strategy: all errors recorded in `logs` table; failed items requeued automatically until retry limit; minimal lost work on crash.

### TRD Reference
Section 1.7 Error Handling; intersects with queue/retry logic.

### Logging Requirements
- Fields: `video_id` (nullable), `level` (INFO/WARN/ERROR), `message`, `timestamp`.
- Always capture stack trace for ERROR (store trimmed message; full trace optional in separate file if needed).

### Helper
```python
import logging, traceback

def log(level: str, message: str, video_id: int|None=None):
    logging.log(getattr(logging, level), message)
    with db_conn() as c:
        c.execute('INSERT INTO logs(video_id, level, message) VALUES (?,?,?)', (video_id, level, message))

def log_exception(video_id: int|None, exc: Exception):
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    trimmed = tb[-4000:]  # avoid unbounded size
    log('ERROR', trimmed, video_id)
```

### Automatic Requeue
In worker processing:
```python
try:
    process_video_subtitles(video)
except TransientError as e:
    log('WARN', f'Transient error: {e}', video.id)
    schedule_retry(video.id, e)
except PermanentError as e:
    log('ERROR', f'Permanent error: {e}', video.id)
    mark_failed(video.id, str(e))
except Exception as e:
    log_exception(video.id, e)
    schedule_retry(video.id, e)
```

### Retry Counter Reset
Per TRD, retry attempts must reset after system restart. Implementation: On startup set `attempts=0` WHERE status in ('pending','processing'). (Alternative: only reset processing; choose approach aligning with TRD phrase: "Retry attempts must reset after system restart" -> all non-completed resets.)
```sql
UPDATE videos SET attempts=0 WHERE status IN ('pending','processing');
```

### Dashboard Visibility
- Recent errors displayed in Job Monitor.
- Provide API `/logs?limit=50&level=ERROR` for UI debugging (future).

### Edge Cases
1. Logging failure (DB locked) -> fallback to console only.
2. Very large error message truncated to prevent DB bloat.
3. Flood of repeated identical errors -> consider dedup (future enhancement).
4. Video becomes available after temporary 403 -> retries succeed.
5. Unexpected schema errors -> escalate & mark job failed.

### Acceptance Criteria
- Errors appear in `logs` with correct level & timestamp.
- Transient errors cause retry until max then video -> failed.
- After restart, attempts reset enabling fresh retry window.
- No unhandled exceptions crash entire service (caught & logged).

### Definition of Done
- Logging helper implemented & imported in key modules.
- Tests: logging insert, retry reset logic, transient/permanent classification.