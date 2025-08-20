## 1-6 UI: Job Monitor

### Objective
Real-time view of scraping activity: overall job status, active workers, throughput, recent errors (from logs), and queue progress.

### Data Source
WebSocket `GET /jobs/status` streaming JSON frames.

### Expected Payload Example
```json
{
  "status": "running",
  "active_workers": 4,
  "pending": 120,
  "processing": 5,
  "completed": 275,
  "failed": 3,
  "throughput_per_min": 18.4,
  "workers": [
    {"name":"w1","video_id":101,"since":"2025-08-20T12:00:00Z"},
    {"name":"w2","video_id":106,"since":"2025-08-20T12:00:05Z"}
  ],
  "recent_errors": [
    {"video_id":55,"message":"No subtitles","timestamp":"..."}
  ]
}
```

### UI Elements
- Status badge (running/paused/idle).
- Counters with colored chips.
- Progress bar (completed / total = sum counters).
- Worker table (name, video id, elapsed time).
- Recent errors collapsible panel.
- Controls: Start, Pause, Resume (call respective endpoints).

### Component Sketch
```tsx
function JobMonitor(){
  const [data,setData]=useState(null)
  const wsRef = useRef<WebSocket|null>(null)
  useEffect(()=>{
    const ws = new WebSocket('ws://localhost:8000/jobs/status')
    wsRef.current=ws
    ws.onmessage=e=>setData(JSON.parse(e.data))
    return ()=>ws.close()
  },[])
  if(!data) return <p>Connecting...</p>
  const total = data.pending+data.processing+data.completed+data.failed
  const pct = total? Math.round((data.completed/total)*100):0
  return <div>
    <h1>Job Monitor</h1>
    <p>Status: {data.status}</p>
    <p>Progress: {pct}%</p>
    <div>Workers Active: {data.active_workers}</div>
    <ul>{data.workers.map(w=> <li key={w.name}>{w.name}: video {w.video_id}</li>)}</ul>
  </div>
}
```

### Edge Cases
1. WebSocket disconnect -> attempt reconnect with exponential backoff.
2. Large error list -> cap at last N (e.g., 20) client-side.
3. Idle job (no work) -> show message & disable Pause button.
4. Latency spikes -> queue updates still processed sequentially, handle out-of-order frames by simple replacement.
5. Start invoked while running -> display toast "Already running".

### Acceptance Criteria
- UI updates at least every second with fresh counts while running.
- Pause/Resume buttons reflect state transitions within 1s.
- Errors panel shows newly logged errors.

### Definition of Done
- Component integrated & route accessible.
- Manual test with processing workload shows live updates.
