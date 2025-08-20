# Contents of /video-subtitle-scraper/video-subtitle-scraper/README.md

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
- **Backend**: Python 3.12 with FastAPI or Flask
- **Database**: SQLite 3
- **Frontend**: Next.js
- **Containerization**: Docker and Docker Compose

## Getting Started

### Prerequisites
- Python 3.12
- Node.js (for frontend)
- Docker and Docker Compose

### Installation
1. Clone the repository:
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