## 1-6 UI: Onboarding / Add Channel

### Objective
Provide form for user to input one or multiple channel URLs; submit to backend; show ingestion progress & immediate feedback.

### Requirements
- Support entering multiple URLs separated by newline or comma.
- Validate basic pattern client-side before submitting.
- Handle partial success (some channels added, some errors) with detailed list.

### Component Behavior
1. User pastes URLs.
2. Split & trim -> array.
3. POST each (or single bulk endpoint if implemented) sequentially or concurrently with concurrency limit (e.g., 3 at a time) to avoid server overload.
4. Display per-channel status row (Pending, Adding..., Added (#videos), Error(message)).
5. After all, offer button to go to Dashboard.

### Sketch
```tsx
function ChannelOnboarding(){
  const [input,setInput]=useState('')
  const [rows,setRows]=useState([])
  const submit=async()=>{
    const urls = parseInput(input)
    const results=[]
    for(const url of urls){
      results.push({url,status:'adding'})
      setRows([...results])
      try{
        const r= await fetch('/api/channels',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})})
        if(r.ok){
          const data=await r.json(); results[results.length-1]={url,status:'added',info:data}
        } else { results[results.length-1]={url,status:'error',error:(await r.json()).detail} }
      }catch(e){ results[results.length-1]={url,status:'error',error:String(e)} }
      setRows([...results])
    }
  }
  return <div>
    <h1>Add Channels</h1>
    <textarea value={input} onChange={e=>setInput(e.target.value)} placeholder="Paste channel URLs"></textarea>
    <button onClick={submit}>Ingest</button>
    <ul>{rows.map(r=> <li key={r.url}>{r.url} - {r.status}</li>)}</ul>
  </div>
}
```

### Edge Cases
1. Duplicate URL in same submission -> de-duplicate client-side.
2. Already existing channel -> backend returns 200 & message; show as "Already added".
3. Network failure mid-batch -> allow retry button for specific failed rows.
4. Extremely long paste (>100 URLs) -> prompt confirmation.
5. Invalid formatting -> client highlights line numbers.

### Acceptance Criteria
- Multiple URLs input supported; each processed with individual status.
- Clear indication of success vs error.
- Dashboard shows newly added channels immediately after ingestion (manual refresh acceptable initial version).

### Definition of Done
- Component accessible from index route.
- Basic validation + success/error messages working.

---

### Added Enhancement: Single Video Subtitle Viewer & Download

While implementing onboarding, a dedicated UI for viewing and downloading subtitles of an individual completed video was also added for faster verification and manual access.

#### Location / Routing
- Page route: `/videos/[id]/subtitles` (Next.js App Router)
- Linked from Channel detail page via a new "View Subtitles" button shown for videos with status `completed`.

#### Backend Endpoints Utilized
- `GET /api/subtitles/videos/{video_id}` → Fetch video metadata + list of subtitle records (language, content_length, timestamps).
- `GET /api/subtitles/{subtitle_id}/download` → Download selected language as `.txt` (opens in new tab).
- (Existing) `GET /api/subtitles/videos/{video_id}/download` still available for bulk-per-video download (all languages / zip or single txt when only one).

#### UI Features
1. Fetches all subtitles for a video and displays:
  - Video title + external YouTube link.
  - List of available subtitle languages with size indicator (approx k chars).
2. Language selection switches in-memory rendered transcript (no refetch).
3. Transcript panel: scrollable, monospace, preserves line breaks (`white-space: pre-wrap`).
4. Per-language download button triggers direct text download using `subtitle_id` endpoint.
5. Basic loading & error states with retry.
6. Graceful fallback if no subtitles present (informational empty state panel).

#### Edge Cases & Handling
- Missing / invalid video id → error banner with retry.
- No subtitles → user sees neutral empty state instead of blank screen.
- Large subtitle content → scroll container capped at 600px height.

#### Potential Future Enhancements (Not Implemented Yet)
- Client-side search within transcript.
- Copy-to-clipboard & highlight matches.
- Toggle auto-generated vs human subtitles if both exist.
- Lazy load extremely large subtitle blobs (streaming / virtualization).

#### Acceptance (Additional)
- From channel detail view, user can both download all subtitles (existing button) and navigate to viewer for inline per-language inspection & download.

This section documents functionality delivered alongside onboarding to satisfy broader TRD UI requirements (Subtitle Viewer / Single Download) early.