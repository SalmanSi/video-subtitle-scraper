#!/bin/bash

# start.sh - Script to start the Video Subtitle Scraper application

echo "🚀 Starting Video Subtitle Scraper Application..."

# Stop any existing containers
echo "📋 Stopping existing containers..."
docker-compose down

# Start the application with Docker Compose
echo "🐳 Building and starting Docker containers..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Check service health
echo "🔍 Checking service health..."
echo "Backend health:"
curl -f http://localhost:8000/health || echo "❌ Backend not ready"

echo -e "\nFrontend accessibility:"
curl -f http://localhost:3000 || echo "❌ Frontend not ready"

echo -e "\n✅ Application started!"
echo ""
echo "Access the application at:"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "🏥 Health check: http://localhost:8000/health"
echo ""
echo "📊 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
