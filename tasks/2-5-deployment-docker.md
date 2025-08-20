# Contents of the file: /video-subtitle-scraper/video-subtitle-scraper/tasks/2-5-deployment-docker.md

## 2-5 Deployment (Docker)

### Objective
Containerize backend & frontend with `docker-compose` enabling single-command startup. Align with TRD deployment requirement.

### Folder Layout
```
backend/Dockerfile
frontend/Dockerfile
docker-compose.yml
```

### Backend Production Entrypoint
Use uvicorn directly (sufficient for this scale). Optionally add `--workers` >1 if CPU-bound tasks emerge.

### Sample docker-compose.yml (Production-ish)
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=sqlite:///data/app.db
    volumes:
      - ./backend/data:/app/data
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

### Dev vs Prod Notes
Dev: mount source volumes for hot reload (already shown). Prod: copy code only; possibly use multi-stage build to prune dev deps.

### Building & Running
```bash
docker-compose up --build
```

### Health Checks (Future)
- Add `HEALTHCHECK` in backend Dockerfile hitting `/health` endpoint.

### Logs
`docker-compose logs -f backend` for worker activity.

### Acceptance Criteria
- Single command spins up both services.
- Stopping containers does not lose DB (persistent volume mapped).
- Rebuild picks up code changes.

### Definition of Done
- Verified containers start successfully & UI accessible.