#!/bin/bash

# validate-running.sh - Validates that the running Video Subtitle Scraper deployment is working correctly

echo "🔍 Validating Running Video Subtitle Scraper Deployment..."
echo "========================================================="

# Check if Docker is running
echo "🐳 Checking Docker service..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi
echo "✅ Docker is running"

# Check if containers are running
echo ""
echo "📦 Checking containers..."
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ No containers are running. Please run './start.sh' first."
    exit 1
fi

backend_status=$(docker-compose ps backend | grep "Up" | wc -l)
frontend_status=$(docker-compose ps frontend | grep "Up" | wc -l)

if [ "$backend_status" -eq 1 ]; then
    echo "✅ Backend container is running"
else
    echo "❌ Backend container is not running"
    exit 1
fi

if [ "$frontend_status" -eq 1 ]; then
    echo "✅ Frontend container is running"
else
    echo "❌ Frontend container is not running"
    exit 1
fi

# Test backend health endpoint
echo ""
echo "🏥 Testing backend health..."
if curl -s -f http://localhost:8000/health > /dev/null; then
    echo "✅ Backend health check passed"
    health_response=$(curl -s http://localhost:8000/health)
    echo "   Response: $health_response"
else
    echo "❌ Backend health check failed"
    exit 1
fi

# Test backend API root
echo ""
echo "🔧 Testing backend API root..."
if curl -s -f http://localhost:8000 > /dev/null; then
    echo "✅ Backend API root accessible"
else
    echo "❌ Backend API root not accessible"
    exit 1
fi

# Test frontend accessibility
echo ""
echo "📱 Testing frontend accessibility..."
if curl -s -f http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend is not accessible"
    exit 1
fi

# Test database connectivity (by checking channels endpoint)
echo ""
echo "🗄️ Testing database connectivity..."
if curl -s -f http://localhost:8000/api/channels > /dev/null; then
    echo "✅ Database is accessible via API"
else
    echo "❌ Database connection failed"
    exit 1
fi

# Check if data volume is properly mounted
echo ""
echo "💾 Checking data persistence..."
if docker-compose exec -T backend test -d /app/data; then
    echo "✅ Data directory is mounted"
else
    echo "❌ Data directory is not properly mounted"
    exit 1
fi

echo ""
echo "🎉 All validation checks passed!"
echo ""
echo "Your Video Subtitle Scraper deployment is ready!"
echo "================================================="
echo "📱 Frontend:     http://localhost:3000"
echo "🔧 Backend API:  http://localhost:8000"
echo "📚 API Docs:     http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo ""
echo "📊 View logs:    docker-compose logs -f"
echo "🛑 Stop:         docker-compose down"
