# Video Subtitle Scraper - Deployment Guide

## Quick Start (Docker)

The fastest way to get the application running is using Docker Compose:

```bash
# Clone and navigate to the project
cd video-subtitle-scraper

# Start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Local Development Setup

### Backend Setup (Non-Docker)

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run the backend
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## Environment Configuration

Copy `.env.example` to `.env` and configure as needed:

```bash
cp .env.example .env
```

Key environment variables:
- `DATABASE_URL`: SQLite database path (default: `sqlite:///data/app.db`)
- `NEXT_PUBLIC_API_URL`: Backend API URL for frontend
- `YT_DLP_CONCURRENCY`: Number of parallel workers
- `MAX_RETRIES`: Maximum retry attempts for failed videos

## Docker Services

### Backend Service
- **Port**: 8000
- **Health Check**: `/health` endpoint
- **Database**: SQLite file stored in `./backend/data/`
- **Source Code**: Hot-reload enabled in development

### Frontend Service
- **Port**: 3000
- **Build**: Production-optimized Next.js build
- **API Connection**: Connects to backend service automatically

## Production Deployment

For production deployment:

1. Set `DEBUG=false` in environment
2. Configure appropriate `NEXT_PUBLIC_API_URL`
3. Consider using external database for scaling
4. Set up reverse proxy (nginx) for SSL/domain routing

## Troubleshooting

### Backend not starting
- Check database permissions in `./backend/data/`
- Verify Python 3.12 compatibility
- Check port 8000 availability

### Frontend build issues
- Clear `.next` folder: `rm -rf frontend/.next`
- Verify Node.js version (20+)
- Check network connectivity to backend

### Docker issues
- Rebuild images: `docker-compose build --no-cache`
- Check logs: `docker-compose logs [service]`
- Reset volumes: `docker-compose down -v`

## Database

SQLite database is automatically created on first run at:
- Local: `backend/data/app.db`
- Docker: Mounted volume `./backend/data/app.db`

No manual database setup required - schema is initialized automatically.
