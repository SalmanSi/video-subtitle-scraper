# 1-1 Channel Ingestion

## Objective
Allow users to submit one or more YouTube channel URLs. System ingests channel metadata and enumerates all video URLs via `yt-dlp`, persisting channel + video records in SQLite. Robust error handling & idempotency required.

## TRD Reference
TRD Section 1.1 Channel Ingestion, 2.2 Database Schema, 2.3 Backend API (Channels endpoints).

## Scope
Backend API (`POST /channels`, `GET /channels`), DB persistence (`channels`, `videos` tables), yt-dlp integration, basic validation, duplicate protection, initial video queue population with status `pending`.

## Preconditions
- SQLite initialized with schema (see `migrations/init.sql`).
- `yt-dlp` installed (`requirements.txt`).
- FastAPI app running.

## Data Model Usage
- `channels`: store unique channel URL + derived name + total_videos.
- `videos`: one row per video URL, `status = 'pending'`, attempts=0.

## API Contract
**POST /channels**  
Request JSON: `{ "url": "<channel-url>" }` OR `{ "urls": ["<url1>", "<url2>"] }`  
Responses:
- 201 Created: `{ "channels_created": n, "videos_enqueued": m }`
- 200 OK (if all provided already existed): `{ "channels_skipped": [...], "videos_existing": k }`
- 400 Validation error / unsupported URL.

**GET /channels** -> Array of: `{ id, url, name, total_videos, pending, processing, completed, failed, created_at }`

## Validation Rules
1. URL must include `youtube.com` or `youtu.be` and represent a channel (accept any supported yt-dlp channel/playlist root; true canonicalization optional).
2. Reject if unreachable or yt-dlp fails extraction (log error; do not create partial channel w/out videos).
3. Idempotent: Re-posting existing channel returns existing channel, does NOT duplicate videos (insert new videos only if newly discovered since last ingestion).

## Ingestion Flow (Pseudocode)
```python
def ingest_channel(channel_url: str):
    norm_url = normalize(channel_url)
    with db.transaction():
        channel = get_or_create_channel(norm_url)
    # Use yt-dlp to list entries
    entries = extract_video_entries(norm_url)
    new_videos = 0
    for entry in entries:
        video_url = entry.get('webpage_url') or f"https://youtu.be/{entry['id']}"
        title = entry.get('title')
        if not video_exists(video_url):
            insert_video(channel.id, video_url, title)
            new_videos += 1
    update_channel_total(channel.id)
    return channel.id, new_videos
```

## yt-dlp Extraction Helper
```python
import yt_dlp

def extract_video_entries(channel_url: str) -> list:
    ydl_opts = { 'ignoreerrors': True, 'skip_download': True, 'extract_flat': True, 'quiet': True }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
    # info may be playlist-like
    if 'entries' in info:
        return [e for e in info['entries'] if e]
    return [info]
```

## Atomic DB Considerations
- Use a UNIQUE constraint on `videos.url` (already specified) to avoid duplicates; ignore conflicts.
- Wrap insert loop in a transaction batch for performance (bulk commit each 100 or at end).

## Error Handling
- If yt-dlp raises -> log to `logs` with level ERROR (no partial insert of videos if channel creation failed).
- If some videos fail to parse, still ingest rest (ignoreerrors True) & record WARN logs for skipped ones.

## Idempotent Reconciliation
On re-ingestion (manual or scheduled), insert only newly discovered videos (UNIQUE constraint). Optionally return counts.

## Edge Cases
1. Channel with zero videos → still create channel (total_videos=0).
2. Invalid / removed channel → 400 + log.
3. Network timeout → retry (exponential backoff up to settings.max_retries) before failing request.
4. Duplicate submission burst (race) → rely on UNIQUE and handle IntegrityError.
5. Private videos present → entries lacking accessible metadata; skip with WARN.

## Testing (Manual)
Add channel:
```bash
curl -X POST http://localhost:8000/channels \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com/@GoogleDevelopers"}'
```
List channels:
```bash
curl http://localhost:8000/channels | jq
```

## Acceptance Criteria
- Can add a valid channel; videos appear with `pending` status.
- Duplicate add does not duplicate existing videos; returns informative counts.
- Failed extraction logs error and returns 400 without orphan records.
- Channel progress fields (pending/completed/failed etc.) computed correctly in GET /channels.
- Performance: Ingest 400+ videos in under 60s (baseline) with network available.

## Definition of Done
- Endpoint implemented + unit tests for normalization, duplicate handling.
- DB migrations consistent; no manual schema edits required.
- Logging in place for success/error counts.
- Documentation updated (README & this task).

## Minimal Unit Test Ideas
- Add channel returns 201 & correct counts.
- Re-add channel returns 200 & zero new videos.
- Malformed URL -> 400.
- Simulated yt-dlp failure -> logged ERROR.

## Future Enhancements (Backlog)
- Support bulk multi-channel ingestion in one request.
- Periodic scheduled refresh of channel to discover new videos.
- Store additional metadata (thumbnails, description) for search.

## Implement yt-dlp logic here
       pass
   ```
7. Test the endpoint using a tool like Postman or cURL:
   ```bash
   curl -X POST "http://localhost:8000/channels" -H "Content-Type: application/json" -d '{"url": "https://www.youtube.com/c/YourChannel"}'
   ```

Acceptance Criteria: Channel URLs can be added, and video URLs are extracted and stored correctly.