## 1-6 UI: Dashboard

### Objective
Display list of channels with aggregate progress (counts per status) and global progress summary.

### Data Requirements
From `GET /channels` each element must include:
`id, name, url, total_videos, pending, processing, completed, failed, created_at`.

### UI Elements
- Table or cards listing channels.
- Progress bar: completed / total_videos.
- Status badges (pending / processing / failed counts).
- Action buttons: View Queue, Delete Channel.
- Global summary: total channels, total videos, % overall completed.

### Example Progress Computation
```ts
const percent = total_videos ? Math.round((completed / total_videos)*100) : 0
```

### Component Sketch
```tsx
function Dashboard() {
  const [channels,setChannels]=useState([])
  useEffect(()=>{fetch('/api/channels').then(r=>r.json()).then(setChannels)},[])
  return <div className="dash">
    <h1>Channels</h1>
    <table>
      <thead><tr><th>Name</th><th>Progress</th><th>Statuses</th><th>Actions</th></tr></thead>
      <tbody>{channels.map(c=>{
        const donePct = c.total_videos? Math.round((c.completed/c.total_videos)*100):0
        return <tr key={c.id}>
          <td>{c.name||'(unknown)'}</td>
          <td>{donePct}% ({c.completed}/{c.total_videos})</td>
          <td>P:{c.pending} Pr:{c.processing} F:{c.failed}</td>
          <td><Link href={`/channels/${c.id}`}>Open</Link></td>
        </tr>
      })}</tbody>
    </table>
  </div>
}
```

### Edge Cases
1. Channel with zero videos -> show 0%.
2. Missing name (not yet fetched) -> placeholder.
3. Large number of channels -> pagination or virtual list (future enhancement).
4. Delete channel -> confirm then re-fetch list.
5. Timezone display for created_at (optional).

### Acceptance Criteria
- Shows accurate counts & progress after ingestion.
- Refresh (manual or via interval) reflects changes as workers run.
- Handles empty state (zero channels) with call to action to add.

### Definition of Done
- Component implemented & integrated route `/dashboard`.
- Basic styling applied (consistent with app theme).
- Manual test verifying progress updates after processing some videos.