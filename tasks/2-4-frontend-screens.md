## 2-4 Frontend Screens

### Objective
Implement all UI surfaces (TRD 2.4) using Next.js components: Onboarding, Dashboard, Video Queue, Job Monitor, Subtitle Viewer, Batch Download, Settings.

### Routing
- `/` -> Onboarding (Add Channels)
- `/dashboard` -> Channels list
- `/channels/[id]` -> Video Queue + Batch Download button
- `/videos/[id]` -> Subtitle Viewer
- `/monitor` -> Job Monitor
- `/settings` -> Settings

### Shared Concerns
- API base path via environment variable (e.g., NEXT_PUBLIC_API_URL) or relative proxy.
- Simple global fetch wrapper handling JSON & errors.
- Basic layout component for navigation.

### Components Mapping (See individual task files for detailed specs)
- ChannelOnboarding (Add Channel UI)
- Dashboard
- VideoQueue
- JobMonitor
- SubtitleViewer
- BatchDownloadButton (embedded in channel page)
- Settings

### Error Handling Strategy
- Fetch wrapper returns `{error}`; components show inline alert.
- WebSocket reconnect backoff for Job Monitor.

### Performance Considerations
- Poll intervals (Video Queue) minimal (5s) or WebSocket future.
- Avoid huge DOM for large video lists (pagination backlog item).

### Acceptance Criteria
- Navigation among routes works & state updates reflect backend progression.
- All core operations (add channel, view progress, view subtitles, download, adjust settings, monitor job) functional.
- Basic responsive layout (mobile vertical stacking).

### Definition of Done
- All pages implemented & linked in nav.
- Local manual run passes smoke test scenario end-to-end.