## NFR: Performance, Reliability, Security

### Performance (TRD 3)
Goal: 400+ videos processed < 15 minutes with 5 workers.

Approach:
- Network-bound operations (yt-dlp) -> concurrency via threads.
- Minimize DB contention (short transactions, bulk insert ingestion).
- Cache channel ingestion intermediate data (avoid repeated yt-dlp calls in same session).
- Measure throughput metric (completed per minute) exposed via Job Monitor.

Benchmarks (Target):
- Ingestion: >= 6–8 videos enumerated/sec.
- Subtitle fetch average < 2s/video (native captions small) -> 5 workers => theoretical 150 videos/10 min.

Optimization Backlog:
- Async subtitle downloads.
- Local caching of previously downloaded subtitle metadata.
- Parallel channel ingestion.

### Reliability
Crash Recovery:
- Startup reset: `processing` -> `pending`.
- Retry attempts reset after restart per TRD to avoid starvation.
- Idempotent channel ingestion & reconciliation step ensures no duplicate or lost completed subtitles.

Failure Budget:
- At most 1 video lost (stuck) per crash; enforced by reset logic.

Monitoring:
- WebSocket status feed.
- Error log counts.

Testing Strategy:
- Simulate forced kill during processing; verify statuses corrected on restart.
- Inject transient network errors to validate exponential backoff.

### Security
Scope is local-only per TRD; minimal controls now.

Baseline Measures:
- No external persistent secrets stored (SQLite local file only).
- Sanitize filenames for zip downloads.
- Escape subtitle content when rendering HTML (prevent injection from malicious caption data).
- Limit path traversal by controlling output dir in settings.

Future Hardening:
- Optional API token or localhost bind restriction.
- Rate limiting & input size caps (channel ingestion bulk).
- Separate service user in Docker (non-root) & read-only FS for frontend container.

### Acceptance Criteria
- Throughput meets target in test run (document actual metrics when measured).
- Restart after abrupt termination leaves queue consistent.
- No obvious XSS when rendering arbitrary subtitle content.

### Definition of Done
- Documented strategies & backlog recorded.
- Basic security hygiene implemented (escaping, filename sanitization).
