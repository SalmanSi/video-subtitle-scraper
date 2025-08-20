## 1-2 Queue Management

### Objective
Maintain persistent job/video processing queue with statuses: `pending`, `processing`, `completed`, `failed`. Ensure safe recovery after crashes, accurate reconciliation, and requeue failed work according to retry policy.

### TRD Reference
Section 1.2 Queue Management; cross-cut with 1.3, 1.4, 1.5, and DB schema definitions.

### Core Rules
1. Default new videos -> `pending`.
2. Worker picks next `pending` video atomically -> set to `processing`.
3. On success + subtitle stored -> set `completed` + `completed_at`.
4. On failure -> increment `attempts`, record `last_error`. If attempts < `settings.max_retries` requeue to `pending` (with backoff scheduling info kept in memory). Else mark `failed`.
5. App startup: any `processing` rows reset to `pending` (crash recovery).
6. Reconciliation: If a subtitle exists for a video still labeled otherwise -> update to `completed`.

### DB Considerations
- Add index on `videos(status)` for faster pending selection.
- Potential future: separate `video_queue` table with priority; current schema sufficient.

### Atomic Selection Pattern (SQLite)
SQLite lacks `SELECT ... FOR UPDATE`; emulate atomic claim with an UPDATE filtering by status and using rowid ordering.
```sql
-- Pseudocode SQL executed inside a transaction
UPDATE videos SET status='processing'
WHERE id = (
  SELECT id FROM videos
  WHERE status='pending'
  ORDER BY id ASC
  LIMIT 1
)
RETURNING id;
```
If no row updated -> queue empty.

### Python Helper (Example)
```python
def claim_next_video(conn):
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")  # lock for atomicity
    cur.execute("""
        UPDATE videos SET status='processing'
        WHERE id = (
            SELECT id FROM videos WHERE status='pending' ORDER BY id LIMIT 1
        ) RETURNING id
    """)
    row = cur.fetchone()
    conn.commit()
    return row[0] if row else None
```

### Reconciliation Task
Run on startup and optionally scheduled:
```sql
UPDATE videos SET status='completed'
WHERE id IN (SELECT video_id FROM subtitles) AND status != 'completed';

UPDATE videos SET status='pending' WHERE status='processing';
```

### Edge Cases
1. Video added twice concurrently -> UNIQUE constraint handles; queue unaffected.
2. Worker crash mid-processing -> row remains `processing` until startup reset.
3. Subtitle present but failure recorded -> reconciliation overrides to `completed`.
4. Retry exhaustion -> status `failed`; manual retry endpoint can reset to `pending` & attempts=0.
5. Large queue scanning performance -> use indexed query; pagination if listing.

### Instrumentation
- Provide counts per status for channel summary (aggregate `videos` grouped by status).
- Optionally expose `/channels/{id}/videos?status=pending` filter.

### Acceptance Criteria
- Only one worker can claim a given pending video.
- Startup resets `processing` -> `pending`.
- Automatic reconciliation updates mismatched statuses.
- Failed videos after max retries remain `failed` until manual retry.
- Queue state persisted at all times in SQLite (no in-memory only state).

### Definition of Done
- Helper implemented & unit tested with concurrency simulation (thread/process) showing single claimant.
- Reconciliation executed on app startup.
- API list endpoints include status counts.

### Test Cases (Examples)
1. Insert 3 pending videos, claim in parallel -> each claimed once, no duplicates.
2. Mark one processing; restart -> becomes pending.
3. Insert subtitle manually; run reconciliation -> status becomes completed.
4. After max retries attempt -> status failed; retry endpoint resets to pending + attempts 0.
