# Video Subtitle Scraper Application

## Overview
The Video Subtitle Scraper Application is designed to ingest YouTube channel URLs, extract video links, and scrape subtitles in parallel. The application utilizes SQLite for data persistence and provides a user-friendly interface for managing channels and subtitles.

## Features
- **Channel Ingestion**: Users can add one or more YouTube channel URLs, and the application will extract all video URLs.
- **Queue Management**: The application maintains a queue of videos with statuses (pending, processing, completed, failed).
- **Subtitle Scraping**: The application scrapes subtitles provided by YouTube and stores them in the database.
- **Parallel Scraping**: Multiple workers can scrape subtitles concurrently to improve efficiency.
- **Pause/Resume Functionality**: Users can pause and resume scraping without losing progress.
- **User Interface**: A web-based UI allows users to manage channels, monitor jobs, view subtitles, and download them.

## Technology Stack
- **Backend**: Python 3.12 with FastAPI
- **Database**: SQLite 3
- **Frontend**: Next.js
- **Containerization**: Docker and Docker Compose

## Quick Start (Docker) 🚀

The fastest way to get the application running:

```bash
# Clone and navigate to the project
git clone [repository-url]
cd video-subtitle-scraper

# Start the application
./start.sh
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Getting Started

### Prerequisites
- Docker and Docker Compose (recommended)
- Python 3.12 (for local development)
- Node.js 20+ (for local development)

### Installation

#### Option 1: Docker (Recommended)
```bash
# Validate deployment setup
./validate-deployment.sh

# Start the application
docker-compose up --build
```

#### Option 2: Local Development
```bash
# Setup development environment
./dev-setup.sh

# Start backend (terminal 1)
cd backend
source .venv/bin/activate
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

# Start frontend (terminal 2)
cd frontend
npm run dev
```
   ```
   git clone <repository-url>
   cd video-subtitle-scraper
   ```

2. Set up the backend:
   - Navigate to the backend directory:
     ```
     cd backend
     ```
   - Install dependencies:
     ```
     pip install -r requirements.txt
     ```

3. Set up the frontend:
   - Navigate to the frontend directory:
     ```
     cd ../frontend
     ```
   - Install dependencies:
     ```
     npm install
     ```

4. Build and run the application using Docker:
   ```
   docker-compose up --build
   ```

### Usage
- Access the application at `http://localhost:3000` for the frontend.
- Use the API endpoints to manage channels and subtitles.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.