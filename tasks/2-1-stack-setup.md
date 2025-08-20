# 2-1 Stack Setup

## Objective
Stand up baseline dev environment with Python (FastAPI), Next.js, SQLite, and yt-dlp, dockerized for consistent local & deployment workflows.

## Components
- Backend: Python 3.12 FastAPI + uvicorn.
- Frontend: Next.js 13+ (App Router) TypeScript.
- DB: SQLite (file stored under `backend/data/app.db`).
- Workers run inside same backend container/process initially.

## Backend Local Setup (Non-Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.app:app --reload
```

## Frontend Local Setup
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables (.env.example)
- `DATABASE_URL` (e.g., `sqlite:///data/app.db`)
- Future: `YT_DLP_CONCURRENCY`, etc.

## Docker Backend (Final Form)
Key points: slim base, layer caching for deps, non-root user (future), healthcheck.
```Dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
EXPOSE 8000
CMD ["uvicorn","src.app:app","--host","0.0.0.0","--port","8000"]
```

## Docker Frontend
```Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY app/ ./app/
EXPOSE 3000
CMD ["npm","run","dev"]
```

## docker-compose.yml Highlights
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./backend/src:/app/src", "./backend/data:/app/data"]
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

## Acceptance Criteria
- Both services start via `docker-compose up`.
- API reachable at http://localhost:8000/docs.
- Frontend reachable at http://localhost:3000 and can call backend.

## Definition of Done
- Verified local & Docker flows documented.
- .env.example updated with necessary variables.