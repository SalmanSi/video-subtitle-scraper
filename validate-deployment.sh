#!/bin/bash

# validate-deployment.sh
# Script to validate the deployment setup

echo "🚀 Validating Video Subtitle Scraper Deployment Setup..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Check if required files exist
required_files=(
    "docker-compose.yml"
    "backend/Dockerfile"
    "frontend/Dockerfile"
    "backend/requirements.txt"
    "frontend/package.json"
    ".env.example"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file missing: $file"
        exit 1
    fi
done

echo "✅ All required files are present"

# Validate docker-compose.yml syntax
if docker-compose config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml syntax is valid"
else
    echo "❌ docker-compose.yml has syntax errors"
    exit 1
fi

# Check if ports are available
check_port() {
    local port=$1
    if lsof -i:$port > /dev/null 2>&1; then
        echo "⚠️  Warning: Port $port is already in use"
        return 1
    else
        echo "✅ Port $port is available"
        return 0
    fi
}

check_port 3000
check_port 8000

echo ""
echo "🎉 Deployment setup validation completed!"
echo ""
echo "To start the application:"
echo "  docker-compose up --build"
echo ""
echo "The application will be available at:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
