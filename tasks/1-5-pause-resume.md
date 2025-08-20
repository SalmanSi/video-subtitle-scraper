# Contents of the file: /video-subtitle-scraper/video-subtitle-scraper/tasks/1-5-pause-resume.md

## 1-5 Pause / Resume

### Objective
Allow users to pause the worker pool (no new videos claimed) and later resume without losing queue integrity. In-progress videos at pause continue or stop gracefully; system guarantees consistency.

### TRD Reference
Section 1.5 Pause/Resume; related to jobs table.

### Jobs Table Usage
- Single active job row (latest) representing current scraping session.
- Fields: `status` in (`idle`,`running`,`paused`,`completed`,`failed`), `active_workers`, timestamps.

### State Machine
idle -> running (start)
running -> paused (pause)
paused -> running (resume)
running -> completed (no pending videos & workers drained)
Any -> failed (fatal error)

### Implementation Steps
1. Add job initialization on first `/jobs/start` if no active running/paused record.
2. Maintain global PAUSE_EVENT (threading.Event). Workers check `.is_set()` before claiming next video; if set, they go idle & update active count.
3. `/jobs/pause`:
   - Set PAUSE_EVENT.
   - Update jobs.status='paused'.
   - Return current queue snapshot.
4. `/jobs/resume`:
   - Clear PAUSE_EVENT.
   - Ensure any `processing` rows (left from earlier crash) are reset to `pending` only if they have no subtitle.
   - Update jobs.status='running'.
5. On shutdown (SIGTERM): set PAUSE_EVENT, join workers, then reset leftover `processing` -> `pending` (crash safety per TRD 1.2/1.5).

### API Contracts
POST /jobs/start -> 200 `{status:'running', workers:n}` (idempotent; if already running returns same)
POST /jobs/pause -> 200 `{status:'paused'}`
POST /jobs/resume -> 200 `{status:'running'}`
GET /jobs/status (WebSocket) -> live JSON: `{ status, active_workers, pending, processing, completed, failed, throughput_per_min }`

### Pseudocode (Pause)
```python
@router.post('/jobs/pause')
def pause_jobs():
    PAUSE_EVENT.set()
    update_job_status('paused')
    return current_job_state()
```

### Pseudocode (Resume)
```python
@router.post('/jobs/resume')
def resume_jobs():
    reset_orphan_processing()
    PAUSE_EVENT.clear()
    update_job_status('running')
    return current_job_state()
```

### Edge Cases
1. Pause when already paused -> 200 no-op.
2. Resume when running -> 200 no-op.
3. Pause while zero active workers -> still transitions.
4. Resume after crash where some `processing` already have subtitles -> reconciliation sets completed.
5. Start when job record exists in paused -> acts as resume.

### Acceptance Criteria
- Issuing pause stops new claims within ≤1 second.
- Resuming restarts processing without duplicate processing of partially-complete videos.
- Crash during running leaves at most one video lost (per NFR) -> validated by resetting `processing` statuses.

### Definition of Done
- Endpoints implemented & documented.
- Unit test: pause prevents new claims (mock time / claim function).
- Manual test sequence start -> pause -> resume works.