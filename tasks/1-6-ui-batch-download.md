## 1-6 UI: Batch Download

### Objective
Provide UI to download all completed subtitles for a channel as a single `.zip` (per TRD 1.6 Batch Download). Backend endpoint: `GET /channels/{id}/subtitles/download`.

### UX Requirements
- Button visible on channel detail (video queue) page when at least one completed subtitle exists.
- Disabled state with tooltip if zero completed.
- Progress indicator (simple spinner) while downloading.

### API Response
Content-Type: application/zip
Filename: `channel-<id>-subtitles.zip`

### Backend Implementation Sketch
```python
@router.get('/channels/{channel_id}/subtitles/download')
def download_channel_subtitles(channel_id: int):
    subs = fetch_completed_subtitles(channel_id)
    if not subs:
        raise HTTPException(404, 'No completed subtitles')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for s in subs:
            safe_title = slugify(s.video_title)[:80]
            name = f"{s.video_id}_{safe_title}.txt"
            z.writestr(name, s.content)
    buf.seek(0)
    return StreamingResponse(buf, media_type='application/zip', headers={
        'Content-Disposition': f'attachment; filename=channel-{channel_id}-subtitles.zip'
    })
```

### Frontend Component Snippet
```tsx
const handleDownload = async () => {
  setLoading(true)
  try {
    const res = await fetch(`/api/channels/${channelId}/subtitles/download`)
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `channel-${channelId}-subtitles.zip`
    a.click()
    URL.revokeObjectURL(url)
  } finally { setLoading(false) }
}
```

### Edge Cases
1. No subtitles -> 404 handled -> show inline message.
2. Large total content -> memory: consider streaming; initial version acceptable (< few MB).
3. Special characters in title -> sanitized.
4. Duplicate filenames -> include video_id prefix ensures uniqueness.
5. Partial failures mid-zip build -> build in memory; if failure occurs return 500, no partial file.

### Acceptance Criteria
- Button triggers download of zip containing one `.txt` per completed video.
- Filenames include video id & readable title fragment.
- Empty channel returns user-visible message (not blank file).
- Works in Chrome/Firefox.

### Definition of Done
- Endpoint implemented & unit test verifying zip entries.
- Frontend button integrated & disabled state logic.
- Manual test with mixed statuses passes.