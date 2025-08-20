## 1-6 UI: Settings

### Objective
Allow user to view & modify runtime configuration: `max_workers`, `max_retries`, `backoff_factor`, `output_dir` (as defined in TRD settings table). Changes persist to `settings` singleton row.

### API
GET /settings -> `{ max_workers, max_retries, backoff_factor, output_dir }`
POST /settings -> same object (persist & return updated values). Validations: numeric positive, reasonable bounds (`1 <= max_workers <= 20`, `1 <= max_retries <= 10`, `1.0 <= backoff_factor <= 10`).

### UI Elements
- Form fields with labels + inline validation messages.
- Save button disabled while saving or if no changes.
- Toast / banner on success.

### Component Sketch
```tsx
function Settings(){
  const [form,setForm]=useState(null)
  const [dirty,setDirty]=useState(false)
  const [saving,setSaving]=useState(false)
  useEffect(()=>{fetch('/api/settings').then(r=>r.json()).then(d=>setForm(d))},[])
  if(!form) return <p>Loading...</p>
  const update=(k,v)=>{setForm({...form,[k]:v}); setDirty(true)}
  const save=async()=>{setSaving(true); await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(form)}); setSaving(false); setDirty(false)}
  return <div>
    <h1>Settings</h1>
    <label>Max Workers <input type='number' value={form.max_workers} onChange={e=>update('max_workers',Number(e.target.value))}/></label>
    <label>Max Retries <input type='number' value={form.max_retries} onChange={e=>update('max_retries',Number(e.target.value))}/></label>
    <label>Backoff Factor <input type='number' step='0.1' value={form.backoff_factor} onChange={e=>update('backoff_factor',Number(e.target.value))}/></label>
    <label>Output Directory <input value={form.output_dir} onChange={e=>update('output_dir',e.target.value)}/></label>
    <button disabled={!dirty||saving} onClick={save}>{saving?'Saving...':'Save'}</button>
  </div>
}
```

### Edge Cases
1. Invalid numeric entry -> client blocks submission.
2. Backend validation fail (e.g., too high) -> display error from response.
3. Concurrent save from another tab -> latest wins; could refetch after save.
4. Changing `max_workers` might require immediate worker pool resize (optional initial; else require restart message).
5. Output dir not writable -> backend returns error; UI states problem.

### Acceptance Criteria
- Current persisted settings displayed on load.
- Editing & saving updates DB; subsequent GET returns new values.
- Invalid values produce validation messages.

### Definition of Done
- Component integrated; tests (if using React Testing Library) for form state changes.