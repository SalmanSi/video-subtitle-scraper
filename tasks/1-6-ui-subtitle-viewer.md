## 1-6 UI: Subtitle Viewer

### Objective
Display subtitle content for a single video with search + download `.txt` option.

### API
GET /videos/{id}/subtitles -> `{ video_id, language, content }`
GET /videos/{id}/subtitles/download -> text/plain attachment.

### Features
- Show video title (fetched alongside or separate endpoint for video details).
- Scrollable mono-spaced text area.
- Client-side search (highlight matches) with incremental scroll navigation.
- Download button.

### Component Sketch
```tsx
function SubtitleViewer({videoId}){
  const [data,setData]=useState(null)
  const [query,setQuery]=useState('')
  useEffect(()=>{fetch(`/api/videos/${videoId}/subtitles`).then(r=>r.json()).then(setData)},[videoId])
  if(!data) return <p>Loading...</p>
  const highlighted = highlight(data.content, query)
  return <div>
    <h1>Subtitles ({data.language})</h1>
    <input placeholder='Search text' value={query} onChange={e=>setQuery(e.target.value)}/>
    <pre className='subs' dangerouslySetInnerHTML={{__html:highlighted}} />
    <button onClick={()=> window.location=`/api/videos/${videoId}/subtitles/download`}>Download .txt</button>
  </div>
}
```

### highlight Helper
```ts
function highlight(content:string, q:string){
 if(!q) return escape(content)
 const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi')
 return escape(content).replace(re, m=>`<mark>${m}</mark>`)
}
```

### Edge Cases
1. Video has no subtitles -> API 404 -> show message + link back.
2. Very large subtitle (>100k chars) -> still render; consider virtualized viewer future.
3. Search term not found -> show "0 matches".
4. Special HTML characters -> escape before highlight.
5. API latency -> show skeleton loader.

### Acceptance Criteria
- Subtitle content displays correctly & is searchable client-side.
- Download button returns matching text file identical to DB content.
- Handles missing subtitles gracefully.

### Definition of Done
- Component integrated in route accessible from video queue (e.g., click video row).
