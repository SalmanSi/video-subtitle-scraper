#!/bin/bash

# dev-start.sh - Development mode script with hot reload

echo "🔧 Starting Video Subtitle Scraper in Development Mode..."

# Stop any existing containers
echo "📋 Stopping existing containers..."
docker-compose -f docker-compose.dev.yml down

# Start the application in development mode
echo "🐳 Starting Docker containers with hot reload..."
docker-compose -f docker-compose.dev.yml up --build

echo "✅ Development environment started!"
echo ""
echo "Features enabled:"
echo "🔥 Hot reload for both frontend and backend"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo ""
echo "📊 To view logs: docker-compose -f docker-compose.dev.yml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.dev.yml down"
