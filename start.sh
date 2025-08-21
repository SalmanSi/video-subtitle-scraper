#!/bin/bash

# start.sh - Simple script to start the Video Subtitle Scraper application

echo "🚀 Starting Video Subtitle Scraper Application..."

# Check if .env file exists, if not copy from example
if [ ! -f .env ]; then
    echo "📋 Creating .env file from .env.example..."
    cp .env.example .env
    echo "ℹ️  Please review and modify .env file if needed"
fi

# Start the application with Docker Compose
echo "🐳 Starting Docker containers..."
docker-compose up --build

echo "✅ Application started!"
echo ""
echo "Access the application at:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
