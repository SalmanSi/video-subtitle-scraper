## 1-6 UI: Video Queue (Per Channel)

### Objective
List all videos for a channel with their status, attempts, and last error. Provide retry for failed videos and link to subtitle viewer when completed.

### API
GET /channels/{id}/videos -> list `{ id, title, status, attempts, last_error }`
POST /videos/{id}/retry -> resets failed video to pending (attempts=0, last_error cleared).

### UI Elements
- Table: Title | Status (badge) | Attempts | Last Error (truncated tooltip) | Actions.
- Filters (optional): status dropdown.
- Bulk Retry (future enhancement) for all failed.

### Component Sketch
```tsx
function VideoQueue({channelId}){
  const [videos,setVideos]=useState([])
  const load=()=> fetch(`/api/channels/${channelId}/videos`).then(r=>r.json()).then(setVideos)
  useEffect(load,[channelId])
  const retry=async(id)=>{await fetch(`/api/videos/${id}/retry`,{method:'POST'}); load()}
  return <table>
    <thead><tr><th>Title</th><th>Status</th><th>Attempts</th><th>Error</th><th/></tr></thead>
    <tbody>{videos.map(v=> <tr key={v.id}>
      <td>{v.title}</td>
      <td>{v.status}</td>
      <td>{v.attempts}</td>
      <td title={v.last_error}>{v.last_error?.slice(0,30)}</td>
      <td>{v.status==='failed' && <button onClick={()=>retry(v.id)}>Retry</button>} {v.status==='completed' && <Link href={`/videos/${v.id}`}>View</Link>}</td>
    </tr>)}</tbody>
  </table>
}
```

### Edge Cases
1. Channel with thousands of videos -> paginate (future) or lazy infinite scroll.
2. Long titles -> ellipsis CSS with full title tooltip.
3. Rapid status updates while viewing -> consider polling every 5s or using WebSocket broadcast updates.
4. Retry of non-failed video -> backend returns 409 or 400; disable button proactively.
5. No videos -> empty state message.

### Acceptance Criteria
- Displays accurate statuses matching backend.
- Retry action moves failed video back to pending (reflected after refresh/poll).
- Completed video links to subtitle viewer.

### Definition of Done
- Component integrated under `/channels/[id]` route.
